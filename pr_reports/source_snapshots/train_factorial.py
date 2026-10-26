"""Full-network FedAvg with paired factorial retraining; adapted BadFU-style pilot."""
import argparse,copy,hashlib,json,random,sys,time
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
from torchvision.datasets import CIFAR10
from torchvision.models import resnet18


def save(path,obj):Path(path).write_text(json.dumps(obj,indent=2),encoding='utf-8')
def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def statehash(sd):
    h=hashlib.sha256()
    for k,v in sorted(sd.items()):h.update(k.encode());h.update(v.detach().cpu().numpy().tobytes())
    return h.hexdigest()
def cpu(sd):return {k:v.detach().cpu().clone() for k,v in sd.items()}
def model(weights=None):
    m=resnet18(weights=None)
    if weights:m.load_state_dict(torch.load(weights,map_location='cpu',weights_only=True))
    m.conv1=torch.nn.Conv2d(3,64,3,1,1,bias=False);m.maxpool=torch.nn.Identity();m.fc=torch.nn.Linear(512,10)
    return m
def patch(x,p):
    z=x.clone();z[:,:,-4:,-4:]=p.to(x);return z
def norm(x):
    return (x-x.new_tensor([.4914,.4822,.4465])[None,:,None,None])/x.new_tensor([.2023,.1994,.2010])[None,:,None,None]
@torch.inference_mode()
def predict(m,x):
    m.eval();return torch.cat([m(norm(b)).cpu() for b in x.split(128)])
def evaluate(m,x,y,px):
    z=predict(m,x);a=predict(m,px);p=z.argmax(1);ap=a.argmax(1);eligible=y!=0
    return dict(accuracy=float((p==y).float().mean()),asr=float((ap[eligible]==0).float().mean()),
                triggered_accuracy=float((ap[eligible]==y[eligible]).float().mean())),z,a


def main():
    pa=argparse.ArgumentParser();pa.add_argument('--repo',required=True);pa.add_argument('--weights',required=True)
    pa.add_argument('--out',required=True);pa.add_argument('--seeds',nargs='+',type=int,default=[71,72,73]);pa.add_argument('--rounds',type=int,default=40)
    pa.add_argument('--data');pa.add_argument('--normal-label-control',action='store_true')
    pa.add_argument('--phases',nargs='+',default=['both','poison_only','cover_only','base'])
    a=pa.parse_args();repo=Path(a.repo);out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    if a.data:root=a.data
    else:
        sys.path.insert(0,str(repo))
        from experiments.purification.post_fu.run_purification import inspect_run
        info,_,_=inspect_run(repo/'artifacts/badfu_author_s42');root=info['options']['data_root']
    tr=CIFAR10(root,train=True,download=False);te=CIFAR10(root,train=False,download=False)
    yl=np.array(tr.targets,dtype=np.int64);yt=np.array(te.targets,dtype=np.int64);start=time.time();allmetrics=[]
    save(out/'manifest.json',dict(code_sha256=digest(__file__),external_weights_sha256=digest(a.weights),
         torch=torch.__version__,gpu=torch.cuda.get_device_name(),rounds=a.rounds,seeds=a.seeds,normal_label_control=a.normal_label_control,
         note='Full-network FedAvg retraining; adapted budget; not FedEraser or original-code reproduction'))
    for seed in a.seeds:
        sd=out/f'seed_{seed}';sd.mkdir();rng=np.random.default_rng(seed);random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
        base=[];pool=[];dev=[];val=[];test=[];parts=[[] for _ in range(5)]
        for c in range(10):
            ix=rng.permutation(np.flatnonzero(yl==c));base.extend(ix[:600]);pool.extend(ix[600:900]);dev.extend(ix[900:920]);val.extend(ix[920:940])
            test.extend(rng.permutation(np.flatnonzero(yt==c))[:200])
            own=c//2;parts[own].extend(ix[:420])
            for cid,chunk in zip([j for j in range(5) if j!=own],np.array_split(ix[420:600],4)):parts[cid].extend(chunk)
        base,pool,dev,val,test=map(np.array,[base,pool,dev,val,test])
        pi=rng.choice(pool[yl[pool]!=0],180,replace=False);ci=rng.choice(np.setdiff1d(pool,pi),720,replace=False)
        assert not (set(base)&set(pi) or set(base)&set(ci) or set(pi)&set(ci) or set(dev)&set(val))
        trigger=torch.rand(1,3,4,4,generator=torch.Generator().manual_seed(20261018))
        torch.save(trigger,sd/'evaluation_trigger.pt')
        save(sd/'splits.json',dict(base=base.tolist(),poison=pi.tolist(),cover=ci.tolist(),development=dev.tolist(),validation=val.tolist(),test=test.tolist(),clients=[list(map(int,v)) for v in parts]))
        clean=[]
        for ids in parts:
            clean.append((torch.from_numpy(tr.data[ids].copy()).permute(0,3,1,2).cuda().float()/255,torch.tensor(yl[ids],device='cuda')))
        xp=patch(torch.from_numpy(tr.data[pi].copy()).permute(0,3,1,2).cuda().float()/255,trigger);yp=torch.zeros(len(pi),dtype=torch.long,device='cuda')
        if a.normal_label_control:yp=torch.tensor(yl[pi],device='cuda')
        xc=patch(torch.from_numpy(tr.data[ci].copy()).permute(0,3,1,2).cuda().float()/255,trigger);yc=torch.tensor(yl[ci],device='cuda')
        xt=torch.from_numpy(te.data[test].copy()).permute(0,3,1,2).cuda().float()/255;ytest=torch.tensor(yt[test]);xat=patch(xt,trigger)
        initial=model(a.weights).state_dict();init=cpu(initial);initsha=statehash(init);torch.save(init,sd/'initial.pt')
        gm=model().cuda();local=model().cuda()
        for phase,hasp,hasc in [('both',True,True),('poison_only',True,False),('cover_only',False,True),('base',False,False)]:
            if phase not in a.phases:continue
            gm.load_state_dict(init);data=[]
            for cid,(cx,cy) in enumerate(clean):
                xx=[cx];yy=[cy]
                if cid==0 and hasp:xx.append(xp);yy.append(yp)
                if cid==0 and hasc:xx.append(xc);yy.append(yc)
                data.append((torch.cat(xx),torch.cat(yy)))
            counts=[len(q[1]) for q in data];history=[];phase_start=time.time()
            for rnd in range(a.rounds):
                global_sd={k:v.detach().clone() for k,v in gm.state_dict().items()}
                aggregated={k:torch.zeros_like(v,dtype=torch.float32) for k,v in global_sd.items()}
                for cid,(xx,yy) in enumerate(data):
                    local.load_state_dict(global_sd);local.train();optim=torch.optim.SGD(local.parameters(),lr=.01)
                    gen=torch.Generator(device='cuda').manual_seed(seed*100000+rnd*10+cid)
                    order=torch.randperm(len(yy),generator=gen,device='cuda')
                    for ix in order.split(64):
                        optim.zero_grad(set_to_none=True);loss=F.cross_entropy(local(norm(xx[ix])),yy[ix]);loss.backward();optim.step()
                    weight=len(yy)/sum(counts)
                    for k,v in local.state_dict().items():aggregated[k].add_(v.float(),alpha=weight)
                for k,v in global_sd.items():
                    if not v.is_floating_point():aggregated[k]=aggregated[k].round().to(v.dtype)
                gm.load_state_dict(aggregated)
                if (rnd+1)%10==0 or rnd+1==a.rounds:
                    met,_,_=evaluate(gm,xt,ytest,xat);row=dict(seed=seed,phase=phase,round=rnd+1,seconds=time.time()-phase_start,**met)
                    history.append(row);print(json.dumps(row),flush=True)
                    save(sd/f'{phase}_progress.json',history)
            endpoint=sd/f'{phase}.pt';torch.save(cpu(gm.state_dict()),endpoint)
            met,z,az=evaluate(gm,xt,ytest,xat)
            np.savez_compressed(sd/f'{phase}_predictions.npz',logits=z.numpy(),attack_logits=az.numpy(),labels=ytest.numpy(),test_ids=test)
            row=dict(seed=seed,phase=phase,counts=counts,initial_state_sha256=initsha,checkpoint_sha256=digest(endpoint),**met)
            allmetrics.append(row);save(out/'results.json',allmetrics)
            save(sd/f'{phase}_complete.json',dict(**row,history=history,seconds=time.time()-phase_start))
        del gm,local,clean,xp,xc,xt,xat;torch.cuda.empty_cache()
    save(out/'complete.json',dict(seconds=time.time()-start,models=len(allmetrics)))


if __name__=='__main__':main()
