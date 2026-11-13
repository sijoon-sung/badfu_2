"""Read-only paired view consistency on previously sealed inference inputs."""
from fractions import Fraction
from pathlib import Path
import hashlib
import json
import os
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parent
D23=Path('D:/FOUR_ROUTES_PCA_DECISION_20261112')
D24=Path('D:/BADFU_FC_PCA_MATCHED_CONTROL_20261112')


def sha(path):
    return hashlib.file_digest(Path(path).open('rb'),'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write(name,value):
    p=ROOT/name
    t=p.with_suffix('.tmp')
    t.write_bytes((json.dumps(value,indent=2)+'\n').encode())
    t.replace(p)


def compare(rows):
    def ratio(r):
        return Fraction(r['joint'],r['eligible']) if r['eligible']>=20 else None

    def score(key):
        return max((v for r in rows if (r['track'],r['round'],r['split'])==key and (v:=ratio(r)) is not None),default=None)

    def outcome(key,cut):
        v=score(key)
        return dict(score=None if v is None else float(v),state='abstain' if v is None or cut is None else 'alert' if v>cut else 'quiet')

    def threshold(keys):
        return max((v for k in keys if (v:=score(k)) is not None),default=None)

    old=('p00','p01','p02')
    rounds=(1,3,5,10,15,20)
    cut=threshold((b,r,'original') for b in old for r in rounds)
    fed=dict(cut=None if cut is None else float(cut),by_track={
        b:{r:outcome((b,r,'original'),cut) for r in rs}
        for b,rs in [*((x,(1,3,5,10)) for x in ('u00','u01','u02')),*((x,(10,15,20)) for x in ('p03','p04'))]})
    bad={}
    for hold,anchor in [('c00','c01'),('c01','c00')]:
        cut=threshold((b,None,'original') for b in (anchor,'c02','c03'))
        bad[hold]=dict(cut=None if cut is None else float(cut),
            panels={s:{b:outcome((b,None,s),cut) for b in (hold,'c04','c05')} for s in ('A','B')})
    return dict(feduba=fed,badfu=bad)


def main():
    (ROOT/'ONCE').open('x').write(str(os.getpid()))
    freeze=read(ROOT/'FREEZE.json')
    assert read(ROOT/'PUBLICATION.json')['freeze_sha256']==sha(ROOT/'FREEZE.json')
    for n,v in freeze['files'].items():assert sha(ROOT/n)==v,n
    for n,v in freeze['reference_files'].items():assert sha(n)==v,n
    sys.path.insert(1,str(D23))
    import evaluate as parent
    from resource_guard import admit
    plan=read(D23/'PLAN.json')
    tasks=parent.preflight(plan)
    observations=admit(plan)
    write('ADMISSION.json',[dict(q,competitors=len(q['competitors'])) for q in observations])
    import torch
    from probe_reference import tensor_sha
    from route_core import Endpoint,load_native,load_transform,settings
    settings(plan)
    d20=Path(plan['d20']);cfg=read(d20/'PROFILE.json')
    assert sha(cfg['raw_data'])==cfg['raw_sha256']
    raw=torch.load(cfg['raw_data'],map_location='cpu',weights_only=True)
    source=read(d20/'PUBLIC_SPLIT.json')
    split={'original':source['test'],**read(D24/'HOLDOUT_SPLITS.json')}
    assert len(set(sum(split.values(),[])))==3000
    assert not set(split['A']+split['B']) & set(source['fit']+source['calibration']+source['test'])
    normal={'c07','n00','n01'}
    specs=[]
    for folder,ids in plan['feduba_probe_roots'].items():
        specs+=parent.probe_specs(folder,normal&set(ids))
    assert len(specs)==6
    base={}
    base_classes={}
    for row in read(D23/'RESULT.json')['rows']:
        for q in row['probes']:
            base[row['track'],row['round'],'original',q['probe'],q['arm']]=q
    for path in plan['panel_results']:
        for row in read(path)['rows']:
            for q in row['probes']:
                base_classes[row['track'],row['round'],q['probe'],q['arm']]=q['witness_by_class']
    for q in read(d20/'RESULT.json')['results']:
        c=q['case']
        counts=[0]*10
        for k in q['source_counts']:
            counts[k['source']]=k['witness']
        base_classes[c,None,c,q['arm']]=counts
    for q in read(D24/'RESULT.json')['rows']:
        if q['round']==40 and q['split']!='original':
            base[q['case'],None,q['split'],q['case'],q['arm']]=q

    def batches(spec,panel):
        case,arm,m,c=spec
        assert sha(m['payload'])==m['payload_sha256']
        t=m['target']
        f=load_transform(m['family'],c,m['payload'],'cuda')
        result=[]
        for b in torch.tensor(split[panel]).split(32):
            y=raw['test_y'][b].long().cuda()
            x=raw['test_x'][b].permute(0,3,1,2).contiguous().float().cuda()/255
            k=y!=t
            if k.any():
                x,y=x[k],y[k]
                z=f(x,torch.full_like(y,t))
                result.append((x,z,y))
        return case,arm,t,result

    def masks(pre,post,x,z,y,t):
        stable=(pre(x).argmax(1)==y)&(post(x).argmax(1)==y)
        elig=stable&(pre(z).argmax(1)==y)
        return stable,elig,post(z).argmax(1)==t

    rows=[]
    start=time.monotonic()
    with torch.inference_mode():
        shared=[('original',batches(s,'original')) for s in specs]
        for task in tasks:
            group,track,r=task['group'],task['track'],task['round']
            pm,pd=load_native(task['pre'],group,'cuda')
            qm,qd=load_native(task['post'],group,'cuda')
            pre,post=Endpoint(pm,group),Endpoint(qm,group)
            panel=shared if group=='feduba' else [
                (s,batches(p,s)) for s in split for p in parent.probe_specs(d20,{track})]
            for label,(p,arm,t,items) in panel:
                n=stable_count=native=eligible=joint=0
                classes=[0]*10
                for x,z,y in items:
                    stable,origin,b0=masks(pre,post,x,z,y,t)
                    hit=origin&b0
                    _,e1,b1=masks(pre,post,x.flip(-1),z.flip(-1),y,t)
                    _,e2,b2=masks(pre,post,x*.9,z*.9,y,t)
                    keep=hit&e1&e2
                    stable_count+=int(stable.sum())
                    native+=int(hit.sum())
                    eligible+=int(keep.sum())
                    joint+=int((keep&b1&b2).sum())
                    n+=len(y)
                    classes=[a+b for a,b in zip(classes,torch.bincount(y[hit],minlength=10).tolist())]
                q=base[track,r,label,p,arm]
                assert (n,stable_count,native)==(q['n'],q['stable'],q['native']),(track,r,label,p,arm)
                if label=='original':assert classes==base_classes[track,r,p,arm],(track,r,p,arm)
                assert 0<=joint<=eligible<=native<=stable_count<=n==900
                rows.append(dict(track=track,round=r,split=label,probe=p,arm=arm,n=n,native=native,eligible=eligible,joint=joint))
            assert tensor_sha(pm.state_dict())==pd and tensor_sha(qm.state_dict())==qd
            pre.close();post.close()
            del pre,post,pm,qm
            write('PROGRESS.json',dict(track=track,round=r,rows=len(rows)))
    assert len(rows)==288
    write('RESULT.json',dict(state='passed',comparisons=48,rows=rows,seconds=time.monotonic()-start,decision=compare(rows)))


if __name__=='__main__':
    try:
        main()
    except BaseException:
        trace=traceback.format_exc().splitlines()
        if 'Admission failed' in trace[-1]:trace[-1]='Resource admission failed before GPU inference'
        write('FAILURE.json',dict(traceback='\n'.join(trace)))
        raise SystemExit(1)
