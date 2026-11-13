"""Train clean retained-data controls and evaluate fixed defensive probes."""
import ast
import hashlib
import json
import os
import random
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CAT = Path('D:/TRAJECTORY_CATALOG_20261023')
D20 = Path('D:/BLIND_ROUTE_DETECTOR_V2_20261110')
BASE = Path('D:/BADFU_FC_PCA_MATCHED_CONTROL_20261112')
SEEDS = (20261020, 20261023)
CHECKS = (1, 2, 3, 10, 20, 30, 40)
CASE = {20261020: 'badfu.paper32.s20261020', 20261023: 'badfu.multiseed.s20261023'}
CLEAN = {20261020: 'clean_model', 20261023: 'clean_pre'}
THRESHOLDS = dict(baseline=91, route=75)
RAM_GIB = 4


def read(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(name, value):
    from bindings import write as atomic

    atomic(ROOT / name, value)


def checked(path, digest):
    assert sha(path) == digest, str(path)
    return Path(path)


def select(seed):
    output = subprocess.check_output([sys.executable, str(CAT / 'select_case.py'), CASE[seed],
                                      '--purpose','retrain_activation'], encoding='utf-8')
    return json.loads(output)


def digest_ids(ids):
    import numpy as np

    return hashlib.sha256(np.asarray(ids, dtype='<i8').tobytes()).hexdigest()


def bind():
    freeze = read(ROOT / 'FREEZE.json')
    assert Path(freeze['root']).resolve() == ROOT
    for name, expected in freeze['files'].items():
        checked(ROOT / name, expected)
    for name, expected in freeze['dependencies'].items():
        checked(name, expected)
    sys.path.insert(1, str(BASE))
    source = {s: select(s) for s in SEEDS}
    roots = {s: Path(source[s]['source_root']) for s in SEEDS}
    workspace = roots[20261020].parents[3]
    assets = workspace / 'research/stage1_20261020/assets'
    pins = read(ROOT / 'PROFILE.json')
    path = {
        'train': assets / 'cifar_train_raw.pt',
        'split': assets / 'badfu_full6_split.json',
        'author': workspace / 'review_BadFU_defend/BadFU_src/BadFU-main/badfu.py',
        'i20': roots[20261020] / 'shared_initial.pt',
        'i23': roots[20261023] / 'initial.pt',
    }
    for k,v in path.items():
        checked(v,pins['inputs'][k])
    for s in SEEDS:
        entries=source[s]['server_inputs']
        for k in (CLEAN[s], 'pre', 'post'):
            checked(entries[k]['path'], entries[k]['sha256'])
    return source,path,pins


def archived(source, seed):
    entry=source[seed]['server_inputs']['post']
    manifest=Path(entry['history_manifest'])
    pin=read(BASE/'PLAN.json')['histories']['c05' if seed==20261020 else 'c04']['manifest_sha256']
    stored=read(checked(manifest,pin))
    rows=stored if isinstance(stored,list) else stored['rounds']
    assert [r['round'] for r in rows] == list(range(1,41))
    for epoch in CHECKS:
        row=rows[epoch-1]
        model=(manifest.parent / row['path']).resolve()
        assert model.is_relative_to(manifest.parent.resolve())
        checked(model,row['sha256'])
        yield epoch,dict(path=str(model),sha256=row['sha256'],payload_key=entry['payload_key'])


def trainer(path):
    import torch
    import torchvision.models as models
    from torch import nn,optim

    tree=ast.parse(path.read_text(encoding='utf-8'))
    names={'ResNet18ForCIFAR10client','local_train','fed_avg'}
    nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names]
    assert {n.name for n in nodes}==names
    scope=dict(torch=torch,nn=nn,optim=optim,models=models)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),scope)
    return scope


def datasets(path):
    import numpy as np
    import torch
    from torch.utils.data import TensorDataset

    raw=torch.load(path['train'],weights_only=True,map_location='cpu')
    x,y=raw['train_x'],raw['train_y'].long()
    assert tuple(x.shape)==(50000,32,32,3) and y.bincount().tolist()==[5000]*10
    assert x.dtype==torch.uint8
    split=read(path['split'])
    parts=[list(map(int,part)) for part in split['clean_cifar10_indices']]
    parts[0]+=split['poison_cifar10_indices']+split['cover_cifar10_indices']
    assert list(map(len,parts))==[11395,9647,9641,9649,9668]
    assert sorted(i for part in parts for i in part)==list(range(50000))
    bright=x.sum(dim=(1,2,3)).numpy()
    labels=y.numpy()
    norm=(x.permute(0,3,1,2).float()/255-torch.tensor([.4914,.4822,.4465])[None,:,None,None])/torch.tensor([.2023,.1994,.2010])[None,:,None,None]
    data={}
    summaries={}
    for seed in SEEDS:
        rng=np.random.default_rng(seed+20261113)
        domain=[]
        dark=np.zeros(len(labels),dtype=bool)
        for cls in range(10):
            idx=np.flatnonzero(labels==cls)
            low=idx[np.lexsort((idx,bright[idx]))[:2000]]
            dark[low]=True
            domain.extend(rng.choice(low,1000,replace=False).tolist())
        for label,removed in [('whole_client1',parts[1]),('dark_balanced',domain)]:
            r=set(removed)
            kept={i:[k for k in ids if k not in r] for i,ids in enumerate(parts)}
            all_kept=[k for ids in kept.values() for k in ids]
            assert len(r)==len(removed) and len(all_kept)==50000-len(r)
            assert not r.intersection(all_kept)
            if label=='dark_balanced':
                assert dark[removed].all() and y[removed].bincount().tolist()==[1000]*10
            name=f'{seed}_{label}'
            summaries[name]=dict(seed=seed,condition=label,removed=len(r),retained=len(all_kept),
                counts=[len(kept[i]) for i in range(5)],removed_classes=y[removed].bincount(minlength=10).tolist(),
                retained_dark=int(dark[all_kept].sum()),removed_sha256=digest_ids(sorted(r)),
                retained_sha256=digest_ids(all_kept))
            data[name]={i:TensorDataset(norm[ids],y[ids]) for i,ids in kept.items() if ids}
    write('DATA_AUDIT.json',summaries)
    return data


def detector(pins):
    import torch
    from route_core import load_transform

    cfg=read(D20/'PROFILE.json')
    checked(cfg['raw_data'],cfg['raw_sha256'])
    selected=read(D20/'SELECTIONS.json')
    raw=torch.load(cfg['raw_data'],weights_only=True,map_location='cpu')
    public=read(D20/'PUBLIC_SPLIT.json')
    ids=public['test']
    assert len(set(ids))==1000 and not set(ids).intersection(public['fit']+public['calibration'])
    y=raw['test_y'][ids].long().cuda()
    x=raw['test_x'][ids].permute(0,3,1,2).contiguous().float().cuda()/255
    assert y.bincount().tolist()==[100]*10
    probes=[]
    for s in selected:
        if s['case'] not in pins['probe_owners']:
            continue
        spec=s['chosen']
        p=checked(spec['payload'],spec['payload_sha256'])
        transform=load_transform(spec['family'],cfg,str(p),'cuda')
        probes.append((s['case'],s['arm'],spec['target'],transform))
    assert len(probes)==12 and len({(p[0],p[1]) for p in probes})==12
    return x,y,probes


def score(pre, post, public):
    import torch
    from route_core import four_routes

    x,y,probes=public
    counts=[]
    with torch.inference_mode():
        for owner,arm,target,transform in probes:
            w=b=0
            for bx,by in zip(x.split(32),y.split(32)):
                keep=by!=target
                if not keep.any():
                    continue
                a,t=bx[keep],by[keep]
                p=[z.argmax(1) for z in four_routes(pre,post,a)]
                q=[z.argmax(1) for z in four_routes(pre,post,transform(a,torch.full_like(t,target)))]
                native=(p[0]==t)&(p[3]==t)&(q[0]==t)&(q[3]==target)
                strict=native&(p[1]==t)&(p[2]==t)&(q[1]==t)&(q[2]==target)
                w+=int(native.sum())
                b+=int(strict.sum())
            assert 0<=b<=w<=900
            counts.append(dict(owner=owner,arm=arm,w=w,b=b))
    def maximum(owner_limit):
        return {a:max(r[k] for r in counts if r['arm']==a and r['owner']<owner_limit)
                for a,k in [('baseline','w'),('route','b')]}
    return dict(scores=maximum('c06'),normal_origin_scores=maximum('c04'),counts=counts)


def check_comparison(rows):
    summary={}
    for epoch in CHECKS:
        group=[r for r in rows if r['round']==epoch]
        neg=[r for r in group if not r['attack']]
        pos=[r for r in group if r['attack']]
        if len(neg)!=4 or len(pos)!=2:
            continue
        studies={}
        for field in ('scores','normal_origin_scores'):
            fixed={}
            equal={}
            splits=[]
            for method,threshold in THRESHOLDS.items():
                n=[r[field][method] for r in neg]
                a=[r[field][method] for r in pos]
                fixed[method]=[sum(v>threshold for v in n),sum(v>threshold for v in a)]
                ops=[(sum(v>t for v in n),sum(v>t for v in a)) for t in set(n+a+[-1])]
                equal[method]=[max(p for k,p in ops if k<=budget) for budget in (0,1)]
            for seed in SEEDS:
                stats={}
                for method in THRESHOLDS:
                    t=max(r[field][method] for r in neg if r['seed']==seed)
                    stats[method]=dict(threshold=t,held_normal=sum(r[field][method]>t for r in neg if r['seed']!=seed),
                                       attack=sum(r[field][method]>t for r in pos))
                splits.append(dict(calibration_seed=seed,methods=stats))
            studies[field]=dict(fixed=fixed,descriptive_same_alarm_budget=equal,seed_holdout=splits)
        summary[str(epoch)]=studies
    return summary


def execute(source,path,pins):
    import numpy as np
    import torch
    from torch.utils.data import DataLoader
    from probe_reference import tensor_sha
    from route_core import Endpoint, load_native, settings

    settings(pins)
    functions=trainer(path['author'])
    make=functions['ResNet18ForCIFAR10client']
    train=functions['local_train']
    aggregate=functions['fed_avg']
    data=datasets(path)
    public=detector(pins)
    endpoints={}
    rows=[]
    def record(seed,name,epoch,attack,post):
        before=endpoints[seed,attack]
        scored=score(before,post,public)
        rows.append(dict(seed=seed,request=name,round=epoch,attack=attack,**scored))
        write('SCORES.json',rows)
        write('COMPARISON.json',check_comparison(rows))
    for seed in SEEDS:
        binding=source[seed]['server_inputs']
        for attack,k in [(False,CLEAN[seed]),(True,'pre')]:
            model,_=load_native(binding[k],'badfu','cuda')
            endpoints[seed,attack]=Endpoint(model,'badfu')
    initial={s:torch.load(path['i20' if s==20261020 else 'i23'],map_location='cpu',weights_only=True) for s in SEEDS}
    assert tensor_sha(initial[SEEDS[0]])!=tensor_sha(initial[SEEDS[1]])
    states={key:initial[int(key[:8])] for key in data}
    epochs={s:dict(archived(source,s)) for s in SEEDS}
    for r in range(1,41):
        if r in CHECKS:
            for seed in SEEDS:
                model,digest=load_native(epochs[seed][r],'badfu','cuda')
                end=Endpoint(model,'badfu')
                record(seed,'stored_attack',r,True,end)
                assert tensor_sha(model.state_dict())==digest
                end.close()
                del model,end
        for name,clients in data.items():
            seed=int(name[:8])
            counts=[len(ds) for ds in clients.values()]
            updates=[]
            for cid,ds in clients.items():
                write('STATE.json',dict(stage='training',pid=os.getpid(),request=name,round=r,client=cid))
                rnd=seed+10000*r+cid
                random.seed(rnd)
                np.random.seed(rnd)
                torch.manual_seed(rnd)
                model=make().cuda()
                model.load_state_dict(states[name])
                trained=train(model,DataLoader(ds,batch_size=32,shuffle=True,num_workers=0),5,'cuda')
                updates.append({k:v.detach().cpu() for k,v in trained.items()})
                del model,trained
            model=make().cpu()
            model.load_state_dict(states[name])
            aggregate(model,updates,counts)
            state=model.state_dict()
            for k,value in state.items():
                expected=torch.zeros_like(value,dtype=torch.float32)
                for u,n in zip(updates,counts):
                    expected+=u[k].float()*(n/sum(counts))
                if value.dtype==torch.long:
                    expected=expected.round()
                assert torch.isfinite(value).all() and torch.equal(expected.to(value.dtype),value),k
            states[name]=state
            folder=ROOT/'models'/name
            folder.mkdir(parents=True,exist_ok=True)
            target=folder/f'round_{r:04d}.pt'
            temporary=target.with_suffix('.tmp')
            torch.save(state,temporary)
            temporary.replace(target)
            digest=sha(target)
            assert tensor_sha(torch.load(target,map_location='cpu',weights_only=True))==tensor_sha(state)
            write('commits/'+name+f'_{r:02d}.json',dict(round=r,request=name,sha256=digest,counts=counts))
            del updates
            if r in CHECKS:
                end=Endpoint(model.eval().cuda(),'badfu')
                record(seed,name,r,False,end)
                end.close()
            del model
    assert len(rows)==42 and len(check_comparison(rows))==len(CHECKS)
    write('STATE.json',dict(stage='complete',rows=len(rows),normal_rounds=160))


if __name__=='__main__':
    try:
        source,path,pins=bind()
        if '--preflight' in sys.argv:
            write('PREFLIGHT.json',dict(state='passed',seeds=SEEDS,guard_profile=pins['admission']))
            raise SystemExit(0)
        (ROOT/'ONCE').open('x').write(str(os.getpid()))
        from resource_guard import admit

        write('ADMISSION.json',admit(pins))
        execute(source,path,pins)
    except Exception:
        (ROOT/'FAILURE.txt').write_text(traceback.format_exc(),encoding='utf-8')
        raise
