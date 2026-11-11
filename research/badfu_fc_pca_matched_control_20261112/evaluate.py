"""Validate the frozen BadFU FC rule on new images and matched FC controls."""
import os
from pathlib import Path
import time
import traceback

from bindings import ROOT, read, select, sha, write


def ident(m):
    return os.path.normcase(os.path.normpath(m['path'])), m['sha256'], m['payload_key']


def bind(plan):
    assert read(ROOT/'PUBLICATION.json')['freeze_sha256']==sha(ROOT/'FREEZE.json')
    for n,v in read(ROOT/'FREEZE.json')['files'].items():assert sha(ROOT/n)==v,n
    for p,v in plan['references'].items():assert sha(p)==v,p
    d20=Path(plan['d20']);source=read(d20/'INPUTS.json')
    selected={};histories={};tasks=[]
    choices=read(ROOT/'BADFU_SELECTION.json')
    for row in source['cases']:
        cid=row['id']
        if cid not in choices:continue
        cfg=choices[cid]; key=(cfg['case_id'],cfg['purpose'])
        if key not in selected:selected[key]=select(*key)['server_inputs']
        for k in ('pre','post'):
            assert ident(row[k])==ident(selected[key][cfg[k]]),(cid,k)
        items={}
        if cid in plan['histories']:
            h=plan['histories'][cid];key=h['case']
            if key not in histories:
                select(key,'global_history')
                histories[key]=select(key,'retrain_activation')['server_inputs']
            entry=histories[key][h['post']];mp=Path(entry['history_manifest'])
            assert sha(mp)==h['manifest_sha256']
            raw=read(mp);rounds=raw if isinstance(raw,list) else raw['rounds']
            assert [r['round'] for r in rounds]==list(range(1,41))
            for r in (10,20,30,40):
                item=rounds[r-1];p=(mp.parent/item['path']).resolve()
                assert p.is_relative_to(mp.parent.resolve())
                assert sha(p)==item['sha256']
                items[r]=dict(path=str(p),sha256=item['sha256'],payload_key=entry['payload_key'])
        tasks.append(dict(case=cid,pre=row['pre'],post=row['post'],history=items))
    assert len(tasks)==6 and sum(len(t['history']) for t in tasks)==20
    return tasks


def run(plan,tasks):
    import numpy as np
    import torch
    from torch.nn.functional import linear
    from probe_reference import tensor_sha
    from route_core import Endpoint, load_native, load_transform, settings

    settings(plan)
    d20=Path(plan['d20']);cfg=read(d20/'PROFILE.json');splits=read(d20/'PUBLIC_SPLIT.json')
    assert sha(cfg['raw_data'])==cfg['raw_sha256']
    raw=torch.load(cfg['raw_data'],map_location='cpu',weights_only=True)
    labels=raw['test_y'].tolist()
    used=set(splits['fit']+splits['calibration']+splits['test'])
    rng=np.random.default_rng(2026111211);holdouts={'A':[],'B':[]}
    for c in range(10):
        ids=[i for i,y in enumerate(labels) if y==c and i not in used]
        permutation=rng.permutation(ids)
        holdouts['A'].extend(permutation[:100].tolist());holdouts['B'].extend(permutation[100:200].tolist())
    assert len(set(holdouts['A']+holdouts['B']))==2000 and not used.intersection(holdouts['A']+holdouts['B'])
    write(ROOT/'HOLDOUT_SPLITS.json',holdouts)
    assert sha(d20/'SELECTIONS.json')==read(d20/'SELECTION_SEAL.json')['sha256']
    selections=read(d20/'SELECTIONS.json')
    d23={r['track']:{q['arm']:q for q in r['probes']} for r in read(plan['d23_result'])['rows'] if r['group']=='badfu'}
    original={(r['case'],r['arm']):r for r in read(d20/'RESULT.json')['results']}

    def samples(ids):
        for b in torch.tensor(ids).split(32):
            yield raw['test_x'][b].permute(0,3,1,2).contiguous().float().cuda()/255,raw['test_y'][b].long().cuda()

    def capture(ep,x):
        pred=ep(x).argmax(1)
        return ep.feature,pred

    def projection(x,v):
        return (x@v)@v.T

    def head_comparisons(pre,post,mean,axes,random_axes):
        delta=post.head.weight-pre.head.weight
        pca=delta-projection(delta,axes)
        norm=float(torch.linalg.vector_norm(pca))
        edits={'pca':pca,'full_head':delta}
        for i,v in enumerate(random_axes,1):
            rem=delta-projection(delta,v)
            rem_norm=float(torch.linalg.vector_norm(rem))
            assert rem_norm>0
            rem=rem*(norm/rem_norm)
            assert abs(float(torch.linalg.vector_norm(rem))-norm)<=1e-5*max(norm,1e-8)
            edits[f'random_{i}']=rem
        weights={k:(post.head.weight-w,post.head.bias+w@mean) for k,w in edits.items()}
        assert all(torch.isfinite(v).all() for pair in weights.values() for v in pair)
        return weights,norm

    def measure(post,batches,t,weights):
        out=dict(n=0,stable=0,native=0)
        for k in weights:
            out[k]=0;out[k+'_clean']=0
        classes=[0]*10
        for x,z,y,pre_clean,pre_z in batches:
            hx,a=capture(post,x);hz,b=capture(post,z)
            stable=(pre_clean==y)&(a==y)
            w=stable&(pre_z==y)&(b==t)
            out['n']+=len(y);out['stable']+=int(stable.sum());out['native']+=int(w.sum())
            classes=[a+b for a,b in zip(classes,torch.bincount(y[w],minlength=10).tolist())]
            for k,(weight,bias) in weights.items():
                clean=linear(hx,weight,bias).argmax(1)==y
                out[k]+=int((w&clean&(linear(hz,weight,bias).argmax(1)==y)).sum())
                out[k+'_clean']+=int(clean.sum())
        assert out['n']==900
        return out,classes

    started=time.monotonic(); rows=[]
    with torch.inference_mode():
        for task in tasks:
            cid=task['case'];pm,pd=load_native(task['pre'],'badfu','cuda');qm,qd=load_native(task['post'],'badfu','cuda')
            pre=Endpoint(pm,'badfu')
            fit=torch.cat([capture(pre,x)[0] for x,_ in samples(splits['fit'])]).cpu().double()
            mean=fit.mean(0);_,sing,vh=torch.linalg.svd(fit-mean,full_matrices=False)
            power=sing.square();rank=int(torch.searchsorted(power.cumsum(0),power.sum()*.95))+1
            axes=vh[:rank].T.contiguous().float().cuda();mean=mean.float().cuda()
            random_axes=[]
            for seed in (2026111201,2026111202,2026111203):
                g=torch.Generator(device='cpu').manual_seed(seed)
                v=torch.randn(fit.shape[1],rank,dtype=torch.float64,generator=g)
                random_axes.append(torch.linalg.qr(v,mode='reduced').Q.float().cuda())
            if 40 in task['history']:
                check,digest=load_native(task['history'][40],'badfu','cpu');assert digest==qd,cid;del check
            probes=[]
            for s in selections:
                if s['case']!=cid:continue
                m=s['chosen'];assert sha(m['payload'])==m['payload_sha256']
                t=m['target'];transform=load_transform(m['family'],cfg,m['payload'],'cuda')
                by_split={}
                for name,ids in dict(original=splits['test'],**holdouts).items():
                    batches=[]
                    for x,y in samples(ids):
                        keep=y!=t
                        if not keep.any():continue
                        x,y=x[keep],y[keep];z=transform(x,torch.full_like(y,t))
                        batches.append((x,z,y,capture(pre,x)[1],capture(pre,z)[1]))
                    by_split[name]=batches
                probes.append((s['arm'],t,by_split));del transform
            assert len(probes)==2
            for r in ([40,10,20,30] if task['history'] else [40]):
                if r==40:model,digest=qm,qd
                else:model,digest=load_native(task['history'][r],'badfu','cuda')
                post=Endpoint(model,'badfu')
                weights,norm=head_comparisons(pre,post,mean,axes,random_axes)
                for arm,t,by_split in probes:
                    for name,batches in by_split.items():
                        if r!=40 and name=='original':continue
                        out,classes=measure(post,batches,t,weights)
                        if name=='original':
                            e=original[cid,arm]
                            assert (out['n'],out['stable'],out['native'])==(e['n'],e['stable'],e['witness'])
                            assert all(classes[q['source']]==q['witness'] for q in e['source_counts'])
                            assert out['pca']==d23[cid][arm]['fc_pca'],(cid,arm,out['pca'])
                        rows.append(dict(case=cid,round=r,split=name,arm=arm,pca_rank=rank,removed_fc_norm=norm,**out))
                assert tensor_sha(model.state_dict())==digest
                post.close();del post,model
                write(ROOT/'PROGRESS.json',dict(case=cid,round=r,probe_panel_rows=len(rows)))
            assert tensor_sha(pm.state_dict())==pd
            pre.close();del pre,pm,qm,probes
            torch.cuda.empty_cache()
    assert len(rows)==96
    write(ROOT/'RESULT.json',dict(rows=rows,seconds=time.monotonic()-started,original_counts_exact=True,
          terminal_tensor_history_exact=True,matched_removed_norm=True,training_steps=0,new_probe_searches=0))


if __name__=='__main__':
    try:
        (ROOT/'ONCE').open('x').write(str(os.getpid()))
        plan=read(ROOT/'PLAN.json');tasks=bind(plan)
        write(ROOT/'PREFLIGHT.json',dict(state='passed',cases=len(tasks),history_checkpoints=20))
        from resource_guard import admit
        observations=admit(plan)
        write(ROOT/'ADMISSION.json',[dict(x,competitors=[dict(pid=p['ProcessId'],name=p['Name']) for p in x['competitors']]) for x in observations])
        run(plan,tasks)
    except BaseException:
        lines=traceback.format_exc().splitlines()
        if 'Admission failed' in lines[-1]:lines[-1]='Resource admission failed before model inference.'
        write(ROOT/'FAILURE.json',dict(traceback='\n'.join(lines)))
        raise SystemExit(1)
