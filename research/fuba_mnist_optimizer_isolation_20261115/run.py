"""Fixed two-arm final-role diagnosis; all original training history stays immutable."""
import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
import copy
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
import numpy as np
import torch
import original_core as core
from diagnostic_core import learn

ROOT=Path(__file__).resolve().parent
UTILITY=Path('D:/FUBA_GAMMA_DETERMINISTIC_20261115/run.py')


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m


sys.modules['reference_core']=core
ops=module('frozen_operations',UTILITY)
read,sha,cpu,exact=ops.read,ops.sha,ops.cpu,ops.exact
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
    binding=read(ROOT/'INPUT_BINDING.json');base=Path(binding['source_root'])
    assert sha(base/'catalog/select_case.py')==binding['selector_sha256']
    selected=json.loads(subprocess.check_output([sys.executable,'-B',str(base/'catalog/select_case.py'),
        binding['case_id'],'--purpose','diagnostic'],text=True,encoding='utf-8'))
    assert selected['guard_state']=='all_snapshot_files_verified_on_this_host'
    assert sha(base/'delivery/REVIEW_MANIFEST.json')==binding['manifest_sha256']
    manifest=read(base/'delivery/REVIEW_MANIFEST.json');(ROOT/'inputs').mkdir(exist_ok=False);files={}
    for name,digest in binding['files'].items():
        assert manifest['files'][name]['sha256']==digest and sha(base/name)==digest,name
        target=ROOT/'inputs'/Path(name).name;shutil.copyfile(base/name,target)
        assert sha(target)==digest;files[target.relative_to(ROOT).as_posix()]=digest
    assert sha(ROOT/'original_core.py')==sha(ROOT/'inputs/reference_core.py')
    b=torch.load(ROOT/'inputs/round0100.pt',map_location='cpu',weights_only=True)
    assert b['round']==100 and b['clients']==[1,5,10,12,14,15,16,18]
    assert [c for c in b['clients'] if c<4]==[1] and 4 not in b['clients']
    exact(b['after'],{k:torch.stack([v[k] for v in b['submitted']]).mean(0) for k in b['after']})
    role=read(ROOT/'inputs/round0100_client01.json');assert role['seed']==21261123 and role['gamma']==1
    assert read(ROOT/'CPU_CONTRACT.json')['state']=='passed'
    write('PREPARED.json',{'state':'passed','files':files,'selection':selected,
        'client':1,'round':100,'incoming_payload_key':'incoming','anchor_payload_key':'model',
        'original_remaining_contributors':b['clients'][1:],'new_full_FL_or_FU':False})
    print('Prepared exact actual-FU last role and seven immutable peer submissions',flush=True)


def restore_rng(r):
    random.setstate(r['python']);n=r['numpy']
    np.random.set_state((n[0],np.array(n[1],dtype=np.uint32),n[2],n[3],n[4]))
    torch.set_rng_state(r['torch_CPU']);torch.cuda.set_rng_state_all(r['torch_CUDA'])


def train():
    frozen();ready=read(ROOT/'PREPARED.json')
    for name,digest in ready['files'].items():assert sha(ROOT/name)==digest,name
    resources=guard();write('STARTED.json',{'pid':os.getpid(),'time':time.time(),'resources':resources})
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic=True;torch.backends.cudnn.benchmark=False
    torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False
    p=read(ROOT/'inputs/PROFILE.json');Net=module('author_Net',ROOT/'inputs/author_model.py').Net
    from torchvision.datasets import MNIST
    data=MNIST(p['data_root'],train=True,download=False);test=MNIST(p['data_root'],train=False,download=False)
    for name,digest in MNIST.resources:assert hashlib.md5((Path(data.raw_folder)/name).read_bytes()).hexdigest()==digest
    split=read(ROOT/'inputs/SPLIT.json')['indices'][1]
    ids=torch.tensor(split);order=torch.randperm(3000,generator=torch.Generator().manual_seed(p['partition_seed']+1))
    train_ids=ids[order[300:]];x=data.data[train_ids].cuda().float().unsqueeze(1)/255;y=data.targets[train_ids].cuda()
    idx=torch.randperm(2700,generator=torch.Generator().manual_seed(p['partition_seed']+1001))[:810].cuda()
    x[idx]=core.stamp(x[idx],1);y[idx]=8
    tx=test.data.cuda().float().unsqueeze(1)/255;ty=test.targets.cuda()
    b=torch.load(ROOT/'inputs/round0100.pt',map_location='cpu',weights_only=True)
    phases=[torch.load(ROOT/'inputs'/f'phase{i:02d}.pt',map_location='cpu',weights_only=True) for i in (1,2,3)]
    incoming=Net().cuda();incoming.load_state_dict(b['incoming'],strict=True)
    anchor=Net().cuda();anchor.load_state_dict(phases[0]['model'],strict=True)
    benign=Net().cuda();benign.load_state_dict(phases[1]['model'],strict=True)
    weights=core.weights(anchor,benign);weights_file=save('weights.pt',weights);del anchor,benign
    rows={};order_hashes={};artifacts=[]
    for arm in ['algorithm_sgd','experimental_adam']:
        frozen();restore_rng(phases[1]['rng']);start_rng=ops.rng();order_hashes[arm]=[]
        def log(**values):
            order_hashes[arm].append(values['order_sha256'])
            rec={'arm':arm,'time':time.time(),**values}
            with (ROOT/'epochs.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(rec,allow_nan=False)+'\n')
            write('STATE.json',{'state':'training','pid':os.getpid(),**rec},False)
        model,opt,lrng,batches=learn(copy.deepcopy(incoming),x,y,core.Settings(),phase_seed=21261126,
            phase='embedding',gradient_weights=weights,log=log,optimizer_policy=arm)
        artifact=save(arm+'/phase03.pt',{'model':model.state_dict(),'optimizer':opt.state_dict(),
            'rng':ops.rng(),'start_rng':start_rng,'loader_rng':lrng,'epochs':50,'batches':batches,
            'order_sha256':order_hashes[arm],'optimizer_policy':arm})
        submission=cpu(core.affine(incoming,model,1.).state_dict())
        submitted=[submission,*b['submitted'][1:]]
        after={k:torch.stack([v[k] for v in submitted]).mean(0) for k in b['after']}
        aggregate=save(arm+'/aggregate.pt',{'after':after,'submitted':submitted,'clients':b['clients'],
            'incoming':b['incoming'],'gamma':1.,'changed_client':1,'new_full_FU':False})
        local=ops.evaluate(model,tx,ty,4)
        model.load_state_dict(after,strict=True);metric=ops.evaluate(model,tx,ty,4)
        old_phase_exact=all(torch.equal(cpu(v),phases[2]['model'][k]) for k,v in torch.load(ROOT/artifact['path'],map_location='cpu',weights_only=True)['model'].items())
        old_after_exact=all(torch.equal(after[k],b['after'][k]) for k in after)
        rows[arm]={'local':local,'aggregate':metric,'phase':artifact,'aggregate_file':aggregate,
            'original_phase3_exact':old_phase_exact,'original_after_exact':old_after_exact}
        artifacts.extend([artifact,aggregate]);del model,opt
    assert order_hashes['algorithm_sgd']==order_hashes['experimental_adam'] and len(order_hashes['algorithm_sgd'])==50
    a=rows['algorithm_sgd']['aggregate'];d=rows['experimental_adam']['aggregate']
    checks={'ASR_gain_20pp':d['ASR_pct']-a['ASR_pct']>=20,'CA97':d['CA_pct']>=97,
        'CA_drop_at_most_1pp':a['CA_pct']-d['CA_pct']<=1,
        'clean_target_bias_increase_at_most_1pp':100*(d['clean_target_bias']-a['clean_target_bias'])/9026<=1}
    write('RESULT.json',{'state':'complete','rows':rows,'weights_file':weights_file,'checks':checks,'hypothesis_supported':all(checks.values()),
        'same_epoch_order_hashes':True,'full_paper_reproduced':False,'new_full_FU':False,
        'algorithm_SGD_remains_conformance_target':True,'independent_validation_pending':True})
    write('STATE.json',{'state':'complete','pid':os.getpid()},False)
    print(json.dumps({'checks':checks,'A':a,'B':d,'SGD_original_exact':rows['algorithm_sgd']['original_after_exact']}),flush=True)


if __name__=='__main__':
    try:
        if sys.argv[1]=='prepare':prepare()
        elif sys.argv[1]=='train':train()
        else:raise ValueError('prepare or train required')
    except Exception:
        write('FAILURE_'+sys.argv[1]+'.json',{'traceback':traceback.format_exc()});raise
