"""Independent arithmetic and NumPy checkpoint audit; never trains a model.

Usage: python audit_results.py ROOT
ROOT contains frozen/, results/, and collected/seed-0 through seed-7.
Uses NumPy; PyTorch files are inspected as raw ZIP tensor storage, not unpickled.
"""
import hashlib
import importlib.util
import json
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(sys.argv[1]).resolve()
OUTPUT = ROOT
if (ROOT / 'archives').is_dir():
    provenance = json.loads((ROOT / 'provenance.json').read_text())
    scratch = tempfile.TemporaryDirectory(prefix='search-budget-audit-')
    for artifact in provenance['artifacts']:
        archive = ROOT / 'archives' / (artifact['name'] + '.zip')
        assert archive.stat().st_size == artifact['size_in_bytes']
        assert 'sha256:' + hashlib.sha256(archive.read_bytes()).hexdigest() == artifact['digest']
        name = artifact['name']
        destination = ('frozen' if '-protocol-' in name else 'results' if '-results-' in name
                       else 'collected/seed-' + name.split('-')[3])
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist())
            z.extractall(Path(scratch.name) / destination)
    ROOT = Path(scratch.name)
rows = json.loads((ROOT / 'results/replicate-results.json').read_text())
summary = json.loads((ROOT / 'results/summary.json').read_text())
manifest = json.loads((ROOT / 'frozen/manifest.json').read_text())
assert [r['replicate'] for r in rows] == list(range(8))
assert json.loads((ROOT / 'results/manifest.json').read_text()) == manifest
for name, expected in manifest['source_hashes'].items():
    assert hashlib.sha256((ROOT / 'frozen' / name).read_bytes()).hexdigest() == expected
for name, expected in manifest['external_sha256'].items():
    assert hashlib.sha256((ROOT / 'frozen/upstream' / name).read_bytes()).hexdigest() == expected


def score(row, readout, method, suite, budget, kind, metric):
    values = row['models'][readout][method]['budgets'][str(budget)][kind][suite]
    return sum(values[str(n)][metric] for n in (4, 12, 24)) / 3


def contrast(row, key):
    suite, method, readout, metric, effect = key.split('/')
    def val(budget, kind='intact', arm=readout):
        return score(row, arm, method, suite, budget, kind, metric)
    if readout == 'readouts':
        def advantage(budget):
            return val(budget, arm='wide_control') - val(budget, arm='interaction')
        if effect == 'advantage_growth':
            return advantage(2048) - advantage(512)
        return advantage(512 if effect.startswith('low_') else 2048)
    if effect == 'low_minus_high':
        return val(512) - val(2048)
    if effect == 'donor_gain_growth':
        return (val(2048, 'donor_history') - val(2048)) - (val(512, 'donor_history') - val(512))
    level, intervention, _ = effect.split('_')
    kind = {'memory': 'no_memory', 'donor': 'donor_history', 'extra': 'drop_extra'}[intervention]
    budget = 512 if level == 'low' else 2048
    return val(budget, kind) - val(budget)


indices = np.random.default_rng(188000000).integers(0, 8, size=(10000, 8))
def estimate(values):
    v = np.asarray(values, dtype=np.float64)
    return {'mean': float(v.mean()),
            'paired_bootstrap_95ci': np.quantile(v[indices].mean(axis=1), [.025, .975]).tolist(),
            'run_differences': v.tolist()}


maximum_summary_error = 0.0
recomputed = {}
for key, reported in summary['contrasts'].items():
    item = estimate([contrast(row, key) for row in rows])
    for field in ('mean', 'paired_bootstrap_95ci', 'run_differences'):
        error = float(np.max(np.abs(np.asarray(item[field]) - np.asarray(reported[field]))))
        maximum_summary_error = max(maximum_summary_error, error)
        assert error < 1e-14, (key, field, error)
    recomputed[key] = item

primary = {k: recomputed[k]['paired_bootstrap_95ci'][0] > threshold
           for k, threshold in summary['joint_primary_criteria'].items()}
assert all(primary.values()) == summary['joint_primary_pass']
assert sum(primary.values()) == 4
for record in summary['secondary_original_architecture_checks'].values():
    assert all(recomputed[k]['paired_bootstrap_95ci'][0] > t
               for k, t in record['criteria'].items()) == record['pass']

# Verify the serialized aggregate against every original seed artifact and its design metadata.
for row in rows:
    folder = ROOT / 'collected' / f"seed-{row['replicate']}"
    assert json.loads((folder / f"result-seed-{row['replicate']}.json").read_text()) == row
    assert json.loads((folder / 'manifest.json').read_text()) == manifest
    assert row['source_hashes'] == manifest['source_hashes']
    assert row['config_sha256'] == manifest['config_sha256']
    assert row['seeds'] == manifest['seed_plan'][row['replicate']]
    all_models = [v for arm in row['models'].values() for v in arm.values()]
    for field in ('training_stream_sha256', 'bank_sha256', 'validation_sha256'):
        assert len({m[field] for m in all_models}) == 1
    for m in all_models:
        assert m['unique_training_lifetimes'] == 32768
        assert m['development_evaluations_by_budget'] == {'512': 513, '2048': 513}
        assert m['resources']['parameters'] == 269
        assert m['training_prefix_sha256']['512'] == m['bank_sha256']
        for b in (512, 2048):
            choice = m['budget_selection'][str(b)]['selected_generation']
            assert 0 <= choice <= b
            if b == 2048:
                assert choice % 4 == 0

# All stored final-score means and selected checkpoint ages.
for suite, levels in summary['final_scores'].items():
    for budget, arms in levels.items():
        for readout, methods in arms.items():
            for method, reported in methods.items():
                for metric in ('choice_brier', 'execution_brier'):
                    if reported[metric] is not None:
                        actual = sum(score(r, readout, method, suite, int(budget), 'intact', metric) for r in rows) / 8
                        assert abs(actual - reported[metric]) < 1e-14
                assert reported['selected_generations'] == [
                    r['models'][readout][method]['budget_selection'][budget]['selected_generation'] for r in rows]

# Independent NumPy forward pass, recreated from the documented tensor organization.
spec = importlib.util.spec_from_file_location('audit_worlds', ROOT / 'frozen/worlds.py')
worlds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worlds)


def infer(theta, readout, data, kind='intact'):
    t = np.asarray(theta, dtype=np.float32)
    gate, proposal = t[:80].reshape(20, 4), t[80:160].reshape(20, 4)
    rw, out, extra = t[160:248].reshape(11, 8), t[248:257], t[257:]
    n = len(data['x'])
    state = np.zeros((n, 4), np.float32)
    if kind != 'no_memory':
        for j in range(data['x'].shape[1]):
            z = np.concatenate((data['x'][:, j], state, np.ones((n, 1), np.float32)), axis=1)
            g = 1 / (1 + np.exp(-(z @ gate)))
            new = state + g * (np.tanh(z @ proposal) - state)
            state = np.where((j < data['lengths'])[:, None], new, state)
    options = data['query'].shape[1]
    query = np.zeros((n, options + 1, 6), np.float32)
    query[:, :, :3] = np.eye(3)[data['query_context']][:, None]
    query[:, :options, 3:5] = np.arcsinh(data['query'] / 4)
    query[:, options, 5] = 1
    z = np.concatenate((np.repeat(state[:, None], options + 1, axis=1), query,
                        np.ones((n, options + 1, 1), np.float32)), axis=-1)
    logits = np.tanh(z @ rw) @ out[:8] + out[8]
    if kind != 'drop_extra':
        if readout == 'interaction':
            logits += ((state @ extra.reshape(4, 3))[:, None] * query[:, :, 3:6]).sum(-1)
        else:
            logits += np.tanh(z @ extra[:11]) * extra[11]
    choice = np.where(data['query_mask'], logits[:, :options], -1e9)
    p = np.exp(choice - choice.max(axis=1, keepdims=True))
    p = (p / p.sum(axis=1, keepdims=True)).astype(np.float64)
    a = (1 / (1 + np.exp(-logits[:, -1]))).astype(np.float64)
    return {'choice_brier': float((.5 * ((p * p).sum(-1) - 2 * p[np.arange(n), data['y_choice']] + 1)).mean()),
            'execution_brier': float(((a - data['y_ability']) ** 2).mean())}


model_count = 0
max_prediction_error = 0.0
for row in rows:
    seed = row['replicate']
    folder = ROOT / 'collected' / f'seed-{seed}'
    weights = json.loads((folder / 'final-weights.json').read_text())
    assert weights['replicate'] == seed and weights['config_sha256'] == manifest['config_sha256']
    data = worlds.synthetic(np.random.default_rng(186000000 + 1000 * seed + 24), 512, 24)
    data['query_context'] = data['contexts'][:, 0].copy()
    permutation = np.arange(512)
    rng = np.random.default_rng(189000000 + 1000 * seed + 24)
    for context in range(3):
        ids = np.flatnonzero(data['query_context'] == context)
        order = rng.permutation(ids)
        permutation[order] = np.roll(order, 1)
    assert np.all(permutation != np.arange(512))
    assert hashlib.sha256(permutation.tobytes()).hexdigest() == row['donor_permutation_hashes']['canonical_seen']['24']
    donor = dict(data, x=data['x'][permutation], lengths=data['lengths'][permutation])
    for budget in ('512', '2048'):
        for readout in ('interaction', 'wide_control'):
            for method in ('evolved', 'random_search', 'matched_gradient'):
                state = weights['models'][budget][readout][method]
                assert set(state) == {'theta'}
                theta = np.asarray(state['theta'], dtype=np.float32)
                assert theta.shape == (269,) and np.all(np.isfinite(theta))
                if method == 'matched_gradient':
                    with zipfile.ZipFile(folder / readout / f'{method}-checkpoints.pt') as z:
                        stores = [z.read(n) for n in z.namelist() if '/data/' in n]
                        assert theta.astype('<f4').tobytes() in stores
                else:
                    with np.load(folder / readout / f'{method}-checkpoints.npz', allow_pickle=False) as z:
                        assert np.array_equal(theta, z[budget])
                for kind in ('intact', 'no_memory', 'donor_history', 'drop_extra'):
                    predicted = infer(theta, readout, donor if kind == 'donor_history' else data, kind)
                    expected = row['models'][readout][method]['budgets'][budget][kind]['canonical_seen']['24']
                    for metric, value in predicted.items():
                        difference = abs(value - expected[metric])
                        max_prediction_error = max(max_prediction_error, difference)
                        assert difference < 1e-6, (seed, budget, readout, method, kind, metric, difference)
                model_count += 1
assert model_count == 96

# Prespecified raw-final secondary check at history length 24; eight whole-run contrasts.
raw_checks = {}
for readout in ('interaction', 'wide_control'):
    for method in ('evolved', 'matched_gradient'):
        for metric in ('choice_brier', 'execution_brier'):
            def raw(row, budget, kind, readout=readout, method=method, metric=metric):
                return row['models'][readout][method]['budgets'][str(budget)]['raw_last'][kind][metric]
            raw_checks[f'{readout}/{method}/{metric}/low_minus_high'] = estimate([
                raw(r, 512, 'intact') - raw(r, 2048, 'intact') for r in rows])
            raw_checks[f'{readout}/{method}/{metric}/donor_gain_growth'] = estimate([
                (raw(r, 2048, 'donor_history') - raw(r, 2048, 'intact')) -
                (raw(r, 512, 'donor_history') - raw(r, 512, 'intact')) for r in rows])

# Reporting-stage exploratory decomposition: compare checkpoint policies at the same length.
selected_length_growth = {}
for length in (4, 12, 24, 48):
    values = []
    for row in rows:
        m = row['models']['interaction']['evolved']['budgets']
        def gain(b, m=m, length=length):
            return (m[b]['donor_history']['canonical_seen'][str(length)]['choice_brier']
                    - m[b]['intact']['canonical_seen'][str(length)]['choice_brier'])
        values.append(gain('2048') - gain('512'))
    selected_length_growth[str(length)] = estimate(values)
raw_growth = raw_checks['interaction/evolved/choice_brier/donor_gain_growth']['run_differences']
policy_difference = estimate(np.array(raw_growth) - np.array(selected_length_growth['24']['run_differences']))

report = {'status': 'passed', 'audit_type': 'independent_arithmetic_and_numpy_forward_pass',
          'numpy_version': np.__version__, 'training_or_api_calls': 0,
          'whole_run_contrasts_recomputed': len(recomputed),
          'maximum_summary_absolute_error': maximum_summary_error,
          'selected_models': model_count, 'parameters_per_model': 269,
          'model_replay': 'canonical seen context, 24-event histories, all 96 models, four interventions, two outcomes',
          'maximum_replayed_brier_absolute_error': max_prediction_error,
          'replay_tolerance': 1e-6,
          'checkpoint_checks': '64 NumPy selected vectors match exact budget key; 32 gradient vectors occur exactly in raw PyTorch tensor storage; no pickle executed',
          'primary_requirement_passes': primary, 'joint_primary_pass': all(primary.values()),
          'raw_final_secondary_checks': raw_checks,
          'exploratory_selected_choice_donor_growth_by_length': selected_length_growth,
          'exploratory_raw_minus_selected_choice_donor_growth_at_24': policy_difference,
          'limits': 'Recomputes saved metrics and independently replays one prespecified evaluation slice; does not retrain or claim a complete original-runtime reproduction.'}
(OUTPUT / ('audit-recomputed.json' if OUTPUT != ROOT else 'audit.json')).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if not k.startswith(('raw_final', 'exploratory_'))}, indent=2))
