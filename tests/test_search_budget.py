"""Integrity checks for fixed evidence and compute budgets; no performance gates."""
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
    raise unittest.SkipTest("Install experiments/search-budget-v1/requirements.txt") from exc

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT/"experiments/search-budget-v1"
sys.path.insert(0, str(DIRECTORY))
spec = importlib.util.spec_from_file_location("search_budget_experiment", DIRECTORY/"experiment.py")
assert spec is not None and spec.loader is not None
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


class SearchBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        e.configure()

    def data(self, size=96, length=12):
        return e.worlds.synthetic(np.random.default_rng(191000001), size, length)

    def theta(self):
        return e.models.initial_mean()+np.random.default_rng(191000002).normal(0, .5, e.models.PARAMETERS).astype(np.float32)

    def test_parameter_counts_and_unchanged_world(self):
        for name in ("models.py", "worlds.py", "external.py", "requirements.txt"):
            self.assertEqual((DIRECTORY/name).read_bytes(), (ROOT/"experiments/memory-payoff-v1"/name).read_bytes())
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
            donor, order = e.donor_histories(data, np.random.default_rng(191000003))
            self.assertFalse(np.any(order == np.arange(len(order))))
            np.testing.assert_array_equal(np.sort(order), np.arange(len(order)))
            np.testing.assert_array_equal(data["query_context"][order], data["query_context"])
            for key in ("x", "lengths", "history_menus", "history_masks", "actions", "voluntary", "success", "observed", "contexts"):
                np.testing.assert_array_equal(donor[key], data[key][order])
            for key in ("query", "query_mask", "query_context", "y_choice", "y_ability", "truth_choice", "truth_ability"):
                np.testing.assert_array_equal(donor[key], data[key])
        with self.assertRaises(ValueError):
            e.donor_histories(self.data(size=1), np.random.default_rng(191000003))

    def tiny_config(self):
        return dict(e.CONFIG, generations=8, budgets=[2, 8], bank_batches=2, development_candidates=2,
                    population=4, elites=2, batch_size=4, validation_lifetimes=8)

    def test_bank_replays_exact_observations_and_each_pass_is_a_permutation(self):
        config = self.tiny_config()
        bank, cached, order, bank_hash = e.make_bank(191000004, config)
        self.assertEqual(len(bank), 2)
        self.assertEqual(len(cached), 2)
        np.testing.assert_array_equal(order[:2], [0, 1])
        for start in range(0, len(order), 2):
            np.testing.assert_array_equal(np.sort(order[start:start+2]), [0, 1])
        again = e.make_bank(191000004, config)
        self.assertEqual(bank_hash, again[3])
        np.testing.assert_array_equal(order, again[2])
        for first, second in zip(bank, again[0]):
            for key in first:
                np.testing.assert_array_equal(first[key], second[key])
        for b in config["budgets"]:
            self.assertEqual(sum(b in e.due_budgets(g, config) for g in range(1, b+1)), 2)
        self.assertEqual(e.due_budgets(1, config), [2])
        self.assertEqual(e.due_budgets(4, config), [8])

    def test_paired_training_and_budget_specific_development_selection(self):
        config = self.tiny_config()
        bank_info = e.make_bank(191000004, config)
        all_meta, initials = [], []
        with tempfile.TemporaryDirectory() as temp:
            for readout in e.READOUTS:
                out = Path(temp)/readout
                out.mkdir()
                snapshots, metadata, validation, initial = e.search(191000004, config, out, readout, bank_info)
                initials.append(initial)
                snapshots["matched_gradient"], metadata["matched_gradient"] = e.gradient(
                    "matched_gradient", 191000004, config, out, validation, initial, readout, bank_info)
                for method in e.METHODS:
                    self.assertEqual(metadata[method]["development_evaluations_by_budget"], {2: 3, 8: 3})
                    self.assertEqual(metadata[method]["unique_training_lifetimes"], 8)
                    self.assertEqual(metadata[method]["training_presentations"], 32)
                    self.assertEqual(metadata[method]["training_prefix_sha256"]["2"], bank_info[3])
                    for budget in config["budgets"]:
                        model = e.restored(method, snapshots[method][budget], readout)
                        actual = float(e.joint_loss(model(e.models.inputs(validation)), validation)[0].detach())
                        selected = metadata[method]["budget_selection"][str(budget)]
                        self.assertAlmostEqual(actual, selected["selected_validation_joint_brier"], places=7)
                        self.assertLessEqual(selected["selected_generation"], budget)
                        self.assertEqual(selected["selected_generation"] % (budget//config["development_candidates"]), 0)
                    if method != "random_search":
                        self.assertIn("raw_2", snapshots[method])
                        self.assertIn("raw_8", snapshots[method])
                all_meta.extend(metadata.values())
                # A separately stopped two-step run must produce exactly the same short-budget champion.
                short = dict(config, generations=2, budgets=[2])
                small_bank = (bank_info[0], bank_info[1], bank_info[2][:2], bank_info[3])
                short_out = out/"short"
                short_out.mkdir()
                short_snap, _, short_validation, short_initial = e.search(191000004, short, short_out, readout, small_bank)
                short_snap["matched_gradient"], _ = e.gradient(
                    "matched_gradient", 191000004, short, short_out, short_validation, short_initial, readout, small_bank)
                for method in e.METHODS:
                    a = e.restored(method, snapshots[method][2], readout)
                    b = e.restored(method, short_snap[method][2], readout)
                    for key in a.state_dict():
                        torch.testing.assert_close(a.state_dict()[key], b.state_dict()[key], rtol=0, atol=0)
            for key in ("training_stream_sha256", "bank_sha256", "validation_sha256"):
                self.assertEqual(len({m[key] for m in all_meta}), 1)
            np.testing.assert_array_equal(initials[0], initials[1])
        import hashlib
        hasher = hashlib.sha256()
        for data in bank_info[0]:
            e.stream_update(hasher, data)
        self.assertEqual(hasher.hexdigest(), bank_info[3])

    def test_saved_arrays_reconstruct_each_readout_exactly(self):
        for readout in e.READOUTS:
            model = e.models.Small(self.theta(), readout)
            arrays = json.loads(json.dumps({key: value.detach().numpy().tolist() for key, value in model.state_dict().items()}))
            recovered = e.models.Small(np.zeros(e.models.PARAMETERS, np.float32), readout)
            recovered.load_state_dict({key: torch.tensor(value, dtype=torch.float32) for key, value in arrays.items()})
            for a, b in zip(e.predictions(model, self.data()), e.predictions(recovered, self.data())):
                np.testing.assert_array_equal(a, b)

    def test_budget_contrast_signs_and_noninferiority_rule(self):
        row = {"models": {}}
        for readout in e.READOUTS:
            row["models"][readout] = {}
            for method in e.METHODS:
                budgets = {}
                for budget in e.CONFIG["budgets"]:
                    intact = (.3 if budget == 512 else .2)+(.04 if readout == "wide_control" else 0)
                    donor_gain = .01 if budget == 512 else .03
                    def cells(v):
                        return {s: {str(n): {"choice_brier": v, "execution_brier": v, "brier": v}
                                    for n in e.CONFIG["primary_lengths"]} for s in e.SUITES}
                    budgets[str(budget)] = {"intact": cells(intact), "donor_history": cells(intact+donor_gain),
                                           "no_memory": cells(intact+.05), "drop_extra": cells(intact+.02)}
                row["models"][readout][method] = {"budgets": budgets}
        result = e.contrasts(row)
        for key, value in result.items():
            if key.endswith("low_minus_high"):
                expected = .1
            elif key.endswith("control_minus_interaction"):
                expected = .04
            elif key.endswith("advantage_growth"):
                expected = 0
            elif key.endswith("donor_gain_growth"):
                expected = .02
            elif key.endswith("memory_gain"):
                expected = .05
            elif key.endswith("extra_gain"):
                expected = .02
            else:
                expected = .01 if key.endswith("low_donor_gain") else .03
            self.assertAlmostEqual(value, expected)
        rules = e.primary_rules()
        self.assertEqual(len(rules), 5)
        self.assertEqual(rules["canonical_seen/evolved/interaction/execution_brier/low_minus_high"], -.002)
        self.assertEqual(e.bootstrap([2]*8), [2, 2])


if __name__ == "__main__":
    unittest.main()
