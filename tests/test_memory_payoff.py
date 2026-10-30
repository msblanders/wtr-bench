"""Integrity checks for a prospective readout comparison; no study-performance gates."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
    import torch
except ImportError as exc:
    raise unittest.SkipTest("Install experiments/memory-payoff-v1/requirements.txt") from exc

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT/"experiments/memory-payoff-v1"
sys.path.insert(0, str(DIRECTORY))
spec = importlib.util.spec_from_file_location("memory_payoff_experiment", DIRECTORY/"experiment.py")
assert spec is not None and spec.loader is not None
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


class MemoryPayoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        e.configure()

    def data(self, size=96, length=12):
        return e.worlds.synthetic(np.random.default_rng(171000001), size, length)

    def theta(self):
        return e.models.initial_mean()+np.random.default_rng(171000002).normal(0, .5, e.models.PARAMETERS).astype(np.float32)

    def test_parameter_counts_and_unchanged_world(self):
        for name in ("worlds.py", "external.py", "requirements.txt"):
            self.assertEqual((DIRECTORY/name).read_bytes(), (ROOT/"experiments/choice-objective-v1"/name).read_bytes())
        for readout in e.READOUTS:
            model = e.models.Small(self.theta(), readout)
            self.assertEqual(sum(p.numel() for p in model.parameters()), 269)
            self.assertEqual(e.models.resources("evolved", readout)["state_values"], 4)
        self.assertEqual(e.models.BASE, 257)

    def test_identical_recurrence_and_shared_base_predictions(self):
        theta = torch.tensor(self.theta()[None])
        data_inputs = e.models.inputs(self.data())
        a, b = [e.models.small(theta, data_inputs, r, return_state=True) for r in e.READOUTS]
        torch.testing.assert_close(a[2], b[2], rtol=0, atol=0)
        outputs = [e.models.small(theta, data_inputs, r, drop_extra=True) for r in e.READOUTS]
        for x, y in zip(*outputs):
            torch.testing.assert_close(x, y, rtol=0, atol=0)

    def test_readouts_equal_explicit_formulas_and_all_parameters_are_trainable(self):
        theta = torch.tensor(self.theta()[None], requires_grad=True)
        data = self.data()
        _, _, query, _ = e.models.inputs(data)
        state = torch.arange(len(data["x"])*4, dtype=torch.float32).reshape(1, -1, 4)/400
        _, _, w, out, extra = e.models.unpack(theta)
        z = torch.cat((state[0, :, None].expand(-1, query.shape[1], -1), query,
                       torch.ones((*query.shape[:2], 1))), -1)
        base = e.models.readout_logits(state, query, w, out, extra, "interaction", drop_extra=True)
        for readout in e.READOUTS:
            actual = e.models.readout_logits(state, query, w, out, extra, readout)
            if readout == "interaction":
                expected_extra = torch.einsum("bh,hq,bkq->bk", state[0], extra[0].reshape(4, 3), query[:, :, 3:6])[None]
            else:
                expected_extra = ((z@extra[0, :11]).tanh()*extra[0, 11])[None]
            torch.testing.assert_close(actual-base, expected_extra, rtol=1e-5, atol=1e-6)
            pred = e.models.small(theta, e.models.inputs(data), readout)
            grad = torch.autograd.grad(e.joint_loss(pred, data).sum(), theta, retain_graph=True)[0]
            self.assertTrue(torch.isfinite(grad).all())
            self.assertTrue((grad.abs() > 0).all())

    def test_joint_loss_uses_both_observed_channels_and_no_latent_truth(self):
        data = self.data()
        model = e.models.Small(self.theta(), "interaction")
        p, a = model(e.models.inputs(data))
        expected = .5*((p[..., 1]-torch.from_numpy(data["y_choice"])).square()+
                        (a-torch.from_numpy(data["y_ability"])).square()).mean(-1)
        torch.testing.assert_close(e.joint_loss((p, a), data), expected)
        altered = dict(data, truth_choice=np.full_like(data["truth_choice"], np.nan),
                       truth_ability=np.full_like(data["truth_ability"], np.nan))
        torch.testing.assert_close(e.joint_loss((p, a), altered), expected)
        with self.assertRaises(ValueError):
            e.joint_loss((p, a), dict(data, y_ability=np.full(len(data["x"]), -1)))

    def test_context_view_and_donor_histories_preserve_queries_and_outcomes(self):
        original = self.data()
        seen = e.seen_context(original)
        for key in original:
            if key != "query_context":
                np.testing.assert_array_equal(seen[key], original[key])
        for data in (original, seen):
            donor, order = e.donor_histories(data, np.random.default_rng(171000003))
            self.assertFalse(np.any(order == np.arange(len(order))))
            np.testing.assert_array_equal(np.sort(order), np.arange(len(order)))
            np.testing.assert_array_equal(data["query_context"][order], data["query_context"])
            for key in ("x", "lengths", "history_menus", "history_masks", "actions", "voluntary", "success", "observed", "contexts"):
                np.testing.assert_array_equal(donor[key], data[key][order])
            for key in ("query", "query_mask", "query_context", "y_choice", "y_ability", "truth_choice", "truth_ability"):
                np.testing.assert_array_equal(donor[key], data[key])
        with self.assertRaises(ValueError):
            e.donor_histories(self.data(size=1), np.random.default_rng(171000003))

    def test_paired_data_initialization_and_joint_checkpoint_judge(self):
        config = dict(e.CONFIG, generations=2, population=4, elites=2, batch_size=4,
                      validation_lifetimes=8, checkpoints=[0, 1, 2])
        all_meta, initials = [], []
        with tempfile.TemporaryDirectory() as temp:
            for readout in e.READOUTS:
                out = Path(temp)/readout
                out.mkdir()
                snapshots, metadata, validation, initial = e.search(171000004, config, out, readout)
                initials.append(initial)
                snapshots["matched_gradient"], metadata["matched_gradient"] = e.gradient(
                    "matched_gradient", 171000004, config, out, validation, initial, readout)
                for method in e.METHODS:
                    model = e.restored(method, snapshots[method][2], readout)
                    actual = float(e.joint_loss(model(e.models.inputs(validation)), validation)[0].detach())
                    self.assertAlmostEqual(actual, metadata[method]["selected_validation_joint_brier"], places=7)
                    self.assertIn(metadata[method]["selected_generation"], [0, 1, 2])
                raw = torch.load(out/"matched_gradient-last-update.pt", weights_only=True)
                self.assertTrue(any(not torch.equal(snapshots["matched_gradient"][0][k], raw[k]) for k in raw))
                all_meta.extend(metadata.values())
            for key in ("training_stream_sha256", "validation_sha256"):
                self.assertEqual(len({m[key] for m in all_meta}), 1)
            np.testing.assert_array_equal(initials[0], initials[1])

    def test_saved_arrays_reconstruct_each_readout_exactly(self):
        for readout in e.READOUTS:
            model = e.models.Small(self.theta(), readout)
            arrays = json.loads(json.dumps({key: value.detach().numpy().tolist() for key, value in model.state_dict().items()}))
            recovered = e.models.Small(np.zeros(e.models.PARAMETERS, np.float32), readout)
            recovered.load_state_dict({key: torch.tensor(value, dtype=torch.float32) for key, value in arrays.items()})
            for a, b in zip(e.predictions(model, self.data()), e.predictions(recovered, self.data())):
                np.testing.assert_array_equal(a, b)

    def test_analysis_signs_and_noninferiority_boundary(self):
        row = {"models": {}}
        for readout in e.READOUTS:
            row["models"][readout] = {}
            intact = .3 if readout == "wide_control" else .2
            def cells(value):
                return {s: {str(n): {"choice_brier": value, "execution_brier": value, "brier": value}
                            for n in e.CONFIG["primary_lengths"]} for s in e.SUITES}
            for method in e.METHODS:
                row["models"][readout][method] = {"checkpoints": {"512": cells(intact)},
                    "no_memory": cells(intact+.05), "donor_history": cells(intact+.03), "drop_extra": cells(intact+.02)}
        result = e.contrasts(row)
        for key, value in result.items():
            expected = .1 if key.endswith("control_minus_interaction") else 0 if key.endswith("donor_gain_interaction") else .05 if key.endswith("memory_gain") else .03 if key.endswith("donor_gain") else .02
            self.assertAlmostEqual(value, expected)
        rules = e.primary_rules()
        self.assertEqual(len(rules), 4)
        self.assertEqual(rules["canonical_seen/evolved/execution_brier/control_minus_interaction"], -.002)
        self.assertEqual(e.bootstrap([2]*8), [2, 2])


if __name__ == "__main__":
    unittest.main()
