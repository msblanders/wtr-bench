"""Independent oracle checks and collection-boundary tests; no API calls."""
import copy
import importlib.util
import io
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = (Path(__file__).resolve().parents[1] / "experiments"
          / "scientific-confidence-v1" / "experiment.py")
SPEC = importlib.util.spec_from_file_location("scientific_confidence", SOURCE)
assert SPEC and SPEC.loader
e = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(e)


class ScientificConfidenceTests(unittest.TestCase):
    def test_oracle_matches_direct_density_product(self):
        cases, _ = e.make_cases()
        for case in cases:
            weights = {}
            # Independent implementation: direct Gaussian densities, not log scores.
            reports = {r["study_id"]: r for r in case["reports"]}.values()
            for h in case["hypotheses"]:
                w = h["prior"]
                for r in reports:
                    mu = h["means"][r["design"] + "_" + r["context"]]
                    w *= math.exp(-(r["estimate"] - mu) ** 2 / (2 * r["se"] ** 2))
                    w /= r["se"] * math.sqrt(2 * math.pi)
                weights[h["id"]] = w
            actual = e.oracle(case)["posterior"]
            for k, w in weights.items():
                self.assertAlmostEqual(actual[k], w / sum(weights.values()), places=12)

    def test_duplicates_and_order_do_not_change_posterior(self):
        cases, _ = e.make_cases()
        for original in cases:
            changed = copy.deepcopy(original)
            changed["reports"] = list(reversed(changed["reports"]))
            changed["reports"].append({**changed["reports"][0], "report_id": "NEW"})
            for k, value in e.oracle(original)["posterior"].items():
                self.assertAlmostEqual(e.oracle(changed)["posterior"][k], value, places=12)

    def test_inconsistent_duplicate_is_rejected(self):
        case = e.make_cases(1)[0][0]
        case["reports"].append({**case["reports"][0], "estimate": 999})
        with self.assertRaises(ValueError):
            e.oracle(case)

    def test_future_tail_symmetry(self):
        case = e.make_cases(1)[0][0]
        for h in case["hypotheses"]:
            h["means"] = {k: 0.0 for k in h["means"]}
        case["future_study"]["threshold"] = 0
        answer = e.oracle(case)
        self.assertAlmostEqual(answer["future_probability"], 0.5)
        for h in case["hypotheses"]:
            self.assertAlmostEqual(answer["posterior"][h["id"]], h["prior"])

    def test_brier_regret_identity(self):
        p, q = {"a": 0.1, "b": 0.6, "c": 0.3}, {"a": 0.3, "b": 0.5, "c": 0.2}
        expected_difference = sum(
            q[k] * (e.squared_distance(p, {j: int(j == k) for j in q})
                    - e.squared_distance(q, {j: int(j == k) for j in q})) for k in q
        )
        self.assertAlmostEqual(e.squared_distance(p, q), expected_difference)

    def test_prompt_boundary_and_equal_budgets(self):
        cases, gold = e.make_cases()
        for case, g in zip(cases, gold):
            self.assertEqual(set(case), {"case_id", "hypotheses", "reports", "future_study"})
            for arm in e.ARMS:
                payload = e.prepare_payload(case, arm)
                self.assertEqual(payload["max_tokens"], e.MAX_TOKENS)
                prompt = json.dumps(payload)
                for forbidden in ("true_h", "future_outcome", "supplied_posterior"):
                    self.assertNotIn(forbidden, prompt)
            self.assertEqual(len(e.unique_studies(case)), 4)
            self.assertEqual(g["case_id"], case["case_id"])

    def test_parser_rejects_invalid_and_truncated(self):
        response = {"stop_reason": "tool_use", "content": [{"type": "tool_use",
                    "name": "submit_assessment", "input": {
                        "probabilities": {"H1": 0.2, "H2": 0.3, "H3": 0.5},
                        "future_probability": 0.6}}]}
        self.assertEqual(e.parse_assessment(response)["normalization_delta"], 0)
        for bad in (float("nan"), -0.1, 1.1, True):
            changed = copy.deepcopy(response)
            changed["content"][0]["input"]["future_probability"] = bad
            with self.assertRaises(ValueError):
                e.parse_assessment(changed)
        response["stop_reason"] = "max_tokens"
        with self.assertRaises(ValueError):
            e.parse_assessment(response)

    def test_freeze_and_offline_report(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "run"
            e.generate(out, 4)
            manifest = json.loads((out / "manifest.json").read_text())
            self.assertEqual(manifest["planned_calls"], 28)
            for name, expected in manifest["files"].items():
                self.assertEqual(e.digest(out / name), expected)
            with self.assertRaises(ValueError):
                e.generate(out, 4)
            e.report(out)
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(summary["arms"]["contrastive_audit"]["missing"], 4)

    def test_budget_blocks_request_and_cost_is_recorded(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            e.os.environ, {"ANTHROPIC_API_KEY": "test-placeholder"}
        ):
            collector = e.Collector(Path(directory), 0.00001)
            payload = e.prepare_payload(e.make_cases(1)[0][0], "generic_review")
            with patch.object(e.urllib.request, "urlopen") as request:
                with self.assertRaises(RuntimeError):
                    collector.call("case", "arm", "prepare", payload)
                request.assert_not_called()
            collector = e.Collector(Path(directory), 1)
            response = {"usage": {"input_tokens": 100, "output_tokens": 50}}
            with patch.object(e.urllib.request, "urlopen",
                              return_value=io.BytesIO(json.dumps(response).encode())):
                collector.call("case", "arm", "prepare", payload)
            self.assertAlmostEqual(collector.actual, 0.00105)
            self.assertAlmostEqual(collector.committed, collector.actual)
            self.assertNotIn("test-placeholder", (Path(directory) / "calls.jsonl").read_text())

    def test_ambiguous_failure_retains_reservation_and_halts(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            e.os.environ, {"ANTHROPIC_API_KEY": "test-placeholder"}
        ):
            collector = e.Collector(Path(directory), 1)
            payload = e.prepare_payload(e.make_cases(1)[0][0], "generic_review")
            with (patch.object(e.urllib.request, "urlopen", side_effect=TimeoutError("secret")),
                  self.assertRaises(RuntimeError)):
                collector.call("case", "arm", "prepare", payload)
            self.assertTrue(collector.stop)
            self.assertGreater(collector.committed, 0)
            self.assertEqual(collector.actual, 0)
            self.assertNotIn("secret", (Path(directory) / "calls.jsonl").read_text())


if __name__ == "__main__":
    unittest.main()
