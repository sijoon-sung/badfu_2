"""New cached-output composition pilot; no CNN, optimizer or private calibration."""
import hashlib,json,os,time,traceback
from pathlib import Path
import numpy as np
import torch
import stage05_common as s
from sourcepair_pilot import cpu_guard
from stage10 import write
from post_confidence_relabel import calibrate,relabel
from correct_reference_audit import independent,gate
from attack_quality import metrics as attack_metrics
core=s.core;OUT=s.HERE/'post_confidence_pilot';ARMS=['plain_relabel','confidence_gated_relabel']


def check_permutation(z,original):
    assert torch.equal(z.sort(1).values,original.sort(1).values)
    error=float((z.log_softmax(1).max(1).values-original.log_softmax(1).max(1).values).abs().max())
    assert error<=1e-12,error
    return error


def main():
    OUT.mkdir(exist_ok=True);s.verify_sources();freeze=core.read(s.HERE/'POST_CONFIDENCE_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    cpu=cpu_guard();assert not torch.cuda.is_initialized()
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time(),'CPU':cpu},f)
    # Algebra and pure-interface contracts precede any new calibration/evaluation.
    synthetic=torch.tensor([[4.,1.,-1.],[0.,3.,1.]],dtype=torch.float64)
    other=torch.tensor([[0.,5.,1.],[5.,0.,1.]],dtype=torch.float64)
    swapped,m=relabel(synthetic,other,0.)
    assert m.all() and torch.equal(swapped.argmax(1),other.argmax(1))
    assert check_permutation(swapped,synthetic)<=1e-12
    identity,mask=relabel(synthetic,other,None);assert torch.equal(identity,synthetic) and not mask.any()
    selected,sealed,states=s.snapshot();split=core.read(s.HERE/'PROXY_SPLIT.json')
    fit=torch.tensor(split['fit_ids']);held=torch.tensor(split['heldout_ids'])
    assert len(fit)==500 and len(held)==9500 and set(fit.tolist()).isdisjoint(held.tolist())
    summary={'state':'running','cases':{},'scope':'one_existing_BadFU_seed_cached_output_composition',
        'new_CNN_inference':False,'new_training':False,'FedUBA_evaluated':False,'full_objective_achieved':False}
    survivors=ARMS.copy();whole=time.monotonic()
    for pair,a,b in [('benign_big19336','clean_pre','clean_big_post'),('attack_cover850','pre','post'),('benign_same850','clean_pre','clean_post')]:
        assert time.monotonic()-whole<600,'ten minute cached arithmetic bound'
        root=OUT/pair;root.mkdir(exist_ok=False)
        before=s.feature_cache(pair,True);after=s.feature_cache(pair,False)
        hp=s.OUT/(pair+'_aligned_model.pt');decl=core.read(s.OUT/'CANDIDATES_BEFORE_EVALUATION.json')
        assert core.sha(hp)==decl['models'][hp.name];teacherstate=torch.load(hp,map_location='cpu',weights_only=True)
        hh=s.head(teacherstate);ph=s.head(states[b])
        ppublic=s.logits(after['clean'][fit],ph);tpublic=s.logits(before['clean'][fit],hh)
        config,outputs=calibrate(ppublic,tpublic)
        for point,z in zip(config['points'],outputs):assert point['routed_n']==int((z.argmax(1)!=ppublic.argmax(1)).sum())
        # Config+public evidence are sealed before evaluator data/trigger/member use.
        torch.save({'post_logits':ppublic,'teacher_logits':tpublic,'candidate_logits':outputs},root/'private_public_calibration.pt')
        config.update({'case_id':selected['case_id'],'purpose':'purification_pilot','pre_role':a,'post_role':b,
            'post_path':selected['server_inputs'][b]['path'],'post_sha256':selected['server_inputs'][b]['sha256'],
            'teacher_path':str(hp),'teacher_sha256':core.sha(hp),'public_evidence_sha256':core.sha(root/'private_public_calibration.pt'),
            'groundtruth_used':False,'actual_trigger_used':False,'member_used':False,'ASR_used':False,'active_arms':survivors.copy()})
        write(root,'CONFIG_BEFORE_PRIVATE_EVALUATION.json',config);fixed=core.sha(root/'CONFIG_BEFORE_PRIVATE_EVALUATION.json')
        info=core.read(s.HERE/'STAGE03_INPUTS.json');assert core.sha(info['clean_path'])==info['clean_path_sha256']
        labels=torch.load(info['clean_path'],map_location='cpu',weights_only=True)['test_y'].long()
        assert core.sha(info['record_path'])==info['record_path_sha256']
        record=torch.load(info['record_path'],map_location='cpu',weights_only=False)
        tids=[int(i) for i in record['bd_test']['bd_data_container']['data_dict']];held_set=set(held.tolist());mask=torch.tensor([i in held_set for i in tids])
        assert len(tids)==9000 and int(mask.sum())==8542 and sorted(tids)==torch.where(labels!=0)[0].tolist()
        pre=s.logits(before['clean'],s.head(states[a]));post=s.logits(after['clean'],ph);tclean=s.logits(before['clean'],hh)
        base=core.metrics(post,labels,pre,post,held)
        baseline=core.read(s.HERE/'heldout_reference_audit/RESULT.json')['original_interventions'][pair]['native_post']['corrected_heldout_reference']
        mr=core.read(s.HERE/'stage07_cpu_v2/COMPLETED.json');mp=s.HERE/'stage07_cpu_v2'/('private_'+pair+'_member_features.pt')
        assert core.sha(mp)==mr['files'][mp.name];mem=torch.load(mp,map_location='cpu',weights_only=True)
        extra=core.read(s.HERE/'STAGE05_INPUTS.json')
        for key in ['train','split','big_complete' if pair=='benign_big19336' else 'attack_complete' if pair=='attack_cover850' else 'same_complete']:
            assert core.sha(extra[key]['path'])==extra[key]['sha256']
        original_split=core.read(extra['split']['path']);ids=original_split['clean_cifar10_indices'][4] if pair=='benign_big19336' else original_split['cover_cifar10_indices']
        ck='big_complete' if pair=='benign_big19336' else 'attack_complete' if pair=='attack_cover850' else 'same_complete'
        complete=core.read(extra[ck]['path']);assert complete['checkpoint_sha256']==selected['server_inputs'][b]['sha256']
        assert hashlib.sha256(np.asarray(sorted(ids),dtype=np.int64).tobytes()).hexdigest()==complete['audit']['removed_indices_sha256']
        train=torch.load(extra['train']['path'],map_location='cpu',weights_only=True)
        my=mem['labels'].long();assert torch.equal(my,train['train_y'][ids].long())
        pm=s.logits(mem['post'],ph);tm=s.logits(mem['pre'],hh)
        result={'selection_sha256':fixed,'cases':{},'state':'running','independent_class_AUC_checks':0,'formal_deletion_certificate':False}
        for arm in survivors:
            tau=0. if arm=='plain_relabel' else config['selected']['threshold']
            cz,cm=relabel(post,tclean,tau);mz,mm=relabel(pm,tm,tau)
            errors=[check_permutation(cz,post),check_permutation(mz,pm)]
            metric=core.metrics(cz,labels,pre,post,held)
            quality=None
            if pair=='attack_cover850':
                pa=s.logits(after['attack'],ph);ta=s.logits(before['attack'],hh);az,am=relabel(pa,ta,tau)
                errors.append(check_permutation(az,pa));quality=attack_metrics(az,labels[tids],mask,post.argmax(1)[tids],target=0)
                nz=az[mask];ny=labels[tids][mask]
            else:nz=cz[held];ny=labels[held]
            audit=s.membership(mz,my,nz,ny);n=independent(audit,mz,my,nz,ny);result['independent_class_AUC_checks']+=n
            privacy=gate(audit,baseline);drop=base['CA_pct']-metric['CA_pct'];worst=max(u-v for u,v in zip(base['class_CA_pct'],metric['class_CA_pct']))
            passed=drop<=.5+1e-10 and worst<=2+1e-10 and privacy['necessary_deletion_gate']
            if quality is not None:passed=passed and quality['ASR_pct']<=10 and quality['heldout_ASR_pct']<=10 and quality['original_label_robustness_gate']
            pack={'clean_logits':cz,'member_logits':mz,'member_labels':my,'routed_clean':cm,'routed_member':mm,
                'native_clean_logits':post,'native_member_logits':pm,'teacher_clean_logits':tclean,'teacher_member_logits':tm}
            if quality is not None:pack.update(attack_logits=az,routed_attack=am,native_attack_logits=pa,teacher_attack_logits=ta)
            torch.save(pack,root/('private_'+arm+'_outputs.pt'))
            result['cases'][arm]={'threshold':tau,'clean':metric,'deletion_audit':audit,**privacy,'overall_drop_pp':drop,'worst_class_drop_pp':worst,
                'routed_clean_n':int(cm.sum()),'routed_member_n':int(mm.sum()),'maxlogprob_permutation_max_abs_error':max(errors),
                'attack_quality':quality,'necessary_gate':bool(passed)}
        assert core.sha(root/'CONFIG_BEFORE_PRIVATE_EVALUATION.json')==fixed
        result['state']='completed';write(root,'RESULT.json',result)
        write(root,'COMPLETED.json',{'result_sha256':core.sha(root/'RESULT.json'),
            'files':{p.name:core.sha(p) for p in root.iterdir() if p.is_file() and p.name!='COMPLETED.json'}})
        summary['cases'][pair]=result;survivors=[arm for arm in survivors if result['cases'][arm]['necessary_gate']]
        write(OUT,'RESULT.json',summary)
        if not survivors:break
    summary.update(state='completed',finished_unix=time.time(),same850_executed='benign_same850' in summary['cases'],
        method_necessary_gates={arm:all(summary['cases'].get(p,{}).get('cases',{}).get(arm,{}).get('necessary_gate',False)
            for p in ['benign_big19336','attack_cover850','benign_same850']) for arm in ARMS})
    assert not torch.cuda.is_initialized();sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    write(OUT,'RESULT.json',summary);write(OUT,'COMPLETED.json',{'result_sha256':core.sha(OUT/'RESULT.json'),
        'source_freeze_sha256':core.sha(s.HERE/'POST_CONFIDENCE_FREEZE.json')})
    print('POST_CONFIDENCE_CACHED_PILOT_COMPLETED',flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True);write(OUT,'FAILURE.json',{'traceback':traceback.format_exc()});raise
