"""Scientific integrity checks for learned social cue transfer."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
    import torch
except ImportError as exc:
    raise unittest.SkipTest("Install experiments/cue-transfer-v1/requirements.txt") from exc

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


e = load("cue_transfer", ROOT/"experiments/cue-transfer-v1/experiment.py")
legacy = load("legacy_social_world", ROOT/"experiments/functional-learning-v1/experiment.py")


class CueTransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        e.configure()

    def test_reference_matches_independent_legacy_scalar_estimator(self):
        for regime in e.REGIMES:
            for suite in e.SUITES:
                data = e.batch(np.random.default_rng(111000001), 8, 24, regime, suite=suite)
                for n in (0, 2, 8, 24):
                    q = e.posterior(data["x"], np.full(8, n), regime)
                    for b in range(8):
                        records = []
                        for row in data["x"][b, :n]:
                            records.append({"partner": "p", "setting": int(row[3:].argmax()),
                                "instruction": "VOLUNTARY" if row[0] else "ASSIGNED",
                                "attempt": bool(row[1]), "outcome": ("success" if row[2] else "failure") if row[1] else "none"})
                        for c in range(3):
                            for k, kind in enumerate(("choice", "execution")):
                                expected = legacy.estimate(records, {"partner": "p", "setting": c, "kind": kind}, "oracle", regime)
                                self.assertAlmostEqual(q[b, c, k], expected, places=12)

    def test_generator_holds_out_a_context_and_has_binary_observed_targets(self):
        for suite in e.SUITES:
            data = e.batch(np.random.default_rng(111000002), 2048, 24, "shared", suite=suite)
            contexts = data["x"][..., 3:].argmax(-1)
            self.assertTrue(np.all(contexts != data["heldout"][:, None]))
            self.assertEqual(data["targets"].shape, (2048, 3, 2))
            self.assertTrue(set(data["targets"].ravel()) == {0, 1})
            self.assertTrue(np.all(data["x"][..., 2] <= data["x"][..., 1]))
            assigned = data["x"][..., 0] == 0
            self.assertTrue(np.all(data["x"][..., 1][assigned] == 1))
            if suite == "canonical":
                for c in range(3):
                    rate = assigned[contexts == c].mean()
                    self.assertLess(abs(rate-e.SUITES[suite][c]), .025)

    def test_filtered_streams_and_wrong_rules_are_not_a_head_permutation(self):
        # Assigned success, voluntary failure, voluntary refusal, voluntary success.
        x = torch.tensor([[[0., 1., 1., 1., 0., 0.], [1., 1., 0., 1., 0., 0.],
                           [1., 0., 0., 0., 1., 0.], [1., 1., 1., 0., 1., 0.]]])
        inputs, counts = e.filtered_inputs(x, torch.tensor([4]))
        self.assertEqual(counts.tolist(), [3, 3])
        self.assertEqual(inputs[0, :3, 0].tolist(), [1, 0, 1])
        self.assertEqual(inputs[1, :3, 0].tolist(), [1, 0, 1])
        wrong, wn = e.filtered_inputs(x, torch.tensor([4]), wrong=True)
        self.assertEqual(wn.tolist(), [4, 4])
        self.assertEqual(wrong[0, :, 0].tolist(), [1, 1, 0, 1])
        self.assertEqual(wrong[1, :, 0].tolist(), [1, 0, 0, 1])

    def test_reference_double_dissociation_and_boundary(self):
        x = np.array([[[0, 1, 1, 1, 0, 0], [1, 1, 0, 1, 0, 0],
                       [1, 0, 0, 1, 0, 0], [1, 1, 1, 0, 1, 0]]], dtype=np.float32)
        q = e.posterior(x, np.array([4]), "shared")
        np.testing.assert_allclose(q, np.full((1, 3, 2), .6), atol=1e-12)
        local = e.posterior(x, np.array([4]), "context_specific")
        np.testing.assert_allclose(local[0, :, 0], [.5, 2/3, .5], atol=1e-12)
        np.testing.assert_allclose(local[0, :, 1], [.6]*3, atol=1e-12)

    def test_no_future_or_padding_leak_and_lifetime_reset(self):
        data = e.batch(np.random.default_rng(111000003), 8, 24, "shared")
        x, _ = e.tensors(data)
        changed = x.clone()
        changed[:, 8:] = 1-changed[:, 8:]
        lengths = torch.full((8,), 8)
        for method in e.METHODS:
            torch.manual_seed(111000004)
            model = e.Learner(method)
            with torch.no_grad():
                p = model(x, lengths)
                torch.testing.assert_close(p, model(changed, lengths))
                torch.testing.assert_close(p, model(x.flip(0), lengths).flip(0))
                torch.testing.assert_close(p[:1], model(x[:1], lengths[:1]))
                empty = torch.zeros_like(lengths)
                torch.testing.assert_close(model(x, empty), model(changed, empty))

    def test_functional_null_updates_and_context_invariance(self):
        data = e.batch(np.random.default_rng(111000005), 8, 24, "shared")
        x, lengths = e.tensors(data)
        # Any assigned success/failure alteration must leave willingness unchanged.
        changed = x.clone()
        assigned = changed[..., 0] == 0
        changed[..., 2][assigned] = 1-changed[..., 2][assigned]
        model = e.Learner("functional")
        with torch.no_grad():
            p = model(x, lengths)
            torch.testing.assert_close(p[..., 0], model(changed, lengths)[..., 0])
            relabeled = x.clone()
            relabeled[..., 3:] = x[..., 3:][..., [1, 0, 2]]
            torch.testing.assert_close(p, model(relabeled, lengths))

    def test_resources_and_ablation_initialization_match(self):
        models = {}
        for method in e.METHODS:
            torch.manual_seed(111000006)
            models[method] = e.Learner(method)
        for method, expected in (("history", 1506), ("functional", 330), ("wrong_rules", 330)):
            r = e.resources(models[method])
            self.assertEqual(r["parameters"], expected)
            self.assertEqual(r["state_values"], 16)
        for key, tensor in models["functional"].state_dict().items():
            torch.testing.assert_close(tensor, models["wrong_rules"].state_dict()[key])

    def test_training_is_real_and_all_models_get_identical_observations_and_targets(self):
        config = dict(e.CONFIG, updates=2, batch_size=8, checkpoints=[0, 1, 2])
        hashes = []
        with tempfile.TemporaryDirectory() as temp:
            for method in e.METHODS:
                folder = Path(temp)/method
                folder.mkdir()
                _, snapshots, metadata = e.train(method, 111000007, "shared", config, folder)
                hashes.append(metadata["training_stream_sha256"])
                self.assertTrue(any(not torch.equal(snapshots[0][k], snapshots[2][k]) for k in snapshots[0]))
            self.assertEqual(len(set(hashes)), 1)

    def test_contrasts_and_constant_bootstrap(self):
        row = {"models": {}}
        for regime in e.REGIMES:
            row["models"][regime] = {}
            for method in e.METHODS:
                v = {"functional": 2 if regime == "shared" else 5, "history": 3, "wrong_rules": 4}[method]
                row["models"][regime][method] = {"curve_means": {"reversed": v},
                    "checkpoints": {"1024": {"reversed": {str(n): {"transfer_excess": v} for n in e.CONFIG["test_lengths"]}}}}
        c = e.contrasts_for_row(row)
        self.assertEqual(c["shared_history_minus_functional"], 1)
        self.assertEqual(c["context_specific_history_minus_functional"], -2)
        self.assertEqual(c["boundary_interaction"], 3)
        self.assertEqual(e.bootstrap([3]*8), [3, 3])


if __name__ == "__main__":
    unittest.main()
