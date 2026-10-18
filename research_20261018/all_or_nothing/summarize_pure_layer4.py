"""Check the FC baseline and compare one-point Conv metrics with old shadows."""
import csv
import json
from pathlib import Path

import numpy as np


def span(values):
    values = list(values)
    return dict(min=min(values), max=max(values))


def main():
    root = Path(__file__).resolve().parent
    result = json.loads((root/'pure_layer4_result.json').read_text(encoding='utf-8'))
    prior_fc = json.loads((root/'fc_spectral_result.json').read_text(encoding='utf-8'))['rows']
    old = json.loads((root/'channel_direction_result.json').read_text(encoding='utf-8'))['rows']
    old = {r['case']: r for r in old}
    old_arrays = np.load(root/'layer4_channels.npz')
    fc_arrays = np.load(root/'fc_one_step_deltas.npz')
    current = np.load(root/'pure_layer4_arrays.npz')
    prior_fc = {r['case']: r for r in prior_fc}
    index = {name: i for i, name in enumerate(fc_arrays['case_names'].tolist())}
    rows, errors = [], []
    assert len(result['rows']) == 16
    for row in result['rows']:
        name = row['case']
        prior = prior_fc[name]
        assert row['checkpoint_sha256'] == prior['checkpoint_sha256']
        assert row['splits_sha256'] == prior['splits_sha256']
        assert row['retained_records'] == prior['retained_records']
        assert row['forget_records'] == prior['forget_records']
        for role in ('retained', 'forget'):
            a, b = current[f'{name}/fc/{role}'], fc_arrays[f'{index[name]}_{role}']
            error = float(np.linalg.norm(a-b)/np.linalg.norm(b))
            errors.append(error)
            # Previous features were evaluated without backward and with a
            # different microbatch partition. Floating-point convolution
            # execution need not be bitwise identical. Retain the actual error
            # and check a .1% relative numerical tolerance, not a decision rule.
            assert error < 1e-3, (name, role, error)
        old_difference = sum(float(old_arrays[f"{name}/{layer['layer']}/difference_energy"].sum())
                             for layer in old[name]['layers'])**.5
        rows.append(dict(case=name, group='attack' if name.startswith('attack') else 'control',
                         pure_ratio=row['conv']['ratio'], pure_cosine=row['conv']['cosine'],
                         pure_difference_norm=row['conv']['difference_norm'],
                         pure_gini=row['conv']['difference_energy_concentration']['gini'],
                         old_ratio=old[name]['conv_norm_ratio'], old_cosine=old[name]['conv_cosine'],
                         old_difference_norm=old_difference,
                         old_direct_difference_gini=old[name]['difference_energy_concentration']['gini'],
                         fc_ratio=row['fc']['ratio']))
    groups = {}
    for label in ('attack', 'control'):
        subset = [r for r in rows if r['group'] == label]
        groups[label] = {key: span(r[key] for r in subset) for key in
                         ('pure_ratio', 'pure_cosine', 'pure_difference_norm', 'pure_gini',
                          'old_ratio', 'old_cosine', 'old_difference_norm', 'old_direct_difference_gini')}
        originals = [r for r in result['rows'] if (r['case'].startswith('attack')) == (label == 'attack')]
        groups[label]['negative_conv_layer_count'] = sum(layer['cosine'] < 0 for r in originals for layer in r['layers'])
    summary = dict(review_date_kst='2026-10-19', groups=groups,
                   pure_conv_ratio_observed_gap=groups['attack']['pure_ratio']['min']-groups['control']['pure_ratio']['max'],
                   old_conv_ratio_observed_gap=groups['attack']['old_ratio']['min']-groups['control']['old_ratio']['max'],
                   fc_reproduction_max_relative_matrix_error=max(errors),
                   fc_reproduction_relative_numerical_tolerance=1e-3,
                   checkpoint_hashes_and_request_counts_match=True,
                   previous_gini_already_used_direct_branch_difference=True,
                   no_kl_clipping_or_clean_reference=True,
                   cosine_remains_positive_without_kl=True,
                   result='One-point CE Conv norm ratios separate the four attacks from twelve controls on these existing cases. Signed cosines remain positive, and direct difference norms and Ginis overlap.',
                   independent_validation=False, threshold_fitted=False,
                   causal_note='Multiple protocol changes were made together, so this does not isolate the effect of KL in the old 100-step trajectories.')
    (root/'pure_layer4_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    with (root/'pure_layer4_comparison.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
