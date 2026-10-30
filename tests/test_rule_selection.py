"""Scientific invariants for the optional NumPy selection experiment; no API calls."""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
except ImportError as exc:
    raise unittest.SkipTest("Optional selection experiment: install its requirements.txt") from exc

MODULE = Path(__file__).resolve().parents[1]/"experiments/rule-selection-v1/experiment.py"
spec = importlib.util.spec_from_file_location("rule_selection", MODULE)
assert spec is not None and spec.loader is not None
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


class RuleSelectionTests(unittest.TestCase):
    def test_event_gating_has_expected_independent_effects(self):
        # 3 declines, 2 voluntary failures, 1 voluntary success, 4 assigned failures, 5 assigned successes.
        counts = np.array([[[[[3., 2., 1., 4., 5.], [0., 0., 0., 0., 0.], [0., 0., 0., 0., 0.]]]]])
        g = e.reference_genotype("both_shared")
        p = e.predict(counts, g)
        self.assertAlmostEqual(p[0, 0, 0, 0, 0], 4/8)
        self.assertAlmostEqual(p[0, 0, 0, 0, 1], 7/14)
        more = counts.copy()
        more[..., 0, 4] += 10
        p2 = e.predict(more, g)
        self.assertEqual(p2[0, 0, 0, 0, 0], p[0, 0, 0, 0, 0])
        self.assertGreater(p2[0, 0, 0, 0, 1], p[0, 0, 0, 0, 1])
        more = counts.copy()
        more[..., 0, 0] += 10
        p3 = e.predict(more, g)
        self.assertLess(p3[0, 0, 0, 0, 0], p[0, 0, 0, 0, 0])
        self.assertEqual(p3[0, 0, 0, 0, 1], p[0, 0, 0, 0, 1])

    def test_reference_matches_independent_history_counting(self):
        for ecology in e.ECOLOGIES:
            world = e.make_world(9000011, ecology)
            counts, _ = e.pack_world(world)
            predicted = e.predict(counts[:, None], e.reference_genotype(ecology))[:, 0]
            for b, n in enumerate(e.CHECKPOINTS):
                for i, name in enumerate(world["names"]):
                    for j, setting in enumerate(world["contexts"]):
                        for channel, shared in enumerate(e.ECOLOGIES[ecology]):
                            records = [r for r in world["records"] if r["exposure"] <= n
                                       and r["partner"] == name and (shared or r["setting"] == setting)
                                       and (r["instruction"] == "VOLUNTARY" if channel == 0 else r["attempt"])]
                            success = sum(r["attempt"] if channel == 0 else r["outcome"] == "success" for r in records)
                            self.assertAlmostEqual(predicted[b, i, j, channel], (1+success)/(2+len(records)))

    def test_base_choices_paired_ecologies_and_identity_permutation(self):
        worlds = {k: e.make_world(9000021, k) for k in e.ECOLOGIES}
        for ecology, world in worlds.items():
            base = e.v1.make_world(9000021, "shared" if e.ECOLOGIES[ecology][0] else "context_specific")
            for old, new in zip(base["records"], world["records"]):
                self.assertEqual(old["attempt"], new["attempt"])
                self.assertEqual(old["setting"], new["setting"])
            for r in world["records"]:
                self.assertEqual(r["outcome"] == "none", not r["attempt"])
            self.assertNotIn(world["contexts"][-1], {r["setting"] for r in world["records"]})
        self.assertEqual([r["attempt"] for r in worlds["both_shared"]["records"]],
                         [r["attempt"] for r in worlds["w_shared_a_local"]["records"]])
        world = worlds["w_local_a_shared"]
        renamed = {"names": ["entity-"+str(i) for i in range(4)], "contexts": ["a", "b", "c"]}
        names = dict(zip(world["names"], renamed["names"]))
        contexts = dict(zip(world["contexts"], renamed["contexts"]))
        renamed["records"] = [dict(r, partner=names[r["partner"]], setting=contexts[r["setting"]]) for r in world["records"]]
        renamed["truth"] = {(names[n], contexts[c]): v for (n, c), v in world["truth"].items()}
        a, t = e.pack_world(world)
        b, u = e.pack_world(renamed)
        np.testing.assert_array_equal(a, b)
        np.testing.assert_array_equal(t, u)

    def test_cached_fitness_matches_direct_predictions(self):
        counts, truth = e.dataset([9000031, 9000032], "w_shared_a_local")
        losses = e.loss_table(counts, truth)
        genomes = e.founders(np.random.default_rng(3), 20, False)
        scores = e.population_fitness(genomes, losses)
        for genome, score in zip(genomes, scores):
            direct = e.evaluation(e.predict(counts, genome), truth)["mse"]
            self.assertAlmostEqual(score, direct, places=12)
        # The truth array is used solely for scoring; changing it leaves predictions unchanged.
        first = e.predict(counts, genomes[0])
        truth[:] = 1-truth
        np.testing.assert_array_equal(first, e.predict(counts, genomes[0]))

    def test_rule_encoding_search_budget_and_exact_optimum(self):
        for i in range(486):
            self.assertEqual(e.encode_rule(e.decode_rule(i)), i)
        rng = np.random.default_rng(4)
        losses = rng.uniform(size=(2, 486))
        config = dict(e.DEFAULTS, population=12, generations=5, elite=2)
        for mode in ("flexible", "tied", "random"):
            result = e.search(losses, 5, config, mode)
            self.assertEqual(result["candidate_evaluations"], 60)
            self.assertGreaterEqual(result["optimization_gap"], -1e-12)
            self.assertEqual(result, e.search(losses, 5, config, mode))
            if mode == "tied":
                self.assertEqual(result["genotype"][5], result["genotype"][11])
            trace = [r["best_so_far"] for r in result["trace"]]
            self.assertEqual(trace, sorted(trace, reverse=True))

    def test_adaptive_prior_and_shared_contextual_equivalence(self):
        counts, _ = e.dataset([9000041], "both_shared")
        adaptive = e.adaptive_predict(counts)
        np.testing.assert_array_equal(adaptive[0], 0.5)
        self.assertTrue(np.all((adaptive > 0) & (adaptive < 1)))
        for genome in e.founders(np.random.default_rng(8), 10, False):
            np.testing.assert_array_equal(e.predict(counts, genome), e.contextual_predict(counts, genome))

    def test_frozen_pipeline_disjoint_seeds_and_duplicate_guard(self):
        config = dict(e.DEFAULTS, replicates=1, selection_worlds=2, evaluation_worlds=2,
                      population=8, generations=2, elite=2, seed_base=9100000)
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            out = Path(temp)/"run"
            e.freeze(out, config)
            manifest = e.validate(out)
            for plan in manifest["seed_plan"]:
                self.assertFalse(set(plan["selection"]) & set(plan["evaluation"]))
                self.assertTrue(all(s >= 9000000 for s in plan["evaluation"]))
            e.run(out)
            e.summarize(out)
            summary = json.loads((out/"summary.json").read_text())
            self.assertEqual(summary["run_ecology_combinations"], 4)
            self.assertEqual(summary["api_cost_usd"], 0)
            with self.assertRaises(FileExistsError):
                e.run(out)
            (out/"protocol.md").write_text("changed")
            with self.assertRaises(AssertionError):
                e.validate(out)


if __name__ == "__main__":
    unittest.main()
