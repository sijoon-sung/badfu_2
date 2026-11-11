"""Apply only the published thresholds to all case and round scores."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
METHODS=('native','pca','random_1','random_2','random_3','full_head')
NORMALS=('c00','c01','c02','c03')
ATTACKS=('c04','c05')


def main():
    raw=json.loads((ROOT/'RESULT.json').read_bytes())
    assert raw['original_counts_exact'] and raw['terminal_tensor_history_exact'] and raw['matched_removed_norm']
    scores={}
    for row in raw['rows']:
        key=(row['case'],row['round'],row['split']);m=scores.setdefault(key,dict.fromkeys(METHODS,0))
        assert row['n']==900
        for method in METHODS:m[method]=max(m[method],row[method])
    assert len(scores)==48
    fixed={};calibrated={}
    for method in METHODS:
        panels={}
        for split in ('A','B'):
            vals={k:scores[k,40,split][method] for k in NORMALS+ATTACKS}
            panels[split]=dict(counts=vals,normal_alerts=[k for k in NORMALS if vals[k]>5],attack_alerts=[k for k in ATTACKS if vals[k]>5])
        fixed[method]=panels
        checks=[]
        for hold,anchor in (('c00','c01'),('c01','c00')):
            threshold=max(scores[k,40,'original'][method] for k in (anchor,'c02','c03'))
            by_panel={}
            for split in ('A','B'):
                by_panel[split]=dict(held_out_normal_alert=scores[hold,40,split][method]>threshold,
                     attack_alerts=[k for k in ATTACKS if scores[k,40,split][method]>threshold])
            checks.append(dict(holdout=hold,threshold=threshold,panels=by_panel))
        calibrated[method]=checks
    rows=[dict(case=k[0],round=k[1],split=k[2],scores=v,pca_alarm=v['pca']>5) for k,v in scores.items()]
    result=dict(fixed_threshold_strictly_greater_than=5,n=900,by_fixed_threshold=fixed,
        calibrated_on_original_test=calibrated,checkpoint_scores=rows,
        fixed_pca_passed=all(not q['normal_alerts'] and len(q['attack_alerts'])==2 for q in fixed['pca'].values()))
    (ROOT/'DECISION.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps({k:v for k,v in result.items() if k!='checkpoint_scores'},indent=2))


if __name__=='__main__':main()
