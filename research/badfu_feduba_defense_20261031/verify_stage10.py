"""Independent state/policy/training-count and ASR/utility/member audit."""
import json
import numpy as np
import torch
import stage05_common as s
from verify_stage09 import np_proxy
from verify_stage05_results import independent_auc


def finite(x):
    if isinstance(x,torch.Tensor):assert torch.isfinite(x).all()
    elif isinstance(x,dict):
        for v in x.values():finite(v)
    elif isinstance(x,(list,tuple)):
        for v in x:finite(v)


def policy(rows,data):
    assert len(rows)==len(data['alphas'])==len(data['candidate_logits'])
    assert data['alphas'][:11]==[i/10 for i in range(11)]
    for r,alpha,z in zip(rows,data['alphas'],data['candidate_logits']):
        v=np_proxy(data['teacher_logits'].numpy(),z.numpy())
        assert alpha==r['alpha'] and v['eligible']==r['eligible']
        assert abs(v['mean_KL']-r['mean_KL'])<1e-10 and abs(v['agreement']-r['agreement'])<1e-12
        assert max(abs(a-b) for a,b in zip(v['class_agreement'],r['class_agreement']))<1e-12
    lo=max(r['alpha'] for r in rows[:11] if r['eligible'])
    if lo==1:assert len(rows)==11
    else:
        assert len(rows)==17;hi=min(r['alpha'] for r in rows[:11] if r['alpha']>lo)
        for r in rows[11:]:
            assert r['alpha']==(lo+hi)/2
            if r['eligible']:lo=r['alpha']
            else:hi=r['alpha']
    return max(r['alpha'] for r in rows if r['eligible'])


def main():
    s.verify_sources();selected,sealed,states=s.snapshot();root=s.HERE/'stage10'
    freeze=s.core.read(s.HERE/'STAGE10_FREEZE.json')
    for n,h in freeze['files'].items():assert s.core.sha(s.HERE/n)==h,n
    parent_audit=s.core.read(s.HERE/'STAGE10_INPUT_AUDIT.json')
    for item in parent_audit['checks_against_previously_preserved_local_receipts']:
        assert s.core.sha(s.HERE/item['name'])==item['sha256']
    top=s.core.read(root/'COMPLETED.json');summary=s.core.read(root/'RESULT.json')
    assert s.core.sha(root/'RESULT.json')==top['result_sha256']
    assert top['source_freeze_sha256']==s.core.sha(s.HERE/'STAGE10_FREEZE.json')
    assert summary['state']=='completed' and summary['CUDA_initialized'] is False
    info=s.core.read(s.HERE/'STAGE03_INPUTS.json');assert s.core.sha(info['clean_path'])==info['clean_path_sha256']
    labels=torch.load(info['clean_path'],map_location='cpu',weights_only=True)['test_y'].numpy()
    held=np.array(s.core.read(s.HERE/'PROXY_SPLIT.json')['heldout_ids'])
    assert s.core.sha(info['record_path'])==info['record_path_sha256']
    record=torch.load(info['record_path'],map_location='cpu',weights_only=False)
    tids=[int(i) for i in record['bd_test']['bd_data_container']['data_dict']]
    assert sorted(tids)==np.flatnonzero(labels!=0).tolist()
    report={'state':'passed','cases':{},'fresh_model_inference':False,'verifier_sha256':s.core.sha(__file__),
            'dependencies':{'np_proxy':s.core.sha(s.HERE/'verify_stage09.py'),'independent_auc':s.core.sha(s.HERE/'verify_stage05_results.py')}}
    cls=sealed.model_class(s.Path(selected['source_root']))
    for pair,case_result in summary['cases'].items():
        folder=root/pair;receipt=s.core.read(folder/'COMPLETED.json')
        for n,h in receipt['files'].items():assert s.core.sha(folder/n)==h,(pair,n)
        result=s.core.read(folder/'RESULT.json');assert result==case_result
        assert s.core.sha(folder/'RESULT.json')==receipt['result_sha256']
        declaration=s.core.read(folder/'SELECTION_BEFORE_PRIVATE_EVALUATION.json')
        assert s.core.sha(folder/'SELECTION_BEFORE_PRIVATE_EVALUATION.json')==result['selection_sha256']
        inputs=s.core.read(folder/'SOURCE_INPUTS.json');a=inputs['pre_role'];b=inputs['post_role'];native=states[b]
        assert inputs['case_id']==selected['case_id'] and inputs['post_sha256']==selected['server_inputs'][b]['sha256']
        assert inputs['teacher_sha256']==s.core.read(s.HERE/'stage05/CANDIDATES_BEFORE_EVALUATION.json')['models'][pair+'_aligned_model.pt']
        bank=torch.load(folder/'private_querybank.pt',map_location='cpu',weights_only=True);finite(bank)
        assert bank['queries'].shape==(256,3,32,32) and float(bank['queries'].min())>=0 and float(bank['queries'].max())<=1
        assert torch.allclose(bank['teacher_prob_T2'].sum(1),torch.ones(256),atol=2e-6)
        query=s.core.read(folder/'QUERYBANK_BEFORE_TRAINING.json')
        assert len(query['logs'])==32 and s.core.sha(folder/'private_querybank.pt')==query['sha256']
        checked={}
        for arm in ['clean_only','query_transfer']:
            raw=declaration['raw_models'][arm];sp=declaration['models'][arm]
            for entry in [raw,sp]:assert s.core.sha(folder/entry['path'])==entry['sha256']
            student=torch.load(folder/raw['path'],map_location='cpu',weights_only=True)
            chosen=torch.load(folder/sp['path'],map_location='cpu',weights_only=True);finite(student);finite(chosen)
            model=cls();model.load_state_dict(student,strict=True);model.load_state_dict(chosen,strict=True)
            for key,value in native.items():
                expected=value+sp['alpha']*(student[key]-value) if value.is_floating_point() else value
                if value.is_floating_point():assert torch.allclose(expected,chosen[key],rtol=2e-6,atol=2e-7),key
                else:assert torch.equal(expected,chosen[key])
                if s.core.is_buffer(key):assert torch.equal(value,student[key]) and torch.equal(value,chosen[key])
            logs=[json.loads(v) for v in (folder/(arm+'_steps.jsonl')).read_text(encoding='utf8').splitlines()]
            assert [v['step'] for v in logs]==list(range(1,101))
            assert all(np.isfinite([v['clean_loss'],v['query_loss'],v['seconds']]).all() for v in logs)
            opt=torch.load(folder/(arm+'_optimizer_rng.pt'),map_location='cpu',weights_only=True);finite(opt)
            assert len(opt['optimizer']['state'])==len(list(model.parameters()))
            assert all(float(v['step'])==100 for v in opt['optimizer']['state'].values())
            proxy=torch.load(folder/('private_'+arm+'_proxy.pt'),map_location='cpu',weights_only=True)
            alpha=policy(declaration['all_points'][arm],proxy)
            assert alpha==sp['alpha']==declaration['choices'][arm]['alpha']
            assert s.core.tensor_digest(chosen)==declaration['choices'][arm]['tensor_sha256']
            arm_report={'steps':100,'alpha':alpha,'policy_points':len(proxy['alphas'])}
            if pair=='attack_cover850':
                counts={}
                for variant,st in [('raw',student),('selected',chosen)]:
                    entry=result['all_ASR'][arm][variant]
                    if entry.get('identity_original_counts_reused'):
                        assert s.core.tensor_digest(st)==s.core.tensor_digest(native)
                        original=next(r for r in s.core.read(s.HERE/'stage03/RESULT.json')['rows'] if r['pair']==pair and r['W']==r['BN']==r['head']==1)
                        n=original['attack_target_n']
                    else:
                        z=torch.load(folder/('private_'+arm+'_'+variant+'_attack.pt'),map_location='cpu',weights_only=True)['attack_logits'];finite(z)
                        assert z.shape==(9000,10);n=int((z.numpy().argmax(1)==0).sum())
                    assert n==entry['target_n'] and entry['n']==9000 and abs(entry['ASR_pct']-n/90)<1e-10
                    counts[variant]=n
                arm_report['independent_ASR_counts']=counts
            checked[arm]=arm_report
        if result['state']=='failed_necessary_ASR':
            assert not result['extension_permitted'] and not summary['same850_executed']
            assert not any(result['all_ASR'][arm]['selected']['ASR_pct']<=10 and declaration['models'][arm]['alpha']>0
                           for arm in summary['large_passed_arms'])
            assert result['clean_member_audits']=='skipped_by_preregistered_ASR_stop'
        else:
            before=s.feature_cache(pair,True);after=s.feature_cache(pair,False)
            pa=s.logits(before['clean'],s.head(states[a])).argmax(1).numpy()
            pb=s.logits(after['clean'],s.head(native)).argmax(1).numpy()
            ny=labels[tids] if pair.startswith('attack') else labels
            baseline=s.core.read(s.HERE/'stage07_cpu_v2/RESULT.json')['cases'][pair]['variants']['native_post']
            old=s.HERE/'stage07_cpu_v2'/('private_'+pair+'_member_features.pt')
            oldreceipt=s.core.read(s.HERE/'stage07_cpu_v2/COMPLETED.json')
            assert s.core.sha(old)==oldreceipt['files'][old.name]
            truth=torch.load(old,map_location='cpu',weights_only=True)['labels'].numpy()
            for arm,row in result['cases'].items():
                if 'deletion_audit' not in row:assert row['necessary_gate'] is False;continue
                data=torch.load(folder/('private_'+arm+'_evaluation.pt'),map_location='cpu',weights_only=True);finite(data)
                cz=data['clean_logits'];mz=data['member_logits'];my=data['member_labels'].numpy();assert np.array_equal(my,truth)
                pred=cz.argmax(1).numpy();candidate_CA=float((pred[held]==labels[held]).mean()*100)
                assert abs(candidate_CA-row['clean']['CA_pct'])<1e-10
                perclass=[float((pred[held][labels[held]==c]==c).mean()*100) for c in range(10)]
                assert max(abs(x-y) for x,y in zip(perclass,row['clean']['class_CA_pct']))<1e-10
                benefit=(pa[held]!=labels[held])&(pb[held]==labels[held])
                assert int(((pred[held]==labels[held])&benefit).sum())==row['clean']['beneficial_kept_n']
                nz=torch.load(folder/('private_'+arm+'_selected_attack.pt'),weights_only=True)['attack_logits'] if pair.startswith('attack') else cz
                ml=mz.log_softmax(1).numpy();nl=nz.log_softmax(1).numpy();weights=np.bincount(my,minlength=10)/len(my)
                scores={};nchecks=0
                for name,ms,ns in [('true_label_logprob',ml[np.arange(len(my)),my],nl[np.arange(len(ny)),ny]),('max_logprob',ml.max(1),nl.max(1))]:
                    auc=[]
                    for c in range(10):
                        v=independent_auc(ms[my==c],ns[ny==c]) if (my==c).any() else .5
                        assert abs(v-row['deletion_audit']['scores'][name]['class_rows'][c]['AUC'])<1e-12
                        auc.append(v);nchecks+=1
                    wa=float(weights@np.asarray(auc));scores[name]={'advantage':2*abs(wa-.5),'weighted_class_advantage':float(weights@(2*np.abs(np.asarray(auc)-.5)))}
                mp=mz.argmax(1).numpy();npred=nz.argmax(1).numpy()
                gap=float(sum(weights[c]*((mp[my==c]==c).mean()-(npred[ny==c]==c).mean()) for c in range(10) if (my==c).any()))
                assert abs(gap-row['deletion_audit']['weighted_accuracy_gap'])<1e-12
                privacy=all(scores[n][k]-baseline['scores'][n][k]<=.04+1e-12 for n in scores for k in scores[n]) and abs(gap)-abs(baseline['weighted_accuracy_gap'])<=.02+1e-12
                drop=float((pb[held]==labels[held]).mean()*100)-candidate_CA
                worst=max(float((pb[held][labels[held]==c]==c).mean()*100)-perclass[c] for c in range(10))
                assert abs(drop-row['overall_drop_pp'])<1e-10 and abs(worst-row['worst_class_drop_pp'])<1e-10
                assert row['necessary_gate']==(drop<=.5+1e-10 and worst<=2+1e-10 and privacy)
                checked[arm]['independent_class_AUC_checks']=nchecks
        report['cases'][pair]={'state':result['state'],'arms':checked}
    for arm in ['clean_only','query_transfer']:
        passed=arm in summary['large_passed_arms'] and all(summary['cases'].get(pair,{}).get('cases',{}).get(arm,{}).get('necessary_gate',False) for pair in ['attack_cover850','benign_same850'])
        assert passed==summary['method_necessary_gates'][arm]
    sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    write_path=root/'INDEPENDENT_VERIFICATION.json'
    write_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
