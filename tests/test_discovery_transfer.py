"""Scientific invariants for selection without supplied cue routing."""
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
    import torch
except ImportError as exc:
    raise unittest.SkipTest("Install experiments/discovery-transfer-v1/requirements.txt") from exc

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT/"experiments/discovery-transfer-v1"
sys.path.insert(0, str(DIRECTORY))
spec = importlib.util.spec_from_file_location("discovery_transfer_experiment", DIRECTORY/"experiment.py")
assert spec is not None and spec.loader is not None
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


class DiscoveryTransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        e.configure()

    def data(self, length=24, size=8):
        return e.worlds.synthetic(np.random.default_rng(131000001), size, length)

    def model(self):
        theta = e.models.initial_mean()+np.random.default_rng(131000002).normal(0, .5, e.models.PARAMETERS).astype(np.float32)
        return e.models.Small(theta)

    def test_history_contexts_and_observed_outcomes(self):
        data = self.data(size=1024)
        self.assertEqual(data["x"].shape, (1024, 24, 15))
        self.assertTrue(np.all(data["contexts"] != data["query_context"][:, None]))
        self.assertTrue(np.all(data["actions"][~data["voluntary"]] == 1))
        self.assertTrue(np.all(data["success"] <= data["observed"]))
        self.assertTrue(np.all(data["observed"] <= (data["actions"] != 0)))
        self.assertTrue(np.any((data["actions"] != 0) & ~data["observed"]))
        self.assertEqual(set(data["y_choice"]), {0, 1})
        self.assertEqual(set(data["y_ability"]), {0, 1})

    def test_no_future_padding_or_target_identity_leak(self):
        model, data = self.model(), self.data()
        data["lengths"][:] = 4
        p = e.predictions(model, data)
        changed = dict(data, x=data["x"].copy(), y_choice=1-data["y_choice"], y_ability=1-data["y_ability"],
                       truth_choice=np.full_like(data["truth_choice"], 99), truth_ability=np.full_like(data["truth_ability"], 99))
        changed["x"][:, 4:] = 99
        for a, b in zip(p, e.predictions(model, changed)):
            np.testing.assert_allclose(a, b, atol=1e-7)
        reversed_data = {k: v[::-1].copy() if isinstance(v, np.ndarray) else v for k, v in data.items()}
        for a, b in zip(p, e.predictions(model, reversed_data)):
            np.testing.assert_allclose(a, b[::-1], atol=1e-7)
        empty = dict(data, lengths=np.zeros(8, dtype=int))
        for a, b in zip(e.predictions(model, empty), e.predictions(model, data, no_memory=True)):
            np.testing.assert_allclose(a, b, atol=1e-7)

    def test_fitness_uses_observed_targets_only(self):
        model, data = self.model(), self.data()
        pred = model(e.models.inputs(data))
        actual = e.models.observed_loss(pred, data)
        poisoned = dict(data, truth_choice=np.full_like(data["truth_choice"], np.nan), truth_ability=np.full_like(data["truth_ability"], np.nan))
        torch.testing.assert_close(actual, e.models.observed_loss(pred, poisoned))
        p, a = e.predictions(model, data)
        independent = .5*(np.mean((p[:, 1]-data["y_choice"])**2)+np.mean((a-data["y_ability"])**2))
        self.assertAlmostEqual(float(actual.detach()[0]), independent, places=6)

    def test_population_and_single_model_agree_and_gradients_reach_update(self):
        model, data = self.model(), self.data()
        theta = model.theta.detach()[None].repeat(3, 1)
        population = e.models.small(theta, e.models.inputs(data))
        single = model(e.models.inputs(data))
        for p, s in zip(population, single):
            torch.testing.assert_close(p, s.expand_as(p))
        e.models.observed_loss(single, data).sum().backward()
        self.assertGreater(float(model.theta.grad[:2*e.models.RECURRENT].abs().sum()), 0)

    def test_query_option_permutation_and_padding(self):
        model, data = self.model(), self.data()
        p, a = e.predictions(model, data)
        changed = dict(data, query=data["query"][:, ::-1].copy(), query_mask=data["query_mask"][:, ::-1].copy())
        cp, ca = e.predictions(model, changed)
        np.testing.assert_allclose(p, cp[:, ::-1], atol=1e-7)
        np.testing.assert_allclose(a, ca, atol=1e-7)
        changed = dict(data, query=np.pad(data["query"], ((0, 0), (0, 3), (0, 0))),
                       query_mask=np.pad(data["query_mask"], ((0, 0), (0, 3))))
        cp, ca = e.predictions(model, changed)
        np.testing.assert_allclose(p, cp[:, :2], atol=1e-7)
        np.testing.assert_array_equal(cp[:, 2:], 0)
        np.testing.assert_allclose(a, ca, atol=1e-7)

    def test_reference_ignores_assigned_choices_and_missing_executions(self):
        data = self.data()
        data["voluntary"][:] = False
        data["observed"][:] = False
        data["success"][:] = 1
        p, a = e.worlds.functional_reference(data)
        zero = dict(data, lengths=np.zeros(len(a), dtype=int))
        zp, za = e.worlds.functional_reference(zero)
        np.testing.assert_allclose(p, zp, atol=1e-12)
        np.testing.assert_allclose(a, za, atol=1e-12)
        data["observed"][:] = True
        _, a = e.worlds.functional_reference(data)
        np.testing.assert_allclose(a, 25/26, atol=1e-12)

    def test_causal_reference_directions_and_nulls(self):
        result = e.diagnose(self.model(), self.data(length=8))
        self.assertGreater(result["failure_vs_decline"]["mean_reference_delta"][0], 0)
        self.assertLess(result["failure_vs_decline"]["mean_reference_delta"][1], 0)
        self.assertAlmostEqual(result["assigned_success_vs_failure"]["mean_reference_delta"][0], 0, places=12)
        self.assertGreater(result["assigned_success_vs_failure"]["mean_reference_delta"][1], 0)
        self.assertAlmostEqual(result["decline_vs_baseline"]["mean_reference_delta"][1], 0, places=12)

    def test_training_streams_match_and_inherited_parameters_change(self):
        config = dict(e.CONFIG, generations=2, population=4, elites=2, batch_size=4,
                      validation_lifetimes=4, checkpoints=[0, 1, 2])
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            snapshots, metadata, validation, initial = e.search(131000003, config, out)
            for method in e.METHODS[2:]:
                snaps, meta = e.gradient(method, 131000003, config, out, validation, initial)
                metadata[method] = meta
                last = torch.load(out/f"{method}-last-update.pt", weights_only=True)
                self.assertTrue(any(not torch.equal(snaps[0][k], last[k]) for k in snaps[0]))
            self.assertEqual(len({m["training_stream_sha256"] for m in metadata.values()}), 1)
            self.assertEqual(set(snapshots["evolved"]), {0, 1, 2})
            distribution = np.load(out/"search-distribution.npz")
            self.assertTrue(np.any(distribution["mean"] != e.models.initial_mean()))
            self.assertEqual(metadata["evolved"]["candidate_fitness_evaluations"], 8)

    def test_resource_counts_and_constant_bootstrap(self):
        self.assertEqual(e.models.resources("evolved")["parameters"], 257)
        self.assertEqual(e.models.resources("dense_gradient")["parameters"], 1969)
        self.assertEqual(e.bootstrap([2]*8), [2, 2])

    def test_exact_upstream_generator_and_actor_adapter(self):
        folder = os.environ.get("DISCOVERY_UPSTREAM")
        if not folder:
            self.skipTest("Dedicated workflow supplies checksum-verified upstream sources")
        namespace = e.external.load(Path(folder))
        rng = np.random.default_rng(131000004)
        sizes = set()
        for _ in range(20):
            game = e.external.sample_menu(namespace, rng)
            menu = np.array(list(game.payoffs.values()))
            sizes.add(len(menu))
            np.testing.assert_array_equal(menu[0], [0, 0])
            self.assertTrue(np.all(menu[1:, 1] > -menu[1:, 0]))
            for kind in (0, 1):
                agent = e.external.actor(namespace, kind)
                base = e.worlds.softmax(menu[:, 0]+kind*menu[:, 1])
                expected = .98*base+.02*(1-base)/(len(base)-1)
                np.testing.assert_allclose(agent.decide_likelihood(game, [0, 1], tremble=.02), expected, atol=1e-12)
        self.assertGreater(len(sizes), 1)
        data = e.worlds.external_games(rng, 8, 4, namespace)
        self.assertTrue(np.all(data["y_ability"] == -1))
        self.assertTrue(np.all(data["observed"] == 0))
        self.assertTrue(np.all(data["voluntary"]))
        self.assertGreater(data["query"].shape[1], 2)
        model = self.model()
        score = e.score(e.predictions(model, data), data)
        self.assertIsNone(score["execution_brier"])
        self.assertAlmostEqual(score["brier"], score["choice_brier"], places=12)
        self.assertTrue(np.isfinite(float(e.models.observed_loss(model(e.models.inputs(data)), data)[0].detach())))


if __name__ == "__main__":
    unittest.main()
