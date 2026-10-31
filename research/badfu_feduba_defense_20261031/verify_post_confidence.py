"""Independent row permutations/policy/counts and fixed-label-provider ceiling."""
import json,os,time
import numpy as np
import torch
import stage05_common as s
from sourcepair_pilot import cpu_guard
from verify_stage09 import np_proxy
from verify_post_anchor import check_attack,softmax,close
core=s.core;ROOT=s.HERE/'post_confidence_pilot'


def check(z,post,teacher,threshold,stored_mask=None):
    p=post.numpy();t=teacher.numpy();actual=z.numpy();confidence=softmax(p).max(1)
    a=p.argmax(1);b=t.argmax(1);expected=(a!=b)&(confidence>=threshold) if threshold is not None else np.zeros(len(p),dtype=bool)
    observed=(actual!=p).any(1) if stored_mask is None else stored_mask.numpy()
    boundary=int((expected!=observed).sum())
    if boundary:
        assert threshold is not None and np.max(np.abs(confidence[expected!=observed]-threshold))<=1e-12
    reference=p.copy()
    for i in np.flatnonzero(observed):reference[i,a[i]],reference[i,b[i]]=p[i,b[i]],p[i,a[i]]
    assert np.array_equal(reference,actual) and np.array_equal(np.sort(actual,axis=1),np.sort(p,axis=1))
    return boundary


def main():
    s.verify_sources();cpu=cpu_guard();freeze=core.read(s.HERE/'POST_CONFIDENCE_DIAGNOSIS_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    original=core.read(s.HERE/'POST_CONFIDENCE_FREEZE.json')
    for n,h in original['files'].items():assert core.sha(s.HERE/n)==h,n
    top=core.read(ROOT/'COMPLETED.json');result=core.read(ROOT/'RESULT.json')
    assert top['result_sha256']==core.sha(ROOT/'RESULT.json') and top['source_freeze_sha256']==core.sha(s.HERE/'POST_CONFIDENCE_FREEZE.json')
    assert result['state']=='completed';selected,sealed,states=s.snapshot()
    info=core.read(s.HERE/'STAGE03_INPUTS.json');assert core.sha(info['clean_path'])==info['clean_path_sha256']
    labels=torch.load(info['clean_path'],map_location='cpu',weights_only=True)['test_y'].numpy()
    assert core.sha(info['record_path'])==info['record_path_sha256'];record=torch.load(info['record_path'],map_location='cpu',weights_only=False)
    tids=np.asarray([int(i) for i in record['bd_test']['bd_data_container']['data_dict']]);held=np.asarray(core.read(s.HERE/'PROXY_SPLIT.json')['heldout_ids']);mask=np.isin(tids,held)
    report={'state':'passed_saved_output_diagnosis','pid':os.getpid(),'CPU':cpu,'cases':{},'new_CNN_or_training':False,
        'root_result_sha256':core.sha(ROOT/'RESULT.json'),'source_freeze_sha256':core.sha(s.HERE/'POST_CONFIDENCE_DIAGNOSIS_FREEZE.json')}
    for pair,rows in result['cases'].items():
        root=ROOT/pair;receipt=core.read(root/'COMPLETED.json')
        for n,h in receipt['files'].items():assert core.sha(root/n)==h,(pair,n)
        assert receipt['result_sha256']==core.sha(root/'RESULT.json') and rows==core.read(root/'RESULT.json')
        config=core.read(root/'CONFIG_BEFORE_PRIVATE_EVALUATION.json');assert rows['selection_sha256']==core.sha(root/'CONFIG_BEFORE_PRIVATE_EVALUATION.json')
        public=torch.load(root/'private_public_calibration.pt',map_location='cpu',weights_only=True)
        assert config['public_evidence_sha256']==core.sha(root/'private_public_calibration.pt')
        conf=softmax(public['post_logits'].numpy()).max(1);boundary=0;passing=[]
        for i,(p,z) in enumerate(zip(config['points'],public['candidate_logits'])):
            tau=float(np.quantile(conf,p['quantile'],method='linear')) if p['quantile'] is not None else None
            if tau is None:assert p['threshold'] is None
            else:close(tau,p['threshold'],1e-12)
            boundary+=check(z,public['post_logits'],public['teacher_logits'],p['threshold'])
            v=np_proxy(public['post_logits'].numpy(),z.numpy());assert v['eligible']==p['eligible']
            close(v['mean_KL'],p['mean_KL']);close(v['agreement'],p['agreement'])
            assert p['routed_n']==int((z.argmax(1)!=public['post_logits'].argmax(1)).sum())
            if v['eligible']:passing.append(i)
        assert config['selected_index']==passing[0] and config['selected']==config['points'][passing[0]]
        armchecks={}
        for arm,row in rows['cases'].items():
            pack=torch.load(root/('private_'+arm+'_outputs.pt'),map_location='cpu',weights_only=True);tau=row['threshold']
            for name in ['clean','member']:
                boundary+=check(pack[name+'_logits'],pack['native_'+name+'_logits'],pack['teacher_'+name+'_logits'],tau,pack['routed_'+name])
            pred=pack['clean_logits'].numpy().argmax(1);close(row['clean']['CA_pct'],100*float((pred[held]==labels[held]).mean()))
            native=pack['native_clean_logits'].numpy().argmax(1);my=pack['member_labels'].numpy();mp=pack['member_logits'].numpy().argmax(1)
            weights=np.bincount(my,minlength=10)/len(my)
            gap=sum(weights[c]*((mp[my==c]==c).mean()-(pred[held][labels[held]==c]==c).mean()) for c in range(10) if (my==c).any()) if pair!='attack_cover850' else None
            if gap is not None:close(gap,row['deletion_audit']['weighted_accuracy_gap'])
            armchecks[arm]={'independent_rowwise_permutation_exact':True}
            if pair=='attack_cover850':
                boundary+=check(pack['attack_logits'],pack['native_attack_logits'],pack['teacher_attack_logits'],tau,pack['routed_attack'])
                armchecks[arm]['independent_attack_counts']=check_attack(pack['attack_logits'],labels[tids],mask,native[tids],row['attack_quality'])
                tp=pack['teacher_attack_logits'].numpy().argmax(1);pp=pack['native_attack_logits'].numpy().argmax(1);truth=labels[tids]
                assert np.all(pp==0) and np.all(truth!=0)
                ceiling=100*float((tp[mask]==truth[mask]).mean());ref=100*float((native[tids][mask]==truth[mask]).mean())
                per=[]
                for c in range(1,10):
                    ix=truth[mask]==c
                    upper=100*float((tp[mask][ix]==c).mean());required=100*float((native[tids][mask][ix]==c).mean())-5
                    per.append({'class':c,'teacher_upper_CA_pct':upper,'required_CA_pct':required,'meets_required':upper>=required-1e-10})
                armchecks[arm]['fixed_label_provider_gate_family_bound']={'Post_all_actual_target':True,'heldout_n':8542,
                    'teacher_upper_correct_n':int((tp[mask]==truth[mask]).sum()),'upper_original_CA_pct':ceiling,
                    'required_original_CA_pct':ref-2,'global_necessary_possible':ceiling>=ref-2-1e-10,
                    'class_rows':per,'all_quality_necessary_possible':ceiling>=ref-2-1e-10 and all(v['meets_required'] for v in per),
                    'applies_only_to_any_gate_selecting_this_fixed_Post_or_H5_argmax':True}
        report['cases'][pair]={'arms':armchecks,'floating_cutoff_boundary_disagreements':boundary}
    assert not torch.cuda.is_initialized();sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    report['finished_unix']=time.time()
    with (ROOT/'INDEPENDENT_DIAGNOSIS.json').open('x',encoding='utf8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
