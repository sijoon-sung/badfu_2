"""Fixed blind patch probes; selection on development, assessment on validation.

This is an information audit, not a novel detector. Four-state contrasts are oracle
diagnostics, since a deployed server does not know poison/camouflage membership.
"""
import argparse, json, time
from pathlib import Path
import numpy as np
import torch
from torchvision.datasets import CIFAR10
from train_factorial import model, norm, digest, save

PHASES = ['both', 'poison_only', 'cover_only', 'base']

def bank():
    checker = (torch.arange(4)[:, None] + torch.arange(4)[None, :]) % 2
    pats = [torch.zeros(3,4,4), torch.ones(3,4,4), checker.expand(3,-1,-1).float(),
            (1-checker).expand(3,-1,-1).float()]
    gen = torch.Generator().manual_seed(919191)
    pats += [torch.rand(3,4,4,generator=gen) for _ in range(4)]
    names = ['black','white','checker','inverse_checker','random0','random1','random2','random3']
    return [(f'{corner}_{name}', r, c, p) for corner,r,c in
            [('tl',0,0),('tr',0,28),('bl',28,0),('br',28,28)] for name,p in zip(names,pats)]

@torch.inference_mode()
def forward(m,x):
    m.eval()
    return torch.cat([m(norm(b)).cpu() for b in x.split(128)])

def prob(z):
    z=z-z.max(axis=-1,keepdims=True); p=np.exp(z);return p/p.sum(axis=-1,keepdims=True)

def stats(z,y):
    """z: patterns x samples x labels; excludes each putative target's own class."""
    pr=prob(z); pred=z.argmax(-1)
    mass=np.stack([pr[:,y!=t,t].mean(1) for t in range(10)],axis=1)
    rate=np.stack([(pred[:,y!=t]==t).mean(1) for t in range(10)],axis=1)
    return mass,rate

def choose(dev,val,names):
    p,t=np.unravel_index(dev.argmax(),dev.shape)
    return dict(pattern=names[p],pattern_index=int(p),target=int(t),development=float(dev[p,t]),
                validation=float(val[p,t]),validation_oracle_max=float(val.max()))

def analyse(sd):
    paths=[sd/f'{p}_probes.npz' for p in PHASES]
    if not all(p.exists() for p in paths):return None
    allz={p:np.load(f) for p,f in zip(PHASES,paths)}
    names=allz['both']['names'].tolist(); metrics={}; tensors={}
    for phase,z in allz.items():
        tensors[phase]={};metrics[phase]={}
        for split in ['development','validation']:
            y=z[f'{split}_labels'];c=z[f'{split}_clean'];b=z[f'{split}_blind'];o=z[f'{split}_oracle']
            cm,cr=stats(c[None],y);bm,br=stats(b,y);om,orr=stats(o[None],y)
            tensors[phase][split]=dict(clean_mass=cm,clean_rate=cr,mass=bm,rate=br,delta=bm-cm)
            metrics[phase][split]=dict(clean_accuracy=float((c.argmax(-1)==y).mean()),
                clean_target0_mass=float(cm[0,0]),clean_target0_rate=float(cr[0,0]),
                oracle_target0_asr=float(orr[0,0]),oracle_target0_mass=float(om[0,0]),
                blind_max_target0_asr=float(br[:,0].max()),blind_max_any_target_asr=float(br.max()))
        for metric in ['rate','mass','delta']:
            selected=choose(tensors[phase]['development'][metric],tensors[phase]['validation'][metric],names)
            p,t=selected['pattern_index'],selected['target']
            selected['validation_asr']=float(tensors[phase]['validation']['rate'][p,t])
            metrics[phase]['selected_'+metric]=selected
    contrasts={}
    for label,pre,post in [('delete_cover_with_poison','both','poison_only'),
                           ('delete_cover_without_poison','cover_only','base'),
                           ('delete_poison_with_cover','both','cover_only'),
                           ('delete_poison_without_cover','poison_only','base')]:
        q={s:tensors[post][s]['delta']-tensors[pre][s]['delta'] for s in ['development','validation']}
        chosen=choose(q['development'],q['validation'],names)
        p,t=chosen['pattern_index'],chosen['target']
        chosen.update(validation_post_asr=float(tensors[post]['validation']['rate'][p,t]),
                      validation_pre_asr=float(tensors[pre]['validation']['rate'][p,t]),
                      validation_clean_target0_change=float(tensors[post]['validation']['clean_mass'][0,0]-tensors[pre]['validation']['clean_mass'][0,0]))
        contrasts[label]=chosen
    interaction={s:tensors['poison_only'][s]['delta']-tensors['both'][s]['delta']-
                   tensors['base'][s]['delta']+tensors['cover_only'][s]['delta'] for s in ['development','validation']}
    contrasts['oracle_factorial_interaction']=choose(interaction['development'],interaction['validation'],names)
    result=dict(seed=int(sd.name.split('_')[1]),phases=metrics,contrasts=contrasts,
                note='Independent validation; four-state interaction is oracle, not deployable detection; no population FPR claim.')
    save(sd/'probe_summary.json',result)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--data',required=True)
    p.add_argument('--seeds',nargs='+',type=int,default=[71,72,73]);p.add_argument('--device',default='cuda')
    a=p.parse_args();run=Path(a.run);torch.set_num_threads(4)
    tr=CIFAR10(a.data,train=True,download=False);ys=np.array(tr.targets);patterns=bank()
    save(run/'probe_manifest.json',dict(code_sha256=digest(__file__),bank_names=[p[0] for p in patterns],
         pattern_seed=919191,selection='200 development samples only; 200 independent validation samples',
         oracle='true pattern available only for evaluation; target 0 not used in blind selection'))
    results=[]
    for seed in a.seeds:
        sd=run/f'seed_{seed}'
        if not (sd/'splits.json').exists():continue
        splits=json.loads((sd/'splits.json').read_text());spl={}
        for name in ['development','validation']:
            ix=splits[name];spl[name]=(torch.from_numpy(tr.data[ix].copy()).permute(0,3,1,2).to(a.device).float()/255,ys[ix])
        trigger=torch.load(sd/'evaluation_trigger.pt',weights_only=True,map_location=a.device)
        for phase in PHASES:
            ck=sd/f'{phase}.pt';dest=sd/f'{phase}_probes.npz'
            if not ck.exists() or dest.exists():continue
            start=time.time();m=model().to(a.device);m.load_state_dict(torch.load(ck,map_location=a.device,weights_only=True));out={}
            for name,(x,y) in spl.items():
                out[f'{name}_labels']=y;out[f'{name}_clean']=forward(m,x).numpy();zs=[]
                for _,r,c,pat in patterns:
                    xx=x.clone();xx[:,:,r:r+4,c:c+4]=pat.to(x);zs.append(forward(m,xx).numpy())
                out[f'{name}_blind']=np.stack(zs)
                xx=x.clone();xx[:,:,-4:,-4:]=trigger;out[f'{name}_oracle']=forward(m,xx).numpy()
            np.savez_compressed(dest,**out,names=np.array([p[0] for p in patterns]))
            print(json.dumps(dict(seed=seed,phase=phase,probe_seconds=time.time()-start)),flush=True)
            del m;torch.cuda.empty_cache()
        res=analyse(sd)
        if res:results.append(res)
    save(run/'probe_results.json',results)

if __name__=='__main__':main()
