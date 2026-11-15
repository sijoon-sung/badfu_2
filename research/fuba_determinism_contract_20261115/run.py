"""Two finite identical FUBA roles under explicit deterministic GPU controls."""
import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
import torch

ROOT=Path(__file__).resolve().parent
PILOT=Path('D:/FUBA_GAMMA_TRAJECTORY_20261115')
sys.path.insert(0,str(PILOT))
import reference_core as core


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


old=load_module('completed_trajectory_ops',PILOT/'run.py')


def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,data):old.write(ROOT/name,data,True)


def main():
    for name,digest in read(ROOT/'FREEZE.json')['files'].items():assert sha(ROOT/name)==digest,name
    old.frozen()
    assert read(PILOT/'STATE.json')['state']=='complete'
    assert read(PILOT/'INDEPENDENT_RESULT.json')['state']=='passed'
    ready=read(PILOT/'PREPARED.json')
    for name,digest in ready['files'].items():assert sha(PILOT/name)==digest,name
    selection=json.loads(subprocess.check_output([sys.executable,'-B','D:/TRAJECTORY_CATALOG_20261023/select_case.py',
        'fuba.reference.mnist.dba.s20261023.pre100.post.kd10','--purpose','diagnostic'],text=True,encoding='utf-8'))
    assert selection['guard_state']=='all_snapshot_files_verified_on_this_host'
    resources=old.guard()
    write('STARTED.json',{'pid':os.getpid(),'time':time.time(),'resources':resources,'selection':selection})
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic=True
    torch.backends.cudnn.benchmark=False
    torch.backends.cudnn.allow_tf32=False
    torch.backends.cuda.matmul.allow_tf32=False
    mod=load_module('author_Net',PILOT/'inputs/author_model.py')
    profile=read(PILOT/'inputs/PROFILE.json')
    from torchvision.datasets import MNIST
    ds=MNIST(profile['data_root'],train=True,download=False)
    for name,digest in MNIST.resources:
        assert hashlib.md5((Path(ds.raw_folder)/name).read_bytes()).hexdigest()==digest
    x=ds.data.cuda().float().unsqueeze(1)/255
    y=ds.targets.cuda()
    split=read(PILOT/'inputs/SPLIT.json')['indices'][0]
    ids=torch.tensor(split,device='cuda');dx,dy=x[ids],y[ids]
    order=torch.randperm(3000,generator=torch.Generator().manual_seed(profile['partition_seed']))
    tr,va=order[300:].cuda(),order[:300].cuda()
    cx,cy,vx,vy=dx[tr],dy[tr],dx[va],dy[va]
    px,py=cx.clone(),cy.clone()
    ix=torch.randperm(2700,generator=torch.Generator().manual_seed(profile['partition_seed']+1000))[:810].cuda()
    px[ix]=core.stamp(px[ix],0);py[ix]=8
    initial=torch.load(PILOT/'inputs/round0020.pt',map_location='cpu',weights_only=True)['after']
    payloads=[];decisions=[]
    for rep in (1,2):
        folder=ROOT/f'repeat{rep}';folder.mkdir(exist_ok=False)
        model=mod.Net().cuda();model.load_state_dict(initial,strict=True)
        old.seed(20471023)
        states=[]
        def log(**event):
            with (folder/'epochs.jsonl').open('a') as f:f.write(json.dumps(event,allow_nan=False)+'\n')
            old.write(ROOT/'STATE.json',{'state':'training','pid':os.getpid(),'repeat':rep,**event})
        def capture(number,net,opt,rng,batches):
            value=old.cpu({'model':net.state_dict(),'optimizer':opt.state_dict(),'loader_rng':rng,'rng':old.rng(),
                           'phase':number,'epochs':50,'batches':batches})
            with (folder/f'phase{number:02d}.pt').open('xb') as f:torch.save(value,f)
            states.append(value)
        upload,decision=core.attacker(model,cx,cy,px,py,core.Settings(),seed=20471023,log=log,capture=capture,
            score=lambda net:old.evaluate(net,vx,vy,0))
        write(f'repeat{rep}/DECISION.json',decision)
        with (folder/'submitted.pt').open('xb') as f:torch.save(old.cpu(upload.state_dict()),f)
        states.append(old.cpu(upload.state_dict()))
        payloads.append(states);decisions.append(decision)
        del upload,model
    compare=load_module('comparison',PILOT/'numerical_control.py').comparisons
    differences=compare(payloads[0],payloads[1])+compare(decisions[0],decisions[1],'/decision')
    events=[json.loads(line) for rep in (1,2) for line in (ROOT/f'repeat{rep}/epochs.jsonl').read_text().splitlines()]
    assert len(events)==400
    result={'state':'passed' if not differences else 'failed_repeat_contract','differences':differences,
            'roles':2,'phases':8,'epochs':400,'batches':17200,'test_inference':0,
            'scope':'same first21R/client0 only; no cause attribution to one backend switch',
            'prior_trajectory_confounding_preserved':True,'full_paper_reproduced':False,
            'files':{p.relative_to(ROOT).as_posix():sha(p) for p in ROOT.rglob('*') if p.is_file() and p.suffix in ('.pt','.jsonl')}}
    write('RESULT.json',result)
    old.write(ROOT/'STATE.json',{'state':'complete','contract':result['state'],'pid':os.getpid()})
    print(json.dumps({k:v for k,v in result.items() if k not in ['files','differences']}),flush=True)
    assert not differences,'Identical deterministic repetitions differed; preserved'


if __name__=='__main__':
    try:main()
    except Exception:
        write('FAILURE.json',{'traceback':traceback.format_exc()});raise
