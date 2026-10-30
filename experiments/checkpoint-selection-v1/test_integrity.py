"""Scientific invariants for the prospectively frozen selection-policy comparison."""
from __future__ import annotations

import contextlib
import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import baseline
import experiment as study
import models
import numpy as np
import torch
import worlds


class Integrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline.configure()

    def test_guard_excludes_execution_damage_and_keeps_joint_feasible(self):
        rows = [{'step': i, 'choice': c, 'execution': e, 'joint': j} for i, c, e, j in
                [(0, .4, .3, .35), (1, .35, .1, .225), (2, .3, .11, .23), (3, .33, .101, .23)]]
        cfg = dict(study.CONFIG, development_candidates=3)
        selected, pool = study.select_policies(rows, 3, cfg)
        self.assertEqual(selected['joint']['step'], 1)
        self.assertEqual(selected['guarded_choice']['step'], 3)
        self.assertEqual(pool['guarded_feasible_count'], 2)

    def test_equal_development_counts_and_distinct_grids(self):
        steps = [0]+[s for s in range(1, 2049) if baseline.due_budgets(s, study.CONFIG)]
        self.assertEqual(len(steps), 897)
        rows = [{'step': s, 'choice': .2, 'execution': .2, 'joint': .2} for s in steps]
        for budget in (512, 2048):
            selected, pool = study.select_policies(rows, budget, study.CONFIG)
            self.assertEqual(pool['candidate_count'], 513)
            self.assertEqual(selected['joint']['step'], 0)
            self.assertEqual(selected['guarded_choice']['step'], 0)
            self.assertEqual(selected['raw_last']['step'], budget)
        self.assertIn(1, study.select_policies(rows, 512, study.CONFIG)[1]['candidate_steps'])
        self.assertNotIn(1, study.select_policies(rows, 2048, study.CONFIG)[1]['candidate_steps'])

    def test_future_candidates_cannot_change_short_selection(self):
        cfg = dict(study.CONFIG, development_candidates=2)
        rows = [{'step': i, 'choice': .2, 'execution': .2, 'joint': .2} for i in range(5)]
        before = study.select_policies(rows, 2, cfg)
        rows[4].update(choice=0., execution=0., joint=0.)
        self.assertEqual(before, study.select_policies(rows, 2, cfg))

    def test_selector_rejects_missing_candidates(self):
        with self.assertRaises(ValueError):
            study.select_policies([{'step': 0, 'choice': .2, 'execution': .2, 'joint': .2}], 512, study.CONFIG)

    def test_component_scores_match_original_joint_arithmetic(self):
        data = worlds.synthetic(np.random.default_rng(1), 32, 24, training=True)
        theta = models.initial_mean()+np.random.default_rng(2).normal(0, .2, 269).astype(np.float32)
        di = models.inputs(data)
        for readout in models.READOUTS:
            result = study.component_scores(theta, data, di, readout)
            original = baseline.vector_loss(theta[None], data, di, readout)[0]
            self.assertEqual(result['joint'], original)
            self.assertAlmostEqual(result['joint'], .5*(result['choice']+result['execution']), places=6)

    def test_latent_truth_cannot_affect_training_or_selection_scores(self):
        data = worlds.synthetic(np.random.default_rng(3), 16, 24, training=True)
        theta = models.initial_mean()
        old = study.component_scores(theta, data, models.inputs(data), 'interaction')
        changed = dict(data, truth_choice=np.full_like(data['truth_choice'], np.nan),
                       truth_ability=np.full_like(data['truth_ability'], np.nan))
        self.assertEqual(old, study.component_scores(theta, changed, models.inputs(changed), 'interaction'))

    def test_new_seed_plan_disjoint_and_replicable(self):
        old = {v for s in range(8) for v in baseline.seeds_for(s).values()}
        new = [v for s in range(8) for v in study.seeds_for(s).values()]
        self.assertFalse(old.intersection(new))
        self.assertEqual(len(new), len(set(new)))
        self.assertEqual(study.seeds_for(0)['evaluation'], 246000000)

    def test_training_bank_reuses_identical_evidence(self):
        cfg = dict(study.CONFIG, generations=8, budgets=[4, 8], bank_batches=4,
                   development_candidates=4, batch_size=8)
        bank, _, order, bank_hash = study.make_bank(0, cfg)
        self.assertEqual(sorted(order[:4]), [0, 1, 2, 3])
        self.assertEqual(sorted(order[4:]), [0, 1, 2, 3])
        h = hashlib.sha256()
        for data in bank:
            baseline.stream_update(h, data)
        self.assertEqual(bank_hash, h.hexdigest())

    def test_training_trajectory_and_joint_selection_exactly_recover_baseline(self):
        cfg = dict(study.CONFIG, generations=8, budgets=[4, 8], bank_batches=4,
                   development_candidates=4, batch_size=8, validation_lifetimes=16, population=4, elites=2)
        bank = study.make_bank(1, cfg)
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            for readout in models.READOUTS:
                root = Path(temp)/readout
                root.mkdir()
                old = root/'old'
                old.mkdir()
                with patch.object(baseline, 'seeds_for', study.seeds_for):
                    original, meta, validation, initial = baseline.search(1, cfg, old, readout, bank)
                    original_gradient, _ = baseline.gradient('matched_gradient', 1, cfg, old, validation, initial, readout, bank)
                for method in study.METHODS:
                    candidates, record = study.train(1, cfg, root/method, readout, method, bank)
                    for b in (4, 8):
                        selected = candidates[record['selection'][str(b)]['joint']['step']]
                        if method == 'evolved':
                            np.testing.assert_array_equal(selected, original[method][b])
                            np.testing.assert_array_equal(candidates[b], original[method][f'raw_{b}'])
                            self.assertEqual(record['selection'][str(b)]['joint']['step'],
                                             meta[method]['budget_selection'][str(b)]['selected_generation'])
                        else:
                            np.testing.assert_array_equal(selected, original_gradient[b]['theta'].numpy())
                            np.testing.assert_array_equal(candidates[b], original_gradient[f'raw_{b}']['theta'].numpy())
                    with np.load(root/method/f'{method}-candidates.npz', allow_pickle=False) as archive:
                        self.assertEqual(record['candidate_theta_sha256'], hashlib.sha256(archive['theta'].tobytes()).hexdigest())

    def test_readouts_have_equal_parameter_counts_and_distinct_functions(self):
        theta = np.random.default_rng(4).normal(0, .2, models.PARAMETERS).astype(np.float32)
        data = worlds.synthetic(np.random.default_rng(5), 8, 24)
        a, b = [models.Small(theta, r) for r in models.READOUTS]
        self.assertEqual(sum(p.numel() for p in a.parameters()), 269)
        self.assertEqual(sum(p.numel() for p in b.parameters()), 269)
        self.assertFalse(torch.equal(a(models.inputs(data))[0], b(models.inputs(data))[0]))

    def test_donor_histories_preserve_targets_and_strata(self):
        data = baseline.seen_context(worlds.synthetic(np.random.default_rng(6), 512, 24))
        changed, permutation = baseline.donor_histories(data, np.random.default_rng(7))
        self.assertTrue(np.all(permutation != np.arange(512)))
        for key in ('query', 'query_mask', 'query_context', 'y_choice', 'y_ability'):
            np.testing.assert_array_equal(changed[key], data[key])
        np.testing.assert_array_equal(data['query_context'][permutation], data['query_context'])
        np.testing.assert_array_equal(changed['x'], data['x'][permutation])

    def test_primary_rules_require_learning_and_execution_safeguard(self):
        rules = study.primary_rules()
        self.assertEqual(len(rules), 5)
        self.assertEqual(list(rules.values()).count(0.), 4)
        self.assertIn(-.002, rules.values())
        self.assertTrue(all('canonical_seen/evolved/interaction/' in k for k in rules))
        result = study.estimate([1.]*8)
        self.assertEqual(result['paired_bootstrap_95ci'], [1., 1.])


if __name__ == '__main__':
    unittest.main(verbosity=2)
