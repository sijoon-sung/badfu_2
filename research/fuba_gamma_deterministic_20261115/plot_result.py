"""Plot verified stored counts only; no model load or inference."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    root=Path(__file__).resolve().parent
    result=json.loads((root/'RESULT.json').read_text())
    for name in ['CPU_AUDIT.json','PREFIX_AUDIT.json','GAMMA_AUDIT.json','INDEPENDENT_RESULT.json']:
        assert json.loads((root/name).read_text())['state']=='passed',name
    fig,axes=plt.subplots(2,1,figsize=(11,7.6),sharex=True,gridspec_kw={'height_ratios':[2,1]})
    styles={'local':('#78879b','Local-patch gamma scoring'),'global':('#176d98','Global-trigger gamma scoring')}
    for arm,(color,label) in styles.items():
        entries=result['results'][arm];x=[e['round'] for e in entries]
        asr=[100*e['evaluation']['target_successes']/9026 for e in entries]
        ca=[100*e['evaluation']['clean_correct']/10000 for e in entries]
        axes[0].plot(x,asr,'o-',color=color,label=label,lw=2,ms=5)
        axes[1].plot(x,ca,'o-',color=color,lw=2,ms=5)
    axes[0].axhline(10,color='#bf4242',linestyle='--',lw=1.4,label='Pre-FU ASR gate: 10%')
    axes[0].set_ylabel('Global-trigger ASR (%)');axes[0].set_ylim(0,30)
    axes[1].axhline(97,color='#bf4242',linestyle='--',lw=1.4)
    axes[1].set_ylabel('Clean accuracy (%)');axes[1].set_ylim(96.5,100);axes[1].set_xlabel('FL round (same original round-20 starting state)')
    for ax in axes:
        ax.axvspan(27.5,30.4,color='#e9b96a',alpha=.16)
        ax.axvline(26,color='#777777',linestyle=':',lw=1)
        ax.set_xlim(20.6,30.4);ax.set_xticks(range(21,31));ax.grid(axis='y',alpha=.18)
        ax.spines[['top','right']].set_visible(False)
    axes[0].legend(loc='upper left',frameon=False,fontsize=10)
    axes[0].text(26.1,28.2,'First gamma divergence: round 26',fontsize=9,color='#555555')
    fig.suptitle('FUBA: deterministic gamma-scope comparison',fontsize=18,y=.98)
    fig.text(.5,.935,f'ASR violations >10%: local {result["violations"]["local"]}, global {result["violations"]["global"]}. All fixed behavior gates passed: {result["hypothesis_supported"]}.',ha='center',fontsize=11)
    fig.text(.5,.025,'20 newly trained rounds, one original seed; full-count and gamma audits passed. Not a completed 100-round FL/FU reproduction.',ha='center',fontsize=10)
    fig.subplots_adjust(top=.88,bottom=.11,left=.09,right=.98,hspace=.14)
    out=root/'DETERMINISTIC_COMPARISON.png';assert not out.exists();fig.savefig(out,dpi=170);plt.close(fig)
    receipt={'result_sha256':hashlib.sha256((root/'RESULT.json').read_bytes()).hexdigest(),'plot_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'model_loads':0,'inference':0}
    with (root/'PLOT_RECEIPT.json').open('x') as f:json.dump(receipt,f,indent=2)
    print(json.dumps(receipt))


if __name__=='__main__':main()
