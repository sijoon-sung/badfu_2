"""Read-only CPU verification after actual100R retained-client FU completes."""
import collections
import json
import math
import os
import torch
from run import ROOT,read,sha,write,exact,frozen,participants,module


def finite(value):
    if isinstance(value,torch.Tensor):assert bool(torch.isfinite(value).all())
    elif isinstance(value,dict):
        for v in value.values():finite(v)
    elif isinstance(value,(tuple,list)):
        for v in value:finite(v)
    elif isinstance(value,float):assert math.isfinite(value)


def main():
    torch.set_num_threads(1);frozen()
    assert read(ROOT/'STATE.json')['state']=='complete'
    for name,digest in read(ROOT/'AUDIT_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest
    write('CPU_AUDIT_STARTED.json',{'pid':os.getpid()})
    events=collections.defaultdict(list)
    for line in (ROOT/'epochs.jsonl').read_text().splitlines():
        e=json.loads(line);events[e['round'],e['client'],e['phase']].append(e)
    previous=torch.load(ROOT/'inputs/initial.pt',weights_only=True,map_location='cpu')
    net=module('audit_Net',ROOT/'inputs/author_model.py').Net().eval()
    net.load_state_dict(previous,strict=True)
    entries=read(ROOT/'MANIFEST.json')['rounds'];assert [e['round'] for e in entries]==list(range(1,101))
    counts=collections.Counter()
    for e in entries:
        path=ROOT/e['path'];assert sha(path)==e['sha256']
        b=torch.load(path,weights_only=True,map_location='cpu');r=b['round']
        original,clients=participants(r)
        assert b['original_selected']==original and b['clients']==clients and 4 not in clients
        assert b['erased_client']==4 and b['weights']==[1/len(clients)]*len(clients)
        exact(previous,b['incoming'])
        assert len(b['roles'])==len(b['submitted'])==len(clients)
        exact(b['after'],{k:torch.stack([s[k] for s in b['submitted']]).mean(0) for k in previous})
        for c,s,role in zip(clients,b['submitted'],b['roles']):
            assert role['client']==c and role['round']==r
            malignant=c<4 and r>5
            names=['backdoor_anchor','benign_anchor','embedding'] if malignant else ['benign']
            assert len(role['phases'])==len(names)
            assert role['role']==('attacker_retrain_gamma1' if malignant else 'benign')
            for phase,item in zip(names,role['phases']):
                file=ROOT/item['path'];assert sha(file)==item['sha256']
                p=torch.load(file,weights_only=True,map_location='cpu')
                assert p['epochs']==50 and p['batches']==(2150 if malignant else 2350)
                finite(p);net.load_state_dict(p['model'],strict=True)
                assert {'model','optimizer','loader_rng','rng'}<=p.keys()
                logs=events[r,c,phase];assert [z['epoch'] for z in logs]==list(range(1,51))
                optimizer='SGD' if phase=='embedding' else 'Adam'
                assert all(z['optimizer']==optimizer for z in logs)
                assert [z['batches'] for z in logs]==[(i+1)*(43 if malignant else 47) for i in range(50)]
                counts['phases']+=1;counts['epochs']+=50;counts['batches']+=p['batches']
            if malignant:
                assert role['gamma']==1 and not role['test_or_validation_used_for_selection']
                exact(s,{k:previous[k]+1.*(p['model'][k]-previous[k]) for k in previous})
                counts['attacker_roles']+=1
            else:exact(s,p['model'])
            submitted=ROOT/role['submitted']['path'];assert sha(submitted)==role['submitted']['sha256']
            exact(s,torch.load(submitted,weights_only=True,map_location='cpu')['model'])
            counts['roles']+=1
        m=e['evaluation'];assert m['N']==10000 and m['non_target_N']==9026
        assert m['CA_pct']==100*m['clean_correct']/10000 and m['ASR_pct']==100*m['target_successes']/9026
        previous=b['after'];counts['rounds']+=1
    assert counts['roles']==759 and counts['attacker_roles']==146 and counts['phases']==1051
    exact(previous,torch.load(ROOT/'after.pt',weights_only=True,map_location='cpu'))
    net.load_state_dict(previous,strict=True)
    with torch.inference_mode():assert bool(torch.isfinite(net(torch.zeros(1,1,28,28))).all())
    result=read(ROOT/'RESULT.json');assert sha(ROOT/'after.pt')==result['after']['sha256']
    assert sum(len(v) for v in events.values())==counts['epochs']
    write('CPU_AUDIT.json',{'state':'passed','counts':dict(counts),'client4_absent_all_rounds':True,
        'all_submission_formulas_and_aggregation_exact':True,'optimizer_RNG_and_full_epoch_logs':True,
        'all_phase_strict_CPU_loads':True,'final_synthetic_finite_forward':True,
        'CUDA_initialized':torch.cuda.is_initialized(),'all_phase_training_replayed':False})
    print(json.dumps(dict(counts)),flush=True)


if __name__=='__main__':main()
