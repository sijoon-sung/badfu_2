"""Independent refresh/state/evaluation audit with bounded disposable replay."""
import hashlib,json
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
import stage05_common as s
from stage08 import norm
from verify_stage10 import finite,policy
from verify_stage09 import np_proxy
from verify_post_anchor import check_private,check_attack,softmax,close,pixel_digest
from sourcepair_pilot import cpu_guard
core=s.core;ROOT=s.HERE/'adaptive_query_run'
ARMS=['fixed_post_refresh','student_refresh'];PAIRS=['benign_big19336','attack_cover850','benign_same850']


def array_sha(v):return hashlib.sha256(v.contiguous().numpy().tobytes()).hexdigest()


def disposable_replay(cls,native,teacher_state,public,initial,bank,buckets,folder):
    """Independently verify the current-student path on private audit copies."""
    post=cls().eval();post.load_state_dict(native,strict=True)
    teacher=cls().eval();teacher.load_state_dict(teacher_state,strict=True)
    for m in [post,teacher]:
        for p in m.parameters():p.requires_grad_(False)
    with torch.no_grad():
        pc=torch.cat([(post(norm(v))/2).softmax(1) for v in public.split(32)])
        anchor=torch.cat([(post(norm(v))/2).softmax(1) for v in initial['starts'].split(32)])
    torch.manual_seed(20261031);student=cls().eval();student.load_state_dict(native,strict=True)
    opt=torch.optim.Adam(student.parameters(),lr=.0001,weight_decay=0)
    gf=torch.Generator().manual_seed(20261031+901);gq=torch.Generator().manual_seed(20261031+902)
    for _ in range(10):
        ix=torch.randint(500,(32,),generator=gf)
        qi=torch.stack([b[torch.randint(len(b),(1,),generator=gq)[0]] for b in buckets])
        opt.zero_grad(set_to_none=True)
        clean=F.kl_div(F.log_softmax(student(norm(public[ix]))/2,dim=1),pc[ix],reduction='batchmean')*4
        query=F.kl_div(F.log_softmax(student(norm(bank['queries'][qi]))/2,dim=1),anchor[qi],reduction='batchmean')*4
        (clean+query).backward();opt.step()
    saved=torch.load(folder/'private_student_refresh_generator_00.pt',map_location='cpu',weights_only=True)
    calc=student.state_dict();errors={k:float((calc[k].double()-v.double()).abs().max()) for k,v in saved.items()}
    exact=all(torch.equal(calc[k],v) for k,v in saved.items())
    check={'ten_update_exact_state_match':exact,'maximum_tensor_abs_error':max(errors.values()),
        'independent_replayed_student_steps':10,'replayed_refresh_indices':[0],'other8_refresh_gradients_recomputed':False}
    if not exact:
        with (folder.parent/'REPLAY_STATE_MISMATCH.json').open('x',encoding='utf8') as f:json.dump({'case':folder.name,**check,'errors':errors},f,indent=2)
    assert exact,'first10 updates differ from saved primary generator00'
    ix=torch.stack([b[0] for b in buckets]);src=initial['sources'][ix];req=initial['requested'][ix]
    details={}
    for arm,generator in [('fixed_post_refresh',post),('student_refresh',student)]:
        original=core.tensor_digest(generator.state_dict());q=initial['starts'][ix].clone();values=[]
        for _ in range(20):
            q=q.detach().requires_grad_(True);t=teacher(norm(q));z=generator(norm(q))
            # Explicit row indexing is independent of the learner's gather code.
            rows=torch.arange(len(q));objective=((z/2).log_softmax(1)[rows,req]+(t/2).log_softmax(1)[rows,src]).mean()
            values.append(float(objective.detach()));gradient=torch.autograd.grad(objective,q)[0]
            q=torch.clamp(q+.1*torch.sign(gradient),min=0,max=1).detach()
        with torch.no_grad():tz=teacher(norm(q));gz=generator(norm(q))
        stored=torch.load(folder/('private_'+arm+'_refresh_00.pt'),map_location='cpu',weights_only=True)
        assert torch.equal(q,stored['queries']) and torch.equal(tz,stored['teacher_logits']) and torch.equal(gz,stored['generator_logits'])
        assert torch.equal(tz.argmax(1)==src,stored['accepted'])
        maxerr=max(abs(v-r['objective']) for v,r in zip(values,stored['steps']));assert maxerr<=1e-6,maxerr
        assert core.tensor_digest(generator.state_dict())==original
        details[arm]={'exact_final_queries_logits_acceptance':True,'maximum_objective_abs_error':maxerr}
    return {**check,'independent_input_gradient_image_evaluations':400,'refresh_replay':details}


def main():
    s.verify_sources();vf=core.read(s.HERE/'ADAPTIVE_QUERY_VERIFICATION_FREEZE.json')
    for n,h in vf['files'].items():assert core.sha(s.HERE/n)==h,n
    freeze=core.read(s.HERE/'ADAPTIVE_QUERY_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    cpu=cpu_guard();selected,sealed,states=s.snapshot();cls=sealed.model_class(Path(selected['source_root']))
    top=core.read(ROOT/'COMPLETED.json');summary=core.read(ROOT/'RESULT.json')
    assert top['result_sha256']==core.sha(ROOT/'RESULT.json') and top['source_freeze_sha256']==core.sha(s.HERE/'ADAPTIVE_QUERY_FREEZE.json')
    assert summary['state']=='completed' and summary['CUDA_initialized'] is False
    assert list(summary['cases'])==PAIRS[:len(summary['cases'])]
    info=core.read(s.HERE/'STAGE03_INPUTS.json');assert core.sha(info['clean_path'])==info['clean_path_sha256']
    data=torch.load(info['clean_path'],map_location='cpu',weights_only=True);labels=data['test_y'].numpy()
    split=core.read(s.HERE/'PROXY_SPLIT.json');held=np.asarray(split['heldout_ids'])
    assert len(held)==9500 and set(held).isdisjoint(split['fit_ids'])
    public=data['test_x'][split['fit_ids']].permute(0,3,1,2).float().div(255).contiguous()
    pixels={pixel_digest(v):i for i,v in enumerate(public)}
    assert core.sha(info['record_path'])==info['record_path_sha256']
    record=torch.load(info['record_path'],map_location='cpu',weights_only=False)
    tids=np.asarray([int(i) for i in record['bd_test']['bd_data_container']['data_dict']]);mask=np.isin(tids,held)
    assert len(tids)==9000 and int(mask.sum())==8542 and sorted(tids.tolist())==np.flatnonzero(labels!=0).tolist()
    baseline=core.read(s.HERE/'heldout_reference_audit/RESULT.json');member_receipt=core.read(s.HERE/'stage07_cpu_v2/COMPLETED.json')
    report={'state':'passed','scope':'finished_pipeline','cases':{},'full_objective_achieved':False,
        'fresh_actual_trigger_clean_member_inference':False,'limited_disposable_training_replay':True,
        'all100_training_steps_or_all9_refresh_gradients_recomputed':False,'CPU':cpu,
        'verifier_sha256':core.sha(__file__),'verification_freeze_sha256':core.sha(s.HERE/'ADAPTIVE_QUERY_VERIFICATION_FREEZE.json'),
        'root_result_sha256':core.sha(ROOT/'RESULT.json')}
    survivors=ARMS.copy()
    for pair,result in summary['cases'].items():
        folder=ROOT/pair;receipt=core.read(folder/'COMPLETED.json')
        for n,h in receipt['files'].items():assert core.sha(folder/n)==h,(pair,n)
        assert receipt['result_sha256']==core.sha(folder/'RESULT.json') and result==core.read(folder/'RESULT.json')
        dec=core.read(folder/'SELECTION_BEFORE_PRIVATE_EVALUATION.json')
        assert result['selection_sha256']==core.sha(folder/'SELECTION_BEFORE_PRIVATE_EVALUATION.json')
        assert all(dec[k] is False for k in ['groundtruth_labels_used','member_used','actual_trigger_used','ASR_used'])
        assert dec['query_targets']=={a:'native_Post_original_anchor' for a in ARMS}
        assert dec['query_generator']=={'fixed_post_refresh':'native_Post','student_refresh':'current_student'}
        assert dec['initial_bank_shared'] and dec['refresh_schedule_after_steps']==list(range(10,100,10))
        inp=core.read(folder/'SOURCE_INPUTS.json');a=inp['pre_role'];b=inp['post_role'];native=states[b]
        assert inp['case_id']==selected['case_id'] and inp['purpose']=='purification_pilot'
        assert inp['post_sha256']==selected['server_inputs'][b]['sha256']
        hp=s.OUT/(pair+'_aligned_model.pt');assert core.sha(hp)==inp['teacher_sha256']==core.read(s.OUT/'CANDIDATES_BEFORE_EVALUATION.json')['models'][hp.name]
        bm=core.read(folder/'BANK_BEFORE_TRAINING.json');bp=Path(bm['bank_path']);ip=Path(bm['initial_path'])
        brp=Path(receipt['bank_receipt_path']);assert core.sha(brp)==receipt['bank_receipt_sha256']
        expected=s.HERE/'sourcepair_pilot'/pair if pair!=PAIRS[2] else folder/'query_generation'
        assert brp.parent.resolve()==expected.resolve()==bp.parent.resolve()==ip.parent.resolve()
        br=core.read(brp)
        for n,h in br['files'].items():assert core.sha(brp.parent/n)==h
        assert core.sha(bp)==bm['bank_sha256'] and core.sha(ip)==bm['initial_sha256']
        bank=torch.load(bp,map_location='cpu',weights_only=True);initial=torch.load(ip,map_location='cpu',weights_only=True);finite(bank);finite(initial)
        src=bank['sources'];req=bank['requested'];valid=bank['teacher_logits'].argmax(1)==src
        assert torch.equal(src,initial['sources']) and torch.equal(req,initial['requested']) and bool((src!=req).all())
        assert torch.equal(req,torch.arange(10).repeat_interleave(9))
        assert torch.equal(src,torch.tensor([c for k in range(10) for c in range(10) if c!=k]))
        assert initial['starts'].shape==bank['queries'].shape==(90,3,32,32)
        im=core.read(brp.parent/'INITIALS.json');assert im['sha256']==core.sha(ip)
        initial_rng=torch.Generator().manual_seed(20261031+1300)
        for c in src.tolist():torch.randint(im['source_pool_counts'][c],(1,),generator=initial_rng)
        assert torch.equal(initial_rng.get_state(),initial['rng'])
        index=np.asarray([pixels[pixel_digest(v)] for v in initial['starts']])
        buckets=[torch.where(valid&(src==c))[0] for c in range(10)];counts=torch.bincount(bank['teacher_logits'].argmax(1),minlength=10)
        usable=all(len(v)>0 for v in buckets) and int(valid.sum())>=72 and int(counts.max())<=18
        assert bm['source_valid_n']==int(valid.sum()) and bm['source_valid_counts']==[len(v) for v in buckets]
        checked={};all_logs={};alias_cache={};digest_cache={}
        if pair=='attack_cover850':
            clean_pred=s.logits(s.feature_cache(pair,False)['clean'],s.head(native)).argmax(1).numpy()[tids]
            reference=result['paired_native_clean_reference'];close(reference['CA_pct'],100*float((clean_pred[mask]==labels[tids][mask]).mean()))
            assert reference['n']==8542
            for c in range(10):
                cm=labels[tids][mask]==c
                if cm.any():close(reference['class_CA_pct'][c],100*float((clean_pred[mask][cm]==c).mean()))
                else:assert reference['class_CA_pct'][c] is None
        for arm in ARMS:
            rd=dec['raw_models'][arm];sd=dec['models'][arm]
            for en in [rd,sd]:assert core.sha(folder/en['path'])==en['sha256']
            raw=torch.load(folder/rd['path'],map_location='cpu',weights_only=True);chosen=torch.load(folder/sd['path'],map_location='cpu',weights_only=True);finite(raw);finite(chosen)
            cls().load_state_dict(raw,strict=True);cls().load_state_dict(chosen,strict=True)
            for k,v in native.items():
                ex=v+sd['alpha']*(raw[k]-v) if v.is_floating_point() else v
                if v.is_floating_point():assert torch.allclose(chosen[k],ex,rtol=2e-6,atol=2e-7),k
                else:assert torch.equal(chosen[k],ex)
                if core.is_buffer(k):assert torch.equal(raw[k],v) and torch.equal(chosen[k],v)
            assert sd['identity']==(core.tensor_digest(chosen)==core.tensor_digest(native))
            steps=100 if usable else 0;assert rd['steps']==steps and rd['identity_fallback']==(not usable)
            trace=core.read(folder/(arm+'_REFRESH_TRACE.json'));assert len(trace)==(9 if usable else 0)==rd['refreshes']
            assert rd['image_gradient_evaluations']==len(trace)*200
            queries=bank['queries'].clone();bank_hash={0:array_sha(queries)};accepted=[]
            for ri,row in enumerate(trace):
                assert row['index']==ri and row['after_student_steps']==(ri+1)*10 and row['attempted']==10
                p=folder/row['path'];assert core.sha(p)==row['sha256'];rr=torch.load(p,map_location='cpu',weights_only=True);finite(rr)
                ix=torch.stack([v[ri%len(v)] for v in buckets])
                assert torch.equal(ix,rr['bank_indices']) and torch.equal(rr['source'],src[ix]) and torch.equal(rr['requested'],req[ix])
                assert rr['queries'].shape==(10,3,32,32) and 0<=rr['queries'].min()<=rr['queries'].max()<=1
                assert [x['step'] for x in rr['steps']]==list(range(1,21)) and all(np.isfinite(x['objective']) for x in rr['steps'])
                ok=rr['teacher_logits'].argmax(1)==src[ix];assert torch.equal(ok,rr['accepted']) and row['accepted']==int(ok.sum())
                if arm=='fixed_post_refresh':assert rr['generator_state_path'] is None and row['model_tensor_sha256']==core.tensor_digest(native)
                else:
                    gp=folder/rr['generator_state_path'];assert core.sha(gp)==rr['generator_state_file_sha256']==row['generator_state_file_sha256']
                    gen=torch.load(gp,map_location='cpu',weights_only=True);finite(gen);cls().load_state_dict(gen,strict=True)
                    assert core.tensor_digest(gen)==row['model_tensor_sha256']
                    for k,v in native.items():
                        if core.is_buffer(k):assert torch.equal(v,gen[k])
                assert rr['unchanged_generator_tensor_sha256']==row['model_tensor_sha256']
                queries[ix[ok]]=rr['queries'][ok];h=array_sha(queries)
                assert h==row['bank_queries_sha256']==rr['updated_bank_queries_sha256'];bank_hash[(ri+1)*10]=h;accepted.append(int(ok.sum()))
            logs=[json.loads(v) for v in (folder/(arm+'_steps.jsonl')).read_text(encoding='utf8').splitlines()]
            assert [v['step'] for v in logs]==list(range(1,steps+1));all_logs[arm]=logs
            opt=torch.load(folder/(arm+'_optimizer_rng.pt'),map_location='cpu',weights_only=True);finite(opt)
            assert all(float(v['step'])==steps for v in opt['optimizer']['state'].values())
            assert len(opt['optimizer']['state'])==(len(list(cls().parameters())) if usable else 0)
            group=opt['optimizer']['param_groups'];assert len(group)==1 and group[0]['lr']==.0001 and group[0]['weight_decay']==0
            gf=torch.Generator().manual_seed(20261031+901);gq=torch.Generator().manual_seed(20261031+902);first=None
            for r in logs:
                ix=torch.randint(500,(32,),generator=gf);qi=torch.stack([v[torch.randint(len(v),(1,),generator=gq)[0]] for v in buckets])
                assert array_sha(ix)==r['public_draw_sha256'] and array_sha(qi)==r['query_draw_sha256'] and r['query_n']==10
                assert np.isfinite([r['clean_loss'],r['query_loss'],r['seconds']]).all()
                last=10*((r['step']-1)//10);assert r['bank_queries_sha256']==bank_hash[last]
                if first is None:first=qi.numpy()
            assert torch.equal(gf.get_state(),opt['public_sampler_rng']) and torch.equal(gq.get_state(),opt['query_sampler_rng'])
            px=torch.load(folder/('private_'+arm+'_proxy.pt'),map_location='cpu',weights_only=True);finite(px)
            if usable:alpha=policy(dec['all_points'][arm],px)
            else:
                assert px['alphas']==[0.] and len(dec['all_points'][arm])==1
                assert np_proxy(px['teacher_logits'].numpy(),px['candidate_logits'][0].numpy())['eligible'];alpha=0.
            assert alpha==sd['alpha']==dec['choices'][arm]['alpha'] and core.tensor_digest(chosen)==dec['choices'][arm]['tensor_sha256']
            diag=torch.load(folder/('private_'+arm+'_bank_diagnostic.pt'),map_location='cpu',weights_only=True);finite(diag)
            assert torch.equal(diag['queries'],queries) and torch.equal(diag['source_valid_mask'],valid)
            assert torch.equal(diag['teacher_logits'].argmax(1)[valid],src[valid])
            anchor=diag['native_anchor_prob_T2'].numpy();expected=softmax(px['teacher_logits'].numpy()[index]/2)
            aerror=float(np.abs(anchor-expected).max());assert aerror<=2e-5 and np.array_equal(anchor.argmax(1),src.numpy())
            lerror=None
            if usable:
                q=anchor[first].astype(np.float64);z=bank['post_logits'].numpy()[first].astype(np.float64)/2;z-=z.max(1,keepdims=True)
                lp=z-np.log(np.exp(z).sum(1,keepdims=True));loss=4*float((q*(np.log(np.maximum(q,np.finfo(float).tiny))-lp)).sum(1).mean())
                lerror=abs(loss-logs[0]['query_loss']);assert lerror<=1e-3
            checked[arm]={'steps':steps,'alpha':alpha,'policy_points':len(px['alphas']),'refreshes':len(trace),'accepted_per_refresh':accepted,
                'image_gradient_evaluations':rd['image_gradient_evaluations'],'anchor_probability_max_abs_error':aerror,
                'first_query_loss_abs_error':lerror,'final_bank_source_correct_n':int((diag['query_logits'].argmax(1)[valid]==src[valid]).sum()),'valid_n':int(valid.sum())}
            if pair=='attack_cover850':
                counts={}
                for variant,st in [('raw',raw),('selected',chosen)]:
                    saved=torch.load(folder/('private_'+arm+'_'+variant+'_attack.pt'),map_location='cpu',weights_only=True);z=saved['attack_logits'];finite(z)
                    digest=core.tensor_digest(st);origin=saved['reused_from'];assert origin==result['all_ASR'][arm][variant]['reused_logits_from']
                    if origin=='identity_original_cache':
                        assert digest==core.tensor_digest(native) and torch.equal(z,s.logits(s.feature_cache(pair,False)['attack'],s.head(native)))
                    elif origin is not None:assert origin in alias_cache and digest==digest_cache[origin] and torch.equal(z,alias_cache[origin])
                    name=arm+'_'+variant;alias_cache[name]=z;digest_cache[name]=digest
                    counts[variant]=check_attack(z,labels[tids],mask,clean_pred,result['all_ASR'][arm][variant])
                checked[arm]['independent_attack_counts']=counts
        assert all(x['public_draw_sha256']==y['public_draw_sha256'] and x['query_draw_sha256']==y['query_draw_sha256']
            for x,y in zip(all_logs[ARMS[0]],all_logs[ARMS[1]]))
        for arm,row in result.get('cases',{}).items():
            if row.get('identity_reference_reused'):assert dec['models'][arm]['identity']
        private=check_private(pair,folder,result,states,a,b,labels,held,tids,mask,baseline,member_receipt)
        for arm,row in private.items():checked[arm].update(row)
        replay=disposable_replay(cls,native,torch.load(hp,map_location='cpu',weights_only=True),public,initial,bank,buckets,folder) if usable else {'skipped_identity_fallback':True}
        if result['state']=='failed_necessary_attack_behavior':
            assert pair=='attack_cover850' and not result['extension_permitted'] and not summary['same850_executed']
            assert result['clean_member_audits']=='skipped_by_preregistered_attack_behavior_stop'
            assert not any(not dec['models'][arm]['identity'] and result['all_ASR'][arm]['selected']['ASR_pct']<=10
                and result['all_ASR'][arm]['selected']['heldout_ASR_pct']<=10 and result['all_ASR'][arm]['selected']['original_label_robustness_gate'] for arm in survivors)
            survivors=[]
        else:
            survivors=[arm for arm in survivors if result['cases'].get(arm,{}).get('necessary_gate',False)]
            if pair==PAIRS[0]:assert summary['large_passed_arms']==survivors
            assert result['extension_permitted']==bool(survivors)
        report['cases'][pair]={'state':result['state'],'arms':checked,'bounded_independent_replay':replay,
            'case_receipt_sha256':core.sha(folder/'COMPLETED.json')}
    for arm in ARMS:
        assert summary['method_necessary_gates'][arm]==all(summary['cases'].get(pair,{}).get('cases',{}).get(arm,{}).get('necessary_gate',False) for pair in PAIRS)
    assert summary['same850_executed']==(PAIRS[2] in summary['cases']) and not torch.cuda.is_initialized()
    sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    with (ROOT/'INDEPENDENT_VERIFICATION.json').open('x',encoding='utf8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
