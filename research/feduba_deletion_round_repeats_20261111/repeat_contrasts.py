"""Read-only arithmetic on the four same-size request repetitions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(n):
    return json.loads((ROOT / n).read_bytes())


def main():
    done=read('COMPLETION.json')
    assert done['state']=='complete' and done['new_FU_rounds']==30
    old=read('PANEL_stored_RESULT.json'); new=read('PANEL_new_RESULT.json')
    assert len(old['rows'])==30 and len(new['rows'])==12
    table={(x['track'],x['round']):x for x in old['rows']+new['rows']}
    ids=('p00','u00','u01','u02')
    details=[];designs=[]
    for r in (1,3,5,10):
        subsets={k:table[k,r] for k in ids}
        for k,row in subsets.items():
            c=row['clean']; ps=row['probes']
            assert c['n']==1000 and c['dark_n']==400 and c['other_n']==600
            mx=max(ps,key=lambda p:p['witness']); assert all(p['n']==900 for p in ps)
            details.append(dict(track=k,round=r,clean=c['correct'],dark=c['dark_correct'],other=c['other_correct'],
                max_fixed_probe_count=mx['witness'],max_fixed_probe=[mx['probe'],mx['arm']],
                specific_probe_counts={p['probe']:p['witness'] for p in ps if p['probe'] in ('c08','c09') and p['arm']=='route'}))
        lookup={k:{(p['probe'],p['arm']):p['witness'] for p in row['probes']} for k,row in subsets.items()}
        keys=lookup['p00']; assert all(set(v)==set(keys) for v in lookup.values())
        # Same-probe observed spread within each repeated selection, not independent FL uncertainty.
        spread_uniform=max(abs(lookup['p00'][p]-lookup['u00'][p]) for p in keys)
        spread_dark=max(abs(lookup['u01'][p]-lookup['u02'][p]) for p in keys)
        dark_higher=uniform_higher=overlapping=0
        for p in keys:
            a=[lookup[k][p] for k in ('p00','u00')]; b=[lookup[k][p] for k in ('u01','u02')]
            if min(b)>max(a):dark_higher+=1
            elif min(a)>max(b):uniform_higher+=1
            else:overlapping+=1
        designs.append(dict(round=r,uniform_same_probe_max_count_difference=spread_uniform,
                            dark_same_probe_max_count_difference=spread_dark,dark_higher_probes=dark_higher,
                            uniform_higher_probes=uniform_higher,overlap_probes=overlapping))
    output=dict(scope='same_5000_and_same_FL_history_two_request_draws_per_distribution',rows=details,repeat_comparisons=designs)
    (ROOT/'REPEAT_CONTRASTS.json').write_bytes((json.dumps(output,indent=2)+'\n').encode())
    print(json.dumps(output,indent=2))


if __name__=='__main__':main()
