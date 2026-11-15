"""Plot all recorded FU rounds, without loading a model or doing inference."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from verify_payload import verify

ROOT=Path(__file__).resolve().parent


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def main():
    payload=ROOT/'delivery/payload'
    seal=read(ROOT/'delivery/SEAL.json');verify(payload,seal['manifest_sha256'])
    rows=read(payload/'MANIFEST.json')['rounds']
    assert [r['round'] for r in rows]==list(range(1,101))
    final=read(payload/'INDEPENDENT_RESULT.json');assert final['state']=='passed'
    assert rows[-1]['evaluation']['clean_correct']==final['CA_correct']
    assert rows[-1]['evaluation']['target_successes']==final['ASR_hits']
    rounds=[r['round'] for r in rows]
    ca=[100*r['evaluation']['clean_correct']/10000 for r in rows]
    asr=[100*r['evaluation']['target_successes']/9026 for r in rows]
    fig,axes=plt.subplots(2,1,figsize=(10,6.5),sharex=True)
    axes[0].plot(rounds,ca,color='#2166ac',lw=1.8,label='Clean accuracy')
    axes[0].axhline(97,color='#757575',ls=':',lw=1,label='Diagnostic CA gate: 97%')
    axes[1].plot(rounds,asr,color='#b2182b',lw=1.8,label='Global DBA target-8 ASR')
    axes[1].axhline(60,color='#757575',ls=':',lw=1,label='Diagnostic post-ASR gate: 60%')
    axes[1].axhline(100*2762/9026,color='#c48223',ls='--',lw=1,label='Original pre-FU ASR: 30.60%')
    for ax,value,color in [(axes[0],ca[-1],'#2166ac'),(axes[1],asr[-1],'#b2182b')]:
        ax.set_ylim(0,103);ax.set_xlim(1,102);ax.set_ylabel('Percent')
        ax.grid(alpha=.18);ax.spines[['top','right']].set_visible(False)
        ax.axvline(27.5,color='#999999',ls='--',lw=.8)
        ax.scatter([100],[value],color=color,s=35,zorder=3)
        ax.legend(loc='lower left',fontsize=9,frameon=False)
        ax.text(.99,.93,f'Round 100: {value:.2f}%',ha='right',va='top',transform=ax.transAxes,color=color,fontsize=11)
    axes[1].set_xlabel('Retained-client retraining round (client 4 excluded)')
    fig.suptitle('Actual FUBA Retrain FU — all 100 rounds',fontsize=16,y=.98)
    fig.text(.5,.925,'10,000 clean images / 9,026 non-target triggered images per round; final counts independently matched',ha='center',fontsize=10)
    fig.text(.5,.035,'Dashed vertical line: saved 27-round prefix followed by verified same-condition operational recovery.',ha='center',fontsize=9)
    fig.text(.5,.008,'Original pre-FU suppression failed. This diagnostic pair does not establish whole-paper reproduction.',ha='center',fontsize=10,color='#9c2727')
    fig.subplots_adjust(top=.87,bottom=.14,hspace=.18)
    path=ROOT/'ACTUAL_RETRAIN_FU_TRAJECTORY.png';assert not path.exists()
    fig.savefig(path,dpi=180);plt.close(fig)
    proof={'state':'created_from_sealed_records','all_rounds':100,'model_loads':0,'inference':0,
           'source_manifest_sha256':seal['manifest_sha256'],'final_CA_pct':ca[-1],'final_ASR_pct':asr[-1],
           'figure_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    with (ROOT/'ACTUAL_RETRAIN_FU_TRAJECTORY.json').open('x') as f:json.dump(proof,f,indent=2)
    print(json.dumps(proof),flush=True)


if __name__=='__main__':main()
