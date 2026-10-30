"""Meaningful boundary and numerical checks for the v2 representation/calculation split."""
import contextlib
import copy
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = (Path(__file__).resolve().parents[1] / "experiments"
          / "scientific-confidence-v2" / "experiment.py")
SPEC = importlib.util.spec_from_file_location("scientific_confidence_v2", SOURCE)
assert SPEC and SPEC.loader
e = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(e)


def reference_table(case):
    """Test-only extraction from known inputs, never called by collection."""
    hs = case["hypotheses"]
    def means(row):
        return {h["id"]: h["means"][row["design"] + "_" + row["context"]] for h in hs}
    return {"priors": {h["id"]: h["prior"] for h in hs},
            "studies": [{k: v for k, v in s.items() if k != "report_id"}
                        | {"predicted_means": means(s)} for s in e.v1.unique_studies(case)],
            "future_study": case["future_study"] | {"predicted_means": means(case["future_study"])}}


class ScientificConfidenceV2Tests(unittest.TestCase):
    def test_calculator_matches_independent_existing_oracle(self):
        for case in e.make_cases("main", 32)[0]:
            computed = e.calculate(reference_table(case))
            expected = e.v1.oracle(case)
            for h in e.HIDS:
                self.assertAlmostEqual(computed["posterior"][h], expected["posterior"][h], places=12)
            self.assertAlmostEqual(computed["future_probability"], expected["future_probability"], places=12)

    def test_wrong_mapping_survives_calculator_and_is_flagged_separately(self):
        case = e.make_cases("main", 1)[0][0]
        table = reference_table(case)
        good = e.calculate(table)
        self.assertTrue(e.source_diagnostic(table, case)["source_faithful"])
        table["studies"][0]["predicted_means"]["H1"] += 2
        wrong = e.calculate(table)
        self.assertGreater(abs(wrong["posterior"]["H1"] - good["posterior"]["H1"]), 1e-8)
        self.assertFalse(e.source_diagnostic(table, case)["source_faithful"])

    def test_duplicate_handling_and_inconsistent_rows(self):
        table = reference_table(e.make_cases("main", 1)[0][0])
        original = e.calculate(table)
        table["studies"].append(copy.deepcopy(table["studies"][0]))
        self.assertEqual(e.calculate(table), original)
        table["studies"][-1]["estimate"] += 1
        with self.assertRaises(ValueError):
            e.calculate(table)

    def test_manual_failure_does_not_hide_valid_calculator_output(self):
        cases, gold = e.make_cases("main", 1)
        table = reference_table(cases[0])
        table.update(probabilities={"H1": 0.9, "H2": 0.8, "H3": 0.7}, future_probability=0.5)
        record = {"kind": "ledger_worksheet", "data": table}
        manual = e.score_record(record, "ledger_manual", cases[0], gold[0])
        computed = e.score_record(record, "ledger_calculated", cases[0], gold[0])
        self.assertFalse(manual["valid"])
        self.assertEqual(manual["posterior_loss"], 2)
        self.assertTrue(computed["valid"])
        self.assertLess(computed["posterior_loss"], 1e-20)

    def test_development_gate_ignores_accuracy_and_catches_cutoff(self):
        records = []
        for i in range(4):
            for arm, stages in (("checklist", ("prepare", "verbal", "worksheet")),
                                ("audit", ("prepare", "verbal")),
                                ("ledger", ("prepare", "worksheet"))):
                for stage in stages:
                    name = "submit_ledger" if stage == "prepare" else (
                        "submit_worksheet" if stage == "worksheet" else "submit_assessment")
                    response = {"stop_reason": "tool_use", "content": [{
                        "type": "tool_use", "name": name, "input": {"deliberately": "wrong"}}]}
                    records.append({"case_id": f"DEV{i:03d}", "arm": arm,
                                    "stage": stage, "response": response})
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            def save():
                (out / "calls.jsonl").write_text("\n".join(json.dumps(r) for r in records))
            save()
            self.assertTrue(e.development_gate(out)["passed"])
            records[0]["response"]["stop_reason"] = "max_tokens"
            save()
            self.assertFalse(e.development_gate(out)["passed"])

    def test_seed_disjointness_and_gold_exclusion(self):
        old = {e.v1.SEED + 7919 * i for i in range(32)}
        dev = {e.SEEDS["development"] + 7919 * i for i in range(4)}
        main = {e.SEEDS["main"] + 7919 * i for i in range(32)}
        self.assertFalse(old & dev or old & main or dev & main)
        case = e.make_cases("main", 1)[0][0]
        for arm in ("checklist", "audit", "ledger"):
            payload = e.preparation(case, arm)
            self.assertEqual(payload["max_tokens"], 4096)
            for forbidden in ("true_h", "future_outcome", "gold.json"):
                self.assertNotIn(forbidden, json.dumps(payload))

    def test_freeze_includes_support_and_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "freeze"
            e.generate(out, 4)
            manifest = json.loads((out / "manifest.json").read_text())
            self.assertEqual(manifest["planned_calls"], 56)
            self.assertIn("v1_support.py", manifest["files"])
            for name, digest in manifest["files"].items():
                self.assertEqual(e.v1.digest(out / name), digest)
            with self.assertRaises(ValueError):
                e.generate(out, 4)

    def test_budget_failure_stops_other_jobs_before_sending(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            e.v1.os.environ, {"ANTHROPIC_API_KEY": "test-placeholder"}
        ):
            collector = e.Collector(Path(directory), 0.000001)
            with patch.object(e.v1.urllib.request, "urlopen") as request:
                with self.assertRaises(RuntimeError):
                    collector.call("DEV000", "checklist", "prepare",
                                   e.preparation(e.make_cases("development", 1)[0][0], "checklist"))
                request.assert_not_called()
                self.assertTrue(collector.stop)

    def test_split_phases_preserve_spend_and_refuse_repeated_collection(self):
        def fake_provider(request, timeout):
            payload = json.loads(request.data)
            case, _ = json.JSONDecoder().raw_decode(payload["messages"][0]["content"][len(e.v1.TASK):])
            if "tools" not in payload:
                response = {"content": [{"type": "text", "text": "Preparation completed."}],
                            "stop_reason": "end_turn"}
            else:
                name = payload["tool_choice"]["name"]
                data = reference_table(case) if name != "submit_assessment" else {}
                if name != "submit_ledger":
                    oracle = e.v1.oracle(case)
                    data.update(probabilities=oracle["posterior"],
                                future_probability=oracle["future_probability"], evidence_basis="Test")
                response = {"content": [{"type": "tool_use", "name": name, "input": data}],
                            "stop_reason": "tool_use"}
            response["usage"] = {"input_tokens": 100, "output_tokens": 50}
            return io.BytesIO(json.dumps(response).encode())

        with (tempfile.TemporaryDirectory() as directory,
              patch.dict(e.v1.os.environ, {"ANTHROPIC_API_KEY": "test-placeholder"}),
              patch.object(e.v1.urllib.request, "urlopen", side_effect=fake_provider) as request,
              contextlib.redirect_stdout(io.StringIO())):
            out = Path(directory) / "run"
            e.generate(out, 4)
            e.collect(out, 1, "development")
            self.assertEqual(request.call_count, 28)
            self.assertTrue(json.loads((out / "development_gate.json").read_text())["passed"])
            e.collect(out, 1, "main")
            self.assertEqual(request.call_count, 56)
            summary = json.loads((out / "summary.json").read_text())
            self.assertAlmostEqual(summary["recorded_cost_usd"], 56 * 0.00105)
            self.assertEqual(summary["main_record_count"], 16)
            self.assertEqual(summary["conditions"]["ledger_calculated"]["valid"], 4)
            self.assertLess(summary["conditions"]["ledger_calculated"]["mean_posterior_loss"], 1e-20)
            with self.assertRaises(ValueError):
                e.collect(out, 1, "main")
            self.assertEqual(request.call_count, 56)


if __name__ == "__main__":
    unittest.main()
