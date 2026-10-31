"""Independent array/RNG/seal checks, no fresh model forward."""
import hashlib,json
import numpy as np
import torch
import stage05_common as s
core=s.core


def digest(t):return hashlib.sha256(t.contiguous().numpy().tobytes()).hexdigest()


def main():
    s.verify_sources();r=s.HERE/'sourcepair_pilot'
    freeze=core.read(s.HERE/'SOURCEPAIR_PILOT_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    result=core.read(r/'RESULT.json');receipt=core.read(r/'COMPLETED.json')
    assert result['state']=='completed' and receipt['result_sha256']==core.sha(r/'RESULT.json')
    assert receipt['source_freeze_sha256']==core.sha(s.HERE/'SOURCEPAIR_PILOT_FREEZE.json')
    info=core.read(s.HERE/'STAGE03_INPUTS.json');assert core.sha(info['clean_path'])==info['clean_path_sha256']
    raw=torch.load(info['clean_path'],map_location='cpu',weights_only=True)['test_x']
    public=raw[core.read(s.HERE/'PROXY_SPLIT.json')['fit_ids']].permute(0,3,1,2).float().div(255).contiguous()
    pool={digest(v) for v in public};selected,sealed,_=s.snapshot()
    report={'state':'passed','cases':{},'fresh_model_inference':False,'all_PGD_gradients_recomputed':False,
        'initial_pseudo_labels_independently_forwarded':False,'verifier_sha256':core.sha(__file__)}
    assert list(result['cases']) in [['benign_big19336'],['benign_big19336','attack_cover850']]
    for pair,row in result['cases'].items():
        folder=r/pair;cr=core.read(folder/'COMPLETED.json')
        for n,h in cr['files'].items():assert core.sha(folder/n)==h,(pair,n)
        assert row==core.read(folder/'RESULT.json') and cr['result_sha256']==core.sha(folder/'RESULT.json')
        inp=core.read(folder/'SOURCE_INPUTS.json');role='clean_big_post' if pair.startswith('benign') else 'post'
        assert inp['case_id']==selected['case_id'] and inp['post_role']==role and inp['post_sha256']==selected['server_inputs'][role]['sha256']
        assert inp['teacher_sha256']==core.read(s.OUT/'CANDIDATES_BEFORE_EVALUATION.json')['models'][pair+'_aligned_model.pt']
        initial=torch.load(folder/'private_initials.pt',map_location='cpu',weights_only=True);meta=core.read(folder/'INITIALS.json')
        assert meta['sha256']==core.sha(folder/'private_initials.pt') and initial['starts'].shape==(90,3,32,32)
        assert all(digest(v) in pool for v in initial['starts'])
        req=torch.arange(10).repeat_interleave(9);src=torch.tensor([s for k in range(10) for s in range(10) if s!=k])
        assert torch.equal(req,initial['requested']) and torch.equal(src,initial['sources'])
        g=torch.Generator().manual_seed(20261031+1300)
        for c in src.tolist():torch.randint(meta['source_pool_counts'][c],(1,),generator=g)
        assert torch.equal(g.get_state(),initial['rng'])
        arms={};feasible={}
        for arm,v in row['arms'].items():
            p=folder/('private_'+arm+'_bank.pt');assert core.sha(p)==v['sha256']
            b=torch.load(p,map_location='cpu',weights_only=True)
            assert torch.equal(b['requested'],req) and torch.equal(b['sources'],src)
            assert b['queries'].shape==(90,3,32,32) and torch.isfinite(b['queries']).all() and 0<=b['queries'].min()<=b['queries'].max()<=1
            assert b['teacher_logits'].shape==b['post_logits'].shape==(90,10)
            assert torch.isfinite(b['teacher_logits']).all() and torch.isfinite(b['post_logits']).all()
            assert torch.equal((b['teacher_logits']/2).softmax(1),b['teacher_prob_T2'])
            t=b['teacher_logits'].numpy().argmax(1);p=b['post_logits'].numpy().argmax(1);sn=src.numpy();kn=req.numpy()
            agree=t==sn;success=agree&(p==kn);counts=np.bincount(t,minlength=10).tolist();matrix=np.zeros((10,10),dtype=int)
            for sc,k,ok in zip(sn,kn,success):matrix[sc,k]+=int(ok)
            assert counts==v['teacher_class_counts'] and np.bincount(p,minlength=10).tolist()==v['post_class_counts']
            assert int(agree.sum())==v['assigned_source_correct_n'] and int(success.sum())==v['joint_pair_success_n'] and matrix.tolist()==v['source_target_success_matrix']
            assert [x['k'] for x in v['logs']]==list(range(10))
            assert all([z['step'] for z in x['steps']]==list(range(1,21)) and all(np.isfinite(z['objective']) for z in x['steps']) for x in v['logs'])
            feasible[arm]=int(agree.sum())>=72 and min(counts)>0 and max(counts)<=18
            arms[arm]={'source_correct_n':int(agree.sum()),'teacher_counts':counts,'joint_success_n':int(success.sum()),
                'source_preserved_count_per_source':np.bincount(sn[agree],minlength=10).tolist(),
                'source_preserved_count_per_requested_target':np.bincount(kn[agree],minlength=10).tolist()}
        assert feasible==row['feasible_arms'] and any(feasible.values())==row['source_feasibility_gate']
        assert row['extra_source_objective_fidelity_gain_n']==arms['teacher_source']['source_correct_n']-arms['teacher_not_k']['source_correct_n']
        report['cases'][pair]=arms
    assert ('attack_cover850' in result['cases'])==result['cases']['benign_big19336']['source_feasibility_gate']
    assert not torch.cuda.is_initialized();sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    with (r/'INDEPENDENT_VERIFICATION.json').open('x',encoding='utf8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
