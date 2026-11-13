"""Plot every frozen probe/round contrast and the clean accuracy trajectories."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.colors import TwoSlopeNorm

ROOT = Path(__file__).resolve().parent


def read(n):
    return json.loads((ROOT / n).read_bytes())


def main():
    summary = read('SUMMARY.json')
    rows = read('PANEL_stored_RESULT.json')['rows']
    if summary['new_rows']:
        rows += read('PANEL_new_RESULT.json')['rows']
    cols = [r['round'] for r in summary['rounds']]
    probes = sorted({(r['probe'], r['arm']) for r in summary['comparisons']})
    margin = {(r['round'],r['probe'],r['arm']): r['large_gap'] for r in summary['comparisons']}
    vals = [[margin[r,p,a] / 9 for r in cols] for p,a in probes]
    limit = max(abs(x) for row in vals for x in row) or 1
    fig, (ax, ca) = plt.subplots(1, 2, figsize=(13.8, 6.0), gridspec_kw={'width_ratios':[1,1.12]})
    im = ax.imshow(vals, cmap='RdBu', norm=TwoSlopeNorm(vmin=-limit,vcenter=0,vmax=limit), aspect='auto')
    for i, row in enumerate(vals):
        for j, val in enumerate(row):
            ax.text(j,i,f'{val:.1f}',ha='center',va='center',fontsize=9,color='white' if abs(val)>.57*limit else '#1b2432')
    ax.set_xticks(range(len(cols)), [str(r) for r in cols]); ax.set_xlabel('Actual unlearning round')
    ax.set_yticks(range(len(probes)),[f'{p} / {a}' for p,a in probes])
    ax.set_title('A. Same-round gap for each frozen probe',loc='left',fontweight='bold')
    fig.colorbar(im,ax=ax,fraction=.05,pad=.035,label='Minimum diagnostic − maximum large normal (pp)')
    labels={'p00':'Balanced 5k A','p01':'Class 2 all','p02':'Normal 125','p03':'Minus diagnostic',
            'p04':'Plus diagnostic','u00':'Balanced 5k B','u01':'Dark 5k A','u02':'Dark 5k B'}
    for k,label in labels.items():
        q=sorted((x for x in rows if x['track']==k),key=lambda z:z['round'])
        if q:ca.plot([x['round'] for x in q],[100*x['clean']['correct']/x['clean']['n'] for x in q],
                     marker='o',markersize=4,linestyle='--' if k in ('p03','p04') else '-',label=label)
    ca.set_title('B. Clean accuracy on the public panel',loc='left',fontweight='bold')
    ca.set_xticks(cols);ca.set_xlabel('Actual unlearning round');ca.set_ylabel('Correct among 1,000 public images (%)')
    ca.legend(ncol=2,loc='lower right',frameon=False,fontsize=8);ca.grid(alpha=.22)
    for a in (ax,ca):a.spines[['top','right']].set_visible(False)
    stage='Stored histories only' if not summary['new_rows'] else 'Stored histories plus three new request repetitions at rounds 1–10'
    fig.text(.095,.02,stage+'.  Terminal probes are used retrospectively; negative or zero gaps indicate overlap on the fixed panel.',fontsize=9,color='#556476')
    fig.subplots_adjust(left=.12,right=.97,top=.92,bottom=.13,wspace=.44)
    fig.savefig(ROOT/'ROUNDS_FIGURE.png',dpi=190)
    plt.close(fig)


if __name__=='__main__':main()
