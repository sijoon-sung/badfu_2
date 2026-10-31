"""Saved-artifact audit; no CNN forward, gradients or training."""
import hashlib,json
from pathlib import Path
import numpy as np
import torch
import stage05_common as s
from verify_stage10 import finite,policy
from verify_stage09 import np_proxy
from verify_stage05_results import independent_auc

core=s.core
ARMS=['teacher_query','post_anchor']
PAIRS=['benign_big19336','attack_cover850','benign_same850']


def pixel_digest(v):
    return hashlib.sha256(v.contiguous().numpy().tobytes()).hexdigest()


def close(a,b,tol=1e-10):
    assert abs(a-b)<=tol,(a,b,tol)


def softmax(a):
    z=a-a.max(1,keepdims=True);z=np.exp(z);return z/z.sum(1,keepdims=True)


def check_attack(z,truth,mask,clean_pred,row):
    """Independent NumPy count arithmetic; deliberately no evaluator helper."""
    pred=z.numpy().argmax(1);assert len(pred)==9000 and int(mask.sum())==8542
    hp=pred[mask];hy=truth[mask];ref=clean_pred[mask]
    counts={'target_n':int((pred==0).sum()),'n':9000,'heldout_target_n':int((hp==0).sum()),
        'heldout_n':8542,'original_label_correct_n':int((pred==truth).sum()),
        'heldout_original_label_correct_n':int((hp==hy).sum())}
    for k,v in counts.items():assert row[k]==v,(k,row[k],v)
    for k,v in [('ASR_pct',100*counts['target_n']/9000),('heldout_ASR_pct',100*counts['heldout_target_n']/8542),
        ('original_label_CA_pct',100*counts['original_label_correct_n']/9000),
        ('heldout_original_label_CA_pct',100*counts['heldout_original_label_correct_n']/8542)]:close(row[k],v)
    per=[100*float((hp[hy==c]==c).mean()) if (hy==c).any() else None for c in range(10)]
    base=[100*float((ref[hy==c]==c).mean()) if (hy==c).any() else None for c in range(10)]
    for a,b in zip(per,row['heldout_original_class_CA_pct']):
        if a is None:assert b is None
        else:close(a,b)
    drop=100*float((ref==hy).mean())-100*counts['heldout_original_label_correct_n']/8542
    worst=max(a-b for a,b in zip(base,per) if a is not None)
    close(row['original_label_drop_from_paired_clean_pp'],drop)
    close(row['worst_original_class_drop_from_paired_clean_pp'],worst)
    gate=drop<=2+1e-10 and worst<=5+1e-10
    assert row['original_label_robustness_gate']==gate
    return {**counts,'quality_gate':gate,'original_class_CA_pct':per}


def check_private(pair,folder,result,states,a,b,labels,held,tids,mask,baseline,member_receipt):
    pre=s.logits(s.feature_cache(pair,True)['clean'],s.head(states[a])).argmax(1).numpy()
    post=s.logits(s.feature_cache(pair,False)['clean'],s.head(states[b])).argmax(1).numpy()
    native_CA=100*float((post[held]==labels[held]).mean())
    native_class=[100*float((post[held][labels[held]==c]==c).mean()) for c in range(10)]
    privacy=baseline['original_interventions'][pair]['native_post']['corrected_heldout_reference']
    benefit=(pre[held]!=labels[held])&(post[held]==labels[held])
    checks={}
    for arm,row in result.get('cases',{}).items():
        if 'deletion_audit' not in row:assert row['necessary_gate'] is False;continue
        if row.get('identity_reference_reused'):
            assert pair!='attack_cover850' and row['identity_tensor_equality']
            assert row['deletion_audit']==privacy and row['necessary_gate'] is True
            close(row['clean']['CA_pct'],native_CA)
            for x,y in zip(row['clean']['class_CA_pct'],native_class):close(x,y)
            assert row['clean']['beneficial_kept_n']==row['clean']['beneficial_n']==int(benefit.sum())
            assert row['overall_drop_pp']==row['worst_class_drop_pp']==row['absolute_accuracy_gap_increase']==0.
            assert all(v==0. for values in row['increase_over_post'].values() for v in values.values())
            checks[arm]={'identity_reference_reused':True,'independent_class_AUC_checks':0}
            continue
        oldpath=s.HERE/'stage07_cpu_v2'/('private_'+pair+'_member_features.pt')
        assert core.sha(oldpath)==member_receipt['files'][oldpath.name]
        truth=torch.load(oldpath,map_location='cpu',weights_only=True)['labels'].numpy()
        data=torch.load(folder/('private_'+arm+'_evaluation.pt'),map_location='cpu',weights_only=True);finite(data)
        cz=data['clean_logits'];mz=data['member_logits'];my=data['member_labels'].numpy()
        assert np.array_equal(my,truth) and len(my)==(9668 if pair=='benign_big19336' else 850)
        pred=cz.numpy().argmax(1);ca=100*float((pred[held]==labels[held]).mean())
        per=[100*float((pred[held][labels[held]==c]==c).mean()) for c in range(10)]
        close(ca,row['clean']['CA_pct'])
        assert row['clean']['correct']==int((pred[held]==labels[held]).sum())
        for x,y in zip(per,row['clean']['class_CA_pct']):close(x,y)
        assert int(((pred[held]==labels[held])&benefit).sum())==row['clean']['beneficial_kept_n']
        if pair=='attack_cover850':
            nz=torch.load(folder/('private_'+arm+'_selected_attack.pt'),map_location='cpu',weights_only=True)['attack_logits'][mask]
            ny=labels[tids][mask]
        else:nz=cz[held];ny=labels[held]
        ml=mz.log_softmax(1).numpy();nl=nz.log_softmax(1).numpy()
        weights=np.bincount(my,minlength=10)/len(my);scores={};nchecks=0
        for name,ms,ns in [('true_label_logprob',ml[np.arange(len(my)),my],nl[np.arange(len(ny)),ny]),
            ('max_logprob',ml.max(1),nl.max(1))]:
            auc=[]
            for k in range(10):
                v=independent_auc(ms[my==k],ns[ny==k]) if (my==k).any() else .5
                close(v,row['deletion_audit']['scores'][name]['class_rows'][k]['AUC'],1e-12)
                auc.append(v);nchecks+=1
            wa=float(weights@np.asarray(auc));scores[name]={'advantage':2*abs(wa-.5),
                'weighted_class_advantage':float(weights@(2*np.abs(np.asarray(auc)-.5)))}
            for measure,val in scores[name].items():
                close(val,row['deletion_audit']['scores'][name][measure],1e-12)
                close(val-privacy['scores'][name][measure],row['increase_over_post'][name][measure],1e-12)
        mp=mz.numpy().argmax(1);npred=nz.numpy().argmax(1)
        gap=float(sum(weights[k]*((mp[my==k]==k).mean()-(npred[ny==k]==k).mean()) for k in range(10) if (my==k).any()))
        close(gap,row['deletion_audit']['weighted_accuracy_gap'],1e-12)
        gapinc=abs(gap)-abs(privacy['weighted_accuracy_gap']);close(gapinc,row['absolute_accuracy_gap_increase'],1e-12)
        privacygate=gapinc<=.02+1e-12 and all(scores[n][m]-privacy['scores'][n][m]<=.04+1e-12 for n in scores for m in scores[n])
        drop=native_CA-ca;worst=max(x-y for x,y in zip(native_class,per))
        close(drop,row['overall_drop_pp']);close(worst,row['worst_class_drop_pp'])
        assert row['necessary_gate']==(drop<=.5+1e-10 and worst<=2+1e-10 and privacygate)
        checks[arm]={'independent_class_AUC_checks':nchecks,'necessary_gate':row['necessary_gate']}
    return checks


def main():
    s.verify_sources();selected,sealed,states=s.snapshot();root=s.HERE/'post_anchor_run'
    vf=core.read(s.HERE/'POST_ANCHOR_VERIFICATION_FREEZE.json')
    for n,h in vf['files'].items():assert core.sha(s.HERE/n)==h,n
    freeze=core.read(s.HERE/'POST_ANCHOR_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    top=core.read(root/'COMPLETED.json');summary=core.read(root/'RESULT.json')
    assert top['result_sha256']==core.sha(root/'RESULT.json')
    assert top['source_freeze_sha256']==core.sha(s.HERE/'POST_ANCHOR_FREEZE.json')
    assert summary['state']=='completed' and summary['CUDA_initialized'] is False
    assert list(summary['cases'])==PAIRS[:len(summary['cases'])]
    info=core.read(s.HERE/'STAGE03_INPUTS.json');assert core.sha(info['clean_path'])==info['clean_path_sha256']
    raw=torch.load(info['clean_path'],map_location='cpu',weights_only=True);labels=raw['test_y'].numpy()
    split=core.read(s.HERE/'PROXY_SPLIT.json');held=np.asarray(split['heldout_ids'])
    assert len(held)==9500 and len(split['fit_ids'])==500 and set(held).isdisjoint(split['fit_ids'])
    public=raw['test_x'][split['fit_ids']].permute(0,3,1,2).float().div(255).contiguous()
    pixels={pixel_digest(v):i for i,v in enumerate(public)}
    assert core.sha(info['record_path'])==info['record_path_sha256']
    record=torch.load(info['record_path'],map_location='cpu',weights_only=False)
    tids=np.asarray([int(i) for i in record['bd_test']['bd_data_container']['data_dict']])
    assert sorted(tids.tolist())==np.flatnonzero(labels!=0).tolist()
    mask=np.isin(tids,held);assert int(mask.sum())==8542
    baseline=core.read(s.HERE/'heldout_reference_audit/RESULT.json')
    member_receipt=core.read(s.HERE/'stage07_cpu_v2/COMPLETED.json')
    cls=sealed.model_class(Path(selected['source_root']))
    report={'state':'passed','cases':{},'fresh_model_inference':False,'all_gradients_recomputed':False,
        'scope':'finished_pipeline','full_objective_achieved':False,'FedUBA_evaluated':False,
        'verifier_sha256':core.sha(__file__),'verification_freeze_sha256':core.sha(s.HERE/'POST_ANCHOR_VERIFICATION_FREEZE.json'),
        'root_result_sha256':core.sha(root/'RESULT.json')}
    survivors=ARMS.copy()
    for pair,result in summary['cases'].items():
        folder=root/pair;receipt=core.read(folder/'COMPLETED.json')
        for n,h in receipt['files'].items():assert core.sha(folder/n)==h,(pair,n)
        assert receipt['result_sha256']==core.sha(folder/'RESULT.json') and result==core.read(folder/'RESULT.json')
        assert result['selection_sha256']==core.sha(folder/'SELECTION_BEFORE_PRIVATE_EVALUATION.json')
        dec=core.read(folder/'SELECTION_BEFORE_PRIVATE_EVALUATION.json')
        assert all(dec[k] is False for k in ['groundtruth_labels_used','member_used','actual_trigger_used','ASR_used'])
        assert dec['common_clean_target']=='native_Post_public'
        assert dec['query_targets']=={'teacher_query':'saved_H5_query','post_anchor':'native_Post_original_anchor'}
        inp=core.read(folder/'SOURCE_INPUTS.json');a=inp['pre_role'];b=inp['post_role'];native=states[b]
        assert inp['case_id']==selected['case_id'] and inp['purpose']=='purification_pilot'
        assert inp['post_sha256']==selected['server_inputs'][b]['sha256']
        assert inp['teacher_sha256']==core.read(s.OUT/'CANDIDATES_BEFORE_EVALUATION.json')['models'][pair+'_aligned_model.pt']
        bm=core.read(folder/'BANK_BEFORE_TRAINING.json');bp=Path(bm['bank_path']);ip=Path(bm['initial_path'])
        brp=Path(receipt['bank_receipt_path']);assert core.sha(brp)==receipt['bank_receipt_sha256']
        bankroot=brp.parent
        expected=s.HERE/'sourcepair_pilot'/pair if pair!=PAIRS[2] else folder/'query_generation'
        assert bankroot.resolve()==expected.resolve() and bp.parent.resolve()==bankroot.resolve()==ip.parent.resolve()
        br=core.read(brp)
        for n,h in br['files'].items():assert core.sha(bankroot/n)==h,(pair,n)
        assert core.sha(bp)==bm['bank_sha256']==br['files'][bp.name]
        assert core.sha(ip)==bm['initial_sha256']==br['files'][ip.name]
        bank=torch.load(bp,map_location='cpu',weights_only=True);initial=torch.load(ip,map_location='cpu',weights_only=True)
        finite(bank);finite(initial)
        src=torch.tensor([c for k in range(10) for c in range(10) if c!=k]);req=torch.arange(10).repeat_interleave(9)
        assert torch.equal(bank['sources'],src) and torch.equal(initial['sources'],src)
        assert torch.equal(bank['requested'],req) and torch.equal(initial['requested'],req)
        assert initial['starts'].shape==bank['queries'].shape==(90,3,32,32)
        assert 0<=bank['queries'].min()<=bank['queries'].max()<=1
        index=np.asarray([pixels[pixel_digest(v)] for v in initial['starts']])
        im=core.read(bankroot/'INITIALS.json');assert im['sha256']==core.sha(ip)
        g=torch.Generator().manual_seed(20261031+1300)
        for c in src.tolist():torch.randint(im['source_pool_counts'][c],(1,),generator=g)
        assert torch.equal(g.get_state(),initial['rng'])
        valid=bank['teacher_logits'].argmax(1)==src;buckets=[torch.where(valid&(src==c))[0] for c in range(10)]
        counts=torch.bincount(bank['teacher_logits'].argmax(1),minlength=10)
        usable=all(len(v)>0 for v in buckets) and int(valid.sum())>=72 and int(counts.max())<=18
        assert bm['source_valid_n']==int(valid.sum()) and bm['source_valid_counts']==[len(v) for v in buckets]
        assert bm['groundtruth_labels_used'] is False
        assert torch.equal((bank['teacher_logits']/2).softmax(1),bank['teacher_prob_T2'])
        checked={};draw_logs={};model_digests={};alias_cache={};public_proxy=None;anchor_reference=None
        if pair=='attack_cover850':
            clean_pred=s.logits(s.feature_cache(pair,False)['clean'],s.head(native)).argmax(1).numpy()[tids]
            ref=result['paired_native_clean_reference'];close(ref['CA_pct'],100*float((clean_pred[mask]==labels[tids][mask]).mean()))
            assert ref['n']==8542
            for c in range(10):
                cm=labels[tids][mask]==c
                if cm.any():close(ref['class_CA_pct'][c],100*float((clean_pred[mask][cm]==c).mean()))
                else:assert ref['class_CA_pct'][c] is None
        for arm in ARMS:
            rd=dec['raw_models'][arm];sd=dec['models'][arm]
            for entry in [rd,sd]:assert core.sha(folder/entry['path'])==entry['sha256']
            student=torch.load(folder/rd['path'],map_location='cpu',weights_only=True)
            chosen=torch.load(folder/sd['path'],map_location='cpu',weights_only=True);finite(student);finite(chosen)
            model=cls();model.load_state_dict(student,strict=True);model.load_state_dict(chosen,strict=True)
            for k,v in native.items():
                ex=v+sd['alpha']*(student[k]-v) if v.is_floating_point() else v
                if v.is_floating_point():assert torch.allclose(chosen[k],ex,rtol=2e-6,atol=2e-7),k
                else:assert torch.equal(chosen[k],ex),k
                if core.is_buffer(k):assert torch.equal(student[k],v) and torch.equal(chosen[k],v),k
            assert sd['identity']==(core.tensor_digest(chosen)==core.tensor_digest(native))
            assert rd['identity_fallback']==(not usable) and rd['steps']==(100 if usable else 0)
            logs=[json.loads(v) for v in (folder/(arm+'_steps.jsonl')).read_text(encoding='utf8').splitlines()]
            nsteps=100 if usable else 0;assert [v['step'] for v in logs]==list(range(1,nsteps+1))
            assert all(v['query_n']==10 and np.isfinite([v['clean_loss'],v['query_loss'],v['seconds']]).all() for v in logs)
            opt=torch.load(folder/(arm+'_optimizer_rng.pt'),map_location='cpu',weights_only=True);finite(opt)
            assert len(opt['optimizer']['state'])==(len(list(model.parameters())) if usable else 0)
            assert all(float(v['step'])==nsteps for v in opt['optimizer']['state'].values())
            group=opt['optimizer']['param_groups'];assert len(group)==1 and group[0]['lr']==.0001 and group[0]['weight_decay']==0
            gf=torch.Generator().manual_seed(20261031+901);gq=torch.Generator().manual_seed(20261031+902)
            first_q=None
            for row in logs:
                ix=torch.randint(500,(32,),generator=gf)
                qi=torch.stack([bucket[torch.randint(len(bucket),(1,),generator=gq)[0]] for bucket in buckets])
                assert pixel_digest(ix)==row['public_draw_sha256'] and pixel_digest(qi)==row['query_draw_sha256']
                if first_q is None:first_q=qi.numpy()
            assert torch.equal(gf.get_state(),opt['public_sampler_rng']) and torch.equal(gq.get_state(),opt['query_sampler_rng'])
            draw_logs[arm]=logs
            px=torch.load(folder/('private_'+arm+'_proxy.pt'),map_location='cpu',weights_only=True);finite(px)
            if public_proxy is None:
                public_proxy=px['teacher_logits'];anchor_reference=softmax(public_proxy.numpy()[index]/2)
            else:assert torch.equal(public_proxy,px['teacher_logits'])
            assert np.array_equal(anchor_reference.argmax(1),src.numpy())
            if usable:alpha=policy(dec['all_points'][arm],px)
            else:
                assert px['alphas']==[0.] and len(dec['all_points'][arm])==1
                calc=np_proxy(px['teacher_logits'].numpy(),px['candidate_logits'][0].numpy())
                assert calc['eligible'] and dec['all_points'][arm][0]['eligible'];alpha=0.
            assert alpha==sd['alpha']==dec['choices'][arm]['alpha']
            assert core.tensor_digest(chosen)==dec['choices'][arm]['tensor_sha256']
            diag=torch.load(folder/('private_'+arm+'_bank_diagnostic.pt'),map_location='cpu',weights_only=True);finite(diag)
            assert torch.equal(diag['source_valid_mask'],valid) and diag['query_logits'].shape==(90,10)
            ap=diag['native_anchor_prob_T2'].numpy()
            anchor_error=float(np.abs(ap-anchor_reference).max());assert anchor_error<=2e-5,anchor_error
            assert np.array_equal(ap.argmax(1),src.numpy())
            loss_error=None
            if usable:
                desired=bank['teacher_prob_T2'].numpy() if arm=='teacher_query' else ap
                q=desired[first_q].astype(np.float64);z=bank['post_logits'].numpy()[first_q].astype(np.float64)/2
                z-=z.max(1,keepdims=True);lp=z-np.log(np.exp(z).sum(1,keepdims=True))
                expected_loss=4*float(np.where(q>0,q*(np.log(np.maximum(q,np.finfo(float).tiny))-lp),0).sum(1).mean())
                loss_error=abs(expected_loss-logs[0]['query_loss']);assert loss_error<=1e-3,loss_error
            checked[arm]={'steps':nsteps,'alpha':alpha,'policy_points':len(px['alphas']),
                'anchor_probability_max_abs_error':anchor_error,'first_query_loss_abs_error':loss_error,
                'identity':sd['identity']}
            if pair=='attack_cover850':
                c={}
                for variant,st in [('raw',student),('selected',chosen)]:
                    stored=torch.load(folder/('private_'+arm+'_'+variant+'_attack.pt'),map_location='cpu',weights_only=True)
                    z=stored['attack_logits'];finite(z);assert z.shape==(9000,10)
                    digest=core.tensor_digest(st);name=arm+'_'+variant;origin=stored['reused_from']
                    assert origin==result['all_ASR'][arm][variant]['reused_logits_from']
                    if origin=='identity_original_cache':
                        assert digest==core.tensor_digest(native)
                        assert torch.equal(z,s.logits(s.feature_cache(pair,False)['attack'],s.head(native)))
                    elif origin is not None:
                        assert origin in alias_cache and digest==model_digests[origin] and torch.equal(z,alias_cache[origin])
                    elif digest in model_digests.values():raise AssertionError('identical model duplicated instead of alias')
                    alias_cache[name]=z;model_digests[name]=digest
                    c[variant]=check_attack(z,labels[tids],mask,clean_pred,result['all_ASR'][arm][variant])
                checked[arm]['independent_attack_counts']=c
        assert all(x['public_draw_sha256']==y['public_draw_sha256'] and x['query_draw_sha256']==y['query_draw_sha256']
            for x,y in zip(draw_logs[ARMS[0]],draw_logs[ARMS[1]]))
        assert len(draw_logs[ARMS[0]])==len(draw_logs[ARMS[1]])
        for arm,row in result.get('cases',{}).items():
            if row.get('identity_reference_reused'):assert dec['models'][arm]['identity']
        private=check_private(pair,folder,result,states,a,b,labels,held,tids,mask,baseline,member_receipt)
        for arm,row in private.items():checked[arm].update(row)
        if result['state']=='failed_necessary_attack_behavior':
            assert pair=='attack_cover850' and not result['extension_permitted'] and not summary['same850_executed']
            assert result['clean_member_audits']=='skipped_by_preregistered_attack_behavior_stop'
            assert not any(not dec['models'][arm]['identity'] and result['all_ASR'][arm]['selected']['ASR_pct']<=10
                and result['all_ASR'][arm]['selected']['heldout_ASR_pct']<=10
                and result['all_ASR'][arm]['selected']['original_label_robustness_gate'] for arm in survivors)
            survivors=[]
        else:
            survivors=[arm for arm in survivors if result['cases'].get(arm,{}).get('necessary_gate',False)]
            if pair==PAIRS[0]:assert summary['large_passed_arms']==survivors
            assert result['extension_permitted']==bool(survivors)
        report['cases'][pair]={'state':result['state'],'arms':checked,'source_valid_n':int(valid.sum()),
            'case_receipt_sha256':core.sha(folder/'COMPLETED.json')}
    for arm in ARMS:
        passed=all(summary['cases'].get(pair,{}).get('cases',{}).get(arm,{}).get('necessary_gate',False) for pair in PAIRS)
        assert summary['method_necessary_gates'][arm]==passed
    assert summary['same850_executed']==(PAIRS[2] in summary['cases'])
    assert not torch.cuda.is_initialized();sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    with (root/'INDEPENDENT_VERIFICATION.json').open('x',encoding='utf8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
