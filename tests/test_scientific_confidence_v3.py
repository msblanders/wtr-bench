"""Checks for sequential inference semantics, information boundaries, and safe collection."""
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
          / "scientific-confidence-v3" / "experiment.py")
SPEC = importlib.util.spec_from_file_location("scientific_confidence_v3", SOURCE)
assert SPEC and SPEC.loader
e = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(e)


def reference_table(case):
    hs = case["hypotheses"]
    def means(row):
        return {h["id"]: e.v1.mean_for(h, row["design"], row["context"]) for h in hs}
    return {"priors": {h["id"]: h["prior"] for h in hs},
            "studies": [s | {"predicted_means": means(s)} for s in e.v1.unique_studies(case)],
            "future_study": case["future_study"] | {"predicted_means": means(case["future_study"])},
            "evidence_basis": "Test fixture"}


class ScientificConfidenceV3Tests(unittest.TestCase):
    def test_oracle_updates_and_neutral_invariance(self):
        trajectories, gold = e.sequential_cases("main", 8)
        for t, g in zip(trajectories, gold):
            last = None
            for step, checkpoint in enumerate(g["checkpoints"]):
                case = e.dossier_at(t, step)
                computed = e.v2.calculate(reference_table(case))
                self.assertEqual(computed, e.v1.oracle(case))
                self.assertTrue(e.v2.source_diagnostic(reference_table(case), case)["source_faithful"])
                if e.STEPS[step] in ("duplicate", "review"):
                    self.assertEqual(computed, last)
                self.assertEqual(computed["posterior"], checkpoint["posterior"])
                last = computed
            self.assertEqual(len(e.v1.unique_studies(e.dossier_at(t, 11))), 6)

    def test_same_schema_information_boundary_and_no_hidden_gold(self):
        t = e.sequential_cases("main", 1)[0][0]
        state = e.calculated_state(reference_table(e.dossier_at(t, 0)))
        state["worksheet"]["evidence_basis"] = "UNIQUE-STATE-SENTINEL"
        schemas = []
        for arm in e.ARMS:
            p = e.sequential_payload(t, 1, arm, state)
            encoded = json.dumps(p)
            schemas.append(p["tools"][0]["input_schema"])
            for forbidden in ("true_h", "future_outcome", "gold.json"):
                self.assertNotIn(forbidden, encoded)
            self.assertEqual("UNIQUE-STATE-SENTINEL" in encoded, arm != "ledger_rebuild")
            self.assertEqual("Report R1:" in encoded, arm == "ledger_rebuild")
            self.assertIn("Report R3:", encoded)
        self.assertEqual(schemas[0], schemas[1])
        self.assertEqual(schemas[0], schemas[2])

    def test_corrupt_state_is_not_repaired_by_solver_or_payload(self):
        t = e.sequential_cases("main", 1)[0][0]
        case = e.dossier_at(t, 1)
        table = reference_table(case)
        table["studies"][0]["predicted_means"]["H1"] += 3
        state = e.calculated_state(table)
        self.assertNotEqual(state["derived_beliefs"]["posterior"], e.v1.oracle(case)["posterior"])
        payload = e.sequential_payload(t, 2, "ledger_state", state)
        self.assertIn(e.v1.canonical(state), payload["messages"][0]["content"])
        self.assertFalse(e.v2.source_diagnostic(table, case)["source_faithful"])
        bad = copy.deepcopy(table)
        bad["priors"] = {"H1": 1, "H2": 1, "H3": 1}
        self.assertIn("error", e.calculated_state(bad)["derived_beliefs"])

    def test_fresh_seeds_and_exact_confirmation_payload(self):
        schedules = [(e.v1.SEED, 32), (e.v2.SEEDS["main"], 32), (e.v2.SEEDS["development"], 4)]
        schedules += [(seed, 64) for seed in e.SEEDS.values()]
        draws = [{seed + 7919 * i for i in range(n)} for seed, n in schedules]
        for i, a in enumerate(draws):
            for b in draws[i + 1:]:
                self.assertFalse(a & b)
        case = e.v1.make_cases(1, seed=e.SEEDS["main_confirmation"])[0][0]
        self.assertEqual(e.v2.preparation(case, "ledger")["max_tokens"], 4096)

    def test_budget_blocks_network_and_sets_stop(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            e.v1.os.environ, {"ANTHROPIC_API_KEY": "test-placeholder"}
        ):
            collector = e.Collector(Path(directory), 0.000001)
            with patch.object(e.v1.urllib.request, "urlopen") as request:
                with self.assertRaises(RuntimeError):
                    collector.call("test", "test", "test", {"max_tokens": 4096})
                request.assert_not_called()
                self.assertTrue(collector.stop)

    def test_complete_mocked_split_run_and_no_repeat(self):
        def provider(request, timeout):
            payload = json.loads(request.data)
            text = payload["messages"][0]["content"]
            name = payload["tool_choice"]["name"]
            if name != "submit_state":
                case, _ = json.JSONDecoder().raw_decode(text[len(e.v1.TASK):])
                table = reference_table(case)
                if name == "submit_worksheet":
                    answer = e.v1.oracle(case)
                    table.update(probabilities=answer["posterior"], future_probability=answer["future_probability"])
            else:
                spec, _ = json.JSONDecoder().raw_decode(text.split("Model specification:\n")[1])
                old = []
                if "Previous working state (not an additional observation):\n" in text:
                    state, _ = json.JSONDecoder().raw_decode(text.split(
                        "Previous working state (not an additional observation):\n")[1])
                    if state:
                        old = [{k: v for k, v in row.items() if k != "predicted_means"}
                               for row in state["worksheet"]["studies"]]
                incoming = []
                pattern = (r"Report (R\d+): Study (S\d+) used a (randomized|observational) design "
                           r"in context ([AB])\. Its effect estimate was ([\d.e+\-]+), "
                           r"with standard error ([\d.e+\-]+)\.")
                for rid, sid, design, context, estimate, se in re.findall(pattern, text):
                    incoming.append({"report_id": rid, "study_id": sid, "design": design,
                                     "context": context, "estimate": float(estimate), "se": float(se)})
                table = reference_table(spec | {"reports": old + incoming})
            response = {"stop_reason": "tool_use", "content": [{"type": "tool_use", "name": name,
                                                                  "input": table}],
                        "usage": {"input_tokens": 100, "output_tokens": 50}}
            return io.BytesIO(json.dumps(response).encode())

        with (tempfile.TemporaryDirectory() as directory,
              patch.dict(e.v1.os.environ, {"ANTHROPIC_API_KEY": "test-placeholder"}),
              patch.object(e.v1.urllib.request, "urlopen", side_effect=provider) as request,
              contextlib.redirect_stdout(io.StringIO())):
            out = Path(directory) / "freeze"
            e.generate(out, confirmations=2, trajectories=1)
            e.collect(out, 5, "development")
            self.assertEqual(request.call_count, 80)
            self.assertTrue(e.development_gate(out)["passed"])
            e.collect(out, 5, "main")
            self.assertEqual(request.call_count, 120)
            summary = json.loads((out / "summary.json").read_text())
            self.assertAlmostEqual(summary["recorded_cost_usd"], 120 * .00105)
            for arm in e.ARMS:
                self.assertEqual(summary["sequential"]["arms"][arm]["source_faithful"], 12)
                self.assertLess(summary["sequential"]["arms"][arm]["mean_posterior_loss"], 1e-20)
            self.assertTrue(summary["confirmation"]["paired_difference"]["passes_prespecified_confirmation"])
            with self.assertRaises(ValueError):
                e.collect(out, 5, "main")
            self.assertEqual(request.call_count, 120)
            with self.assertRaises(ValueError):
                e.generate(out)


if __name__ == "__main__":
    unittest.main()
