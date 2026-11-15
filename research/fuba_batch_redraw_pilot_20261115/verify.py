"""CPU verification of the finite treatment, including every saved mask draw."""
import collections
import json
import math
import torch
from run import ROOT,read,sha,write,exact,frozen,module


def finite(v):
    if isinstance(v,torch.Tensor):assert bool(torch.isfinite(v).all())
    elif isinstance(v,dict):
        for x in v.values():finite(x)
    elif isinstance(v,(list,tuple)):
        for x in v:finite(x)
    elif isinstance(v,float):assert math.isfinite(v)


def main():
    torch.set_num_threads(1);frozen()
    assert read(ROOT/'STATE.json')['state']=='complete'
    for name,digest in read(ROOT/'AUDIT_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest
    write('CPU_AUDIT_STARTED.json',{'state':'started'})
    grouped=collections.defaultdict(list)
    for line in (ROOT/'epochs.jsonl').read_text().splitlines():
        e=json.loads(line);grouped[e['round'],e['client'],e['phase']].append(e)
    entries=read(ROOT/'MANIFEST.json')['rounds'];assert [e['round'] for e in entries]==list(range(21,31))
    previous=torch.load(ROOT/'inputs/round0020.pt',weights_only=True,map_location='cpu')['after']
    net=module('audit_net',ROOT/'inputs/author_model.py').Net().eval();count=collections.Counter()
    reference={e['round']:e for e in read(ROOT/'PREPARED.json')['control_rows']}
    for e in entries:
        path=ROOT/e['path'];assert sha(path)==e['sha256']
        b=torch.load(path,weights_only=True,map_location='cpu');r=e['round']
        assert b['clients']==reference[r]['clients'] and len(b['roles'])==len(b['submitted'])==8
        exact(previous,b['incoming']);exact(b['after'],{k:torch.stack([v[k] for v in b['submitted']]).mean(0) for k in previous})
        for client,s,role in zip(b['clients'],b['submitted'],b['roles']):
            assert role['client']==client and role['round']==r and role['arm']=='batch_redraw'
            names=['benign'] if client>=5 else ['backdoor_anchor','benign_anchor','embedding','recovery' if client==4 else 'representative']
            assert len(role['phases'])==len(names);phases=[]
            for number,(name,item) in enumerate(zip(names,role['phases']),1):
                path=ROOT/item['path'];assert sha(path)==item['sha256']
                p=torch.load(path,weights_only=True,map_location='cpu');finite(p);net.load_state_dict(p['model'],strict=True)
                batches=2350 if client>=5 else 2150
                assert p['epochs']==50 and p['batches']==batches and p['phase']==number
                logs=grouped[r,client,name];assert [l['epoch'] for l in logs]==list(range(1,51))
                assert [l['batches'] for l in logs]==[(i+1)*(47 if client>=5 else 43) for i in range(50)]
                optimizer='SGD' if name in ['embedding','recovery'] else 'Adam'
                assert all(l['optimizer']==optimizer for l in logs)
                assert (not p['optimizer']['state'])==(optimizer=='SGD')
                prng=p['loader_rng']
                if client<5 and name in ['backdoor_anchor','embedding']:
                    expected_seed=role['seed']+number+70000000
                    assert prng['role']==client and prng['mask_seed']==expected_seed and prng['probability']==.3
                    assert len(prng['mask_hex'])==2150
                    generator=torch.Generator().manual_seed(expected_seed)
                    for index,encoded in enumerate(prng['mask_hex']):
                        size=12 if index%43==42 else 64
                        expected=bytes((torch.rand(size,generator=generator)<.3).to(torch.uint8).tolist())
                        actual=bytes.fromhex(encoded);assert actual==expected
                        count['mask_batches']+=1;count['mask_examples']+=len(actual);count['poison_examples']+=sum(actual)
                    assert torch.equal(prng['mask'],generator.get_state())
                    assert isinstance(prng['shuffle'],torch.Tensor)
                else:assert isinstance(prng,torch.Tensor)
                phases.append(p['model']);count['phases']+=1;count['epochs']+=50;count['batches']+=batches
            if client<4:
                d=role['decision'];assert [s['gamma'] for s in d['scores']]==[i/10 for i in range(11)]
                for score in d['scores']:
                    assert score['N']==300 and score['trigger_role']==4
                    assert score['ASR_pct']==100*score['target_successes']/score['non_target_N']
                passed=[s['gamma'] for s in d['scores'] if s['ASR_pct']<10]
                gamma=max(passed) if passed else 0.
                assert d['gamma']==gamma and d['constraint_met']==bool(passed)
                exact(s,{k:previous[k]+gamma*(phases[2][k]-previous[k]) for k in previous})
                count['gamma_traces']+=1
            elif client==4:
                exact(s,{k:previous[k]+phases[3][k]-phases[2][k] for k in previous});count['defender_roles']+=1
            else:exact(s,phases[0])
            path=ROOT/role['submitted']['path'];assert sha(path)==role['submitted']['sha256']
            exact(s,torch.load(path,weights_only=True,map_location='cpu')['model']);count['roles']+=1
        previous=b['after'];m=e['evaluation'];assert m['N']==10000 and m['non_target_N']==9026
        assert m['CA_pct']==100*m['clean_correct']/10000 and m['ASR_pct']==100*m['target_successes']/9026
        count['rounds']+=1
    assert count['roles']==80 and count['phases']==137 and count['gamma_traces']==18 and count['defender_roles']==1
    assert sum(len(v) for v in grouped.values())==count['epochs']==6850
    assert count['mask_batches']==81700 and count['mask_examples']==5130000
    net.load_state_dict(previous,strict=True)
    with torch.inference_mode():assert bool(torch.isfinite(net(torch.zeros(1,1,28,28))).all())
    write('CPU_AUDIT.json',{'state':'passed','counts':dict(count),'all_masks_independently_reconstructed':True,
        'all_submission_and_aggregation_exact':True,'full_epoch_optimizer_RNG_checked':True,
        'all_phase_strict_CPU_loads':True,'CUDA_initialized':torch.cuda.is_initialized(),'gradient_training_replay':False})
    print(json.dumps(dict(count)),flush=True)


if __name__=='__main__':main()
