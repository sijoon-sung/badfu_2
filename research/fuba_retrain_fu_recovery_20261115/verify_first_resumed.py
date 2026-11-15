"""One CPU bridge audit after first actual resumed round28 commits."""
import collections
import json
import torch
from run import ROOT,read,sha,write,exact,frozen,module
from verify import finite


def main():
    torch.set_num_threads(1);frozen()
    for name,digest in read(ROOT/'BRIDGE_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest
    p=ROOT/'rounds/round0028.pt';b=torch.load(p,map_location='cpu',weights_only=True)
    prior=ROOT/'rounds/round0027.pt'
    assert sha(prior)=='1c1a71ed549a0bf9f6a0333641db8a3584c4959f78a1f78b0015e4a1960f3515'
    old=torch.load(prior,map_location='cpu',weights_only=True);exact(b['incoming'],old['after'])
    assert b['round']==28 and 4 not in b['clients'] and b['weights']==[1/len(b['clients'])]*len(b['clients'])
    exact(b['after'],{k:torch.stack([s[k] for s in b['submitted']]).mean(0) for k in old['after']})
    # Only completed round28 records are read; the active writer appends later rounds.
    logs=collections.defaultdict(list)
    for line in (ROOT/'epochs.jsonl').read_text().splitlines():
        try:e=json.loads(line)
        except json.JSONDecodeError:continue
        if e['round']==28:logs[e['client'],e['phase']].append(e)
    net=module('bridge_net',ROOT/'inputs/author_model.py').Net().eval();count=0
    for c,s,role in zip(b['clients'],b['submitted'],b['roles']):
        names=['backdoor_anchor','benign_anchor','embedding'] if c<4 else ['benign']
        assert len(names)==len(role['phases'])
        for name,item in zip(names,role['phases']):
            assert sha(ROOT/item['path'])==item['sha256']
            x=torch.load(ROOT/item['path'],map_location='cpu',weights_only=True);finite(x)
            net.load_state_dict(x['model'],strict=True)
            assert x['epochs']==50 and [e['epoch'] for e in logs[c,name]]==list(range(1,51));count+=1
        if c<4:exact(s,{k:b['incoming'][k]+1.*(x['model'][k]-b['incoming'][k]) for k in s})
        else:exact(s,x['model'])
    write('FIRST_RESUMED_ROUND.json',{'state':'passed','original_committed_rounds':27,'actual_new_round':28,
        'round27_SHA256':sha(prior),'round28_SHA256':sha(p),'incoming_and_aggregation_exact':True,
        'new_roles':len(b['clients']),'new_phases':count,'new_epochs':count*50,
        'full_epoch_optimizer_RNG_finite':True,'CUDA_initialized':torch.cuda.is_initialized(),
        'real_data_inference':0,'actual100R_completed':False})
    print('Exact27-to28 continuation, complete actual new phases and aggregation passed',flush=True)


if __name__=='__main__':main()
