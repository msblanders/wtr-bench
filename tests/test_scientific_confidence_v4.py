"""Numerical, provenance, information-boundary, and collection checks for v4."""
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
          / "scientific-confidence-v4" / "experiment.py")
SPEC = importlib.util.spec_from_file_location("scientific_confidence_v4", SOURCE)
assert SPEC and SPEC.loader
e = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(e)


class ScientificConfidenceV4Tests(unittest.TestCase):
    def test_reference_calculation_and_neutral_updates(self):
        cases, gold = e.make_cases("main", 8)
        for case, g in zip(cases, gold):
            previous = None
            for cp in g["checkpoints"]:
                computed = e.calculate(cp["state"])
                self.assertEqual(computed, e.v1.oracle(e.active_case(cp["state"], case["hypotheses"])))
                self.assertEqual(computed["posterior"], cp["posterior"])
                diagnostic = e.state_diagnostic(cp["state"], cp, case["hypotheses"])
                self.assertTrue(diagnostic["active_source_faithful"])
                self.assertTrue(diagnostic["full_revision_history_faithful"])
                if cp["event"] in ("alias_duplicate", "stale_superseded", "stale_withdrawn", "review"):
                    self.assertEqual(computed, previous)
                previous = computed

    def test_correction_withdrawal_scope_and_reinstatement_semantics(self):
        _, gs = e.make_cases("main", 1)
        cps = gs[0]["checkpoints"]
        first_id = cps[0]["state"]["entries"][0]["study_id"]
        def versions(step, sid):
            return {r["revision"]: r for r in cps[step]["state"]["entries"] if r["study_id"] == sid}
        self.assertEqual(versions(2, first_id)[1]["status"], "superseded")
        self.assertEqual(versions(2, first_id)[2]["status"], "active")
        self.assertTrue(all(r["status"] == "withdrawn" for r in versions(5, first_id).values()))
        self.assertTrue(all(r["status"] == "withdrawn" for r in versions(7, first_id).values()))
        self.assertEqual(versions(10, first_id)[3]["status"], "active")
        self.assertEqual(versions(10, first_id)[2]["status"], "withdrawn")
        subid = next(r["study_id"] for r in cps[3]["state"]["entries"] if r["study_id"].endswith("/cohort-b"))
        self.assertEqual(versions(3, subid)[1]["context"], "A")
        self.assertEqual(versions(6, subid)[2]["context"], "B")
        self.assertTrue(all(r["status"] == "withdrawn" for r in versions(9, subid).values()))
        parent = subid.split("/")[0] + "/main"
        self.assertEqual(versions(9, parent)[1]["status"], "active")
        self.assertEqual(len([r for r in cps[11]["state"]["entries"] if r["status"] == "active"]), 4)

    def test_solver_does_not_resolve_aliases_or_repair_reactivated_history(self):
        cases, gs = e.make_cases("main", 1)
        cp = gs[0]["checkpoints"][5]
        bad = copy.deepcopy(cp["state"])
        withdrawn = next(r for r in bad["entries"] if r["status"] == "withdrawn")
        withdrawn["status"] = "active"
        wrong = e.calculate(bad)
        self.assertGreater(e.v1.squared_distance(wrong["posterior"], cp["posterior"]), 1e-12)
        d = e.state_diagnostic(bad, cp, cases[0]["hypotheses"])
        self.assertIn("inactive_revision_reactivated", d["problems"])
        good = copy.deepcopy(gs[0]["checkpoints"][0]["state"])
        duplicate = copy.deepcopy(good["entries"][0])
        duplicate["study_id"] = "unresolved-alias"
        good["entries"].append(duplicate)
        self.assertNotEqual(e.calculate(good)["posterior"], gs[0]["checkpoints"][0]["posterior"])
        duplicate["study_id"] = good["entries"][0]["study_id"]
        with self.assertRaises(ValueError):
            e.calculate(good)

    def test_inactive_history_does_not_contribute_likelihood(self):
        cases, gs = e.make_cases("main", 1)
        cp = gs[0]["checkpoints"][10]
        active = copy.deepcopy(cp["state"])
        active["entries"] = [r for r in active["entries"] if r["status"] == "active"]
        self.assertEqual(e.calculate(active), e.calculate(cp["state"]))
        diagnostic = e.state_diagnostic(active, cp, cases[0]["hypotheses"])
        self.assertTrue(diagnostic["active_source_faithful"])
        self.assertFalse(diagnostic["full_revision_history_faithful"])
        damaged = copy.deepcopy(cp["state"])
        next(r for r in damaged["entries"] if r["status"] == "active")["predicted_means"]["H1"] += 2
        self.assertFalse(e.state_diagnostic(damaged, cp, cases[0]["hypotheses"])["active_source_faithful"])

    def test_same_schema_and_no_reference_state_in_payload(self):
        case, gold = e.make_cases("main", 1)
        schemas = []
        previous = {"sentinel": "OWN-STATE"}
        for arm in e.ARMS:
            payload = e.payload(case[0], 4, arm, previous)
            text = json.dumps(payload)
            schemas.append(payload["tools"][0]["input_schema"])
            self.assertIn("OWN-STATE", text)
            self.assertNotIn("Reference state; evaluator only.", text)
            for forbidden in ("true_h", "future_outcome", "gold.json", "checkpoints"):
                self.assertNotIn(forbidden, text)
        self.assertEqual(schemas[0], schemas[1])
        self.assertEqual(schemas[1], schemas[2])
        self.assertEqual(e.make_cases("main", 1), (case, gold))
        old_seeds = [(20261030, 32), (20261031, 32), (90261031, 4),
                     (20371101, 64), (20481101, 32), (90371101, 4), (90481101, 2)]
        prior_draws = {s + 7919 * i for s, size in old_seeds for i in range(size)}
        new = [{s + 7919 * i for i in range(32)} for s in e.SEEDS.values()]
        self.assertFalse(new[0] & new[1])
        self.assertFalse(prior_draws & (new[0] | new[1]))

    def test_gate_accepts_reasoning_errors_but_rejects_truncation(self):
        records = [{"case_id": "DEV000", "arm": "active_checklist", "stage": str(i),
                    "cost_usd": .001, "response": {"stop_reason": "tool_use", "content": [
                        {"type": "tool_use", "name": "submit_state", "input": {"wrong": True}}]}}
                   for i in range(72)]
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            def save():
                (out / "calls.jsonl").write_text("\n".join(json.dumps(r) for r in records))
            save()
            self.assertTrue(e.gate(out)["passed"])
            records[0]["response"]["stop_reason"] = "max_tokens"
            save()
            self.assertFalse(e.gate(out)["passed"])

    def test_budget_and_split_collection(self):
        reference = {}
        def provider(request, timeout):
            p = json.loads(request.data)
            cid, step = re.search(r"Case (DEV\d+|TEST\d+); update (\d+)\.", p["messages"][0]["content"]).groups()
            state = copy.deepcopy(reference[cid][int(step)]["state"])
            if e.RETENTION["active_checklist"] in p["messages"][0]["content"]:
                state["entries"] = [r for r in state["entries"] if r["status"] == "active"]
            response = {"stop_reason": "tool_use", "content": [
                {"type": "tool_use", "name": "submit_state", "input": state}],
                "usage": {"input_tokens": 100, "output_tokens": 50}}
            return io.BytesIO(json.dumps(response).encode())
        with (tempfile.TemporaryDirectory() as directory,
              patch.dict(e.v1.os.environ, {"ANTHROPIC_API_KEY": "test-placeholder"}),
              patch.object(e.v1.urllib.request, "urlopen", side_effect=provider) as request,
              contextlib.redirect_stdout(io.StringIO())):
            out = Path(directory) / "freeze"
            e.generate(out, 1)
            for g in json.loads((out / "gold.json").read_text()):
                reference[g["case_id"]] = g["checkpoints"]
            collector = e.Collector(out, 0.000001)
            with self.assertRaises(RuntimeError):
                collector.call("test", "test", "test", {"max_tokens": 4096})
            request.assert_not_called()
            self.assertTrue(collector.stop)
            e.collect(out, 5, "development")
            self.assertEqual(request.call_count, 72)
            e.collect(out, 5, "main")
            self.assertEqual(request.call_count, 108)
            summary = json.loads((out / "summary.json").read_text())
            self.assertAlmostEqual(summary["recorded_cost_usd"], 108 * .00105)
            for arm in e.ARMS:
                self.assertEqual(summary["conditions"][arm]["active_source_faithful"], 12)
                self.assertLess(summary["conditions"][arm]["mean_posterior_loss"], 1e-20)
            with self.assertRaises(ValueError):
                e.collect(out, 5, "main")
            self.assertEqual(request.call_count, 108)
            with self.assertRaises(ValueError):
                e.generate(out, 1)


if __name__ == "__main__":
    unittest.main()
