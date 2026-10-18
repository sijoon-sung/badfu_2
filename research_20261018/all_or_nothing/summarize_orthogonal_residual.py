"""Summarize all five Conv layers and FC without selecting a winning layer."""
import csv
import json
from pathlib import Path

import numpy as np


def ranges(rows, field):
    a = [r[field] for r in rows if r['case'].startswith('attack')]
    b = [r[field] for r in rows if not r['case'].startswith('attack')]
    return dict(attack_min=min(a), attack_max=max(a), control_min=min(b), control_max=max(b),
                observed_gap=min(a)-max(b), ranges_overlap=max(b) >= min(a))


def main():
    root = Path(__file__).resolve().parent
    fc = json.loads((root/'orthogonal_fc_result.json').read_text(encoding='utf-8'))['rows']
    conv = json.loads((root/'orthogonal_conv_result.json').read_text(encoding='utf-8'))['rows']
    previous = json.loads((root/'pure_layer4_result.json').read_text(encoding='utf-8'))['rows']
    previous = {r['case']: r for r in previous}
    fc_by_case = {r['case']: r for r in fc}
    error = 0.
    flat = []
    for row in conv:
        old = previous[row['case']]
        assert row['checkpoint_sha256'] == old['checkpoint_sha256']
        assert row['splits_sha256'] == old['splits_sha256']
        assert abs(row['conv']['ratio']-old['conv']['ratio']) < 1e-12
        value = row['fc']['orthogonal_residual']['residual_spectral_over_forget']
        error = max(error, abs(value-fc_by_case[row['case']]['residual_spectral_over_forget']))
        assert error < 1e-10
        for layer in row['layers']:
            flat.append(dict(case=row['case'], layer=layer['layer'], **layer['orthogonal_residual']))
    with (root/'orthogonal_conv_scores.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)
    layer_ranges = {}
    for key in dict.fromkeys(r['layer'] for r in flat):
        group = [r for r in flat if r['layer'] == key]
        layer_ranges[key] = {field:ranges(group, field) for field in
                             ('residual_spectral_over_forget', 'residual_frobenius_over_forget', 'residual_spectral_concentration')}
    # A benign, correctly predicted two-class FC example. Both records have
    # label0; only their normal feature vectors differ. No trigger or poison.
    probabilities = np.exp([2., 0.]); probabilities /= probabilities.sum()
    error_vector = probabilities-np.array([1., 0.])
    a = np.outer(error_vector, [0., 10., 1.])
    b = np.outer(error_vector, [1., 0., 1.])
    residual = a-np.sum(a*b)/np.sum(b*b)*b
    counterexample = dict(type='Algebraic benign CE-gradient counterexample, not an empirical CIFAR control',
                          both_labels=0, both_predictions=0, target0_probability=float(probabilities[0]),
                          retained_augmented_features=[0., 10., 1.], forget_augmented_features=[1., 0., 1.],
                          residual_rank=int(np.linalg.matrix_rank(residual)),
                          proposed_score=float(np.linalg.svd(residual, compute_uv=False)[0]/np.linalg.norm(b)))
    summary = dict(review_date_kst='2026-10-19', cases=16,
                   fc={key:ranges(fc, key) for key in
                       ('norm_ratio', 'residual_frobenius_over_forget', 'residual_spectral_over_forget', 'residual_spectral_concentration')},
                   conv_layers=layer_ranges, independent_validation=False,
                   all_five_conv_spectral_ranges_separate=all(not r['residual_spectral_over_forget']['ranges_overlap'] for r in layer_ranges.values()),
                   fc_scores_reproduced_max_absolute_error=error,
                   algebraic_counterexample=counterexample,
                   score_identity='S = (||A||F/||B||F) * sqrt(1-cos(A,B)^2) * (sigma_max(R)/||R||F)',
                   limitations=['Projection removes span(B), not every benign or Non-IID effect.',
                                'Weight residual spectra are not equal to input-patch Jacobian effects.',
                                'FC residual Frobenius norms already separate the reused cases; added SVD detection value is unestablished.',
                                'Different score scales make raw gap size insufficient evidence of improved detection.',
                                'No threshold or winning Conv layer was fitted.'])
    (root/'orthogonal_residual_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
