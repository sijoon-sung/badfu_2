"""Full CPU audit of both saved phases and diagnostic aggregation."""
import json
import torch
from run import ROOT,read,sha,write,frozen,module,exact
from check_core import exact as exact_tree


def main():
    torch.set_num_threads(1);frozen();assert read(ROOT/'STATE.json')['state']=='complete'
    for name,digest in read(ROOT/'AUDIT_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest
    write('CPU_AUDIT_STARTED.json',{'state':'started'})
    result=read(ROOT/'RESULT.json');b=torch.load(ROOT/'inputs/round0100.pt',map_location='cpu',weights_only=True)
    old2=torch.load(ROOT/'inputs/phase02.pt',map_location='cpu',weights_only=True)
    old3=torch.load(ROOT/'inputs/phase03.pt',map_location='cpu',weights_only=True)
    old1=torch.load(ROOT/'inputs/phase01.pt',map_location='cpu',weights_only=True)
    wfile=result['weights_file'];assert sha(ROOT/wfile['path'])==wfile['sha256']
    weights=torch.load(ROOT/wfile['path'],map_location='cpu',weights_only=True)
    diffs={k:(old1['model'][k]-old2['model'][k]).abs() for k in weights}
    low=min(float(v.min()) for v in diffs.values());high=max(float(v.max()) for v in diffs.values())
    for k,v in weights.items():
        expected=torch.ones_like(v) if high==low else 1-(diffs[k]-low)/(high-low)
        assert bool(torch.isfinite(v).all()) and torch.allclose(v,expected,rtol=0,atol=1e-7)
    net=module('audit_Net',ROOT/'inputs/author_model.py').Net().eval();logs=[json.loads(x) for x in (ROOT/'epochs.jsonl').read_text().splitlines()]
    phases=[];states=0
    for arm in ['algorithm_sgd','experimental_adam']:
        row=result['rows'][arm];item=row['phase'];assert sha(ROOT/item['path'])==item['sha256']
        p=torch.load(ROOT/item['path'],map_location='cpu',weights_only=True);assert p['epochs']==50 and p['batches']==2150
        exact_tree(p['start_rng'],old2['rng']);assert len(p['order_sha256'])==50
        gl=[l for l in logs if l['arm']==arm];assert [l['epoch'] for l in gl]==list(range(1,51))
        assert [l['batches'] for l in gl]==[43*i for i in range(1,51)]
        assert [l['order_sha256'] for l in gl]==p['order_sha256']
        assert all(l['examples']==2700 and l['optimizer']==('SGD' if arm=='algorithm_sgd' else 'Adam') for l in gl)
        assert bool(p['optimizer']['state'])==(arm=='experimental_adam')
        agg=row['aggregate_file'];assert sha(ROOT/agg['path'])==agg['sha256']
        g=torch.load(ROOT/agg['path'],map_location='cpu',weights_only=True)
        exact(g['incoming'],b['incoming']);assert g['clients']==b['clients'] and g['changed_client']==1
        exact(g['submitted'][0],{k:b['incoming'][k]+(p['model'][k]-b['incoming'][k]) for k in b['incoming']})
        for left,right in zip(g['submitted'][1:],b['submitted'][1:]):exact(left,right)
        exact(g['after'],{k:torch.stack([s[k] for s in g['submitted']]).mean(0) for k in b['after']})
        phase_equal=all(torch.equal(p['model'][k],old3['model'][k]) for k in p['model'])
        after_equal=all(torch.equal(g['after'][k],b['after'][k]) for k in b['after'])
        assert phase_equal==row['original_phase3_exact'] and after_equal==row['original_after_exact']
        for state in [p['model'],g['after'],*g['submitted']]:
            assert all(bool(torch.isfinite(v).all()) for v in state.values());net.load_state_dict(state,strict=True)
            with torch.inference_mode():assert bool(torch.isfinite(net(torch.zeros(1,1,28,28))).all())
            states+=1
        for state in p['optimizer']['state'].values():
            for v in state.values():
                if isinstance(v,torch.Tensor):assert bool(torch.isfinite(v).all())
        phases.append(p)
    assert len(logs)==100 and phases[0]['order_sha256']==phases[1]['order_sha256']
    assert torch.equal(phases[0]['loader_rng'],phases[1]['loader_rng'])
    exact_tree(phases[0]['rng'],phases[1]['rng'])
    write('CPU_AUDIT.json',{'state':'passed','phases':2,'epochs':100,'batches':4300,
        'strict_CPU_states':states,'same_start_and_end_global_RNG':True,'same_all_epoch_order_hashes':True,
        'unchanged_peer_submissions_per_arm':7,'exact_aggregation':True,'Eq1_weights_CPU_max_tolerance':1e-7,
        'SGD_original_phase_exact':result['rows']['algorithm_sgd']['original_phase3_exact'],
        'SGD_original_aggregate_exact':result['rows']['algorithm_sgd']['original_after_exact'],
        'CUDA_initialized':torch.cuda.is_initialized()})
    print('CPU phases, optimizer/RNG,100 epoch orders, peers and aggregation passed',flush=True)


if __name__=='__main__':main()
