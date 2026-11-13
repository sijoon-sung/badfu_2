"""Report eligible-input and witness-persistence sensitivity from stored integers."""
from fractions import Fraction
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    rows = []
    for stage in ('stored','new'):
        p = ROOT / ('PANEL_'+stage+'_RESULT.json')
        if p.exists(): rows.extend(json.loads(p.read_bytes())['rows'])
    groups = {}
    for row in rows:
        for p in row['probes']:
            groups.setdefault((row['round'],p['probe'],p['arm']),{})[row['track']]=p
    per_round = {}
    for (r,pid,arm), by in sorted(groups.items()):
        normal = [k for k in by if k not in ('p02','p03','p04')]
        attack = ['p03','p04']
        def eligible(p):
            return None if not p['stable'] else Fraction(p['witness'],p['stable'])
        def persist(p):
            if p['kept'] is None or p['kept']+p['lost']==0:return None
            return Fraction(p['kept'],p['kept']+p['lost'])
        dest = per_round.setdefault(r,{'eligible_compared':0,'eligible_overlap':0,'eligible_attack_probe_overlap':0,
                                      'persistence_compared':0,'persistence_overlap':0,'persistence_unmeasured':0})
        for name,func in (('eligible',eligible),('persistence',persist)):
            aa=[func(by[k]) for k in attack];nn=[func(by[k]) for k in normal]
            if None in aa or None in nn:
                if name=='persistence':dest['persistence_unmeasured']+=1
                continue
            dest[name+'_compared']+=1
            hit=max(nn)>=min(aa);dest[name+'_overlap']+=int(hit)
            if hit and name=='eligible' and pid in ('c08','c09'):dest['eligible_attack_probe_overlap']+=1
    result=dict(scope='post_hoc_sensitivity_only_not_a_detector',actual_model_rows=len(rows),rounds=per_round)
    (ROOT/'DIAGNOSTIC_ARITHMETIC.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
