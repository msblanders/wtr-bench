"""Integrity checks for a paired objective ablation, without performance gates."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
    import torch
except ImportError as exc:
    raise unittest.SkipTest("Install experiments/choice-objective-v1/requirements.txt") from exc

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT/"experiments/choice-objective-v1"
sys.path.insert(0, str(DIRECTORY))
spec = importlib.util.spec_from_file_location("choice_objective_experiment", DIRECTORY/"experiment.py")
assert spec is not None and spec.loader is not None
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


class ChoiceObjectiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        e.configure()

    def data(self, size=96, length=12):
        return e.worlds.synthetic(np.random.default_rng(151000001), size, length)

    def model(self):
        values = e.models.initial_mean()+np.random.default_rng(151000002).normal(0, .5, e.models.PARAMETERS).astype(np.float32)
        return e.models.Small(values)

    def test_architectures_worlds_and_external_adapter_are_unchanged(self):
        prior = ROOT/"experiments/discovery-transfer-v1"
        for name in ("models.py", "worlds.py", "external.py", "requirements.txt"):
            self.assertEqual((DIRECTORY/name).read_bytes(), (prior/name).read_bytes())
        self.assertEqual(e.models.resources("evolved")["parameters"], 257)
        self.assertEqual(e.models.resources("dense_gradient")["parameters"], 1969)

    def test_joint_loss_matches_predecessor_and_choice_removes_only_execution(self):
        data = self.data()
        pred = self.model()(e.models.inputs(data))
        joint = e.objective_loss(pred, data, "joint")
        choice = e.objective_loss(pred, data, "choice_only")
        torch.testing.assert_close(joint, e.models.observed_loss(pred, data))
        p, a = pred
        expected = .5*(a-torch.from_numpy(data["y_ability"])).square().mean(-1)
        torch.testing.assert_close(joint-choice, expected)
        altered = dict(data, y_ability=1-data["y_ability"], truth_choice=np.full_like(data["truth_choice"], np.nan),
                       truth_ability=np.full_like(data["truth_ability"], np.nan))
        torch.testing.assert_close(choice, e.objective_loss(pred, altered, "choice_only"))
        observed_choice = .5*(p[..., 1]-torch.from_numpy(data["y_choice"])).square().mean(-1)
        torch.testing.assert_close(choice, observed_choice)
        with self.assertRaises(ValueError):
            e.objective_loss(pred, data, "unknown")

    def test_choice_gradient_coefficient_is_held_fixed(self):
        data = self.data()
        p = torch.full((1, len(data["x"]), 2), .5, requires_grad=True)
        a = torch.full((1, len(data["x"])), .4, requires_grad=True)
        cg = torch.autograd.grad(e.objective_loss((p, a), data, "choice_only").sum(), p, retain_graph=True)[0]
        jg = torch.autograd.grad(e.objective_loss((p, a), data, "joint").sum(), p)[0]
        torch.testing.assert_close(cg, jg)

    def test_observed_context_view_preserves_shared_trait_targets(self):
        data = self.data()
        seen = e.seen_context(data)
        self.assertTrue(np.all(data["query_context"] != data["contexts"][:, 0]))
        np.testing.assert_array_equal(seen["query_context"], data["contexts"][:, 0])
        for key in data:
            if key != "query_context":
                np.testing.assert_array_equal(seen[key], data[key])
        for a, b in zip(e.worlds.functional_reference(data), e.worlds.functional_reference(seen)):
            np.testing.assert_allclose(a, b, atol=1e-12)

    def test_donor_controls_derange_histories_without_moving_queries_or_targets(self):
        for data in (self.data(), e.seen_context(self.data())):
            donor, permutation = e.donor_histories(data, np.random.default_rng(151000003))
            self.assertFalse(np.any(permutation == np.arange(len(permutation))))
            np.testing.assert_array_equal(np.sort(permutation), np.arange(len(permutation)))
            np.testing.assert_array_equal(data["query_context"][permutation], data["query_context"])
            for key in ("x", "lengths", "history_menus", "history_masks", "actions", "voluntary", "success", "observed", "contexts"):
                np.testing.assert_array_equal(donor[key], data[key][permutation])
            for key in ("query", "query_mask", "query_context", "y_choice", "y_ability", "truth_choice", "truth_ability"):
                np.testing.assert_array_equal(donor[key], data[key])
        singleton = self.data(size=1)
        with self.assertRaises(ValueError):
            e.donor_histories(singleton, np.random.default_rng(151000003))

    def test_all_eight_trainings_share_data_initialization_and_choice_judge(self):
        config = dict(e.CONFIG, generations=2, population=4, elites=2, batch_size=4,
                      validation_lifetimes=8, checkpoints=[0, 1, 2])
        all_meta, all_snapshots, initials = [], {}, []
        with tempfile.TemporaryDirectory() as temp:
            for objective in e.OBJECTIVES:
                out = Path(temp)/objective
                out.mkdir()
                snapshots, metadata, validation, initial = e.search(151000004, config, out, objective)
                initials.append(initial)
                for method in e.METHODS[2:]:
                    snapshots[method], metadata[method] = e.gradient(method, 151000004, config, out, validation, initial, objective)
                    raw = torch.load(out/f"{method}-last-update.pt", weights_only=True)
                    self.assertTrue(any(not torch.equal(snapshots[method][0][k], raw[k]) for k in raw))
                for method in e.METHODS:
                    model = e.restored(method, snapshots[method][2])
                    actual = float(e.objective_loss(model(e.models.inputs(validation)), validation, "choice_only")[0].detach())
                    self.assertAlmostEqual(actual, metadata[method]["selected_validation_half_choice_brier"], places=7)
                    self.assertIn(metadata[method]["selected_generation"], [0, 1, 2])
                all_meta.extend(metadata.values())
                all_snapshots[objective] = snapshots
            for key in ("training_stream_sha256", "validation_sha256"):
                self.assertEqual(len({m[key] for m in all_meta}), 1)
            np.testing.assert_array_equal(initials[0], initials[1])
            for key, value in all_snapshots["joint"]["dense_gradient"][0].items():
                torch.testing.assert_close(value, all_snapshots["choice_only"]["dense_gradient"][0][key])

    def test_saved_parameter_arrays_reconstruct_predictions(self):
        data = self.data()
        for model in (self.model(), e.models.Dense()):
            arrays = {key: value.detach().numpy().tolist() for key, value in model.state_dict().items()}
            reconstructed = e.models.Small(np.zeros(e.models.PARAMETERS, np.float32)) if isinstance(model, e.models.Small) else e.models.Dense()
            reconstructed.load_state_dict({key: torch.tensor(value, dtype=torch.float32) for key, value in arrays.items()})
            for a, b in zip(e.predictions(model, data), e.predictions(reconstructed, data)):
                np.testing.assert_array_equal(a, b)

    def test_contrasts_use_choice_scores_and_the_correct_paired_sign(self):
        row = {"models": {}}
        for objective in e.OBJECTIVES:
            row["models"][objective] = {}
            intact = .3 if objective == "joint" else .2
            zero = .29 if objective == "joint" else .28
            donor = .32 if objective == "joint" else .29
            for method in e.METHODS:
                cell = lambda value: {suite: {str(n): {"choice_brier": value, "execution_brier": 99.} for n in e.CONFIG["primary_lengths"]} for suite in e.SUITES}
                row["models"][objective][method] = {"checkpoints": {"512": cell(intact)}, "no_memory": cell(zero), "donor_history": cell(donor)}
        values = e.contrasts(row)
        for suite in e.SUITES:
            for method in e.METHODS:
                prefix = suite+"/"+method+"/"
                self.assertAlmostEqual(values[prefix+"joint_minus_choice"], .1)
                self.assertAlmostEqual(values[prefix+"choice_only_memory_gain"], .08)
                self.assertAlmostEqual(values[prefix+"choice_only_donor_gain"], .09)
                self.assertAlmostEqual(values[prefix+"donor_gain_interaction"], .07)
        self.assertEqual(e.bootstrap([2]*8), [2, 2])


if __name__ == "__main__":
    unittest.main()
