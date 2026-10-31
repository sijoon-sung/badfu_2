"""Independent saved-output audit and bounded replay, preserving all primary files."""
import hashlib,json,gc
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
import stage05_common as s
from stage08 import norm
from sourcepair_pilot import cpu_guard
from verify_stage10 import finite,policy
from verify_post_anchor import check_private,check_attack,close
core=s.core;ROOT=s.HERE/'shared_feature_run'
ARMS=['pointwise_logits','shared_logits','pointwise_features','shared_features']
PAIRS=['benign_big19336','attack_cover850','benign_same850']


def array_sha(v):return hashlib.sha256(v.contiguous().numpy().tobytes()).hexdigest()


def hooked(model,x):
    captured=[];hook=model.model.fc.register_forward_pre_hook(lambda _module,args:captured.append(args[0]))
    try:z=model(norm(x))
    finally:hook.remove()
    assert len(captured)==1 and captured[0].shape==(len(x),512)
    return z,captured[0]


def replay(cls,native,teacherstate,public,initial,banks,targets,folder,bank_summary):
    post=cls().eval();post.load_state_dict(native,strict=True)
    teacher=cls().eval();teacher.load_state_dict(teacherstate,strict=True)
    for model in [post,teacher]:
        for p in model.parameters():p.requires_grad_(False)
    with torch.no_grad():
        c=[hooked(post,v) for v in public.split(32)];a=[hooked(post,v) for v in initial['starts'].split(32)]
    assert torch.equal(torch.cat([v[0] for v in c]),targets['public_logits'])
    assert torch.equal(torch.cat([v[1] for v in c]),targets['public_features'])
    assert torch.equal(torch.cat([v[0] for v in a]),targets['anchor_logits'])
    assert torch.equal(torch.cat([v[1] for v in a]),targets['anchor_features'])
    gen={}
    for kind in ['pointwise','shared']:
        anchor=initial['starts'][:9];source=initial['sources'][:9]
        delta=torch.zeros((9 if kind=='pointwise' else 1,3,32,32));saved=torch.load(folder/('private_'+kind+'_k0_generation.pt'),map_location='cpu',weights_only=True)
        errs=[]
        for i in range(20):
            delta=delta.detach().requires_grad_(True);query=torch.clamp(anchor+delta,min=0,max=1)
            tz=teacher(norm(query));pz=post(norm(query));rows=torch.arange(9)
            # Independent explicit row indexing, not learner gather/objective.
            value=((pz/2).log_softmax(1)[rows,0]+(tz/2).log_softmax(1)[rows,source]).mean()
            gradient=torch.autograd.grad(value,delta)[0]
            assert core.tensor_digest({'gradient':gradient.detach()})==bank_summary[kind]['trace'][0]['steps'][i]['gradient_sha256']
            err=abs(float(value.detach())-bank_summary[kind]['trace'][0]['steps'][i]['objective']);assert err<=1e-6;errs.append(err)
            delta=torch.clamp(delta+.1*gradient.sign(),min=-1,max=1).detach()
            assert torch.equal(delta,saved['steps'][i]['delta'])
            assert torch.equal(torch.clamp(anchor+delta,0,1),saved['steps'][i]['queries'])
        gen[kind]={'first_requested0_all20_delta_query_gradient_hash_exact':True,'objective_max_abs_error':max(errs)}
    torch.manual_seed(20261101+1701);student=cls().eval();student.load_state_dict(native,strict=True)
    for p in student.model.fc.parameters():p.requires_grad_(False)
    opt=torch.optim.Adam([p for p in student.parameters() if p.requires_grad],lr=.0001,weight_decay=0)
    gf=torch.Generator().manual_seed(20261101+901);gq=torch.Generator().manual_seed(20261101+902)
    bank=banks['shared'];buckets=[torch.where(bank['sources']==c)[0] for c in range(10)]
    for _ in range(10):
        ix=torch.randint(500,(32,),generator=gf);qi=torch.stack([b[torch.randint(len(b),(1,),generator=gq)[0]] for b in buckets])
        opt.zero_grad(set_to_none=True);cz,ch=hooked(student,public[ix]);qz,qh=hooked(student,bank['queries'][qi])
        c=F.kl_div(F.log_softmax(cz/2,dim=1),targets['public_prob_T2'][ix],reduction='batchmean')*4
        q=F.kl_div(F.log_softmax(qz/2,dim=1),targets['anchor_prob_T2'][qi],reduction='batchmean')*4
        cf=((ch-targets['public_features'][ix])**2).mean()/targets['feature_scale']
        qf=((qh-targets['anchor_features'][qi])**2).mean()/targets['feature_scale']
        ((c+q)+(cf+qf)).backward();opt.step()
    stored=torch.load(folder/'shared_features_step010.pt',map_location='cpu',weights_only=True);calc=student.state_dict()
    error=max(float((calc[k].double()-v.double()).abs().max()) for k,v in stored.items())
    exact=all(torch.equal(calc[k],v) for k,v in stored.items())
    if not exact:
        with (ROOT/('REPLAY_MISMATCH_'+folder.name+'.json')).open('x',encoding='utf8') as f:json.dump({'max_abs_error':error},f)
    assert exact,'bounded primary first10 state replay mismatch'
    return {'generation_replay':gen,'fresh_public_and_anchor_logits_features_exact':True,'first10_primary_updates_exact':True,'maximum_state_abs_error':error,
        'input_gradient_image_evaluations':360,'disposable_classifier_updates':10,
        'other9_requested_targets_or_remaining90_updates_recomputed':False}


def main():
    s.verify_sources();vf=core.read(s.HERE/'SHARED_FEATURE_VERIFICATION_FREEZE.json')
    for n,h in vf['files'].items():assert core.sha(s.HERE/n)==h,n
    freeze=core.read(s.HERE/'SHARED_FEATURE_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    cpu=cpu_guard();selected,sealed,states=s.snapshot();cls=sealed.model_class(Path(selected['source_root']))
    top=core.read(ROOT/'COMPLETED.json');summary=core.read(ROOT/'RESULT.json')
    assert top['result_sha256']==core.sha(ROOT/'RESULT.json') and top['source_freeze_sha256']==core.sha(s.HERE/'SHARED_FEATURE_FREEZE.json')
    assert summary['state']=='completed' and summary['CUDA_initialized'] is False and list(summary['cases'])==PAIRS[:len(summary['cases'])]
    info=core.read(s.HERE/'STAGE03_INPUTS.json');assert core.sha(info['clean_path'])==info['clean_path_sha256']
    data=torch.load(info['clean_path'],map_location='cpu',weights_only=True);labels=data['test_y'].numpy()
    split=core.read(s.HERE/'PROXY_SPLIT.json');held=np.asarray(split['heldout_ids']);assert len(held)==9500 and set(held).isdisjoint(split['fit_ids'])
    public=data['test_x'][split['fit_ids']].permute(0,3,1,2).float().div(255).contiguous()
    assert core.sha(info['record_path'])==info['record_path_sha256'];record=torch.load(info['record_path'],map_location='cpu',weights_only=False)
    tids=np.asarray([int(i) for i in record['bd_test']['bd_data_container']['data_dict']]);mask=np.isin(tids,held)
    assert len(tids)==9000 and int(mask.sum())==8542 and sorted(tids.tolist())==np.flatnonzero(labels!=0).tolist()
    baseline=core.read(s.HERE/'heldout_reference_audit/RESULT.json');member_receipt=core.read(s.HERE/'stage07_cpu_v2/COMPLETED.json')
    report={'state':'passed','scope':'finished_pipeline','cases':{},'CPU':cpu,'full_objective_achieved':False,
        'fresh_actual_trigger_clean_member_inference':False,'limited_disposable_replay':True,
        'all_gradients_recomputed':False,'root_result_sha256':core.sha(ROOT/'RESULT.json'),
        'verifier_sha256':core.sha(__file__),'verification_freeze_sha256':core.sha(s.HERE/'SHARED_FEATURE_VERIFICATION_FREEZE.json')}
    survivors=ARMS.copy()
    for pair,result in summary['cases'].items():
        folder=ROOT/pair;receipt=core.read(folder/'COMPLETED.json')
        for n,h in receipt['files'].items():assert core.sha(folder/n)==h,(pair,n)
        assert result==core.read(folder/'RESULT.json') and receipt['result_sha256']==core.sha(folder/'RESULT.json')
        dec=core.read(folder/'SELECTION_BEFORE_PRIVATE_EVALUATION.json');assert result['selection_sha256']==core.sha(folder/'SELECTION_BEFORE_PRIVATE_EVALUATION.json')
        assert dec['common_head_fixed'] and dec['BN_buffers_fixed'] and dec['query_target']=='native_Post_original_anchor'
        assert all(dec[k] is False for k in ['groundtruth_labels_used','member_used','actual_trigger_used','ASR_used'])
        inp=core.read(folder/'SOURCE_INPUTS.json');a=inp['pre_role'];b=inp['post_role'];native=states[b]
        assert inp['case_id']==selected['case_id'] and inp['purpose']=='purification_pilot' and inp['post_sha256']==selected['server_inputs'][b]['sha256']
        hp=s.OUT/(pair+'_aligned_model.pt');assert core.sha(hp)==inp['teacher_sha256']
        initial=torch.load(folder/'private_initials.pt',map_location='cpu',weights_only=True);finite(initial)
        src=torch.tensor([c for k in range(10) for c in range(10) if c!=k]);req=torch.arange(10).repeat_interleave(9)
        assert torch.equal(initial['sources'],src) and torch.equal(initial['requested'],req)
        assert torch.equal(initial['starts'],public[initial['public_indices']])
        gen=torch.Generator().manual_seed(20261101+1700);expected=[]
        for c in src.tolist():
            pool=initial['source_pools'][c];assert torch.equal(pool,torch.where((initial['teacher_predictions']==c)&(initial['post_predictions']==c))[0])
            expected.append(pool[torch.randint(len(pool),(1,),generator=gen)[0]])
        assert torch.equal(torch.stack(expected),initial['public_indices']) and torch.equal(gen.get_state(),initial['source_sampler_rng'])
        bm=core.read(folder/'BANK_BEFORE_TRAINING.json');banks={}
        for kind in ['pointwise','shared']:
            p=folder/('private_'+kind+'_bank.pt');assert core.sha(p)==bm[kind]['sha256'];bank=torch.load(p,map_location='cpu',weights_only=True);finite(bank);banks[kind]=bank
            valid=bank['raw_teacher_logits'].argmax(1)==src
            assert torch.equal(valid,bank['raw_source_valid']) and torch.equal(bank['sources'],src) and torch.equal(bank['requested'],req)
            assert torch.equal(bank['starts'],initial['starts']) and torch.equal(bank['teacher_logits'].argmax(1),src)
            ex=bank['raw_queries'].clone();ex[~valid]=initial['starts'][~valid];assert torch.equal(ex,bank['queries'])
            assert int(valid.sum())==bm[kind]['raw_source_valid_n'] and int((~valid).sum())==bm[kind]['identity_replacement_n']
            assert int((valid&(bank['raw_post_logits'].argmax(1)==req)).sum())==bm[kind]['raw_joint_n']
            assert bm[kind]['image_gradient_evaluations']==1800 and len(bm[kind]['trace'])==10
            for k in range(10):
                saved=torch.load(folder/('private_'+kind+'_k'+str(k)+'_generation.pt'),map_location='cpu',weights_only=True);finite(saved)
                assert len(saved['steps'])==20 and [r['step'] for r in bm[kind]['trace'][k]['steps']]==list(range(1,21))
                for row in saved['steps']:
                    d=row['delta'];assert d.shape==(9 if kind=='pointwise' else 1,3,32,32) and -1<=d.min()<=d.max()<=1
                    assert torch.equal(row['queries'],(initial['starts'][k*9:(k+1)*9]+d).clamp(0,1))
                assert torch.equal(saved['steps'][-1]['queries'],bank['raw_queries'][k*9:(k+1)*9])
        target=torch.load(folder/'private_targets.pt',map_location='cpu',weights_only=True);finite(target)
        assert torch.equal(target['public_prob_T2'],(target['public_logits']/2).softmax(1))
        assert torch.equal(target['anchor_prob_T2'],(target['anchor_logits']/2).softmax(1))
        assert torch.equal(target['anchor_prob_T2'].argmax(1),src)
        assert torch.equal(target['feature_scale'],target['public_features'].square().mean().clamp_min(1e-8));close(dec['feature_scale'],float(target['feature_scale']))
        checked={};alllogs={}
        for arm in ARMS:
            rd=dec['raw_models'][arm];sd=dec['models'][arm]
            for entry in [rd,sd]:assert core.sha(folder/entry['path'])==entry['sha256']
            raw=torch.load(folder/rd['path'],map_location='cpu',weights_only=True);chosen=torch.load(folder/sd['path'],map_location='cpu',weights_only=True);finite(raw);finite(chosen)
            cls().load_state_dict(raw,strict=True);cls().load_state_dict(chosen,strict=True)
            for k,v in native.items():
                ex=torch.lerp(v,raw[k],sd['alpha']) if v.is_floating_point() else v
                assert torch.equal(ex,chosen[k]),k
                if core.is_buffer(k) or k.startswith('model.fc.'):assert torch.equal(raw[k],v) and torch.equal(chosen[k],v)
            assert sd['identity']==(core.tensor_digest(chosen)==core.tensor_digest(native))
            logs=[json.loads(v) for v in (folder/(arm+'_steps.jsonl')).read_text(encoding='utf8').splitlines()];alllogs[arm]=logs
            assert rd['steps']==100 and [r['step'] for r in logs]==list(range(1,101))
            gf=torch.Generator().manual_seed(20261101+901);gq=torch.Generator().manual_seed(20261101+902);buckets=[torch.where(src==c)[0] for c in range(10)]
            for r in logs:
                ix=torch.randint(500,(32,),generator=gf);qi=torch.stack([v[torch.randint(len(v),(1,),generator=gq)[0]] for v in buckets])
                assert array_sha(ix)==r['public_draw_sha256'] and array_sha(qi)==r['query_draw_sha256']
                assert r['feature_loss_in_objective']==arm.endswith('_features')
                assert np.isfinite([r[k] for k in ['clean_loss','query_loss','clean_feature_loss','query_feature_loss','seconds']]).all()
            opt=torch.load(folder/(arm+'_optimizer_rng.pt'),map_location='cpu',weights_only=True);finite(opt)
            assert torch.equal(opt['public_sampler_rng'],gf.get_state()) and torch.equal(opt['query_sampler_rng'],gq.get_state())
            assert len(opt['optimizer']['state'])==len(list(cls().parameters()))-2 and all(float(v['step'])==100 for v in opt['optimizer']['state'].values())
            groups=opt['optimizer']['param_groups'];assert len(groups)==1 and groups[0]['lr']==.0001 and groups[0]['weight_decay']==0
            px=torch.load(folder/('private_'+arm+'_proxy.pt'),map_location='cpu',weights_only=True);finite(px);alpha=policy(dec['all_points'][arm],px)
            assert alpha==sd['alpha']==dec['choices'][arm]['alpha'] and dec['choices'][arm]['tensor_sha256']==core.tensor_digest(chosen)
            assert torch.allclose((px['teacher_logits']/2).softmax(1),target['public_prob_T2'].double(),atol=2e-6,rtol=2e-6)
            checked[arm]={'steps':100,'alpha':alpha,'policy_points':len(px['alphas']),'head_and_BN_exact_fixed':True}
            if pair=='attack_cover850':
                clean_pred=s.logits(s.feature_cache(pair,False)['clean'],s.head(native)).argmax(1).numpy()[tids]
                counts={}
                for variant in ['raw','selected']:
                    z=torch.load(folder/('private_'+arm+'_'+variant+'_attack.pt'),map_location='cpu',weights_only=True)['attack_logits'];finite(z)
                    counts[variant]=check_attack(z,labels[tids],mask,clean_pred,result['all_ASR'][arm][variant])
                checked[arm]['independent_attack_counts']=counts
        for arm in ARMS[1:]:assert all(x['public_draw_sha256']==y['public_draw_sha256'] and x['query_draw_sha256']==y['query_draw_sha256'] for x,y in zip(alllogs[ARMS[0]],alllogs[arm]))
        privacy=check_private(pair,folder,result,states,a,b,labels,held,tids,mask,baseline,member_receipt)
        bounded=replay(cls,native,torch.load(hp,map_location='cpu',weights_only=True),public,initial,banks,target,folder,bm)
        report['cases'][pair]={'arms':checked,'independent_private_checks':privacy,'bounded_replay':bounded}
        survivors=[arm for arm in survivors if result.get('cases',{}).get(arm,{}).get('necessary_gate',False)]
        if not survivors:assert pair==list(summary['cases'])[-1]
        gc.collect()
    for arm in ARMS:assert summary['method_necessary_gates'][arm]==all(summary['cases'].get(p,{}).get('cases',{}).get(arm,{}).get('necessary_gate',False) for p in PAIRS)
    assert not torch.cuda.is_initialized();sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    with (ROOT/'INDEPENDENT_VERIFICATION.json').open('x',encoding='utf8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
