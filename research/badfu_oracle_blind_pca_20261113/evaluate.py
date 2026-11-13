"""Evaluate already stored BadFU inputs and compare frozen defensive scores."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = Path('D:/BADFU_FC_PCA_MATCHED_CONTROL_20261112')
T03 = Path('D:/BADFU_FEDUBA_DEFENSE_20261031')
D27 = Path('D:/PCA_SUPPORT_EXPANSION_20261112/recovery')
METHODS = ('native', 'pca_320', 'random_1_320', 'random_2_320', 'random_3_320')


def read(p):
    return json.loads(Path(p).read_bytes())


def sha(p):
    with Path(p).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def decision():
    rows = read(D27 / 'RESULT.json')['rows']
    assert len(rows) == 180
    scores = {}
    for row in rows:
        key = (row['round'], row['split'], row['case'])
        scores.setdefault(key, []).append(row)
    assert all(len(pair) == 2 and {r['arm'] for r in pair} == {'baseline', 'route'} for pair in scores.values())
    out = {}
    for name in METHODS:
        vals = {key: max(r[name] for r in pair) for key, pair in scores.items()}
        limit = max(vals[40, 'original', cid] for cid in ('c02', 'c03'))
        endpoints = [(panel, cid, vals[40, panel, cid]) for panel in 'ABCD'
                     for cid in ('c00', 'c01', 'c02', 'c03', 'c04', 'c05')]
        neg = [v for _, cid, v in endpoints if cid < 'c04']
        pos = [v for _, cid, v in endpoints if cid >= 'c04']
        possible = [(sum(v > t for v in neg), sum(v > t for v in pos))
                    for t in set(neg + pos + [-1])]
        out[name] = dict(threshold=limit, normal_alarms=sum(v > limit for v in neg),
                         attack_alarms=sum(v > limit for v in pos),
                         large_normal_alarms=sum(v > limit and cid in ('c00', 'c01') for _,cid,v in endpoints),
                         by_panel=endpoints,
                         max_detection_at_normal_budget=[max(p for n,p in possible if n <= k) for k in range(3)],
                         rounds=[dict(round=epoch,
                            normal=sum(v>limit for (r,s,c),v in vals.items() if r==epoch and s in 'ABCD' and c<'c04'),
                            attack_history=sum(v>limit for (r,s,c),v in vals.items() if r==epoch and s in 'ABCD' and c>='c04'))
                            for epoch in (10,20,30)])
    return out


def bind():
    sys.path.insert(1, str(BASE))
    spec = importlib.util.spec_from_file_location('prior_binding', BASE / 'evaluate.py')
    prior = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prior)
    plan = read(BASE / 'PLAN.json')
    tasks = prior.bind(plan)
    assert plan['admission']['memory_gib'] == 6
    plan['admission']['memory_gib'] = 4
    return plan, tasks


def oracle(plan, tasks):
    import numpy as np
    import torch
    from PIL import Image
    from probe_reference import tensor_sha
    from route_core import Endpoint, load_native, settings

    settings(plan)
    cfg = read(Path(plan['d20']) / 'PROFILE.json')
    info = read(T03 / 'STAGE03_INPUTS.json')
    for k in ('record_path','image_manifest_path','clean_path'):
        assert sha(info[k]) == info[k+'_sha256'], k
    assert sha(cfg['raw_data']) == cfg['raw_sha256']
    raw = torch.load(cfg['raw_data'], map_location='cpu', weights_only=True)
    clean_reference = torch.load(info['clean_path'], map_location='cpu', weights_only=True)
    x, y = raw['test_x'], raw['test_y'].long()
    assert torch.equal(clean_reference['test_x'], x) and torch.equal(clean_reference['test_y'].long(), y)
    del raw, clean_reference
    manifest = {k.replace(chr(92), '/'): v for k,v in read(info['image_manifest_path'])['image_sha256'].items()}
    record = torch.load(info['record_path'], map_location='cpu', weights_only=False)
    entries = record['bd_test']['bd_data_container']['data_dict']
    keys = sorted(int(k) for k in entries)
    target = int(next(iter(entries.values()))['other_info'][0])
    assert keys == torch.where(y != target)[0].tolist()
    actual = torch.empty_like(x)
    for key, row in entries.items():
        parts = str(row['path']).replace(chr(92), '/').split('/')
        relative = '/'.join(parts[parts.index('bd_test_dataset'):])
        file = Path(info['record_root']) / relative
        assert sha(file) == manifest[relative] and int(row['other_info'][0]) == target
        with Image.open(file) as image:
            actual[int(key)] = torch.from_numpy(np.asarray(image.convert('RGB')).copy())
    del record, entries
    original = read(Path(plan['d20']) / 'PUBLIC_SPLIT.json')['test']
    holdout = read(D27 / 'NEW_SPLITS.json')
    panels = dict(full=keys, original=original, **read(BASE/'HOLDOUT_SPLITS.json'), C=holdout['C'], D=holdout['D'])
    assert len(set(sum([panels[k] for k in ('original','A','B','C','D')], []))) == 5000

    def infer(model, data):
        outputs = []
        for batch in data.split(32):
            z = batch.permute(0, 3, 1, 2).contiguous().float().cuda() / 255
            outputs.append(model(z).argmax(1).cpu())
        return torch.cat(outputs)

    def predictions(binding):
        model,digest = load_native(binding,'badfu','cuda')
        ep = Endpoint(model,'badfu',capture=False)
        a = infer(ep,x)
        b = torch.full_like(y,-1)
        b[keys] = infer(ep,actual[keys])
        assert tensor_sha(model.state_dict()) == digest
        return a,b

    rows = []
    cached = {}
    with torch.inference_mode():
        for task in tasks:
            endpoint = {}
            for key in ('pre','post'):
                binding = task[key]
                h = binding['sha256']
                if h not in cached:
                    cached[h] = predictions(binding)
                endpoint[key] = cached[h]
            pre, post = endpoint['pre'], endpoint['post']
            stable = (pre[0] == y) & (post[0] == y)
            witness = stable & (pre[1] == y) & (post[1] == target)
            for panel, indexes in panels.items():
                selected = torch.tensor(indexes)
                chosen = selected[y[selected] != target]
                assert len(chosen) == (9000 if panel=='full' else 900)
                event = chosen[witness[chosen]]
                rows.append(dict(case=task['case'],split=panel,n=len(chosen),clean_pre=int((pre[0][selected]==y[selected]).sum()),
                                 clean_post=int((post[0][selected]==y[selected]).sum()),clean_n=len(selected),
                                 asr_pre=int((pre[1][chosen]==target).sum()),asr_post=int((post[1][chosen]==target).sum()),
                                 stable=int(stable[chosen].sum()),witness=len(event),
                                 by_class=torch.bincount(y[event],minlength=10).tolist()))
    full = {r['case']:r for r in rows if r['split']=='full'}
    full_clean = {}
    for t in tasks:
        full_clean[t['case']] = {k:int((cached[t[k]['sha256']][0] == y).sum()) for k in ('pre','post')}
    anchors = {cid:abs(full[cid]['witness']-expected) for cid,expected in [('c00',9),('c02',8),('c04',6754)]}
    for cid,pre,post in [('c04',1286,9000),('c05',1453,8999)]:
        anchors[cid+'_pre'] = abs(full[cid]['asr_pre']-pre)
        anchors[cid+'_post'] = abs(full[cid]['asr_post']-post)
    assert len(rows)==36
    return dict(rows=rows,clean_accuracy_10000=full_clean,anchor_abs_differences=anchors,
                anchors_pass=max(anchors.values())<=2)


def main():
    (ROOT / 'ONCE').open('x').close()
    freeze = read(ROOT/'FREEZE.json')
    for name,digest in freeze['files'].items():
        assert sha(ROOT/name)==digest,name
    for name,digest in freeze['dependencies'].items():
        assert sha(name)==digest,name
    plan,tasks = bind()
    from resource_guard import admit
    admission = admit(plan)
    known = oracle(plan,tasks)
    result = dict(oracle=known,blind=decision(),admission=admission,training=0,new_probe_searches=0)
    (ROOT/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    if not known['anchors_pass']:
        raise SystemExit('Evaluator anchor outside tolerance')


if __name__=='__main__':
    main()
