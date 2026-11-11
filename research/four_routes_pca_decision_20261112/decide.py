"""Apply the frozen normal-only decision rule to the completed counts."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
METHODS = ('native','four_routes','feature_pca','feature_random','fc_pca')
NORMAL_CALIBRATION = ('p00','p01','p02')
NORMAL_HOLDOUT = ('u00','u01','u02')
DIAGNOSTICS = ('p03','p04')


def read(name):
    return json.loads((ROOT/name).read_bytes())


def score(row, method, primary=True):
    selected = [p for p in row['probes'] if p['primary_panel'] or not primary]
    assert selected and all(p['n']==900 for p in selected)
    return max(p[method] for p in selected)


def feduba(rows, thresholds, primary=True):
    decisions = {}
    for method in METHODS:
        scores = {(r['track'],r['round']):score(r,method,primary) for r in rows}
        bound = max(s for (t,_),s in scores.items() if t in NORMAL_CALIBRATION)
        if primary:
            assert bound==thresholds[method]
        flags = {t:[r for (v,r),s in scores.items() if v==t and s>bound] for t in NORMAL_HOLDOUT+DIAGNOSTICS}
        fp=sum(bool(flags[t]) for t in NORMAL_HOLDOUT)
        late=sum(r in flags[t] for t in DIAGNOSTICS for r in (10,15,20))
        decisions[method]=dict(threshold_count=bound,normal_request_false_alarms=fp,normal_requests=3,
           late_diagnostic_hits=late,late_diagnostic_checks=6,criterion_passed=fp==0 and late==6,
           flags_by_request=flags,score_rows=[dict(track=t,round=r,count=s) for (t,r),s in scores.items()])
    return decisions


def badfu(rows):
    out = {}
    for method in METHODS:
        scores={r['track']:score(r,method) for r in rows}
        splits=[]
        for hold, anchor in (('c00','c01'),('c01','c00')):
            threshold=max(scores[t] for t in (anchor,'c02','c03'))
            hit=[t for t in ('c04','c05') if scores[t]>threshold]
            splits.append(dict(holdout=hold,calibration_large=anchor,threshold_count=threshold,
                               normal_alert=scores[hold]>threshold,attack_hits=hit))
        out[method]=dict(score_counts=scores,splits=splits,
                         both_splits_passed=all(not s['normal_alert'] and len(s['attack_hits'])==2 for s in splits))
    return out


def main():
    raw=read('RESULT.json')
    assert raw['state']=='complete' and raw['native_counts_exact']
    panel=[r for r in raw['rows'] if r['group']=='feduba']
    endpoints=[r for r in raw['rows'] if r['group']=='badfu']
    assert len(panel)==42 and len(endpoints)==6
    assert {r['track']:r for r in read('BADFU_NORMAL_COUNTS.json')}=={r['track']:r for r in endpoints if r['track'] in ('c00','c01','c02','c03')}
    thresholds=read('NORMAL_THRESHOLDS.json')
    assert thresholds['calibration_rows']==18 and thresholds['n']==900
    f=feduba(panel,thresholds['strictly_greater_than'])
    b=badfu(endpoints)
    summary=dict(denominator=900,feduba_normal_probe_panel=f,feduba_all_probe_sensitivity=feduba(panel,{},False),badfu_large_normal_holdout=b)
    (ROOT/'DECISION.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
    for m in METHODS:
        print(m, 'FedUBA', {k:v for k,v in f[m].items() if k!='score_rows'}, 'BadFU', b[m])


if __name__=='__main__':main()
