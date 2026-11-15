"""One fixed round23 full-batch treatment; the completed fixed-mask control is never trained again."""
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


def prerequisite():
    base=Path('D:/FUBA_BATCH_REDRAW_PILOT_20261115')
    receipt=read(base/'DELIVERY_COMPLETE.json')
    assert receipt['state']=='complete' and receipt['both_catalogue_guards_passed']
    assert sha(base/'DELIVERY_COMPLETE.json')=='884bf3e060b2f6f4b7846e90e63288826139a70f3ae2d6b836952e2a8faae70d'
    assert not receipt['performance_supported']
    for name in ['CPU_AUDIT.json','INDEPENDENT_RESULT.json','GAMMA_AUDIT.json']:
        assert read(base/name)['state']=='passed'
    return receipt


def prepare():
    frozen();write('PREPARE_STARTED.json',{'pid':os.getpid(),'time':time.time()})
    binding=read(ROOT/'INPUT_BINDING.json');base=Path(binding['source_root'])
    assert sha(base/'catalog/select_case.py')==binding['selector_sha256']
    selection=json.loads(subprocess.check_output([sys.executable,'-B',str(base/'catalog/select_case.py'),
        binding['case_id'],'--purpose','diagnostic'],text=True,encoding='utf-8'))
    assert selection['guard_state']=='all_snapshot_files_verified_on_this_host'
    assert selection['server_inputs']['round23_incoming']['payload_key']=='incoming'
    assert sha(base/'REVIEW_MANIFEST.json')==binding['manifest_sha256']
    manifest=read(base/'REVIEW_MANIFEST.json')
    (ROOT/'inputs').mkdir(exist_ok=False);files={}
    for name,digest in binding['files'].items():
        assert manifest['files'][name]['sha256']==digest and sha(base/name)==digest
        target=ROOT/'inputs'/Path(name).name;shutil.copyfile(base/name,target)
        assert sha(target)==digest;files[target.relative_to(ROOT).as_posix()]=digest
    control=read(ROOT/'inputs/RESULT.json');rows=[e for e in control['results'] if e['round']==23]
    assert len(rows)==1 and rows[0]['clients']==[0,1,2,3,11,13,18,19]
    bundle=torch.load(ROOT/'inputs/round0023.pt',map_location='cpu',weights_only=True)
    assert bundle['round']==23 and bundle['clients']==rows[0]['clients']
    exact(bundle['after'],{k:torch.stack([v[k] for v in bundle['submitted']]).mean(0) for k in bundle['after']})
    assert read(ROOT/'CPU_CONTRACT.json')['state']=='passed'
    prerequisite()
    write('PREPARED.json',{'state':'passed','selection':selection,'files':files,
        'control_rows':rows,'payload_key':'incoming','training_rounds':[23],
        'control_retraining':False,'model_inference':0,'posthoc_diagnostic_round_selection':True})
    print('Prepared sealed round23 incoming and immutable control; no training',flush=True)


def train():
    frozen();ready=read(ROOT/'PREPARED.json')
    for name,digest in ready['files'].items():assert sha(ROOT/name)==digest
    delivered=prerequisite();resources=ops.guard()
    write('STARTED.json',{'pid':os.getpid(),'time':time.time(),'resources':resources,'prior_delivery':delivered})
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
    current=torch.load(ROOT/'inputs/round0023.pt',map_location='cpu',weights_only=True)['incoming']
    net=Net().cuda();entries=[]
    for r in [23]:
        clients=sorted(random.Random(p['seed']+1000000+r-1).sample(range(20),8))
        submitted_states=[];roles=[]
        for client in clients:
            frozen();rs=p['seed']+r*10000+client*100;ops.seed(rs);net.load_state_dict(current,strict=True)
            ids=torch.tensor(splits[client],device='cuda');dx,dy=x[ids],y[ids]
            role={'round':r,'client':client,'seed':rs,'arm':'fullbatch',
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
        write('MANIFEST.json',{'arm':'fullbatch','rounds':entries},False)
        print(json.dumps({'round':r,**metric}),flush=True);del submitted_states,rb;gc.collect()
    control=ready['control_rows'];metric=entries[0]['evaluation'];old=control[0]['evaluation']
    checks={'CA97':metric['CA_pct']>=97,'ASR_strict10':metric['ASR_pct']<10,
            'ASR_reduced':metric['target_successes']<old['target_successes']}
    write('RESULT.json',{'state':'complete','results':entries,'fixed_control':control,'checks':checks,
        'behavioral_hypothesis_supported':all(checks.values()),'independent_validation_pending':True,
        'posthoc_diagnostic_round_selection':True,'full_paper_reproduced':False,'unlearning_executed':False})
    write('STATE.json',{'state':'complete','pid':os.getpid()},False)


if __name__=='__main__':
    try:
        if sys.argv[1]=='prepare':prepare()
        elif sys.argv[1]=='train':train()
        else:raise ValueError('prepare or train required')
    except Exception:
        write('FAILURE_'+sys.argv[1]+'.json',{'traceback':traceback.format_exc()});raise
