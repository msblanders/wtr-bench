"""Optional neural update experiment invariants; development streams only."""
import copy
import importlib.util
import itertools
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
    import torch
except ImportError as exc:
    raise unittest.SkipTest("Install experiments/neural-update-v1/requirements.txt") from exc

MODULE = Path(__file__).resolve().parents[1]/"experiments/neural-update-v1/experiment.py"
spec = importlib.util.spec_from_file_location("neural_update", MODULE)
assert spec is not None and spec.loader is not None
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


class NeuralUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        e.configure()

    def test_bayesian_reference_matches_exhaustive_latent_enumeration(self):
        for length in range(1, 5):
            for prefix in itertools.product((0, 1), repeat=length):
                q = e.bayes_mixture(np.array([prefix], dtype=float))[0, -1]
                self.assertAlmostEqual(q, e.brute_prediction(prefix), places=12)

    def test_bayesian_symbol_symmetry_and_prefix_causality(self):
        observations, _ = e.sequences(np.random.default_rng(9100000), 8, 12)
        q = e.bayes_mixture(observations)
        np.testing.assert_allclose(e.bayes_mixture(1-observations), 1-q, atol=1e-12)
        changed = observations.copy()
        changed[:, 6:] = 1-changed[:, 6:]
        np.testing.assert_array_equal(e.bayes_mixture(changed)[:, :6], q[:, :6])
        self.assertTrue(np.all((q > 0) & (q < 1)))

    def test_balanced_generator_reproducibility_and_no_metadata_input(self):
        a, fa = e.sequences(np.random.default_rng(9100001), 8, 12)
        b, fb = e.sequences(np.random.default_rng(9100001), 8, 12)
        np.testing.assert_array_equal(a, b)
        np.testing.assert_array_equal(fa, fb)
        self.assertEqual(a.shape, (8, 13))
        self.assertEqual(int(fa.sum()), 4)
        self.assertTrue(set(a.ravel()) <= {0, 1})
        with self.assertRaises(ValueError):
            e.sequences(np.random.default_rng(2), 7, 12)

    def test_models_are_causal_and_states_reset(self):
        torch.manual_seed(9100002)
        x = torch.randint(0, 2, (8, 10, 1)).float()
        changed = x.clone()
        changed[:, 5:] = 1-changed[:, 5:]
        for method in e.METHODS:
            model = e.Learner(method)
            model.eval()
            with torch.no_grad():
                before = model(x)["prediction"]
                after = model(changed)["prediction"]
                permuted = model(x.flip(0))["prediction"].flip(0)
            torch.testing.assert_close(before[:, :5], after[:, :5])
            torch.testing.assert_close(before, permuted)
            self.assertEqual(before.shape, (8, 10))

    def test_parameter_and_active_compute_accounting(self):
        expected = {"dense": 1153, "routed": 1156, "shared": 1210}
        resources = {name: e.resources(e.Learner(name)) for name in expected}
        for name, n in expected.items():
            self.assertEqual(resources[name]["parameters"], n)
        self.assertGreater(resources["shared"]["state_values"], resources["routed"]["state_values"])
        self.assertGreater(resources["shared"]["approx_forward_matrix_macs_per_observation"],
                           resources["routed"]["approx_forward_matrix_macs_per_observation"])
        self.assertLess(resources["shared"]["parameters"]/resources["routed"]["parameters"], 1.05)

    def test_full_branch_permutation_is_behaviorally_invariant(self):
        torch.manual_seed(9100003)
        model = e.Learner("routed")
        permuted = copy.deepcopy(model)
        permuted.cells[0].load_state_dict(model.cells[1].state_dict())
        permuted.cells[1].load_state_dict(model.cells[0].state_dict())
        permuted.heads[0].load_state_dict(model.heads[1].state_dict())
        permuted.heads[1].load_state_dict(model.heads[0].state_dict())
        with torch.no_grad():
            order = torch.cat((torch.arange(12, 24), torch.arange(12)))
            permuted.gate.weight.copy_(model.gate.weight.flip(0)[:, order])
            permuted.gate.bias.copy_(model.gate.bias.flip(0))
            x = torch.randint(0, 2, (8, 6, 1)).float()
            torch.testing.assert_close(model(x)["prediction"], permuted(x)["prediction"])

    def test_training_streams_match_and_checkpoints_are_real_updates(self):
        config = dict(e.CONFIG, updates=2, batch_size=8, train_length=4, checkpoints=[0, 1, 2])
        hashes = []
        with tempfile.TemporaryDirectory() as temp:
            for method in e.METHODS:
                out = Path(temp)/method
                out.mkdir()
                _, checkpoints, metadata = e.train(method, 9100004, config, out)
                hashes.append(metadata["training_stream_sha256"])
                self.assertEqual(set(checkpoints), {0, 1, 2})
                self.assertTrue(any(not torch.equal(checkpoints[0][k], checkpoints[2][k]) for k in checkpoints[0]))
                self.assertEqual(len(list(out.glob("*.pt"))), 3)
            self.assertEqual(len(set(hashes)), 1)

    def test_forced_gates_and_score_use_observable_reference(self):
        torch.manual_seed(9100005)
        model = e.Learner("routed")
        obs, family = e.sequences(np.random.default_rng(9100005), 8, 10)
        x = torch.from_numpy(obs[:, :-1, None].copy())
        with torch.no_grad():
            for i in (0, 1):
                result = model(x, force_gate=i)
                torch.testing.assert_close(result["prediction"], result["experts"][..., i])
            result = model(x, force_gate="uniform")
            torch.testing.assert_close(result["prediction"], result["experts"].mean(-1))
        oracle = e.bayes_mixture(obs[:, :-1])
        score = e.score(torch.from_numpy(oracle), oracle, obs[:, 1:], family, 5)
        self.assertEqual(score["excess_brier"], 0)
        self.assertEqual(score["longer_history_excess"], 0)


if __name__ == "__main__":
    unittest.main()
