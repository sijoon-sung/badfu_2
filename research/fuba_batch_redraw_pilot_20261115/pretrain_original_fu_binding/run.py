"""One fixed 21--30R treatment; the completed fixed-mask control is never trained again."""
import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
import copy
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time
import traceback
import torch
import reference_core as core

ROOT=Path(__file__).resolve().parent
UTILITY=Path('D:/FUBA_GAMMA_DETERMINISTIC_20261115/run.py')


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);sys.modules[name]=obj;spec.loader.exec_module(obj);return obj


ops=module('frozen_operations',UTILITY)
read,sha,exact,cpu=ops.read,ops.sha,ops.exact,ops.cpu
guard=ops.guard


def write(name,value,exclusive=True):ops.write(ROOT/name,value,exclusive)


def save(name,value):
    p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:torch.save(cpu(value),f);f.flush();os.fsync(f.fileno())
    return {'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size}


def frozen():
    for name,digest in read(ROOT/'FREEZE.json')['files'].items():assert sha(ROOT/name)==digest,name
    assert sha(UTILITY)=='987e012285e696877aee24672b75ce1d5d4b46839642d73d11bfc895014db9c6'


def prepare():
    frozen();write('PREPARE_STARTED.json',{'pid':os.getpid(),'time':time.time()})
    binding=read(ROOT/'INPUT_BINDING.json')
    selection=json.loads(subprocess.check_output([sys.executable,'-B','D:/TRAJECTORY_CATALOG_20261023/select_case.py',
        binding['case_id'],'--purpose','diagnostic'],text=True,encoding='utf-8'))
    assert selection['guard_state']=='all_snapshot_files_verified_on_this_host'
    packet=Path(selection['source_root']);manifest_path=packet/'FULL_REMOTE_RAW_MANIFEST.json'
    assert sha(manifest_path)==binding['full_manifest_sha256']
    manifest=read(manifest_path);raw=Path(manifest['remote_root'])
    (ROOT/'inputs').mkdir(exist_ok=False);files={}
    for name,digest in binding['files'].items():
        assert digest==manifest['files'][name]['sha256'] and sha(raw/name)==digest
        target=ROOT/'inputs'/Path(name).name;shutil.copyfile(raw/name,target)
        assert sha(target)==digest;files[target.relative_to(ROOT).as_posix()]=digest
    initial=torch.load(ROOT/'inputs/round0020.pt',map_location='cpu',weights_only=True)
    assert initial['round']==20
    exact(initial['after'],{k:torch.stack([s[k] for s in initial['submitted']]).mean(0) for k in initial['after']})
    control=read(ROOT/'CONTROL_BINDING.json');base=Path(control['root'])
    for name,digest in control['files'].items():assert sha(base/name)==digest
    original=read(base/'RESULT.json')
    assert original['state']=='complete' and not original['hypothesis_supported']
    assert original['violations']['global']==3
    for receipt in ['CPU_AUDIT.json','PREFIX_AUDIT.json','INDEPENDENT_RESULT.json','GAMMA_AUDIT.json']:
        assert read(base/receipt)['state']=='passed'
    assert read(ROOT/'CPU_CONTRACT.json')['state']=='passed'
    write('PREPARED.json',{'state':'passed','selection':selection,'files':files,
         'control_rows':original['results']['global'],'control_files':control,'payload_key':'after',
         'training_rounds':list(range(21,31)),'control_retraining':False,'model_inference':0})
    print('Prepared original round20 and immutable completed control; no training',flush=True)


def prerequisite():
    # Produced only after both-host packet/catalogue verification of actual FU.
    base=Path('D:/FUBA_RETRAIN_FU_20261115')
    receipt=read(base/'FU_DELIVERY_COMPLETE.json')
    assert receipt['state']=='complete' and receipt['both_catalogue_guards_passed']
    assert receipt['actual_FU_rounds']==100
    for name,digest in receipt['remote_receipts'].items():assert sha(base/name)==digest
    assert read(base/'STATE.json')['state']=='complete'
    assert read(base/'CPU_AUDIT.json')['state']==read(base/'INDEPENDENT_RESULT.json')['state']=='passed'
    return receipt


def train():
    frozen();ready=read(ROOT/'PREPARED.json')
    for name,digest in ready['files'].items():assert sha(ROOT/name)==digest
    delivered=prerequisite();resources=ops.guard()
    write('STARTED.json',{'pid':os.getpid(),'time':time.time(),'resources':resources,'FU_delivery':delivered})
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic=True;torch.backends.cudnn.benchmark=False
    torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False
    p=read(ROOT/'inputs/PROFILE.json');ops.seed(p['seed'])
    Net=module('fixed_author_net',ROOT/'inputs/author_model.py').Net
    from torchvision.datasets import MNIST
    data=MNIST(p['data_root'],train=True,download=False);test=MNIST(p['data_root'],train=False,download=False)
    for name,digest in MNIST.resources:assert hashlib.md5((Path(data.raw_folder)/name).read_bytes()).hexdigest()==digest
    x,y=data.data.cuda().float().unsqueeze(1)/255,data.targets.cuda()
    tx,ty=test.data.cuda().float().unsqueeze(1)/255,test.targets.cuda()
    splits=read(ROOT/'inputs/SPLIT.json')['indices'];settings=core.Settings()
    current=torch.load(ROOT/'inputs/round0020.pt',map_location='cpu',weights_only=True)['after']
    net=Net().cuda();entries=[]
    for r in range(21,31):
        clients=sorted(random.Random(p['seed']+1000000+r-1).sample(range(20),8))
        submitted_states=[];roles=[]
        for client in clients:
            frozen();rs=p['seed']+r*10000+client*100;ops.seed(rs);net.load_state_dict(current,strict=True)
            ids=torch.tensor(splits[client],device='cuda');dx,dy=x[ids],y[ids]
            role={'round':r,'client':client,'seed':rs,'arm':'batch_redraw',
                  'role':'defender' if client==4 else 'attacker' if client<4 else 'benign','phases':[]}
            folder=f'phases/round{r:04d}_client{client:02d}'
            def log(**values):
                rec={'time':time.time(),'round':r,'client':client,**values}
                with (ROOT/'epochs.jsonl').open('a',encoding='utf-8') as f:
                    f.write(json.dumps(rec,allow_nan=False)+'\n');f.flush()
                write('STATE.json',{'state':'training','pid':os.getpid(),**rec},False)
            def capture(number,model,optimizer,loader_rng,batches):
                role['phases'].append(save(f'{folder}/phase{number:02d}.pt',{'model':model.state_dict(),
                    'optimizer':optimizer.state_dict(),'rng':ops.rng(),'loader_rng':loader_rng,
                    'epochs':50,'batches':batches,'phase':number,'role':role['role']}))
            if client<5:
                order=torch.randperm(3000,generator=torch.Generator().manual_seed(p['partition_seed']+client))
                tr,va=order[300:].cuda(),order[:300].cuda();cx,cy,vx,vy=dx[tr],dy[tr],dx[va],dy[va]
                if client==4:
                    submitted,decision=core.defender(net,cx,cy,cx,cy,settings,seed=rs,log=log,capture=capture,redraw_role=client)
                else:
                    submitted,decision=core.attacker(net,cx,cy,cx,cy,settings,seed=rs,log=log,capture=capture,
                        redraw_role=client,score=lambda m:ops.evaluate(m,vx,vy,4))
                role['decision']=decision;del cx,cy,vx,vy
            else:
                submitted,opt,lrng,n=core.learn(copy.deepcopy(net),dx,dy,settings,phase_seed=rs+1,phase='benign',log=log)
                capture(1,submitted,opt,lrng,n);del opt
            state=cpu(submitted.state_dict());assert all(bool(torch.isfinite(v).all()) for v in state.values())
            role['submitted']=save(f'{folder}/submitted.pt',{'model':state,'rng':ops.rng()})
            write(f'roles/round{r:04d}_client{client:02d}.json',role)
            submitted_states.append(state);roles.append(role);del submitted,dx,dy;gc.collect()
        after={k:torch.stack([s[k] for s in submitted_states]).mean(0) for k in current}
        entry=save(f'rounds/round{r:04d}.pt',{'round':r,'clients':clients,'incoming':current,
            'submitted':submitted_states,'after':after,'roles':roles,'rng':ops.rng()})
        rb=torch.load(ROOT/entry['path'],map_location='cpu',weights_only=True)
        exact(rb['incoming'],current);exact(rb['after'],{k:torch.stack([s[k] for s in rb['submitted']]).mean(0) for k in current})
        current=after;net.load_state_dict(current,strict=True);metric=ops.evaluate(net,tx,ty,4)
        entry.update(round=r,clients=clients,evaluation=metric,exact_aggregation=True);entries.append(entry)
        write('MANIFEST.json',{'arm':'batch_redraw','rounds':entries},False)
        print(json.dumps({'round':r,**metric}),flush=True);del submitted_states,rb;gc.collect()
    control=ready['control_rows'];violations=sum(row['evaluation']['ASR_pct']>10 for row in entries)
    checks={'all_CA97':all(e['evaluation']['CA_pct']>=97 for e in entries),
            'last3_ASR10':all(e['evaluation']['ASR_pct']<=10 for e in entries[-3:]),
            'fewer_violations':violations<3}
    write('RESULT.json',{'state':'complete','results':entries,'fixed_control':control,'checks':checks,
         'violations':violations,'control_violations':3,'behavioral_hypothesis_supported':all(checks.values()),
         'independent_validation_pending':True,'full_paper_reproduced':False,'unlearning_executed':False})
    write('STATE.json',{'state':'complete','pid':os.getpid()},False)


if __name__=='__main__':
    try:
        if sys.argv[1]=='prepare':prepare()
        elif sys.argv[1]=='train':train()
        else:raise ValueError('prepare or train required')
    except Exception:
        write('FAILURE_'+sys.argv[1]+'.json',{'traceback':traceback.format_exc()});raise
