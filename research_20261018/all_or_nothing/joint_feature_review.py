"""Join the existing sixteen requests and plot both FC definitions against Conv.

No new model training, classifier fitting, threshold tuning, or image access.
The shaded vertical band is the observed FC range gap, not a chosen threshold.
"""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Patch
import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parent
    fc_path = root / 'fc_spectral_result.json'
    conv_path = root / 'conv_ratio_result.json'
    f = json.loads(fc_path.read_text(encoding='utf-8'))
    c = json.loads(conv_path.read_text(encoding='utf-8'))
    frows = {r['case']: r for r in f['rows']}
    crows = {r['case']: r for r in c['rows']}
    assert len(frows) == len(crows) == 16 and set(frows) == set(crows)
    rows = []
    for name, row in frows.items():
        conv = crows[name]
        assert row['checkpoint_sha256'] in conv['source_hashes'].values()
        rows.append(dict(
            case=name, seed=int(name[-2:]),
            group='attack' if name.startswith('attack') else 'control',
            fc_frobenius_ratio=row['spectral']['frobenius_ratio'],
            fc_spectral_ratio=row['spectral']['spectral_ratio'],
            conv_frobenius_ratio=conv['conv_only']['ratio'],
            fc_steps=1, fc_clean_reference_images=0,
            conv_steps=conv['original_branch_training']['steps'],
            conv_clean_reference_images=conv['original_branch_training']['anchor_size'],
        ))
    values = np.array([[r['fc_frobenius_ratio'], r['fc_spectral_ratio'], r['conv_frobenius_ratio']]
                       for r in rows])
    assert np.isfinite(values).all() and (values > 0).all()
    with (root / 'joint_features.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    attacks = [r for r in rows if r['group'] == 'attack']
    controls = [r for r in rows if r['group'] == 'control']
    ranges = {}
    for key in ('fc_frobenius_ratio', 'fc_spectral_ratio', 'conv_frobenius_ratio'):
        amin = min(r[key] for r in attacks)
        cmax = max(r[key] for r in controls)
        ranges[key] = dict(attack_min=amin, attack_max=max(r[key] for r in attacks),
                           control_min=min(r[key] for r in controls), control_max=cmax,
                           ranges_overlap=cmax >= amin, observed_range_gap=amin-cmax)
    summary = dict(
        review_date_kst='2026-10-19', cases=16, attack_cases=4, control_cases=12,
        source_hashes={str(p.name): digest(p) for p in (fc_path, conv_path)},
        matched_original_checkpoint_hashes=True, features=ranges,
        observation='Both FC features already separate the four attacks from twelve controls on these examined cases; adding Conv has no demonstrated additional error reduction.',
        two_dimensional_separability='Yes for the observed points, since a vertical separator already exists in either FC plot. No two-dimensional classifier was fitted.',
        classifier_fitted=False, threshold_selected=False, new_training_steps=0,
        additional_value_established=False, independent_validation=False,
        protocol_caveat='FC is a separate one-step classifier probe without extra clean references. Conv is a 100-step layer4 probe with 500 clean-reference anchors and gradient clipping.',
        raw_private_records='Needed client-side to generate diagnostic updates; not read by this plot script.',
        bounds_on_claims=[
            'Adding features does not guarantee separation on new requests.',
            'The different intervention budgets prevent attributing coordinates solely to layer location.',
            'Existing Conv branches have frozen FC; the nonzero FC coordinates come from a separate intervention.',
            'This vector does not establish malicious intent or justify request rejection.',
        ])
    (root / 'joint_feature_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

    font = Path('C:/Windows/Fonts/malgun.ttf')
    if font.exists():
        font_manager.fontManager.addfont(str(font))
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams.update({'axes.unicode_minus': False, 'font.size': 11,
                         'axes.titleweight': 'bold', 'axes.spines.top': False,
                         'axes.spines.right': False, 'pdf.fonttype': 42})
    fig, axes = plt.subplots(1, 2, figsize=(13.6, 6.5))
    red, blue, orange = '#be3144', '#2a689b', '#d98900'
    special_offsets = {'attack71': (8, 8), 'attack72': (8, -16),
                       'attack73': (8, -16), 'attack74': (-64, 9),
                       'noise74': (-72, 10), 'normal71': (-66, -18)}
    for ax, key, title in zip(axes, ('fc_frobenius_ratio', 'fc_spectral_ratio'),
                               ('FC 전체 노름 비율 + Conv 비율', 'FC 최대 특이값 비율 + Conv 비율')):
        gap = ranges[key]
        ax.axvspan(gap['control_max'], gap['attack_min'], color='#6ca887', alpha=.2, zorder=0)
        ordinary = [r for r in controls if r['case'] != 'noise74']
        ax.scatter([r[key] for r in ordinary], [r['conv_frobenius_ratio'] for r in ordinary],
                   s=62, c=blue, edgecolors='white', linewidths=.8, zorder=3)
        noise = next(r for r in rows if r['case'] == 'noise74')
        ax.scatter([noise[key]], [noise['conv_frobenius_ratio']], marker='s',
                   s=85, c=orange, edgecolors='white', linewidths=.9, zorder=4)
        ax.scatter([r[key] for r in attacks], [r['conv_frobenius_ratio'] for r in attacks],
                   s=108, marker='^', c=red, edgecolors='white', linewidths=.9, zorder=5)
        for r in rows:
            if r['case'] in special_offsets:
                ax.annotate(r['case'], (r[key], r['conv_frobenius_ratio']),
                            xytext=special_offsets[r['case']], textcoords='offset points',
                            fontsize=9, color='#263242',
                            arrowprops=dict(arrowstyle='-', lw=.65, color='#8395a3'))
        ax.set(xlim=(0, 5.3), ylim=(.48, 1.43), title=title,
               xlabel='FC 변화량 비율 (유지 ÷ 삭제)',
               ylabel='Conv 변화량 비율 (유지 ÷ 삭제)')
        ax.grid(alpha=.14)
        ax.text(.035, .965, 'FC 단독의 관측 간격: '+format(gap['observed_range_gap'], '.3f'),
                transform=ax.transAxes, va='top', fontsize=10,
                bbox=dict(facecolor='white', edgecolor='#d9e3dd', boxstyle='round,pad=.4'))
    handles = [plt.Line2D([], [], marker='^', linestyle='', color=red, markersize=9, label='공격 4건'),
               plt.Line2D([], [], marker='o', linestyle='', color=blue, markersize=7, label='그 외 대조 11건'),
               plt.Line2D([], [], marker='s', linestyle='', color=orange, markersize=8, label='오라벨 대조 1건'),
               Patch(facecolor='#6ca887', alpha=.25, label='관측된 FC 범위 사이의 간격')]
    fig.suptitle('FC·Conv를 함께 본 기존 16개 요청', x=.5, y=.98, fontsize=19, fontweight='bold')
    fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(.5, .91), ncol=4, frameon=False, fontsize=10)
    fig.text(.5, .065, 'FC만으로도 두 그룹의 범위가 분리됩니다. Conv를 추가한 탐지 이득은 아직 확인되지 않았습니다.',
             ha='center', fontsize=11, color='#273b4d')
    fig.text(.5, .025, 'FC: 별도 1스텝·추가 정상 기준 자료 0장  |  Conv: 100스텝·정상 기준 자료 500장  |  탐색 결과, 독립 검증 아님',
             ha='center', fontsize=9, color='#626f7c')
    fig.subplots_adjust(left=.07, right=.975, top=.79, bottom=.18, wspace=.24)
    fig.savefig(root/'joint_feature_scatter.png', dpi=180, facecolor='white')
    fig.savefig(root/'joint_feature_scatter.pdf', facecolor='white')
    plt.close(fig)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
