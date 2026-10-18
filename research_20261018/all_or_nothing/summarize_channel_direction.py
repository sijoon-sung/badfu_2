"""Summarize the prespecified profiles without fitting a detector."""
import csv
import json
from pathlib import Path

import numpy as np


def span(values):
    values = list(values)
    return dict(min=min(values), max=max(values))


def main():
    root = Path(__file__).resolve().parent
    result = json.loads((root/'channel_direction_result.json').read_text(encoding='utf-8'))
    previous = json.loads((root/'conv_ratio_result.json').read_text(encoding='utf-8'))
    previous = {r['case']: r for r in previous['rows']}
    arrays = np.load(root/'layer4_channels.npz')
    rows = result['rows']
    attack = [r for r in rows if r['case'].startswith('attack')]
    control = [r for r in rows if not r['case'].startswith('attack')]
    flat = []
    for row in rows:
        old = previous[row['case']]
        assert set(row['source_hashes'].values()).issubset(set(old['source_hashes'].values()))
        assert abs(row['conv_norm_ratio']-old['conv_only']['ratio']) < 1e-12
        for layer in row['layers']:
            prefix = row['case']+'/'+layer['layer']+'/'
            nr, nf = arrays[prefix+'retained_norm'], arrays[prefix+'forget_norm']
            cosine = arrays[prefix+'cosine']
            energy = arrays[prefix+'difference_energy']
            valid = (nr > 0) & (nf > 0)
            reconstructed = nr*nr+nf*nf-2*nr*nf*np.nan_to_num(cosine)
            assert np.allclose(reconstructed, energy, rtol=1e-10, atol=1e-20)
            assert np.isfinite(cosine[valid]).all()
            assert abs(np.linalg.norm(nr)/np.linalg.norm(nf)-layer['norm_ratio']) < 1e-12
            sub = layer['subspace']
            flat.append(dict(case=row['case'], group='attack' if row in attack else 'control',
                             layer=layer['layer'], norm_ratio=layer['norm_ratio'], cosine=layer['cosine'],
                             negative_channel_fraction=layer['negative_cosine_channel_fraction'],
                             difference_energy_gini=layer['profile_concentration']['gini'],
                             top10_energy_share=layer['profile_concentration']['top_ten_percent_energy_share'],
                             subspace_affinity=sub['normalized_affinity'],
                             principal_angle_1_deg=sub['principal_angles_degrees'][0],
                             principal_angle_2_deg=sub['principal_angles_degrees'][1],
                             principal_angle_3_deg=sub['principal_angles_degrees'][2]))
    with (root/'channel_direction_per_layer.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)
    groups = {}
    for name, group in [('attack', attack), ('control', control)]:
        groups[name] = dict(cases=len(group), conv_cosine=span(r['conv_cosine'] for r in group),
                            channel_difference_energy_gini=span(r['difference_energy_concentration']['gini'] for r in group),
                            top10_channel_energy_share=span(r['difference_energy_concentration']['top_ten_percent_energy_share'] for r in group),
                            layer_cosine=span(l['cosine'] for r in group for l in r['layers']),
                            negative_layer_cosine_count=sum(l['cosine'] < 0 for r in group for l in r['layers']))
    layer_ranges = {}
    for i, layer in enumerate(rows[0]['layers']):
        layer_ranges[layer['layer']] = {}
        for name, group in [('attack', attack), ('control', control)]:
            layer_ranges[layer['layer']][name] = dict(
                cosine=span(r['layers'][i]['cosine'] for r in group),
                gini=span(r['layers'][i]['profile_concentration']['gini'] for r in group),
                subspace_affinity=span(r['layers'][i]['subspace']['normalized_affinity'] for r in group))
    summary = dict(review_date_kst='2026-10-19', groups=groups, layer_ranges=layer_ranges,
                   old_norm_ratios_and_checkpoint_hashes_match=True,
                   channel_energy_identity_checked=True,
                   channel_arrays_preserved=len(arrays.files),
                   current_same_run_history_available=False,
                   same_run_round_like_weight_files=sum(len(r['history_like_weight_files']) for r in result['history_inventory']),
                   conclusion='Channel concentration, signed cosines and subspace profiles are computable. Sparse-only attacks and strong negative layer alignment are not supported in these shadows. Added detection value of the entire vector is untested.',
                   classifier_fitted=False, threshold_tuned=False,
                   caveat='layer4 shadows only, 100 steps with 500 clean anchors; other blocks frozen; same sixteen reused cases')
    (root/'channel_direction_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ('groups','old_norm_ratios_and_checkpoint_hashes_match','channel_energy_identity_checked','same_run_round_like_weight_files')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
