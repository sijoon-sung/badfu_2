"""Preserve failed original, verify/copy committed27R, and prepare only continuation."""
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import torch
from run import ROOT,read,sha,write,exact,frozen,participants,module

OLD=Path('D:/FUBA_RETRAIN_FU_20261115')

def finite(v):
    if isinstance(v,torch.Tensor):assert bool(torch.isfinite(v).all())
    elif isinstance(v,dict):
        for x in v.values():finite(x)
    elif isinstance(v,(list,tuple)):
        for x in v:finite(x)
    elif isinstance(v,float):assert math.isfinite(v)

def main():
    torch.set_num_threads(1);frozen()
    write('RECOVERY_PREPARE_STARTED.json',{'pid':os.getpid()})
    command="@(Get-CimInstance Win32_Process|Where-Object {$_.Name -eq 'python.exe'}|Select-Object ProcessId,CommandLine)|ConvertTo-Json -Depth 3"
    raw=subprocess.check_output(['powershell','-NoProfile','-Command',command],text=True)
    processes=json.loads(raw) if raw.strip() else []
    if isinstance(processes,dict):processes=[processes]
    for p in processes:
        assert p['ProcessId']!=51232
        assert 'FUBA_RETRAIN_FU_20261115/run.py train' not in (p.get('CommandLine') or '')
    failure=read(OLD/'FAILURE_train.json')
    trace=failure['traceback']
    assert 'print(' in trace and ('BrokenPipeError' in trace or 'OSError: [Errno 22]' in trace),trace
    old_freeze=read(OLD/'FREEZE.json')
    for name,digest in old_freeze['files'].items():assert sha(OLD/name)==digest
    assert old_freeze==read(ROOT/'ORIGINAL_BINDING.json')['original_freeze']
    assert sha(ROOT/'reference_core.py')==old_freeze['files']['reference_core.py']
    assert read(ROOT/'INPUT_BINDING.json')==read(OLD/'INPUT_BINDING.json')
    manifest=read(OLD/'MANIFEST.json')
    assert [e['round'] for e in manifest['rounds']]==list(range(1,28))
    assert manifest['rounds'][-1]['sha256']=='1c1a71ed549a0bf9f6a0333641db8a3584c4959f78a1f78b0015e4a1960f3515'
    full={p.relative_to(OLD).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size}
          for p in sorted(OLD.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.tmp'}
    write('original_incident/FULL_ORIGINAL_MANIFEST.json',{'remote_root':str(OLD),'files':full,'state':'stopped27R'})
    for name in ['run.py','reference_core.py','FREEZE.json','PREPARED.json','STARTED.json','RUNTIME.json','STATE.json',
                 'MANIFEST.json','FAILURE_train.json','PROTOCOL.txt','INPUT_BINDING.json',
                 'SSH_DISCONNECT_20261115.json','SSH_RECONNECTED_20261115.json']:
        if (OLD/name).exists():
            target=ROOT/'original_incident'/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(OLD/name,target);assert sha(target)==full[name]['sha256']
    copied={}
    def copy_file(name):
        target=ROOT/name;assert not target.exists(),name
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(OLD/name,target)
        assert sha(target)==full[name]['sha256'];copied[name]=full[name]['sha256']
    ready=read(OLD/'PREPARED.json')
    for name,digest in ready['files'].items():
        assert sha(OLD/name)==digest
        if name.startswith('inputs/'):copy_file(name)
        else:assert name=='reference_core.py' and sha(ROOT/name)==digest
    logs=collections.defaultdict(list);all_events=[]
    for line in (OLD/'epochs.jsonl').read_text(encoding='utf-8').splitlines():
        e=json.loads(line);assert e['round']<=27
        logs[e['round'],e['client'],e['phase']].append(e);all_events.append(e)
    previous=torch.load(OLD/'inputs/initial.pt',map_location='cpu',weights_only=True)
    net=module('prefix_audit_net',OLD/'inputs/author_model.py').Net().eval()
    counts=collections.Counter()
    for e in manifest['rounds']:
        path=OLD/e['path'];assert sha(path)==e['sha256']
        b=torch.load(path,map_location='cpu',weights_only=True);r=e['round'];original,clients=participants(r)
        assert b['round']==r and b['original_selected']==original and b['clients']==clients and 4 not in clients
        assert b['weights']==[1/len(clients)]*len(clients)
        exact(previous,b['incoming']);exact(b['after'],{k:torch.stack([s[k] for s in b['submitted']]).mean(0) for k in previous})
        assert len(b['roles'])==len(b['submitted'])==len(clients)
        for c,s,role in zip(clients,b['submitted'],b['roles']):
            assert role['client']==c and role['round']==r
            malicious=c<4 and r>5
            phases=['backdoor_anchor','benign_anchor','embedding'] if malicious else ['benign']
            assert len(role['phases'])==len(phases)
            for number,(name,item) in enumerate(zip(phases,role['phases']),1):
                assert sha(OLD/item['path'])==item['sha256']
                p=torch.load(OLD/item['path'],map_location='cpu',weights_only=True);finite(p)
                net.load_state_dict(p['model'],strict=True)
                assert p['epochs']==50 and p['phase']==number and p['batches']==(2150 if malicious else 2350)
                events=logs[r,c,name];assert [v['epoch'] for v in events]==list(range(1,51))
                assert [v['batches'] for v in events]==[(i+1)*(43 if malicious else 47) for i in range(50)]
                expected='SGD' if name=='embedding' else 'Adam'
                assert all(v['optimizer']==expected for v in events)
                copy_file(item['path']);counts['phases']+=1;counts['epochs']+=50
            if malicious:
                assert role['gamma']==1
                exact(s,{k:previous[k]+1.*(p['model'][k]-previous[k]) for k in previous})
                counts['attacker_roles']+=1
            else:exact(s,p['model'])
            name=role['submitted']['path'];assert sha(OLD/name)==role['submitted']['sha256']
            exact(s,torch.load(OLD/name,map_location='cpu',weights_only=True)['model']);copy_file(name)
            copy_file(f'roles/round{r:04d}_client{c:02d}.json');counts['roles']+=1
        previous=b['after'];copy_file(e['path']);counts['rounds']+=1
    assert counts['epochs']==len(all_events)
    net.load_state_dict(previous,strict=True)
    with torch.inference_mode():assert bool(torch.isfinite(net(torch.zeros(1,1,28,28))).all())
    for name in ['epochs.jsonl','MANIFEST.json']:copy_file(name)
    write('PREPARED.json',ready)
    write('RECOVERY_PREPARED.json',{'state':'passed','original_root':str(OLD),'original_PID_absent':True,
        'committed_rounds':27,'continuation_rounds':[28,100],'prefix_counts':dict(counts),'copied_files':copied,
        'all_prefix_hash_chain_submission_aggregation_epochs_exact':True,'CUDA_initialized':torch.cuda.is_initialized(),
        'new_training':0,'real_data_inference':0,'original_failure':failure,
        'full_original_manifest_sha256':sha(ROOT/'original_incident/FULL_ORIGINAL_MANIFEST.json')})
    print(json.dumps({'state':'passed','committed_rounds':27,'counts':dict(counts),'copied_files':len(copied)}),flush=True)

if __name__=='__main__':main()
