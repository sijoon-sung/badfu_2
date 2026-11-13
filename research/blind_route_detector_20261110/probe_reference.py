"""Pure server probe functions; no ASR, roles, true trigger or private data."""
import ast,hashlib,json,os,time,uuid
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from torchvision import models


def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(8<<20),b''):h.update(block)
    return h.hexdigest()
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);q=p.with_name(p.name+'.'+uuid.uuid4().hex+'.tmp')
    q.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8');q.replace(p)
def tensor_sha(state):
    h=hashlib.sha256()
    for k,v in sorted(state.items()):
        h.update(k.encode());h.update(v.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


class Classifier(nn.Module):
    def __init__(self,state):
        super().__init__();self.core=models.resnet18(weights=None)
        self.core.conv1=nn.Conv2d(3,64,3,1,1,bias=False);self.core.maxpool=nn.Identity();self.core.fc=nn.Linear(512,10)
        self.core.load_state_dict({k.removeprefix('model.'):v for k,v in state.items()},strict=True)
        self.register_buffer('mean',torch.tensor([.4914,.4822,.4465])[None,:,None,None])
        self.register_buffer('std',torch.tensor([.2023,.1994,.2010])[None,:,None,None])
    def forward(self,x):return self.core((x-self.mean)/self.std)


def load_model(cfg,key,device):
    s=cfg['models'][key]
    if sha(s['path'])!=s['sha256']:raise ValueError('Selected checkpoint hash mismatch: '+key)
    payload=torch.load(s['path'],map_location='cpu',weights_only=True)
    state=payload if s['payload_key'] is None else payload[s['payload_key']]
    if not isinstance(state,dict) or not state or not all(isinstance(v,torch.Tensor) for v in state.values()):
        raise TypeError('Declared payload is not a model state')
    model=Classifier(state).to(device).eval().requires_grad_(False)
    return model,state


def public_data(cfg,device):
    raw=torch.load(cfg['raw_data'],weights_only=True,map_location='cpu');y=raw['test_y'];rng=np.random.default_rng(cfg['data_seed'])
    indices={k:[] for k in ['fit','calibration','test']}
    for c in range(10):
        ids=rng.permutation(np.flatnonzero(y.numpy()==c));lo=0
        for key in indices:
            n=cfg['public'][key+'_per_class'];indices[key]+=ids[lo:lo+n].tolist();lo+=n
    sets=[set(v) for v in indices.values()];assert all(not sets[i]&sets[j] for i in range(3) for j in range(i))
    arrays={k:((raw['test_x'][ids].permute(0,3,1,2).float()/255).to(device),y[ids].to(device)) for k,ids in indices.items()}
    return arrays,indices,raw


class Conditional(nn.Module):
    def __init__(self):
        super().__init__()
        self.c1=nn.Conv2d(13,16,3,padding=1);self.c2=nn.Conv2d(16,32,3,padding=1)
        self.c3=nn.Conv2d(32,32,3,padding=1);self.c4=nn.Conv2d(64,16,3,padding=1)
        self.c5=nn.Conv2d(32,3,3,padding=1)
        nn.init.zeros_(self.c5.weight);nn.init.zeros_(self.c5.bias)
    def forward(self,x,c):
        condition=F.one_hot(c,10).to(x.dtype)[:,:,None,None].expand(-1,-1,32,32)
        a=F.relu(self.c1(torch.cat([x,condition],1)))
        b=F.relu(self.c2(F.avg_pool2d(a,2)));d=F.relu(self.c3(F.avg_pool2d(b,2)))
        e=F.relu(self.c4(torch.cat([F.interpolate(d,size=(16,16),mode='bilinear',align_corners=False),b],1)))
        return self.c5(torch.cat([F.interpolate(e,size=(32,32),mode='bilinear',align_corners=False),a],1))


class Transform(nn.Module):
    def __init__(self,family,cfg):
        super().__init__();self.family=family;self.eps=cfg['epsilon'];self.mass=cfg['mask_mass']
        if family=='mask':
            self.mask=nn.Parameter(torch.rand(10,1,32,32)*self.mass/1024)
            self.pattern=nn.Parameter(torch.rand(10,3,32,32))
        elif family=='additive':self.delta=nn.Parameter(torch.randn(10,3,32,32)*.001)
        elif family=='conditional':self.net=Conditional()
        else:raise ValueError(family)
    def forward(self,x,c):
        if self.family=='mask':return (x*(1-self.mask[c])+self.pattern[c]*self.mask[c]).clamp(0,1)
        d=self.delta[c] if self.family=='additive' else self.eps*self.net(x,c).tanh()
        return (x+d).clamp(0,1)
    @torch.no_grad()
    def project(self):
        if self.family=='mask':
            self.mask.clamp_(0,1);self.pattern.clamp_(0,1)
            for m in self.mask:
                flat=m.flatten()
                if flat.sum()>self.mass:
                    u=flat.sort(descending=True).values;css=u.cumsum(0)-self.mass
                    ok=u-css/torch.arange(1,len(u)+1,device=u.device)>0
                    rho=int(ok.sum())-1;theta=css[rho]/(rho+1)
                    flat.copy_((flat-theta).clamp_min(0))
        elif self.family=='additive':self.delta.clamp_(-self.eps,self.eps)


@torch.inference_mode()
def logits(model,x):return torch.cat([model(b) for b in x.split(32)])


@torch.inference_mode()
def evaluate(pre,post,t,x,y,z0=None,z1=None):
    z0=logits(pre,x) if z0 is None else z0;z1=logits(post,x) if z1 is None else z1
    stable=(z0.argmax(1)==y)&(z1.argmax(1)==y);rows=[]
    for c in range(10):
        select=y!=c;xx=x[select];yy=y[select];cc=torch.full((len(xx),),c,dtype=torch.long,device=x.device)
        changed=torch.cat([t(b,d) for b,d in zip(xx.split(32),cc.split(32))])
        a=logits(pre,changed);b=logits(post,changed)
        witness=stable[select]&(a.argmax(1)==yy)&(b.argmax(1)==c)
        source_counts=[]
        for k in range(10):
            if k==c:continue
            take=yy==k;source_counts.append(dict(source=k,n=int(take.sum()),witness=int(witness[take].sum()),stable=int(stable[select][take].sum())))
        d=(b.softmax(1)[:,c]-z1[select].softmax(1)[:,c])-(a.softmax(1)[:,c]-z0[select].softmax(1)[:,c])
        rows.append(dict(target=c,n=len(xx),stable_n=int(stable[select].sum()),witness_n=int(witness.sum()),
            rate=float(witness.double().mean()),conditional_rate=float(witness.sum()/stable[select].sum()) if stable[select].any() else None,
            probability_DID=float(d.double().mean()),post_target_n=int((b.argmax(1)==c).sum()),
            mean_L1=float((changed-xx).abs().flatten(1).sum(1).mean()),max_Linf=float((changed-xx).abs().max()),source_counts=source_counts))
    return rows


def rank(row):return (row['rate'],row['probability_DID'],-row['mean_L1'])


def train(pre,post,t,cfg,objective,x,y,seed,root,pair,family):
    rng=np.random.default_rng(seed);eligible={c:torch.where(y!=c)[0].cpu().numpy() for c in range(10)}
    targets=torch.arange(10,device=x.device).repeat_interleave(cfg['batch_per_target'])
    lr=.02 if family=='mask' else .005
    opt=torch.optim.Adam(t.parameters(),lr=lr);begin=time.time();trace=[]
    for step in range(1,cfg['steps']+1):
        ids=np.concatenate([rng.choice(eligible[c],cfg['batch_per_target'],replace=False) for c in range(10)])
        xx=x[ids];yy=y[ids];changed=t(xx,targets)
        loss_post=F.cross_entropy(post(changed),targets)
        loss_pre=F.cross_entropy(pre(changed),yy) if objective=='paired' else torch.zeros((),device=x.device)
        loss=loss_post+cfg['pre_loss_weight']*loss_pre
        opt.zero_grad();loss.backward();opt.step();t.project()
        if step%50==0:
            item=dict(step=step,post_loss=float(loss_post),pre_loss=float(loss_pre),seconds=time.time()-begin)
            trace.append(item);write(root/'STATE.json',dict(state='search',pair=pair,family=family,objective=objective,probe_start=seed,**item))
            print(json.dumps(dict(pair=pair,family=family,objective=objective,start=seed,**item)),flush=True)
    return trace


def settings(cfg):
    torch.set_num_threads(cfg['threads']);torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.cuda.set_per_process_memory_fraction(cfg['memory_fraction'])
