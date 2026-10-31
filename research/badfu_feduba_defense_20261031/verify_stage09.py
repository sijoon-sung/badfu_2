"""Independent proxy policy/tensor path and deleted-member metric verification."""
import json
import numpy as np
import torch
import stage05_common as s
from verify_stage05_results import independent_auc


def np_proxy(teacher,z):
    def logs(a):
        a=a-a.max(1,keepdims=True);return a-np.log(np.exp(a).sum(1,keepdims=True))
    t=logs(teacher);v=logs(z);a=teacher.argmax(1);b=z.argmax(1)
    kl=max(0.,float((np.exp(t)*(t-v)).sum(1).mean()))
    agreement=float((a==b).mean());classes=[float((b[a==c]==c).mean()) if (a==c).any() else 1. for c in range(10)]
    return {'mean_KL':kl,'agreement':agreement,'class_agreement':classes,
            'eligible':kl<=.010+1e-12 and agreement>=.98-1e-12 and min(classes)>=.95-1e-12}


def main():
    s.verify_sources();selected,sealed,states=s.snapshot();out=s.HERE/'stage09'
    freeze=s.core.read(s.HERE/'STAGE09_FREEZE.json')
    for n,h in freeze['files'].items():assert s.core.sha(s.HERE/n)==h,n
    receipt=s.core.read(out/'COMPLETED.json')
    for n,h in receipt['files'].items():assert s.core.sha(out/n)==h,n
    result=s.core.read(out/'RESULT.json');assert s.core.sha(out/'RESULT.json')==receipt['result_sha256']
    declaration=s.core.read(out/'SELECTION_BEFORE_PRIVATE_EVALUATION.json')
    assert s.core.sha(out/'SELECTION_BEFORE_PRIVATE_EVALUATION.json')==result['selection_sha256']
    parent=s.core.read(s.HERE/'stage08/MODELS_BEFORE_PRIVATE_EVALUATION.json')
    info=s.core.read(s.HERE/'STAGE03_INPUTS.json');assert s.core.sha(info['clean_path'])==info['clean_path_sha256']
    y=torch.load(info['clean_path'],map_location='cpu',weights_only=True)['test_y'].numpy()
    held=np.array(s.core.read(s.HERE/'PROXY_SPLIT.json')['heldout_ids'])
    pre=s.feature_cache('benign_big19336',True);post=s.feature_cache('benign_big19336',False)
    a=s.logits(pre['clean'],s.head(states['clean_pre'])).argmax(1).numpy()
    b=s.logits(post['clean'],s.head(states['clean_big_post'])).argmax(1).numpy()
    old=s.core.read(s.HERE/'stage07_cpu_v2/COMPLETED.json')
    oldp=s.HERE/'stage07_cpu_v2/private_benign_big19336_member_features.pt'
    assert s.core.sha(oldp)==old['files'][oldp.name]
    my=torch.load(oldp,map_location='cpu',weights_only=True)['labels'].numpy()
    baseline=s.core.read(s.HERE/'stage07_cpu_v2/RESULT.json')['cases']['benign_big19336']['variants']['native_post']
    report={'state':'passed','arms':{},'verifier_sha256':s.core.sha(__file__),'fresh_model_inference':False}
    for arm in ['clean_only','query_transfer']:
        px=torch.load(out/('private_'+arm+'_proxy.pt'),map_location='cpu',weights_only=True)
        rows=declaration['all_points'][arm];assert len(rows)==len(px['alphas'])==len(px['candidate_logits'])
        assert px['alphas'][:11]==[i/10 for i in range(11)]
        checked=[]
        for row,alpha,z in zip(rows,px['alphas'],px['candidate_logits']):
            calc=np_proxy(px['teacher_logits'].numpy(),z.numpy())
            assert alpha==row['alpha'] and calc['eligible']==row['eligible']
            for key in ['mean_KL','agreement']:assert abs(calc[key]-row[key])<1e-10
            assert max(abs(x-y) for x,y in zip(calc['class_agreement'],row['class_agreement']))<1e-10
            checked.append({'alpha':alpha,**calc})
        first=max(r['alpha'] for r in checked[:11] if r['eligible'])
        if first==1:assert len(checked)==11
        else:
            assert len(checked)==17;lo=first;hi=min(r['alpha'] for r in checked[:11] if r['alpha']>lo)
            for row in checked[11:]:
                assert row['alpha']==(lo+hi)/2
                if row['eligible']:lo=row['alpha']
                else:hi=row['alpha']
        chosen=max(r['alpha'] for r in checked if r['eligible'])
        assert chosen==declaration['choices'][arm]['alpha']==declaration['models'][arm]['alpha']
        pp=s.HERE/'stage08'/parent[arm]['path'];assert s.core.sha(pp)==parent[arm]['sha256']
        student=torch.load(pp,map_location='cpu',weights_only=True)
        path=out/declaration['models'][arm]['path'];assert s.core.sha(path)==declaration['models'][arm]['sha256']
        st=torch.load(path,map_location='cpu',weights_only=True)
        native=states['clean_big_post']
        # Independent elementwise state formula; all-close allows lerp rounding.
        for key,value in native.items():
            expected=value+chosen*(student[key]-value) if value.is_floating_point() else value
            assert torch.isfinite(st[key]).all()
            if value.is_floating_point():assert torch.allclose(st[key],expected,rtol=2e-6,atol=2e-7),key
            else:assert torch.equal(st[key],expected)
            if s.core.is_buffer(key):assert torch.equal(st[key],value)
        model=sealed.model_class(s.Path(selected['source_root']))();model.load_state_dict(st,strict=True)
        row=result['cases'][arm]
        if chosen==0:
            assert row['identity'] and row['necessary_gate'] is False
            report['arms'][arm]={'selected_alpha':0,'policy_checks':len(checked),'identity':True};continue
        data=torch.load(out/('private_'+arm+'_evaluation.pt'),map_location='cpu',weights_only=True)
        assert np.array_equal(data['member_labels'].numpy(),my)
        cz=data['clean_logits'];mz=data['member_logits'];pred=cz.argmax(1).numpy();mp=mz.argmax(1).numpy()
        assert int((pred[held]==y[held]).sum())==row['clean']['correct']
        for c in range(10):assert abs(float((pred[held][y[held]==c]==c).mean()*100)-row['clean']['class_CA_pct'][c])<1e-10
        beneficial=(a[held]!=y[held])&(b[held]==y[held])
        assert int(((pred[held]==y[held])&beneficial).sum())==row['clean']['beneficial_kept_n']
        ml=mz.log_softmax(1).numpy();nl=cz.log_softmax(1).numpy();weights=np.bincount(my,minlength=10)/len(my)
        scores={};auc_checks=0
        for name,ms,ns in [('true_label_logprob',ml[np.arange(len(my)),my],nl[np.arange(len(y)),y]),('max_logprob',ml.max(1),nl.max(1))]:
            auc=[]
            for c in range(10):
                v=independent_auc(ms[my==c],ns[y==c]);assert abs(v-row['deletion_audit']['scores'][name]['class_rows'][c]['AUC'])<1e-12
                auc.append(v);auc_checks+=1
            wa=float(weights@np.asarray(auc));scores[name]={'advantage':2*abs(wa-.5),'weighted_class_advantage':float(weights@(2*np.abs(np.asarray(auc)-.5)))}
        gap=float(sum(weights[c]*((mp[my==c]==c).mean()-(pred[y==c]==c).mean()) for c in range(10)))
        assert abs(gap-row['deletion_audit']['weighted_accuracy_gap'])<1e-12
        privacy=all(scores[n][k]-baseline['scores'][n][k]<=.04+1e-12 for n in scores for k in scores[n]) and abs(gap)-abs(baseline['weighted_accuracy_gap'])<=.02+1e-12
        candidate_CA=float((pred[held]==y[held]).mean()*100)
        assert abs(candidate_CA-row['clean']['CA_pct'])<1e-10
        drop=float((b[held]==y[held]).mean()*100)-candidate_CA
        worst=max(float((b[held][y[held]==c]==c).mean()*100)-row['clean']['class_CA_pct'][c] for c in range(10))
        assert abs(drop-row['overall_drop_pp'])<1e-10 and abs(worst-row['worst_class_drop_pp'])<1e-10
        expected_gate=drop<=.5+1e-10 and worst<=2+1e-10 and privacy
        assert expected_gate==row['necessary_gate']
        report['arms'][arm]={'selected_alpha':chosen,'policy_checks':len(checked),'independent_class_AUC_checks':auc_checks,
                             'necessary_gate':expected_gate,'strict_prior_correction_fraction':row['clean']['beneficial_kept_fraction']}
    sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    s.core.OUT=out;s.core.write('INDEPENDENT_VERIFICATION.json',report);print(json.dumps(report),flush=True)


if __name__=='__main__':main()
