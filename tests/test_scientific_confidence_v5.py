"""Verified-start, amendment, endpoint and paid-collection boundaries."""
import contextlib
import copy
import importlib.util
import io
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = (Path(__file__).resolve().parents[1] / "experiments"
          / "scientific-confidence-v5" / "experiment.py")
SPEC = importlib.util.spec_from_file_location("scientific_confidence_v5", SOURCE)
assert SPEC and SPEC.loader
e = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(e)


class ScientificConfidenceV5Tests(unittest.TestCase):
    def test_verified_initial_records_and_equal_information(self):
        cases, gold = e.make_cases("main", 64)
        for case, truth in zip(cases, gold):
            state = case["initial_state"]
            self.assertTrue(e.state_diagnostic(state["record"], truth["checkpoints"][0], case["hypotheses"])["active_source_faithful"])
            self.assertEqual(state["derived_beliefs"], e.v1.oracle(e.active_case(state["record"], case["hypotheses"])))
            self.assertTrue(all(row["status"] == "active" for row in state["record"]["entries"]))
            payloads = []
            for arm in e.ARMS:
                p = e.payload(case, 1, arm, state)
                p["messages"][0]["content"] = p["messages"][0]["content"].replace(e.RETENTION[arm], "POLICY")
                payloads.append(p)
            self.assertEqual(payloads[0], payloads[1])
            text = json.dumps(payloads[0])
            for forbidden in ("true_h", "future_outcome", "checkpoints", "Reference state; evaluator only.", "D13", "D14", "D15"):
                self.assertNotIn(forbidden, text)
        with self.assertRaises(ValueError):
            e.payload(cases[0], 0, e.ARMS[0], cases[0]["initial_state"])
        later = json.dumps(e.payload(cases[0], 5, e.ARMS[0], {"own": "SENTINEL"}))
        self.assertIn("SENTINEL", later)
        self.assertNotIn("Verified initial record:", later)
        self.assertEqual((cases, gold), e.make_cases("main", 64))

    def test_fresh_seed_schedules(self):
        schedules = [(20261030, 32), (20261031, 32), (90261031, 4),
                     (20371101, 64), (20481101, 32), (90371101, 4), (90481101, 2),
                     (20591203, 32), (90591203, 2)]
        previous = {seed + 7919 * i for seed, count in schedules for i in range(count)}
        main = {e.SEEDS["main"] + 7919 * i for i in range(64)}
        development = {e.SEEDS["development"] + 7919 * i for i in range(2)}
        self.assertFalse(main & development or previous & (main | development))

    def test_reference_amendments_and_numerical_consequences(self):
        cases, gold = e.make_cases("main", 64)
        leveraged = 0
        for case, truth in zip(cases, gold):
            cps = truth["checkpoints"]
            sid = cps[0]["state"]["entries"][0]["study_id"]
            for cp in cps:
                self.assertEqual(e.calculate(cp["state"]), e.v1.oracle(e.active_case(cp["state"], case["hypotheses"])))
                self.assertEqual(e.calculate(cp["state"])["posterior"], cp["posterior"])
            versions = {r["revision"]: r for r in cps[11]["state"]["entries"] if r["study_id"] == sid}
            self.assertEqual({k: r["status"] for k, r in versions.items()},
                             {1: "withdrawn", 2: "withdrawn", 3: "superseded", 4: "active"})
            self.assertTrue(all(r["status"] == "withdrawn" for r in cps[12]["state"]["entries"] if r["study_id"] == sid))
            self.assertEqual(cps[12]["posterior"], cps[13]["posterior"])
            bad = copy.deepcopy(cps[11]["state"])
            obsolete = copy.deepcopy(versions[3])
            obsolete.update(study_id="unresolved-alias", status="active")
            bad["entries"].append(obsolete)
            answer = e.calculate(bad)
            if max(abs(answer["posterior"][h] - cps[11]["posterior"][h]) for h in e.HIDS) >= .05:
                leveraged += 1
            self.assertIn("extra_active_unit", e.state_diagnostic(bad, cps[11], case["hypotheses"])["problems"])
        self.assertGreater(leveraged, 0)

    def test_development_gate_ignores_accuracy_but_checks_keys_and_truncation(self):
        calls = [{"case_id": f"DEV{i:03d}", "arm": arm, "stage": str(step), "cost_usd": .001,
                  "response": {"stop_reason": "tool_use", "content": [{"type": "tool_use",
                    "name": "submit_state", "input": {"reasoning_error": True}}]}}
                 for i in range(2) for arm in e.ARMS for step in e.PAID_STEPS]
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            def save():
                (out / "calls.jsonl").write_text("\n".join(json.dumps(c) for c in calls))
            save()
            self.assertTrue(e.gate(out)["passed"])
            calls[0]["response"]["stop_reason"] = "max_tokens"
            save()
            self.assertFalse(e.gate(out)["passed"])
            calls[0]["response"]["stop_reason"] = "tool_use"
            calls[0]["stage"] = calls[1]["stage"]
            save()
            self.assertFalse(e.gate(out)["passed"])

    def test_complete_mocked_collection_budget_replay_and_primary_endpoint(self):
        reference = {}
        first_requests = {}
        def provider(request, timeout):
            p = json.loads(request.data)
            text = p["messages"][0]["content"]
            cid, step = re.search(r"Case (DEV\d+|TEST\d+); update (\d+)\.", text).groups()
            step = int(step)
            arm = "active_checklist" if e.RETENTION["active_checklist"] in text else "versioned_checklist"
            if step == 1:
                first_requests[cid, arm] = text.replace(e.RETENTION[arm], "POLICY")
            state = copy.deepcopy(reference[cid][step]["state"])
            if arm == "active_checklist":
                state["entries"] = [r for r in state["entries"] if r["status"] == "active"]
                if cid.startswith("TEST") and step == 10:
                    state["entries"][0]["study_id"] = "wrong-canonical-id"
            response = {"stop_reason": "tool_use", "content": [{"type": "tool_use", "name": "submit_state", "input": state}],
                        "usage": {"input_tokens": 100, "output_tokens": 50}}
            return io.BytesIO(json.dumps(response).encode())
        with (tempfile.TemporaryDirectory() as directory,
              patch.dict(e.v1.os.environ, {"ANTHROPIC_API_KEY": "test-placeholder"}),
              patch.object(e.v1.urllib.request, "urlopen", side_effect=provider) as request,
              contextlib.redirect_stdout(io.StringIO())):
            out = Path(directory) / "freeze"
            e.generate(out, 2)
            for g in json.loads((out / "gold.json").read_text()):
                reference[g["case_id"]] = g["checkpoints"]
            collector = e.Collector(out, .000001)
            with self.assertRaises(RuntimeError):
                collector.call("test", "test", "test", {"max_tokens": 4096})
            request.assert_not_called()
            self.assertTrue(collector.stop)
            e.collect(out, 5, "development")
            self.assertEqual(request.call_count, 52)
            e.collect(out, 5, "main")
            self.assertEqual(request.call_count, 104)
            for cid in reference:
                self.assertEqual(first_requests[cid, e.ARMS[0]], first_requests[cid, e.ARMS[1]])
            summary = json.loads((out / "summary.json").read_text())
            self.assertTrue(summary["complete_call_and_record_keys"])
            self.assertTrue(summary["starting_states_verified"])
            self.assertAlmostEqual(summary["recorded_cost_usd"], 104 * .00105)
            primary = summary["comparisons"]["primary_post_active_failure"]
            self.assertEqual(primary["mean_delta"], -.25)
            self.assertEqual(primary["n_paired_cases"], 2)
            self.assertEqual(primary["bootstrap_95_percentile_interval"], [-.25, -.25])
            self.assertEqual(summary["conditions"]["active_checklist"]["post_reinstatement"]["active_source_faithful"], 6)
            self.assertLess(summary["conditions"]["active_checklist"]["mean_posterior_loss"], 1e-20)
            e.report(out)
            self.assertEqual(summary, json.loads((out / "summary.json").read_text()))
            with self.assertRaises(ValueError):
                e.collect(out, 5, "main")
            with self.assertRaises(ValueError):
                e.generate(out, 2)
            self.assertEqual(request.call_count, 104)
            (out / "cases.json").write_text("[]")
            with self.assertRaises(ValueError):
                e.report(out)


if __name__ == "__main__":
    unittest.main()
