"""Tests of study invariants, scoring, and collection boundaries; no paid calls."""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "experiments/functional-learning-v1/experiment.py"
spec = importlib.util.spec_from_file_location("functional_learning", MODULE)
assert spec is not None and spec.loader is not None
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


class FunctionalLearningTests(unittest.TestCase):
    def test_nested_exposure_and_heldout_setting(self):
        w = e.make_world(3, "shared")
        self.assertEqual(len(w["records"]), 96)
        self.assertTrue(all(r["setting"] != w["heldout_setting"] for r in w["records"]))
        for n in e.BUDGETS:
            rows = [r for r in w["records"] if r["exposure"] <= n]
            for partner in w["parameters"]:
                self.assertEqual(sum(r["partner"] == partner for r in rows), n)

    def test_body_does_not_contain_answers_or_regime(self):
        w = e.make_world(2, "context_specific")
        r = e.make_request(w, 8, "functional", "claude-sonnet-4-6")
        body = json.dumps(r["body"])
        for forbidden in ("answer_key", "references", "context_specific", "truth", "parameters"):
            # "latent parameters" is part of output instructions, not an answer key.
            if forbidden != "parameters":
                self.assertNotIn(forbidden, body)
        self.assertEqual(len(r["answer_key"]), 24)

    def test_conditions_share_evidence_and_keys(self):
        w = e.make_world(7, "shared")
        rs = [e.make_request(w, 24, arm, "claude-sonnet-4-6") for arm in e.ARMS]
        tails = [r["body"]["messages"][0]["content"].split("Observed records:\n")[1] for r in rs]
        self.assertTrue(all(t == tails[0] for t in tails))
        self.assertTrue(all(r["answer_key"] == rs[0]["answer_key"] for r in rs))

    def test_assigned_does_not_update_inclination(self):
        q = {"partner": "A", "setting": "X", "kind": "choice"}
        rows = [{"partner": "A", "setting": "X", "instruction": "ASSIGNED", "attempt": True, "outcome": "success"}] * 20
        self.assertEqual(e.estimate(rows, q, "functional", "shared"), 0.5)
        q["kind"] = "execution"
        self.assertAlmostEqual(e.estimate(rows, q, "functional", "shared"), 21 / 22)

    def test_declines_do_not_become_execution_failures(self):
        q = {"partner": "A", "setting": "X", "kind": "execution"}
        rows = [{"partner": "A", "setting": "X", "instruction": "VOLUNTARY", "attempt": False, "outcome": "none"}] * 20
        self.assertEqual(e.estimate(rows, q, "functional", "shared"), 0.5)
        q["kind"] = "choice"
        self.assertAlmostEqual(e.estimate(rows, q, "functional", "shared"), 1 / 22)

    def test_context_specific_oracle_does_not_transfer_choice(self):
        q = {"partner": "A", "setting": "Y", "kind": "choice"}
        rows = [{"partner": "A", "setting": "X", "instruction": "VOLUNTARY", "attempt": True, "outcome": "success"}] * 20
        self.assertEqual(e.estimate(rows, q, "oracle", "context_specific"), 0.5)
        self.assertGreater(e.estimate(rows, q, "functional", "context_specific"), 0.9)

    def test_paired_worlds_share_parameters_except_context_choice(self):
        a, b = e.make_world(2, "shared"), e.make_world(2, "context_specific")
        self.assertEqual(a["heldout_setting"], b["heldout_setting"])
        for name in a["parameters"]:
            self.assertEqual(a["parameters"][name]["ability"], b["parameters"][name]["ability"])
        for x, y in zip(a["records"], b["records"]):
            for k in ("partner", "setting", "instruction", "exposure"):
                self.assertEqual(x[k], y[k])

    def test_probability_parser_rejects_invalid_outputs(self):
        invalid = ['{"reasoning":"x","predictions":{"q01":true}}',
                   '{"reasoning":"x","predictions":{"q01":NaN}}',
                   '{"reasoning":"x","predictions":{"q01":0.1,"q01":0.2}}',
                   '{"reasoning":"x","predictions":{"q01":1.1}}',
                   '{"reasoning":"x","predictions":{"q02":0.1}}']
        for text in invalid:
            with self.assertRaises(ValueError):
                e.parse_response(text, ["q01"])

    def test_exact_truth_has_zero_probability_error(self):
        r = e.make_request(e.make_world(0, "shared"), 8, "general", "claude-sonnet-4-6")
        scores = e.score(r, {q["id"]: q["truth"] for q in r["answer_key"]})
        self.assertTrue(all(x == 0 for x in scores.values()))

    def test_budget_transport_and_duplicate_collection(self):
        with tempfile.TemporaryDirectory() as root, contextlib.redirect_stdout(io.StringIO()):
            out = Path(root) / "run"
            e.generate(out, 1, "claude-sonnet-4-6")
            calls = []
            def forbidden(body):
                calls.append(body)
                raise AssertionError("Should never send")
            e.collect(out, 0.000001, forbidden)
            self.assertFalse(calls)
            self.assertEqual(json.loads((out / "collection-status.json").read_text())["status"], "budget_stop")
            with self.assertRaises(FileExistsError):
                e.collect(out, 25, forbidden)

    def test_unknown_transport_outcome_is_not_retried(self):
        with tempfile.TemporaryDirectory() as root, contextlib.redirect_stdout(io.StringIO()):
            out = Path(root) / "run"
            e.generate(out, 1, "claude-sonnet-4-6")
            calls = []
            def timeout(body):
                calls.append(body)
                raise TimeoutError()
            with self.assertRaises(RuntimeError):
                e.collect(out, 25, timeout)
            self.assertEqual(len(calls), 1)
            self.assertEqual(len(e.read_jsonl(out / "attempts.jsonl")), 1)

    def test_frozen_hash_changes_are_rejected(self):
        with tempfile.TemporaryDirectory() as root, contextlib.redirect_stdout(io.StringIO()):
            out = Path(root) / "run"
            e.generate(out, 1, "claude-sonnet-4-6")
            with (out / "requests.jsonl").open("a") as f:
                f.write("\n")
            with self.assertRaises(ValueError):
                e.check_manifest(out)

    def test_complete_synthetic_pipeline_is_explicitly_a_test(self):
        with tempfile.TemporaryDirectory() as root, contextlib.redirect_stdout(io.StringIO()):
            out = Path(root) / "run"
            e.generate(out, 2, "claude-sonnet-4-6")
            requests = e.read_jsonl(out / "requests.jsonl")
            response_map = {r["request_hash"]: r["references"]["oracle"] for r in requests}
            def fake(body):
                return {"model": body["model"], "stop_reason": "end_turn",
                        "usage": {"input_tokens": 100, "output_tokens": 100},
                        "content": [{"type": "text", "text": json.dumps({"reasoning": "TEST DOUBLE ONLY", "predictions": response_map[e.digest(body)]})}]}
            e.collect(out, 25, fake)
            e.report(out)
            report = json.loads((out / "report.json").read_text())
            self.assertTrue(report["complete"])
            self.assertEqual(report["valid"], 64)
            self.assertTrue(all(c["mean_mse_advantage"] == 0 for c in report["contrasts"]))
            self.assertEqual(json.loads((out / "collection-started.json").read_text())["data_origin"], "test_double")


if __name__ == "__main__":
    unittest.main()
