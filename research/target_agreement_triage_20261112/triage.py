"""Classify requests from sealed D20 and D25 aggregates."""
from fractions import Fraction
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
ARMS = ('baseline', 'route')
PANELS = ('A', 'B')
CAL = ('c02', 'c03')
HOLDOUT = ('c00', 'c01', 'c04', 'c05')
MIN_ELIGIBLE = 20


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def rate(row):
    assert row['n'] == 900 and 0 <= row['joint'] <= row['eligible'] <= row['native'] <= row['n']
    return Fraction(row['joint'], row['eligible']) if row['eligible'] >= MIN_ELIGIBLE else None


def triage(flags, target_agrees):
    flat = tuple(v for arm in ARMS for v in flags[arm])
    if None in flat:
        return dict(single_confirmed='abstain', both_confirmed='abstain', joint='abstain')
    quiet = not any(flat)
    single = any(all(flags[arm]) for arm in ARMS)
    both = all(flat)

    def decide(alarm):
        return 'alert' if alarm else 'pass' if quiet else 'abstain'

    return dict(single_confirmed=decide(single), both_confirmed=decide(both),
                joint=decide(both and target_agrees))


def main():
    freeze = read(ROOT/'FREEZE.json')
    receipt = read(ROOT/'PUBLICATION.json')
    assert receipt['all_raw_blob_bytes_verified'] and receipt['freeze_sha256']==sha(ROOT/'FREEZE.json')
    assert all(sha(ROOT/n)==v for n,v in freeze['files'].items())
    p=read(ROOT/'PLAN.json')
    assert all(sha(n)==v for n,v in p['references'].items())
    d20=read(p['d20'])
    d25=read(p['d25'])
    cases=set(CAL+HOLDOUT)
    targets={(q['case'],q['arm']):q['target'] for q in d20['results'] if q['case'] in cases}
    assert len(targets)==12
    rows={}
    for q in d25['rows']:
        case=q['track']
        if case not in cases:
            continue
        assert q['probe']==case and q['round'] is None
        key=(case,q['split'],q['arm'])
        assert key not in rows
        rate(q)
        rows[key]=q
    assert len(rows)==36
    cuts={}
    for arm in ARMS:
        values=[rate(rows[c,'original',arm]) for c in CAL]
        assert None not in values
        cuts[arm]=max(values)
    decisions={}
    for case in HOLDOUT:
        flags={}
        evidence={}
        for arm in ARMS:
            vals=[rate(rows[case,panel,arm]) for panel in PANELS]
            flags[arm]=[None if v is None else v>cuts[arm] for v in vals]
            evidence[arm]={panel:{'joint':rows[case,panel,arm]['joint'],'eligible':rows[case,panel,arm]['eligible'],
                                  'exceeds':v} for panel,v in zip(PANELS,flags[arm])}
        ts=[targets[case,arm] for arm in ARMS]
        agree=ts[0]==ts[1]
        decisions[case]=dict(targets=ts,target_agrees=agree,evidence=evidence,decision=triage(flags,agree))
    # Only the aggregate evaluation below uses the known request labels.
    cases_by_truth={'large_normal':('c00','c01'),'attack':('c04','c05')}
    tally={}
    for rule in ('single_confirmed','both_confirmed','joint'):
        tally[rule]={k:{v:sum(decisions[c]['decision'][rule]==v for c in ids)
                        for v in ('alert','pass','abstain')} for k,ids in cases_by_truth.items()}
    joint=tally['joint']
    passed=joint['large_normal']['alert']==0 and joint['large_normal']['pass']>=1 and joint['attack']['alert']==2
    output=dict(state='classified_stored_requests',thresholds={a:str(v) for a,v in cuts.items()},decisions=decisions,
        evaluation=tally,predeclared_acceptance_passed=passed,model_loads=0,new_inferences=0,new_training=0)
    with (ROOT/'RESULT.json').open('x',encoding='utf-8',newline='\n') as out:
        out.write(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))


if __name__=='__main__':
    main()
