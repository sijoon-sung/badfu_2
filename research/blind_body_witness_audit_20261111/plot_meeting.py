"""Render the meeting figure from the checked summaries; no model reads."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt

ROOT = Path(__file__).resolve().parent


def main():
    summary = json.loads((ROOT / 'SUMMARY.json').read_bytes())
    gaps = summary['search_gap']
    strict = summary['strict_body_percent']
    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={'width_ratios': [1, 1.15]})
    fig.patch.set_facecolor('#fbfcfe')
    for ax in (left, right):
        ax.set_facecolor('#fbfcfe')
        ax.set_axisbelow(True)
        ax.grid(axis='x', color='#e3e9f0', linewidth=.7)
        ax.spines[['top', 'right', 'left']].set_visible(False)
        ax.spines['bottom'].set_color('#b0bac6')
        ax.tick_params(axis='y', length=0)
    for i, key in enumerate(('BadFU', 'FedUBA_large')):
        for dy, arm, color, label in ((-.16, 'baseline', '#7e8b9b', 'Basic pre/post'), (.16, 'four_routes', '#27689e', 'Four routes')):
            v = gaps[key][arm]['percentage_points']
            left.barh(i + dy, v, .27, color=color, label=label if i == 0 else None)
            left.text(v + .55, i + dy, f'{v:.2f}', va='center', fontsize=10)
    left.set_yticks([0, 1], ['BadFU', 'FedUBA\nlarge controls'])
    left.set_ylim(1.55, -.6)
    left.set_xlim(0, 36)
    left.set_title('A. Did four routes help the search?', loc='left', fontweight='bold', fontsize=12)
    left.set_xlabel('Lowest attack − highest benign (percentage points)')
    left.legend(loc='lower right', frameon=False, fontsize=9)
    groups = [
        ('BadFU benign', ('c00', 'c01', 'c02', 'c03'), '#27689e'),
        ('BadFU attack', ('c04', 'c05'), '#ad4f38'),
        ('FedUBA benign', ('c07', 'n00', 'n01'), '#27689e'),
        ('FedUBA diagnostic', ('c08', 'c09'), '#ad4f38'),
        ('FUBA diagnostic only', ('c06',), '#7e8b9b'),
    ]
    for i, (_, ids, color) in enumerate(groups):
        vals = [strict[c] for c in ids if c in strict]
        if vals:
            lo, hi = min(vals), max(vals)
            right.plot([lo, hi], [i, i], color=color, linewidth=3, alpha=.6)
            right.scatter(vals, [i] * len(vals), color=color, s=30, zorder=4)
            if i < 4:
                stat, v = ('max', hi) if i % 2 == 0 else ('min', lo)
                right.text(3, i, f'{stat} {v:.2f}%', va='center', color=color, fontsize=9)
    right.set_yticks(range(len(groups)), [label for label, _, _ in groups])
    right.set_ylim(len(groups) - .5, -.5)
    right.set_xlim(0, 101)
    right.set_xticks(range(0, 101, 20))
    right.set_title('B. Does the transition follow the body?', loc='left', fontweight='bold', fontsize=12)
    right.set_xlabel('Strict body-following among basic-search witnesses (%)')
    fig.text(.065, .025, 'Fixed checkpoints and public test split. FedUBA/FUBA rows are diagnostic; gaps are not operating detection rates.',
             color='#566575', fontsize=9)
    fig.subplots_adjust(left=.13, right=.97, top=.89, bottom=.18, wspace=.55)
    fig.savefig(ROOT / 'MEETING_FIGURE.png', dpi=210)
    plt.close(fig)


if __name__ == '__main__':
    main()
