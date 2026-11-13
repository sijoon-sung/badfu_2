"""Read-only comparison of the two previously sealed defensive probe arms."""
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = Path('D:/BADFU_FC_PCA_MATCHED_CONTROL_20261112')
D27 = Path('D:/PCA_SUPPORT_EXPANSION_20261112/recovery')
D29 = Path('D:/LOW_RECURRENCE_CONFIRMATION_20261112')
T04 = Path('D:/BLIND_BODY_WITNESS_AUDIT_20261111_V2')


def read(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def bind():
    freeze = read(ROOT / 'FREEZE.json')
    assert Path(freeze['root']).resolve() == ROOT
    for name, expected in freeze['files'].items():
        assert sha(ROOT / name) == expected, name
    for name, expected in freeze['dependencies'].items():
        assert sha(name) == expected, name
    sys.path.insert(1, str(BASE))
    spec = importlib.util.spec_from_file_location('frozen_d24', BASE / 'evaluate.py')
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    plan = read(BASE / 'PLAN.json')
    tasks = original.bind(plan)
    assert plan['admission']['memory_gib'] == 6
    plan['admission']['memory_gib'] = 4
    return plan, tasks


def audit(plan, tasks):
    import torch
    from probe_reference import tensor_sha
    from route_core import Endpoint, four_routes, load_native, load_transform, settings

    settings(plan)
    d20 = Path(plan['d20'])
    config = read(d20 / 'PROFILE.json')
    assert sha(config['raw_data']) == config['raw_sha256']
    raw = torch.load(config['raw_data'], map_location='cpu', weights_only=True)
    panels = {'original': read(d20 / 'PUBLIC_SPLIT.json')['test'],
              **read(BASE / 'HOLDOUT_SPLITS.json'), **read(D29 / 'NEW_SPLITS.json')}
    assert set(panels) == {'original', 'A', 'B', 'E', 'F'}
    assert len({i for panel in panels.values() for i in panel}) == 5000
    expected = {(r['case'], r['split'], r['arm']): r['native'] for r in read(D27 / 'RESULT.json')['rows']
                if r['round'] == 40 and r['split'] in ('original','A','B')}
    expected.update({(r['case'], r['split'], r['arm']): sum(r['classes']['native'])
                     for r in read(D29 / 'RESULT.json')['rows'] if r['round'] == 40 and r['case'] == r['probe_owner']})
    strict_anchor = {r['case']: r['strict_body'] for r in read(T04 / 'RESULT.json')['rows']}
    selections = read(d20 / 'SELECTIONS.json')
    out = []
    with torch.inference_mode():
        for task in tasks:
            cid = task['case']
            loaded = [load_native(task[side], 'badfu', 'cuda') for side in ('pre','post')]
            pre, post = [Endpoint(m, 'badfu') for m,_ in loaded]
            chosen = [s for s in selections if s['case'] == cid]
            assert {s['arm'] for s in chosen} == {'baseline','route'} and len(chosen)==2
            for item in chosen:
                probe = item['chosen']
                arm = item['arm']
                assert sha(probe['payload']) == probe['payload_sha256']
                transform = load_transform(probe['family'],config,probe['payload'],'cuda')
                target = probe['target']
                for panel, ids in panels.items():
                    total = stable_n = w_n = strict_n = cross_clean_n = 0
                    for batch in torch.tensor(ids).split(32):
                        labels = raw['test_y'][batch].long().cuda()
                        keep = labels != target
                        if not keep.any():
                            continue
                        y = labels[keep]
                        x = raw['test_x'][batch].permute(0,3,1,2).contiguous().float().cuda()[keep] / 255
                        p = [v.argmax(1) for v in four_routes(pre,post,x)]
                        z = four_routes(pre,post,transform(x,torch.full_like(y,target)))
                        a = [v.argmax(1) for v in z]
                        stable = (p[0]==y) & (p[3]==y)
                        w = stable & (a[0]==y) & (a[3]==target)
                        cross_clean = (p[1]==y) & (p[2]==y)
                        strict = w & cross_clean & (a[1]==y) & (a[2]==target)
                        margins = [v[:,target] - v.gather(1,y[:,None]).flatten() for v in z]
                        for i,m in enumerate(margins):
                            if i < 2:
                                assert (m[strict] <= 0).all()
                            else:
                                assert (m[strict] >= 0).all()
                        total += len(y)
                        stable_n += int(stable.sum())
                        w_n += int(w.sum())
                        cross_clean_n += int((w & cross_clean).sum())
                        strict_n += int(strict.sum())
                    assert total==900 and 0<=strict_n<=cross_clean_n<=w_n<=stable_n<=total
                    assert w_n==expected[cid,panel,arm], (cid,panel,arm,w_n)
                    if panel=='original' and arm=='baseline':
                        assert strict_n==strict_anchor[cid],cid
                    out.append(dict(case=cid,panel=panel,arm=arm,w=w_n,b=strict_n,other=w_n-strict_n))
                del transform
            for model,digest in loaded:
                assert tensor_sha(model.state_dict())==digest
            pre.close()
            post.close()
            del loaded,pre,post,model
            print(cid,flush=True)
    assert len(out)==60
    rows={(r['case'],r['panel'],r['arm']):r for r in out}
    gains=[]
    alarms={}
    for cid,panel,arm in rows:
        if arm!='baseline':
            continue
        baseline,route=[rows[cid,panel,a] for a in ('baseline','route')]
        dw,db,dr=(route[k]-baseline[k] for k in ('w','b','other'))
        assert dw==db+dr
        gains.append(dict(case=cid,panel=panel,delta_w=dw,delta_b=db,delta_other=dr,
                          supports=dw>0 and db>0 and 2*db>=dw))
    for arm,kind in [('baseline','w'),('route','w'),('route','b')]:
        limit=max(rows[c,'original',arm][kind] for c in ('c02','c03'))
        test=[(c,r[kind]) for (c,p,a),r in rows.items() if p!='original' and a==arm]
        alarms[arm+'_'+kind]=dict(threshold=limit,normal=sum(v>limit for c,v in test if c<'c04'),
                                   large_normal=sum(v>limit for c,v in test if c in ('c00','c01')),
                                   attack=sum(v>limit for c,v in test if c>='c04'))
    return dict(rows=out,gains=gains,alarms=alarms,exact_native=60,exact_t04=6,
                new_training=0,new_probe_searches=0)


if __name__=='__main__':
    (ROOT/'ONCE').open('x').write(str(os.getpid()))
    plan,tasks=bind()
    from resource_guard import admit

    admission=admit(plan)
    output=audit(plan,tasks)
    output['admission']=admission
    (ROOT/'RESULT.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8',newline='\n')
