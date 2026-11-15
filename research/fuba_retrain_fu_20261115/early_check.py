"""Single CPU check of the first erased-client round and first gamma1 attacker."""
import json
import os
import ctypes
from ctypes import wintypes
import msvcrt
import torch
from run import ROOT,read,sha,write,frozen,exact,participants
from verify import finite


def live_json(path):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    kernel.CreateFileW.restype=wintypes.HANDLE
    handle=kernel.CreateFileW(str(path),0x80000000,7,None,3,0x80,None)
    if handle==wintypes.HANDLE(-1).value:raise ctypes.WinError(ctypes.get_last_error())
    descriptor=msvcrt.open_osfhandle(handle,os.O_RDONLY)
    with os.fdopen(descriptor,'r',encoding='utf-8') as f:return json.load(f)


def main():
    torch.set_num_threads(1);frozen()
    for name,digest in read(ROOT/'EARLY_CHECK_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest
    prepared=read(ROOT/'PREPARED.json')
    erased_round=next(int(k) for k,v in prepared['schedule'].items() if 4 in v[0])
    first_r,first_c=next((int(k),c) for k,v in prepared['schedule'].items() if int(k)>5 for c in v[1] if c<4)
    assert (erased_round,first_r,first_c)==(2,7,0)
    role=read(ROOT/f'roles/round{first_r:04d}_client{first_c:02d}.json')
    rows={r['round']:r for r in live_json(ROOT/'MANIFEST.json')['rounds']}
    assert erased_round in rows and first_r-1 in rows
    write('EARLY_CHECK_STARTED.json',{'pid':os.getpid()})
    def bundle(r):
        item=rows[r];assert sha(ROOT/item['path'])==item['sha256']
        return torch.load(ROOT/item['path'],map_location='cpu',weights_only=True)
    removed=bundle(erased_round);previous=bundle(erased_round-1)
    original,retained=participants(erased_round)
    assert removed['original_selected']==original and removed['clients']==retained and 4 in original and 4 not in retained
    assert len(retained)==7 and removed['weights']==[1/7]*7
    exact(removed['incoming'],previous['after'])
    exact(removed['after'],{k:torch.stack([s[k] for s in removed['submitted']]).mean(0) for k in previous['after']})
    incoming=bundle(first_r-1)['after'];phases=[]
    assert role['gamma']==1 and role['role']=='attacker_retrain_gamma1' and len(role['phases'])==3
    for item in role['phases']:
        assert sha(ROOT/item['path'])==item['sha256']
        p=torch.load(ROOT/item['path'],map_location='cpu',weights_only=True);finite(p)
        assert p['epochs']==50 and p['batches']==2150 and {'optimizer','rng','loader_rng'}<=p.keys();phases.append(p)
    item=role['submitted'];assert sha(ROOT/item['path'])==item['sha256']
    submitted=torch.load(ROOT/item['path'],map_location='cpu',weights_only=True)['model']
    exact(submitted,{k:incoming[k]+1.*(phases[2]['model'][k]-incoming[k]) for k in incoming})
    logs=[]
    with (ROOT/'epochs.jsonl').open() as f:
        for line in f:
            if not line.endswith('\n'):continue
            event=json.loads(line)
            if event['round']==first_r and event['client']==first_c:logs.append(event)
    assert len(logs)==150
    for phase,opt in [('backdoor_anchor','Adam'),('benign_anchor','Adam'),('embedding','SGD')]:
        selected=[e for e in logs if e['phase']==phase]
        assert [e['epoch'] for e in selected]==list(range(1,51)) and all(e['optimizer']==opt for e in selected)
    assert not phases[2]['optimizer']['state']
    result={'state':'passed','first_erased_round':2,'actual_retained_clients':retained,'actual_weight':1/7,
            'first_attacker':{'round':7,'client':0,'gamma':1,'epochs':150,'batches':6450},
            'submission_exact':True,'round_aggregation_exact':True,'finite_phase_optimizer_RNG':True,
            'CUDA_initialized':torch.cuda.is_initialized(),'real_data_inference':0,'final100R_verified':False}
    write('EARLY_CHECK.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':main()
