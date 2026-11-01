"""Compact-index information boundaries, conservative decision rule and encrypted collection."""
import contextlib
import copy
import importlib.util
import io
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "experiments/scientific-confidence-v6/experiment.py"
SPEC = importlib.util.spec_from_file_location("confidence_v6", SOURCE)
assert SPEC and SPEC.loader
e = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(e)


def condition_state(state, arm):
    result = copy.deepcopy(state)
    if arm != "versioned_checklist":
        result["entries"] = [r for r in result["entries"] if r["status"] == "active"]
    if arm != "compact_index":
        result["identity_index"] = []
    return result


class ScientificConfidenceV6Tests(unittest.TestCase):
    def test_index_lifecycle_and_source_blind_calculator(self):
        cases, gold = e.make_cases("main", 8)
        for case, truth in zip(cases, gold):
            cps = truth["checkpoints"]
            sid = cps[0]["state"]["entries"][0]["study_id"]
            for cp in cps:
                compact = condition_state(cp["state"], "compact_index")
                self.assertEqual(e.calculate(compact), e.v1.oracle(e.active_case(cp["state"], case["hypotheses"])))
                self.assertTrue(e.index_diagnostic(compact, cp)["index_source_faithful"])
                self.assertTrue(e.state_diagnostic(compact, cp, case["hypotheses"])["active_source_faithful"])
                active_ids = {r["study_id"] for r in compact["entries"]}
                index_ids = {r["study_id"] for r in compact["identity_index"]}
                self.assertFalse(active_ids & index_ids)
                self.assertLessEqual(len(active_ids | index_ids), 5)
                for row in compact["identity_index"]:
                    self.assertEqual(set(row), {"study_id", "current_revision", "status", "identity_refs"})
            self.assertNotIn(sid, {r["study_id"] for r in cps[2]["state"]["identity_index"]})
            item = next(r for r in cps[5]["state"]["identity_index"] if r["study_id"] == sid)
            self.assertEqual(item["current_revision"], 2)
            self.assertTrue({"D1", "D4", "D5"} <= set(item["identity_refs"]))
            self.assertNotIn(sid, {r["study_id"] for r in cps[10]["state"]["identity_index"]})
            item = next(r for r in cps[12]["state"]["identity_index"] if r["study_id"] == sid)
            self.assertEqual(item["current_revision"], 4)
            self.assertTrue({"D1", "D4", "D5", "D13", "D14"} <= set(item["identity_refs"]))
            bad = condition_state(cps[5]["state"], "compact_index")
            before = e.calculate(bad)
            bad["identity_index"][0]["study_id"] = "incorrect"
            self.assertEqual(before, e.calculate(bad))
            self.assertFalse(e.index_diagnostic(bad, cps[5])["index_source_faithful"])

    def test_same_initial_information_fresh_seeds_and_gold_isolation(self):
        cases, gold = e.make_cases("main", 96)
        self.assertEqual((cases, gold), e.make_cases("main", 96))
        for case, truth in zip(cases, gold):
            initial = case["initial_state"]
            self.assertEqual(initial["record"]["identity_index"], [])
            self.assertTrue(e.state_diagnostic(initial["record"], truth["checkpoints"][0], case["hypotheses"])["active_source_faithful"])
            requests = []
            for arm in e.ARMS:
                request = e.payload(case, 1, arm, initial)
                request["messages"][0]["content"] = request["messages"][0]["content"].replace(e.RETENTION[arm], "POLICY")
                requests.append(request)
            self.assertTrue(all(p == requests[0] for p in requests))
            text = json.dumps(requests[0])
            for forbidden in ("true_h", "future_outcome", "checkpoints", "Reference state; evaluator only.", "D13", "D14", "D15"):
                self.assertNotIn(forbidden, text)
        schedules = [(20261030, 32), (20261031, 32), (90261031, 4),
                     (20371101, 64), (20481101, 32), (90371101, 4), (90481101, 2),
                     (20591203, 32), (90591203, 2), (20691203, 64), (90691203, 2)]
        previous = {s + 7919 * i for s, count in schedules for i in range(count)}
        main = {e.SEEDS["main"] + 7919 * i for i in range(96)}
        dev = {e.SEEDS["development"] + 7919 * i for i in range(4)}
        self.assertFalse(previous & (main | dev) or main & dev)

    def test_noninferiority_boundary_is_not_zero_width_and_cost_ratio(self):
        self.assertAlmostEqual(e.binomial_upper(0, 96), 1 - .05 ** (1 / 96), places=14)
        self.assertGreater(e.binomial_upper(0, 32), .05)
        self.assertLess(e.binomial_upper(1, 96), .05)
        self.assertGreater(e.binomial_upper(2, 96), .05)
        self.assertEqual(e.binomial_upper(96, 96), 1)
        ratio = e.paired_cost_ratio([(1., 2.), (3., 6.)])
        self.assertEqual(ratio["ratio_of_mean_costs"], .5)
        self.assertEqual(ratio["bootstrap_95_percentile_interval"], [.5, .5])
        self.assertIsNone(e.paired_cost_ratio([(0., 2.)]))

    def test_development_gate_checks_transport_not_accuracy(self):
        calls = [{"case_id": f"DEV{i:03d}", "arm": arm, "stage": str(step), "cost_usd": .001,
                  "response": {"stop_reason": "tool_use", "content": [{"type": "tool_use",
                    "name": "submit_state", "input": {"reasoning_error": True}}]}}
                 for i in range(4) for arm in e.ARMS for step in e.PAID_STEPS]
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

    def test_full_mocked_run_primary_decision_integrity_and_replay_guard(self):
        reference = {}
        def provider(request, timeout):
            p = json.loads(request.data)
            text = p["messages"][0]["content"]
            cid, step = re.search(r"Case (DEV\d+|TEST\d+); update (\d+)\.", text).groups()
            step = int(step)
            arm = next(a for a in e.ARMS if e.RETENTION[a] in text)
            state = condition_state(reference[cid][step]["state"], arm)
            if arm == "active_checklist" and cid.startswith("TEST") and step == 10:
                state["entries"][0]["study_id"] = "wrong-canonical-id"
            output = 100 if arm == "versioned_checklist" else 50
            response = {"stop_reason": "tool_use", "content": [{"type": "tool_use", "name": "submit_state", "input": state}],
                        "usage": {"input_tokens": 100, "output_tokens": output}}
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
            self.assertEqual(request.call_count, 156)
            e.collect(out, 5, "main")
            self.assertEqual(request.call_count, 234)
            summary = json.loads((out / "summary.json").read_text())
            self.assertTrue(summary["complete_call_and_record_keys"])
            decision = summary["decision"]
            self.assertTrue(decision["eligible_complete_run"])
            self.assertTrue(decision["compact_superior_to_active"])
            self.assertTrue(decision["at_least_10_percent_cheaper_than_history"])
            # Two tied cases are insufficient evidence of noninferiority.
            self.assertFalse(decision["compact_noninferior_to_history"])
            self.assertFalse(decision["all_criteria_met"])
            self.assertEqual(decision["noninferiority"]["worse_trajectories"], 0)
            self.assertEqual(summary["comparisons"]["compact_vs_active"]["post_active_failure"]["mean_delta"], -.25)
            audit_spec = importlib.util.spec_from_file_location("audit_v6", out / "audit_saved_run.py")
            module = importlib.util.module_from_spec(audit_spec)
            audit_spec.loader.exec_module(module)
            module.audit(out)
            integrity = json.loads((out / "integrity_audit.json").read_text())
            self.assertEqual(integrity["requests_and_state_handoffs_verified"], 234)
            self.assertEqual(integrity["conditions_per_group"], 3)
            self.assertEqual(integrity["matched_initial_request_groups"], 6)
            with self.assertRaises(ValueError):
                e.collect(out, 5, "main")
            with self.assertRaises(ValueError):
                e.generate(out, 2)
            self.assertEqual(request.call_count, 234)

    def test_encryption_roundtrip_and_authentication_failure(self):
        spec = importlib.util.spec_from_file_location("seal_v6", SOURCE.parent / "seal_artifact.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            private, public = root / "private.pem", root / "public.pem"
            subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private)], check=True, capture_output=True)
            subprocess.run(["openssl", "pkey", "-in", str(private), "-pubout", "-out", str(public)], check=True, capture_output=True)
            source, recovered = root / "source.zip", root / "recovered.zip"
            source.write_bytes(b"private synthetic experiment record\x00" * 100)
            module.seal(source, public, root / "sealed")
            self.assertNotIn(source.read_bytes(), (root / "sealed/raw.enc").read_bytes())
            module.unseal(root / "sealed", private, recovered)
            self.assertEqual(source.read_bytes(), recovered.read_bytes())
            data = bytearray((root / "sealed/raw.enc").read_bytes())
            data[-1] ^= 1
            (root / "sealed/raw.enc").write_bytes(data)
            with self.assertRaises(ValueError):
                module.unseal(root / "sealed", private, root / "tampered.zip")
            self.assertFalse((root / "tampered.zip").exists())


if __name__ == "__main__":
    unittest.main()
