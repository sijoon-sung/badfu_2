"""One-time, evaluator-only factorial interventions on sealed BadFU states."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')

import numpy as np
from PIL import Image
import torch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OUT = HERE / 'stage03'
PAIRS = [('benign_big19336','clean_pre','clean_big_post'),
         ('benign_same850','clean_pre','clean_post'),
         ('attack_cover850','pre','post')]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def write(name,obj):
    p=OUT/name
    temporary=p.with_suffix(p.suffix+'.tmp')
    temporary.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    os.replace(temporary,p)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def resource_guard():
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=utilization.gpu,memory.free,memory.used',
                                  '--format=csv,noheader,nounits'],text=True).strip()
    utilization,free,used=map(int,gpu.splitlines()[0].split(','))
    script="Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python|mpiexec'} | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    raw=subprocess.check_output(['powershell','-NoProfile','-Command',script],text=True).strip()
    processes=json.loads(raw) if raw else []
    if isinstance(processes,dict):processes=[processes]
    competitors=[p for p in processes if p['ProcessId']!=os.getpid() and
                 any(s in (p.get('CommandLine') or '') for s in
                     ['FEDUBA_PAPER_IMPLEMENTATION_20261031','FUBA_SEED_REPRO_20261031','mpiexec'])]
    guard={'GPU':gpu,'processes':processes,'competing_experiment_processes':competitors,
           'free_min_MiB':3072,'utilization_max':10,'per_process_fraction':.25}
    write('RESOURCE.json',guard)
    assert free>=3072 and utilization<=10 and not competitors, 'Resource entry contract not met'


def is_buffer(name):
    return name.endswith(('running_mean','running_var','num_batches_tracked'))


def combine(a,b,w,buff,h):
    """Accept states and fixed binary factors only; no labels or attack truth."""
    states=[a,b]
    return {k:states[h if k.startswith('model.fc.') else buff if is_buffer(k) else w][k].clone()
            for k in b}


def tensor_digest(state):
    h=hashlib.sha256()
    for k in sorted(state):
        v=state[k].contiguous().cpu()
        h.update(k.encode());h.update(str(v.dtype).encode());h.update(str(tuple(v.shape)).encode())
        h.update(v.numpy().tobytes())
    return h.hexdigest()


def normalise(raw):
    x=raw.permute(0,3,1,2).float()/255.
    return ((x-torch.tensor([.4914,.4822,.4465])[None,:,None,None])/
            torch.tensor([.2023,.1994,.2010])[None,:,None,None]).contiguous()


@torch.inference_mode()
def extract(model,raw):
    features=[]
    handle=model.model.fc.register_forward_pre_hook(lambda _m,inputs:features.append(inputs[0].cpu()))
    try:
        for offset in range(0,len(raw),32):
            model(normalise(raw[offset:offset+32]).cuda())
            if offset%3200==0:
                write('PROGRESS.json',{'pid':os.getpid(),'variant':CURRENT_VARIANT,
                      'dataset_n':len(raw),'images_completed':min(offset+32,len(raw)),
                      'time_unix':time.time()})
    finally:handle.remove()
    result=torch.cat(features)
    assert result.shape==(len(raw),512) and torch.isfinite(result).all()
    return result


def metrics(logits,labels,pre,post,ids):
    y=labels[ids];p=logits[ids].argmax(1)
    a=pre[ids].argmax(1);b=post[ids].argmax(1)
    benefit=(a!=y)&(b==y)
    return {'n':len(ids),'correct':int((p==y).sum()),'CA_pct':100*float((p==y).double().mean()),
       'class_CA_pct':[100*float((p[y==c]==y[y==c]).double().mean()) for c in range(10)],
       'beneficial_n':int(benefit.sum()),'beneficial_kept_n':int(((p==y)&benefit).sum()),
       'beneficial_kept_fraction':float((p[benefit]==y[benefit]).double().mean()) if benefit.any() else 1.,
       'disagree_post_n':int((p!=b).sum())}


def load_data(info):
    for k in ['clean_path','record_path','image_manifest_path']:
        assert sha(info[k])==info[k+'_sha256'],k
    data=torch.load(info['clean_path'],map_location='cpu',weights_only=True)
    expected=read(info['image_manifest_path'])['image_sha256']
    expected={k.replace('\\','/'):v for k,v in expected.items()}
    record=torch.load(info['record_path'],map_location='cpu',weights_only=False)
    images=[];ids=[]
    for i,entry in record['bd_test']['bd_data_container']['data_dict'].items():
        parts=str(entry['path']).replace('\\','/').split('/')
        rel='/'.join(parts[parts.index('bd_test_dataset'):])
        path=Path(info['record_root'])/rel
        assert sha(path)==expected[rel],rel
        assert int(entry['other_info'][0])==0
        images.append(np.asarray(Image.open(path).convert('RGB')).copy());ids.append(int(i))
    assert len(images)==9000 and sorted(ids)==torch.where(data['test_y']!=0)[0].tolist()
    return data['test_x'],data['test_y'].long(),torch.from_numpy(np.stack(images))


def main():
    OUT.mkdir(exist_ok=True)
    freeze=read(HERE/'STAGE03_FREEZE.json')
    for n,h in freeze['files'].items():assert sha(HERE/n)==h,('source freeze',n)
    if (OUT/'STARTED.json').exists():raise RuntimeError('Finite factorial already started; do not relaunch')
    resource_guard()
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:
        json.dump({'pid':os.getpid(),'time_unix':time.time(),'freeze_sha256':sha(HERE/'STAGE03_FREEZE.json')},f)
    info=read(HERE/'STAGE03_INPUTS.json')
    selector=subprocess.run([sys.executable,info['selector'],'badfu.confirmed.s20261023.v1',
             '--purpose','purification_pilot'],capture_output=True,text=True,encoding='utf8',check=True)
    selection=json.loads(selector.stdout);write('SELECTED_CASE.json',selection)
    snap=Path(selection['source_root']);guard=selection['checkpoint_guard']
    assert sha(guard['manifest_path'])==guard['manifest_sha256']
    assert sha(guard['seal_path'])==guard['seal_sha256']
    declared=read(guard['manifest_path'])
    assert sha(guard['loader_path'])==declared['files']['load_confirmed.py']['sha256']
    spec=importlib.util.spec_from_file_location('sealed_defense_snapshot',guard['loader_path'])
    sealed=importlib.util.module_from_spec(spec);spec.loader.exec_module(sealed)
    sealed.verify(snap,guard['manifest_sha256'])
    torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.cuda.set_per_process_memory_fraction(.25)
    states={}
    for role,entry in selection['server_inputs'].items():
        assert sha(entry['path'])==entry['sha256']
        s=torch.load(entry['path'],map_location='cpu',weights_only=True)
        states[role]=s if entry['payload_key'] is None else s[entry['payload_key']]
        assert all(torch.isfinite(v).all() for v in states[role].values())
    # All intervention definitions exist before actual attack images are opened.
    definitions={}
    for name,a,b in PAIRS:
        for w in range(2):
            for buff in range(2):
                s=combine(states[a],states[b],w,buff,1)
                label=f'{name}_W{w}B{buff}'
                p=OUT/(label+'_posthead.pt');torch.save(s,p)
                definitions[label]={'tensor_sha256':tensor_digest(s),'file_sha256':sha(p),
                                    'pre_role':a,'post_role':b,'W':w,'BN':buff,'head':1}
    write('INTERVENTIONS_BEFORE_TRIGGER.json',definitions)
    clean,y,attack=load_data(info)
    split=read(HERE/'PROXY_SPLIT.json');ids=torch.tensor(split['heldout_ids'])
    native={r:torch.load(HERE/'inputs'/('logits_'+r+'.pt'),weights_only=True).double() for r in states}
    cache={};result={'state':'running','evaluator':'defense_factorial_W_B_H_v1',
                    'rows':[],'native_checks':{},'actual_trigger_images':9000,
                    'formal_deletion_checked':False,'new_FL_seeds':0}
    literal=read(HERE/'NATIVE_REFERENCE.json')['metrics']
    model=sealed.model_class(snap)().cuda().eval()
    for name,a,b in PAIRS:
        baseline=metrics(native[b],y,native[a],native[b],ids)
        for w in range(2):
            for buff in range(2):
                global CURRENT_VARIANT
                CURRENT_VARIANT=f'{name}_W{w}B{buff}'
                state=combine(states[a],states[b],w,buff,1)
                key=tensor_digest({k:v for k,v in state.items() if not k.startswith('model.fc.')})
                if key not in cache:
                    model.load_state_dict(state,strict=True)
                    start=time.time()
                    fc=extract(model,clean);fa=extract(model,attack)
                    assert tensor_digest(model.cpu().state_dict())==tensor_digest(state),'forward mutated state'
                    model.cuda()
                    path=OUT/(CURRENT_VARIANT+'_features.pt')
                    torch.save({'clean':fc,'attack':fa},path)
                    cache[key]=(fc.double(),fa.double(),path.name)
                    print(json.dumps({'variant':CURRENT_VARIANT,'seconds':time.time()-start}),flush=True)
                fc,fa,feature_path=cache[key]
                for head,role in [(0,a),(1,b)]:
                    wc=states[role]['model.fc.weight'].double();bias=states[role]['model.fc.bias'].double()
                    z=fc@wc.T+bias;za=fa@wc.T+bias
                    metric=metrics(z,y,native[a],native[b],ids)
                    drops=[u-v for u,v in zip(baseline['class_CA_pct'],metric['class_CA_pct'])]
                    row={'pair':name,'W':w,'BN':buff,'head':head,'heldout_clean':metric,
                         'full_clean_correct':int((z.argmax(1)==y).sum()),'full_clean_n':10000,
                         'attack_target_n':int((za.argmax(1)==0).sum()),'attack_n':9000,
                         'ASR_pct':100*float((za.argmax(1)==0).double().mean()),
                         'overall_drop_pp':baseline['CA_pct']-metric['CA_pct'],
                         'worst_class_drop_pp':max(drops),'feature_path':feature_path}
                    row['necessary_utility_gate']=(row['overall_drop_pp']<=.5+1e-10 and max(drops)<=2+1e-10 and
                        (not name.startswith('benign') or metric['beneficial_kept_fraction']>=.9))
                    result['rows'].append(row)
                    if w==buff==head:
                        ref=literal[role]
                        differences={'CA_pp':row['full_clean_correct']/100-ref['CA_pct'],
                                     'ASR_pp':row['ASR_pct']-ref['ASR_pct']}
                        result['native_checks'][role]=differences
                        assert max(map(abs,differences.values()))<=.1+1e-10,(role,differences)
                    write('RESULT.json',result)
                if w==buff==0:
                    hp=HERE/('transport_'+name.replace('attack_cover850','attack_cover850_clean_only')+'.pt')
                    assert sha(hp)==read(HERE/'COMPLETED.json')['files'][hp.name]
                    transport=torch.load(hp,map_location='cpu',weights_only=True)
                    z=fc@transport['weight'].double().T+transport['bias'].double()
                    za=fa@transport['weight'].double().T+transport['bias'].double()
                    result.setdefault('previous_H2_attack_evaluation',{})[name]={
                        'clean':metrics(z,y,native[a],native[b],ids),
                        'attack_target_n':int((za.argmax(1)==0).sum()),'attack_n':9000,
                        'ASR_pct':100*float((za.argmax(1)==0).double().mean()),'head_sha256':sha(hp)}
                    write('RESULT.json',result)
    assert len(result['rows'])==24
    result.update(state='completed',unique_backbone_forward_pairs=len(cache),
                  gpu_max_allocated_bytes=torch.cuda.max_memory_allocated(),
                  source_checkpoint_hash_guard='passed_before_after',finished_unix=time.time())
    sealed.verify(snap,guard['manifest_sha256'])
    write('RESULT.json',result)
    write('COMPLETED.json',{'pid':os.getpid(),'result_sha256':sha(OUT/'RESULT.json'),
          'source_freeze_sha256':sha(HERE/'STAGE03_FREEZE.json'),
          'files':{p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='COMPLETED.json'}})
    print('FACTORIAL_COMPLETED',flush=True)


if __name__=='__main__':
    try:main()
    except Exception:
        OUT.mkdir(exist_ok=True)
        write('FAILURE.json',{'pid':os.getpid(),'traceback':traceback.format_exc()})
        raise
