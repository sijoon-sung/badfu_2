"""Actual retained-client retraining FU, with fixed Algorithm-1 gamma=1."""
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
UTILS=Path('D:/FUBA_GAMMA_DETERMINISTIC_20261115/run.py')


def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


ops=module('frozen_fuba_utilities',UTILS)
read,sha,cpu,exact=ops.read,ops.sha,ops.cpu,ops.exact


def write(name,value,exclusive=True):ops.write(ROOT/name,value,exclusive)


def frozen():
    f=read(ROOT/'FREEZE.json')
    for name,digest in f['files'].items():assert sha(ROOT/name)==digest,name
    assert sha(UTILS)==f['utility_sha256']


def participants(round_id,seed=20261023):
    original=sorted(random.Random(seed+1000000+round_id-1).sample(range(20),8))
    return original,[i for i in original if i!=4]


def save(name,value):
    p=ROOT/name;p.parent.mkdir(exist_ok=True,parents=True)
    with p.open('xb') as f:torch.save(cpu(value),f);f.flush();os.fsync(f.fileno())
    return {'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size}


def prepare():
    frozen();write('PREPARE_STARTED.json',{'pid':os.getpid(),'time':time.time()})
    b=read(ROOT/'INPUT_BINDING.json')
    selected=json.loads(subprocess.check_output([sys.executable,'-B','D:/TRAJECTORY_CATALOG_20261023/select_case.py',b['case_id'],'--purpose','diagnostic'],text=True,encoding='utf-8'))
    assert selected['guard_state']=='all_snapshot_files_verified_on_this_host'
    packet=Path(selected['source_root']);full=packet/'FULL_REMOTE_RAW_MANIFEST.json'
    assert sha(full)==b['full_manifest_sha256']
    manifest=read(full);raw=Path(manifest['remote_root'])
    (ROOT/'inputs').mkdir(exist_ok=False)
    files={}
    for name,digest in b['files'].items():
        assert digest==manifest['files'][name]['sha256'] and sha(raw/name)==digest,name
        shutil.copyfile(raw/name,ROOT/'inputs'/name)
        files['inputs/'+name]=digest
    pre=selected['server_inputs']['pre']
    assert pre==b['pre'] and sha(pre['path'])==pre['sha256']
    shutil.copyfile(pre['path'],ROOT/'inputs/before.pt');files['inputs/before.pt']=pre['sha256']
    assert sha(ROOT/'reference_core.py')==files['inputs/reference_core.py']
    net=module('author_Net',ROOT/'inputs/author_model.py').Net()
    initial=torch.load(ROOT/'inputs/initial.pt',map_location='cpu',weights_only=True)
    net.load_state_dict(initial,strict=True)
    assert not list(net.buffers()) and all(bool(torch.isfinite(v).all()) for v in initial.values())
    schedule={str(r):participants(r) for r in range(1,101)}
    assert all(4 not in retained and len(retained) in (7,8) for original,retained in schedule.values())
    original_history=raw/'run/MANIFEST.json'
    assert sha(original_history)==manifest['files']['run/MANIFEST.json']['sha256']
    rows=read(original_history)['rounds'];assert len(rows)==100
    assert all(schedule[str(row['round'])][0]==row['clients'] for row in rows)
    write('PREPARED.json',{'state':'passed','selection':selected,'files':files,'schedule':schedule,
         'initial_payload_key':None,'before_payload_key':None,'pretrained_model_inference':0,
         'original_100_cohorts_matched':True,'original_history_manifest_sha256':sha(original_history)})
    print('Prepared exact initial state, original split, before model, and client4 exclusion',flush=True)


def train():
    frozen();ready=read(ROOT/'PREPARED.json')
    for name,digest in ready['files'].items():assert sha(ROOT/name)==digest,name
    resources=ops.guard()
    write('STARTED.json',{'pid':os.getpid(),'time':time.time(),'resources':resources})
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic=True;torch.backends.cudnn.benchmark=False
    torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False
    write('RUNTIME.json',{'python':sys.version,'torch':torch.__version__,'CUDA':torch.version.cuda,
         'cudnn':torch.backends.cudnn.version(),'GPU':torch.cuda.get_device_name(0),'deterministic':True,'TF32':False})
    p=read(ROOT/'inputs/PROFILE.json');splits=read(ROOT/'inputs/SPLIT.json')['indices']
    Net=module('author_Net',ROOT/'inputs/author_model.py').Net
    from torchvision.datasets import MNIST
    data=MNIST(p['data_root'],train=True,download=False);test=MNIST(p['data_root'],train=False,download=False)
    for name,digest in MNIST.resources:assert hashlib.md5((Path(data.raw_folder)/name).read_bytes()).hexdigest()==digest
    x,y=data.data.cuda().float().unsqueeze(1)/255,data.targets.cuda()
    tx,ty=test.data.cuda().float().unsqueeze(1)/255,test.targets.cuda()
    current=torch.load(ROOT/'inputs/initial.pt',map_location='cpu',weights_only=True)
    net=Net().cuda();settings=core.Settings();entries=[]
    for r in range(1,101):
        frozen();original,clients=participants(r,p['seed'])
        assert [original,clients]==ready['schedule'][str(r)] and 4 not in clients
        submissions=[];roles=[]
        for client in clients:
            rs=p['seed']+r*10000+client*100;ops.seed(rs)
            net.load_state_dict(current,strict=True)
            ids=torch.tensor(splits[client],device='cuda');dx,dy=x[ids],y[ids]
            malicious=client<4 and r>5
            role={'round':r,'client':client,'role':'attacker_retrain_gamma1' if malicious else 'benign','seed':rs,'phases':[]}
            folder=f'phases/round{r:04d}_client{client:02d}'
            def log(**event):
                row={'round':r,'client':client,**event}
                with (ROOT/'epochs.jsonl').open('a') as f:f.write(json.dumps(row,allow_nan=False)+'\n');f.flush()
                write('STATE.json',{'state':'training','pid':os.getpid(),**row},False)
            def capture(number,m,opt,lrng,batches):
                rec=save(f'{folder}/phase{number:02d}.pt',{'model':m.state_dict(),'optimizer':opt.state_dict(),
                    'rng':ops.rng(),'loader_rng':lrng,'epochs':50,'batches':batches,'phase':number,'role':role['role']})
                role['phases'].append(rec)
            if malicious:
                order=torch.randperm(3000,generator=torch.Generator().manual_seed(p['partition_seed']+client))
                tr=order[300:].cuda();cx,cy=dx[tr],dy[tr];px,py=cx.clone(),cy.clone()
                ix=torch.randperm(2700,generator=torch.Generator().manual_seed(p['partition_seed']+1000+client))[:810].cuda()
                px[ix]=core.stamp(px[ix],client);py[ix]=8
                embedded=core.embed(net,cx,cy,px,py,settings,seed=rs,log=log,capture=capture)
                submitted=core.affine(net,embedded,1.)
                del embedded
                role['gamma']=1.;role['test_or_validation_used_for_selection']=False
                del cx,cy,px,py
            else:
                submitted,opt,lrng,batches=core.learn(copy.deepcopy(net),dx,dy,settings,phase_seed=rs+1,phase='benign',log=log)
                capture(1,submitted,opt,lrng,batches);del opt
            state=cpu(submitted.state_dict());assert all(bool(torch.isfinite(v).all()) for v in state.values())
            role['submitted']=save(f'{folder}/submitted.pt',{'model':state,'rng':ops.rng()})
            write(f'roles/round{r:04d}_client{client:02d}.json',role)
            submissions.append(state);roles.append(role)
            del submitted,dx,dy;gc.collect()
        after={k:torch.stack([s[k] for s in submissions]).mean(0) for k in current}
        rec=save(f'rounds/round{r:04d}.pt',{'round':r,'original_selected':original,'clients':clients,'erased_client':4,
            'incoming':current,'submitted':submissions,'weights':[1/len(clients)]*len(clients),'after':after,'roles':roles,'rng':ops.rng()})
        rb=torch.load(ROOT/rec['path'],map_location='cpu',weights_only=True)
        exact(rb['incoming'],current);exact(rb['after'],{k:torch.stack([s[k] for s in rb['submitted']]).mean(0) for k in current})
        current=after;net.load_state_dict(current,strict=True);metric=ops.evaluate(net,tx,ty,4)
        rec.update(round=r,clients=clients,evaluation=metric,exact_aggregation=True);entries.append(rec)
        write('MANIFEST.json',{'method':'Retrain_from_scratch','rounds':entries},False)
        print(json.dumps({'round':r,**metric}),flush=True)
        del submissions,rb;gc.collect()
    final=save('after.pt',current)
    write('RESULT.json',{'state':'complete','method':'Retrain_from_scratch','rounds':100,'erased_client':4,
        'after':final,'evaluation':metric,'post_gate_CA97_ASR60':metric['CA_pct']>=97 and metric['ASR_pct']>=60,
        'original_pre_suppression_passed':False,'full_paper_reproduced':False})
    write('STATE.json',{'state':'complete','pid':os.getpid()},False)


if __name__=='__main__':
    try:
        if sys.argv[1]=='prepare':prepare()
        elif sys.argv[1]=='train':train()
        else:raise ValueError('prepare or train required')
    except Exception:
        write('FAILURE_'+sys.argv[1]+'.json',{'traceback':traceback.format_exc()});raise
