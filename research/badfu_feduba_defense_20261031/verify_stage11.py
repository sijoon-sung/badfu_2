"""Audit completed matched-query artifacts without fresh model inference."""
import hashlib,json
from pathlib import Path
import numpy as np
import torch
import stage05_common as s
from verify_stage10 import finite,policy
from verify_stage05_results import independent_auc

ARMS=['matched_kl','all_class_disjoint']
PAIRS=['benign_big19336','attack_cover850','benign_same850']


def main():
    s.verify_sources();selected,sealed,states=s.snapshot();root=s.HERE/'stage11'
    vf=s.core.read(s.HERE/'STAGE11_VERIFICATION_FREEZE.json')
    for n,h in vf['files'].items():assert s.core.sha(s.HERE/n)==h,n
    freeze=s.core.read(s.HERE/'STAGE11_FREEZE.json')
    for n,h in freeze['files'].items():assert s.core.sha(s.HERE/n)==h,n
    top=s.core.read(root/'COMPLETED.json');summary=s.core.read(root/'RESULT.json')
    assert top['result_sha256']==s.core.sha(root/'RESULT.json')
    assert top['source_freeze_sha256']==s.core.sha(s.HERE/'STAGE11_FREEZE.json')
    assert summary['state']=='completed' and summary['CUDA_initialized'] is False
    assert list(summary['cases'])==PAIRS[:len(summary['cases'])]
    info=s.core.read(s.HERE/'STAGE03_INPUTS.json')
    assert s.core.sha(info['clean_path'])==info['clean_path_sha256']
    labels=torch.load(info['clean_path'],map_location='cpu',weights_only=True)['test_y'].numpy()
    split=s.core.read(s.HERE/'PROXY_SPLIT.json');held=np.asarray(split['heldout_ids'])
    assert len(held)==9500 and set(held).isdisjoint(split['fit_ids'])
    assert s.core.sha(info['record_path'])==info['record_path_sha256']
    record=torch.load(info['record_path'],map_location='cpu',weights_only=False)
    tids=np.asarray([int(i) for i in record['bd_test']['bd_data_container']['data_dict']])
    assert sorted(tids.tolist())==np.flatnonzero(labels!=0).tolist()
    heldmask=np.isin(tids,held);assert int(heldmask.sum())==8542
    cls=sealed.model_class(Path(selected['source_root']))
    baseline=s.core.read(s.HERE/'heldout_reference_audit/RESULT.json')
    prior_members=s.core.read(s.HERE/'stage07_cpu_v2/COMPLETED.json')
    report={'state':'passed','cases':{},'fresh_model_inference':False,
            'verifier_sha256':s.core.sha(__file__),'verification_freeze_sha256':s.core.sha(s.HERE/'STAGE11_VERIFICATION_FREEZE.json')}
    survivors=ARMS.copy()
    for pair,result in summary['cases'].items():
        folder=root/pair;receipt=s.core.read(folder/'COMPLETED.json')
        for n,h in receipt['files'].items():assert s.core.sha(folder/n)==h,(pair,n)
        assert receipt['result_sha256']==s.core.sha(folder/'RESULT.json')
        assert result==s.core.read(folder/'RESULT.json')
        assert result['selection_sha256']==s.core.sha(folder/'SELECTION_BEFORE_PRIVATE_EVALUATION.json')
        declaration=s.core.read(folder/'SELECTION_BEFORE_PRIVATE_EVALUATION.json')
        assert all(declaration[k] is False for k in ['groundtruth_labels_used','member_used','actual_trigger_used','ASR_used'])
        inp=s.core.read(folder/'SOURCE_INPUTS.json');a=inp['pre_role'];b=inp['post_role'];native=states[b]
        assert inp['case_id']==selected['case_id'] and inp['purpose']=='purification_pilot'
        assert inp['post_sha256']==selected['server_inputs'][b]['sha256']
        assert inp['teacher_sha256']==s.core.read(s.HERE/'stage05/CANDIDATES_BEFORE_EVALUATION.json')['models'][pair+'_aligned_model.pt']
        initial=torch.load(folder/'private_shared_initials.pt',map_location='cpu',weights_only=True);finite(initial)
        contract=s.core.read(folder/'INITIAL_BANK_CONTRACT.json')
        assert contract['sha256']==s.core.sha(folder/'private_shared_initials.pt') and contract['groundtruth_labels_used'] is False
        assert initial['starts'].shape==(240,3,32,32) and 0<=initial['starts'].min()<=initial['starts'].max()<=1
        requested=torch.tensor([batch%10 for batch in range(30) for _ in range(8)])
        assert torch.equal(initial['requested_classes'],requested)
        assert contract['requested_count_per_output']==[24]*10
        generation=s.core.read(folder/'QUERYBANKS_BEFORE_TRAINING.json');checked={};saved_logs={}
        for arm in ARMS:
            meta=generation[arm];bank_path=folder/('private_'+arm+'_querybank.pt')
            assert meta['sha256']==s.core.sha(bank_path)
            bank=torch.load(bank_path,map_location='cpu',weights_only=True);finite(bank)
            assert torch.equal(bank['requested_classes'],requested)
            assert bank['queries'].shape==(240,3,32,32) and 0<=bank['queries'].min()<=bank['queries'].max()<=1
            assert bank['post_logits'].shape==bank['teacher_prob_T2'].shape==(240,10)
            assert float(bank['teacher_prob_T2'].min())>=0 and torch.allclose(bank['teacher_prob_T2'].sum(1),torch.ones(240),atol=2e-6)
            assert meta['n']==240 and meta['inner_steps']==600 and meta['image_gradient_evaluations']==4800
            assert [v['batch'] for v in meta['logs']]==list(range(30))
            pp=bank['post_logits'].argmax(1);tp=bank['teacher_prob_T2'].argmax(1)
            assert meta['nativepost_class_counts']==torch.bincount(pp,minlength=10).tolist()
            assert meta['teacher_class_counts']==torch.bincount(tp,minlength=10).tolist()
            for batch,row in enumerate(meta['logs']):
                k=batch%10;lo=batch*8;hi=lo+8
                assert row['requested_class']==k and row['inner_steps']==20
                assert row['joint_success_n']==int(((pp[lo:hi]==k)&(tp[lo:hi]!=k)).sum())
            successes=[int(((requested==k)&(pp==k)&(tp!=k)).sum()) for k in range(10)]
            assert successes==meta['joint_success_per_requested_class']
            raw=declaration['raw_models'][arm];chosen_entry=declaration['models'][arm]
            for entry in [raw,chosen_entry]:assert s.core.sha(folder/entry['path'])==entry['sha256']
            student=torch.load(folder/raw['path'],map_location='cpu',weights_only=True)
            chosen=torch.load(folder/chosen_entry['path'],map_location='cpu',weights_only=True);finite(student);finite(chosen)
            model=cls();model.load_state_dict(student,strict=True);model.load_state_dict(chosen,strict=True)
            for key,value in native.items():
                expected=value+chosen_entry['alpha']*(student[key]-value) if value.is_floating_point() else value
                if value.is_floating_point():assert torch.allclose(expected,chosen[key],rtol=2e-6,atol=2e-7),key
                else:assert torch.equal(expected,chosen[key])
                if s.core.is_buffer(key):assert torch.equal(value,student[key]) and torch.equal(value,chosen[key])
            logs=[json.loads(v) for v in (folder/(arm+'_steps.jsonl')).read_text(encoding='utf8').splitlines()]
            assert [v['step'] for v in logs]==list(range(1,101))
            assert all(v['query_n']==10 and np.isfinite([v['clean_loss'],v['query_loss'],v['seconds']]).all() for v in logs)
            saved_logs[arm]=logs
            opt=torch.load(folder/(arm+'_optimizer_rng.pt'),map_location='cpu',weights_only=True);finite(opt)
            assert len(opt['optimizer']['state'])==len(list(model.parameters()))
            assert all(float(v['step'])==100 for v in opt['optimizer']['state'].values())
            gf=torch.Generator().manual_seed(20261031+901);gq=torch.Generator().manual_seed(20261031+902)
            buckets=[torch.where(requested==k)[0] for k in range(10)]
            for row in logs:
                ix=torch.randint(500,(32,),generator=gf);draws=torch.randint(24,(10,),generator=gq)
                qi=torch.stack([buckets[k][draws[k]] for k in range(10)])
                assert hashlib.sha256(ix.numpy().tobytes()).hexdigest()==row['public_draw_sha256']
                assert hashlib.sha256(qi.numpy().tobytes()).hexdigest()==row['query_draw_sha256']
            assert torch.equal(gf.get_state(),opt['public_sampler_rng']) and torch.equal(gq.get_state(),opt['query_sampler_rng'])
            proxy=torch.load(folder/('private_'+arm+'_proxy.pt'),map_location='cpu',weights_only=True)
            alpha=policy(declaration['all_points'][arm],proxy)
            assert alpha==chosen_entry['alpha']==declaration['choices'][arm]['alpha']
            assert s.core.tensor_digest(chosen)==declaration['choices'][arm]['tensor_sha256']
            diag=torch.load(folder/('private_'+arm+'_bank_diagnostic.pt'),map_location='cpu',weights_only=True);finite(diag)
            qz=diag['query_logits'];assert qz.shape==(240,10)
            row_report={'steps':100,'alpha':alpha,'policy_points':len(proxy['alphas']),
                        'query_joint_success_per_requested_class':successes,
                        'raw_teacher_bank_agreement':float((qz.argmax(1)==tp).double().mean())}
            if pair.startswith('attack'):
                counts={}
                for variant,st in [('raw',student),('selected',chosen)]:
                    entry=result['all_ASR'][arm][variant]
                    if entry.get('identity_original_counts_reused'):
                        assert s.core.tensor_digest(st)==s.core.tensor_digest(native)
                        z=s.logits(s.feature_cache(pair,False)['attack'],s.head(native))
                    else:z=torch.load(folder/('private_'+arm+'_'+variant+'_attack.pt'),map_location='cpu',weights_only=True)['attack_logits']
                    finite(z);assert z.shape==(9000,10)
                    n=int((z.numpy().argmax(1)==0).sum());hn=int((z.numpy().argmax(1)[heldmask]==0).sum())
                    assert entry['target_n']==n and entry['n']==9000 and abs(entry['ASR_pct']-n/90)<1e-10
                    assert entry['heldout_target_n']==hn and entry['heldout_n']==8542 and abs(entry['heldout_ASR_pct']-100*hn/8542)<1e-10
                    counts[variant]={'full_n':n,'heldout_n':hn}
                row_report['independent_ASR_counts']=counts
            checked[arm]=row_report
        assert all(x['public_draw_sha256']==y['public_draw_sha256'] and x['query_draw_sha256']==y['query_draw_sha256']
                   for x,y in zip(saved_logs[ARMS[0]],saved_logs[ARMS[1]]))
        if result['state']=='failed_necessary_ASR':
            assert pair=='attack_cover850' and not result['extension_permitted'] and not summary['same850_executed']
            assert result['clean_member_audits']=='skipped_by_preregistered_ASR_stop'
            assert not any(declaration['models'][arm]['alpha']>0 and result['all_ASR'][arm]['selected']['ASR_pct']<=10
                and result['all_ASR'][arm]['selected']['heldout_ASR_pct']<=10 for arm in survivors)
            survivors=[]
        else:
            pre=s.logits(s.feature_cache(pair,True)['clean'],s.head(states[a])).argmax(1).numpy()
            post=s.logits(s.feature_cache(pair,False)['clean'],s.head(native)).argmax(1).numpy()
            oldpath=s.HERE/'stage07_cpu_v2'/('private_'+pair+'_member_features.pt')
            assert s.core.sha(oldpath)==prior_members['files'][oldpath.name]
            truth=torch.load(oldpath,map_location='cpu',weights_only=True)['labels'].numpy()
            base=baseline['original_interventions'][pair]['native_post']['corrected_heldout_reference']
            for arm,row in result['cases'].items():
                if 'deletion_audit' not in row:assert row['necessary_gate'] is False;continue
                data=torch.load(folder/('private_'+arm+'_evaluation.pt'),map_location='cpu',weights_only=True);finite(data)
                cz=data['clean_logits'];mz=data['member_logits'];my=data['member_labels'].numpy()
                assert np.array_equal(my,truth) and len(my)==(9668 if pair=='benign_big19336' else 850)
                pred=cz.numpy().argmax(1);ca=100*float((pred[held]==labels[held]).mean())
                perclass=[100*float((pred[held][labels[held]==k]==k).mean()) for k in range(10)]
                assert abs(ca-row['clean']['CA_pct'])<1e-10
                assert max(abs(x-y) for x,y in zip(perclass,row['clean']['class_CA_pct']))<1e-10
                benefit=(pre[held]!=labels[held])&(post[held]==labels[held])
                assert int(((pred[held]==labels[held])&benefit).sum())==row['clean']['beneficial_kept_n']
                if pair.startswith('attack'):
                    nz=torch.load(folder/('private_'+arm+'_selected_attack.pt'),map_location='cpu',weights_only=True)['attack_logits'][heldmask]
                    ny=labels[tids][heldmask]
                else:nz=cz[held];ny=labels[held]
                ml=mz.log_softmax(1).numpy();nl=nz.log_softmax(1).numpy()
                weights=np.bincount(my,minlength=10)/len(my);scores={};nchecks=0
                for name,ms,ns in [('true_label_logprob',ml[np.arange(len(my)),my],nl[np.arange(len(ny)),ny]),('max_logprob',ml.max(1),nl.max(1))]:
                    auc=[]
                    for k in range(10):
                        v=independent_auc(ms[my==k],ns[ny==k]) if (my==k).any() else .5
                        assert abs(v-row['deletion_audit']['scores'][name]['class_rows'][k]['AUC'])<1e-12
                        auc.append(v);nchecks+=1
                    wa=float(weights@np.asarray(auc));scores[name]={'advantage':2*abs(wa-.5),'weighted_class_advantage':float(weights@(2*np.abs(np.asarray(auc)-.5)))}
                    for measure,val in scores[name].items():
                        assert abs(val-row['deletion_audit']['scores'][name][measure])<1e-12
                        assert abs(val-base['scores'][name][measure]-row['increase_over_post'][name][measure])<1e-12
                mp=mz.numpy().argmax(1);npred=nz.numpy().argmax(1)
                gap=float(sum(weights[k]*((mp[my==k]==k).mean()-(npred[ny==k]==k).mean()) for k in range(10) if (my==k).any()))
                assert abs(gap-row['deletion_audit']['weighted_accuracy_gap'])<1e-12
                gapinc=abs(gap)-abs(base['weighted_accuracy_gap']);assert abs(gapinc-row['absolute_accuracy_gap_increase'])<1e-12
                privacy=gapinc<=.02+1e-12 and all(scores[n][m]-base['scores'][n][m]<=.04+1e-12 for n in scores for m in scores[n])
                drop=100*float((post[held]==labels[held]).mean())-ca
                worst=max(100*float((post[held][labels[held]==k]==k).mean())-perclass[k] for k in range(10))
                assert abs(drop-row['overall_drop_pp'])<1e-10 and abs(worst-row['worst_class_drop_pp'])<1e-10
                assert row['necessary_gate']==(drop<=.5+1e-10 and worst<=2+1e-10 and privacy)
                checked[arm]['independent_class_AUC_checks']=nchecks
            survivors=[arm for arm in survivors if result['cases'].get(arm,{}).get('necessary_gate',False)]
            if pair==PAIRS[0]:assert summary['large_passed_arms']==survivors
            assert result['extension_permitted']==bool(survivors)
        report['cases'][pair]={'state':result['state'],'arms':checked}
    for arm in ARMS:
        passed=all(summary['cases'].get(pair,{}).get('cases',{}).get(arm,{}).get('necessary_gate',False) for pair in PAIRS)
        assert passed==summary['method_necessary_gates'][arm]
    assert summary['same850_executed']==(PAIRS[2] in summary['cases'])
    assert not torch.cuda.is_initialized();sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    path=root/'INDEPENDENT_VERIFICATION.json'
    with path.open('x',encoding='utf8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
