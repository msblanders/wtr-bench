"""Scientific invariants for the controlled memory/ecology follow-up."""
import importlib.util
import itertools
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
    import torch
except ImportError as exc:
    raise unittest.SkipTest("Install experiments/memory-ecology-v1/requirements.txt") from exc

MODULE = Path(__file__).resolve().parents[1]/"experiments/memory-ecology-v1/experiment.py"
spec = importlib.util.spec_from_file_location("memory_ecology", MODULE)
assert spec is not None and spec.loader is not None
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


class MemoryEcologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        e.configure()

    def test_oracle_enumeration_in_all_ecologies(self):
        for prior in e.ECOLOGIES.values():
            for length in range(1, 5):
                for prefix in itertools.product((0, 1), repeat=length):
                    q = e.bayes_mixture(np.array([prefix], dtype=float), stable_prior=prior)[0, -1]
                    self.assertAlmostEqual(q, e.brute_prediction(prefix, stable_prior=prior), places=12)

    def test_generator_and_oracle_symmetry_causality(self):
        for prior in e.ECOLOGIES.values():
            obs, family = e.sequences(np.random.default_rng(9300001), 8, 12, stable_prior=prior)
            self.assertEqual(int((family == 0).sum()), int(8*prior))
            self.assertEqual(obs.shape, (8, 13))
            self.assertTrue(set(obs.ravel()) <= {0, 1})
            q = e.bayes_mixture(obs, stable_prior=prior)
            np.testing.assert_allclose(e.bayes_mixture(1-obs, stable_prior=prior), 1-q, atol=1e-12)
            changed = obs.copy()
            changed[:, 6:] = 1-changed[:, 6:]
            np.testing.assert_array_equal(q[:, :6], e.bayes_mixture(changed, stable_prior=prior)[:, :6])

    def test_initial_predictions_identical_and_tying_gradient_identity(self):
        x = torch.tensor([[[0.], [1.], [1.]], [[1.], [0.], [0.]]])
        y = torch.tensor([[1., 0., 1.], [0., 1., 1.]])
        for h in e.CONFIG["widths"]:
            models = {}
            for method in e.METHODS:
                torch.manual_seed(9300002)
                model = e.Learner(method, h)
                loss = torch.nn.functional.binary_cross_entropy(model(x)["prediction"], y)
                loss.backward()
                models[method] = model
            shared, separate = models["shared"], models["separate"]
            torch.testing.assert_close(shared(x)["prediction"], separate(x)["prediction"])
            grads = [dict(cell.named_parameters()) for cell in separate.cells]
            for name, parameter in shared.cells[0].named_parameters():
                torch.testing.assert_close(parameter.grad, grads[0][name].grad+grads[1][name].grad,
                                           rtol=1e-4, atol=1e-7)
            for a, b in zip(shared.heads.parameters(), separate.heads.parameters()):
                torch.testing.assert_close(a.grad, b.grad)

    def test_state_and_forward_arithmetic_match(self):
        for h, params, macs in ((2, (58, 100), 72), (12, (688, 1300), 1152)):
            for method, n in zip(e.METHODS, params):
                r = e.resources(e.Learner(method, h))
                self.assertEqual(r["parameters"], n)
                self.assertEqual(r["state_values"], 2*h)
                self.assertEqual(r["approx_forward_matrix_macs_per_observation"], macs)

    def test_models_are_causal_and_reset_per_lifetime(self):
        torch.manual_seed(9300003)
        x = torch.randint(0, 2, (8, 10, 1)).float()
        changed = x.clone()
        changed[:, 5:] = 1-changed[:, 5:]
        for method in e.METHODS:
            model = e.Learner(method, 2)
            with torch.no_grad():
                p = model(x)["prediction"]
                torch.testing.assert_close(p[:, :5], model(changed)["prediction"][:, :5])
                torch.testing.assert_close(p, model(x.flip(0))["prediction"].flip(0))
                torch.testing.assert_close(p[:1], model(x[:1])["prediction"])

    def test_paired_training_and_actual_updates(self):
        config = dict(e.CONFIG, updates=2, batch_size=8, train_length=4, checkpoints=[0, 1, 2])
        hashes = []
        with tempfile.TemporaryDirectory() as temp:
            for h in (2, 3):
                for method in e.METHODS:
                    folder = Path(temp)/f"{method}-{h}"
                    folder.mkdir()
                    _, states, metadata = e.train(method, 9300004, config, folder, h, "mixed")
                    hashes.append(metadata["training_stream_sha256"])
                    self.assertTrue(any(not torch.equal(states[0][k], states[2][k]) for k in states[0]))
            self.assertEqual(len(set(hashes)), 1)

    def test_contrast_is_paired_difference_of_differences(self):
        row = {"conditions": {}}
        # Width 2 penalties: mixed 8, stable 2, changing 4 => D=5.
        # Width 12 penalties: mixed 3, stable 1, changing 1 => D=2. J=3.
        for h, penalties in ((2, {"mixed": 8, "stable": 2, "changing": 4}),
                             (12, {"mixed": 3, "stable": 1, "changing": 1})):
            for eco, p in penalties.items():
                row["conditions"][f"{eco}-h{h}"] = {
                    "shared": {"data_efficiency_excess": 10+p},
                    "separate": {"data_efficiency_excess": 10}}
        self.assertEqual(e.contrasts_for_row(row)["primary_memory_ecology_interaction"], 3)
        self.assertEqual(e.bootstrap([3]*8), [3, 3])

    def test_empty_family_summaries_are_not_nan(self):
        model = e.Learner("shared", 2)
        for eco in ("stable", "changing"):
            obs, family = e.sequences(np.random.default_rng(9300005), 8, 5, stable_prior=e.ECOLOGIES[eco])
            score = e.evaluate(model, obs, family, dict(e.CONFIG, train_length=3), eco)
            self.assertEqual(sum(v is None for v in score["family_excess"].values()), 1)
            self.assertTrue(np.isfinite(score["excess_brier"]))


if __name__ == "__main__":
    unittest.main()
