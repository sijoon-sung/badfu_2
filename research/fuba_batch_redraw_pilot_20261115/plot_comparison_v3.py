"""Plot fixed comparison metrics already stored in the sealed packet."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from receive_packet import verify

ROOT=Path(__file__).resolve().parent


def main():
    p=ROOT/'delivery/payload';seal=json.loads((ROOT/'delivery/SEAL.json').read_text());verify(p,seal['manifest_sha256'])
    result=json.loads((p/'RESULT.json').read_text());assert result['state']=='complete'
    independent=json.loads((p/'INDEPENDENT_RESULT.json').read_text());assert independent['state']=='passed'
    for label in ['CPU_AUDIT.json','GAMMA_AUDIT.json']:
        assert json.loads((p/label).read_text())['state']=='passed'
    fig,axes=plt.subplots(2,1,figsize=(10,6.5),sharex=True)
    for rows,label,color,marker in [(result['fixed_control'],'Fixed samples (completed control)','#2166ac','o'),
                                   (result['results'],'Per-batch redraw (new treatment)','#b2182b','s')]:
        rounds=[x['round'] for x in rows];assert rounds==list(range(21,31))
        ca=[100*x['evaluation']['clean_correct']/10000 for x in rows]
        asr=[100*x['evaluation']['target_successes']/9026 for x in rows]
        axes[0].plot(rounds,ca,color=color,marker=marker,lw=1.4,label=label)
        axes[1].plot(rounds,asr,color=color,marker=marker,lw=1.4,label=label)
    axes[0].axhline(97,color='#777777',ls=':',lw=1,label='CA gate: 97%')
    axes[0].set_ylim(0,103);axes[0].set_ylabel('Clean accuracy (%)')
    axes[1].axhline(10,color='#777777',ls=':',lw=1,label='ASR gate: 10%')
    axes[1].set_ylim(bottom=0);axes[1].set_ylabel('Global DBA ASR (%)')
    for ax in axes:
        ax.grid(alpha=.18);ax.spines[['top','right']].set_visible(False)
    axes[0].legend(loc='lower left',fontsize=9,frameon=False)
    axes[1].text(21,10.2,'ASR gate: 10%',fontsize=9,color='#555555')
    axes[1].set_xticks(range(21,31));axes[1].set_xlabel('Communication round (same original round-20 input)')
    fig.suptitle('FUBA: fixed samples vs. per-batch redraw',fontsize=16,y=.98)
    verdict='PASSED' if result['behavioral_hypothesis_supported'] else 'FAILED'
    fig.text(.5,.925,f'Registered behavioral gates: {verdict} | ASR violations: control 3, treatment {result["violations"]}',ha='center',fontsize=11)
    fig.text(.5,.035,'All ten rounds shown. 10,000 clean / 9,026 non-target images per round; new treatment independently verified.',ha='center',fontsize=9)
    fig.text(.5,.008,'One bounded implementation comparison; no new100R/FU or whole-paper reproduction claim.',ha='center',fontsize=10,color='#9c2727')
    fig.subplots_adjust(top=.87,bottom=.14,hspace=.17)
    output=ROOT/'BATCH_REDRAW_COMPARISON_v3.png';assert not output.exists();fig.savefig(output,dpi=180);plt.close(fig)
    proof={'state':'created_from_sealed_records','manifest_sha256':seal['manifest_sha256'],
           'inference':0,'figure_sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
    with (ROOT/'BATCH_REDRAW_COMPARISON_v3.json').open('x') as f:json.dump(proof,f,indent=2)
    print(json.dumps(proof),flush=True)


if __name__=='__main__':main()
