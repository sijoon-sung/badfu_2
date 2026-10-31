"""Post-anchored consistency repair; large benign first, then attack and same850."""
import hashlib,json,os,shutil,subprocess,time,traceback
from pathlib import Path
import numpy as np
import torch
import stage05_common as s
import stage05_delete as removed
from stage08 import norm,loss
from stage09 import mix,proxy_metrics
core=s.core
OUT=s.HERE/'post_anchor_run'
ARMS=['teacher_query','post_anchor']


def write(root,name,obj):
    p=root/name;t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8');os.replace(t,p)


@torch.inference_mode()
def forward(model,raw,root,phase):
    parts=[]
    for i in range(0,len(raw),32):
        parts.append(model(core.normalise(raw[i:i+32])))
        if i%3200==0:write(root,'PROGRESS.json',{'phase':phase,'n':len(raw),'completed':min(i+32,len(raw)),'time':time.time()})
    z=torch.cat(parts).double();assert torch.isfinite(z).all();return z


from post_anchor_method import train_and_select
from sourcepair_pilot import run_case as generate_bank,cpu_guard


def evaluate(pair,a,b,states,declaration,cls,root,info,labels,held,large_passed,deadline):
    """Evaluator only: true labels/reference never enter fitting or selection."""
    import copy
    selected_path=root/'SELECTION_BEFORE_PRIVATE_EVALUATION.json';fixed=core.sha(selected_path)
    datasets,extra=removed.data();member,my,ids,key,ny=datasets[pair]
    complete=core.read(extra[key]['path'])
    assert hashlib.sha256(np.asarray(sorted(ids),dtype=np.int64).tobytes()).hexdigest()==complete['audit']['removed_indices_sha256']
    assert complete['checkpoint_sha256']==core.read(root/'SOURCE_INPUTS.json')['post_sha256']
    if pair=='attack_cover850':clean,y,attack=core.load_data(info)
    else:
        assert core.sha(info['clean_path'])==info['clean_path_sha256']
        data=torch.load(info['clean_path'],map_location='cpu',weights_only=True)
        clean=data['test_x'];y=data['test_y'].long();attack=None
    assert torch.equal(y,labels)
    before=s.feature_cache(pair,True);after=s.feature_cache(pair,False)
    pre=s.logits(before['clean'],s.head(states[a]));post=s.logits(after['clean'],s.head(states[b]))
    base=core.metrics(post,labels,pre,post,held)
    privacybase=core.read(s.HERE/'heldout_reference_audit/RESULT.json')['original_interventions'][pair]['native_post']['corrected_heldout_reference']
    result={'state':'running','cases':{},'selection_sha256':fixed,'formal_deletion_certificate':False}
    model=cls().eval();native_digest=core.tensor_digest(states[b])
    if pair=='attack_cover850':
        record=torch.load(info['record_path'],map_location='cpu',weights_only=False)
        tids=[int(i) for i in record['bd_test']['bd_data_container']['data_dict']]
        truth=labels[tids];assert torch.equal(ny,truth) and bool((truth!=0).all())
        held_set=set(held.tolist());mask=torch.tensor([i in held_set for i in tids]);assert int(mask.sum())==8542
        clean_prediction=post.argmax(1)[tids]
        ref_CA=100*float((clean_prediction[mask]==truth[mask]).double().mean())
        ref_class=[100*float((clean_prediction[mask][truth[mask]==c]==c).double().mean()) if bool((truth[mask]==c).any()) else None for c in range(10)]
        result['paired_native_clean_reference']={'CA_pct':ref_CA,'class_CA_pct':ref_class,'n':int(mask.sum()),
            'profile':'sealed_H3_GPU_features_FP64_head_original_Post_paired_IDs_evaluator_only'}
        asr={};cache={}
        for arm in ARMS:
            asr[arm]={}
            for variant,entry in [('raw',declaration['raw_models'][arm]),('selected',declaration['models'][arm])]:
                deadline();path=root/entry['path'];assert core.sha(path)==entry['sha256']
                state=torch.load(path,map_location='cpu',weights_only=True);digest=core.tensor_digest(state)
                origin=None
                if digest in cache:z,origin=cache[digest]
                elif digest==native_digest:
                    z=s.logits(after['attack'],s.head(states[b]));origin='identity_original_cache'
                else:
                    model.load_state_dict(state,strict=True);z=forward(model,attack,root,arm+'_'+variant+'_attack')
                    assert core.tensor_digest(model.state_dict())==digest
                if digest not in cache:cache[digest]=(z,arm+'_'+variant)
                torch.save({'attack_logits':z,'reused_from':origin},root/('private_'+arm+'_'+variant+'_attack.pt'))
                from attack_quality import metrics as attack_metrics
                asr[arm][variant]=attack_metrics(z,truth,mask,clean_prediction,target=0)
                asr[arm][variant]['reused_logits_from']=origin
        result['all_ASR']=asr
        eligible=[arm for arm in ARMS if arm in large_passed and not declaration['models'][arm]['identity']
                  and asr[arm]['selected']['ASR_pct']<=10 and asr[arm]['selected']['heldout_ASR_pct']<=10
                  and asr[arm]['selected']['original_label_robustness_gate']]
        if not eligible:
            result.update(state='failed_necessary_attack_behavior',extension_permitted=False,clean_member_audits='skipped_by_preregistered_attack_behavior_stop')
            assert core.sha(selected_path)==fixed;write(root,'RESULT.json',result);return result
    else:eligible=[arm for arm in ARMS if arm in large_passed]
    for arm in ARMS:
        if arm not in eligible:
            result['cases'][arm]={'necessary_gate':False,'reason':'failed earlier necessary gate'};continue
        deadline();entry=declaration['models'][arm];path=root/entry['path'];assert core.sha(path)==entry['sha256']
        state=torch.load(path,map_location='cpu',weights_only=True)
        if pair!='attack_cover850' and core.tensor_digest(state)==native_digest:
            result['cases'][arm]={'alpha':entry['alpha'],'clean':copy.deepcopy(base),'deletion_audit':copy.deepcopy(privacybase),
                'identity_reference_reused':True,'identity_tensor_equality':True,'overall_drop_pp':0.,'worst_class_drop_pp':0.,
                'increase_over_post':{n:{m:0. for m in ['advantage','weighted_class_advantage']} for n in privacybase['scores']},
                'absolute_accuracy_gap_increase':0.,'necessary_gate':True}
            continue
        model.load_state_dict(state,strict=True);cz=forward(model,clean,root,arm+'_clean');mz=forward(model,member,root,arm+'_removed')
        assert core.tensor_digest(state)==core.tensor_digest(model.state_dict())
        torch.save({'clean_logits':cz,'member_logits':mz,'member_labels':my},root/('private_'+arm+'_evaluation.pt'))
        if pair=='attack_cover850':
            za=torch.load(root/('private_'+arm+'_selected_attack.pt'),map_location='cpu',weights_only=True)['attack_logits']
            nz=za[mask];nlabel=truth[mask]
        else:nz=cz[held];nlabel=ny[held]
        metric=core.metrics(cz,labels,pre,post,held);audit=s.membership(mz,my,nz,nlabel)
        increases={n:{m:audit['scores'][n][m]-privacybase['scores'][n][m] for m in ['advantage','weighted_class_advantage']} for n in privacybase['scores']}
        gap=abs(audit['weighted_accuracy_gap'])-abs(privacybase['weighted_accuracy_gap'])
        drop=base['CA_pct']-metric['CA_pct'];worst=max(u-v for u,v in zip(base['class_CA_pct'],metric['class_CA_pct']))
        result['cases'][arm]={'alpha':entry['alpha'],'clean':metric,'deletion_audit':audit,'increase_over_post':increases,
            'absolute_accuracy_gap_increase':gap,'overall_drop_pp':drop,'worst_class_drop_pp':worst,
            'necessary_gate':drop<=.5+1e-10 and worst<=2+1e-10 and gap<=.02+1e-12 and all(v<=.04+1e-12 for z in increases.values() for v in z.values())}
        write(root,'RESULT.json',result)
    assert core.sha(selected_path)==fixed
    result.update(state='completed',extension_permitted=any(v['necessary_gate'] for v in result['cases'].values()))
    write(root,'RESULT.json',result);return result


def main():
    OUT.mkdir(exist_ok=True);s.verify_sources()
    freeze=core.read(s.HERE/'POST_ANCHOR_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    prior=core.read(s.HERE/'stage11/RESULT.json')
    parent_audit=core.read(s.HERE/'stage11/INDEPENDENT_VERIFICATION.json')
    bank_audit=core.read(s.HERE/'sourcepair_pilot/INDEPENDENT_VERIFICATION.json')
    assert prior['state']=='completed' and prior['cases']['attack_cover850']['state']=='failed_necessary_ASR'
    assert parent_audit['state']=='passed' and bank_audit['state']=='passed'
    assert core.read(s.HERE/'sourcepair_pilot/RESULT.json')['state']=='completed'
    quality=core.read(s.HERE/'POST_ANCHOR_QUALITY_CONTRACT.json')
    assert quality['state']=='passed' and quality['source_sha256']==core.sha(s.HERE/'attack_quality.py')
    large_passed=ARMS.copy();cpu=cpu_guard()
    assert not torch.cuda.is_initialized() and shutil.disk_usage(OUT).free>=4*1024**3
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time(),'CPU':cpu,'candidate_arms':ARMS},f)
    whole=time.monotonic();selected,sealed,states=s.snapshot();cls=sealed.model_class(Path(selected['source_root']))
    info=core.read(s.HERE/'STAGE03_INPUTS.json');assert core.sha(info['clean_path'])==info['clean_path_sha256']
    raw=torch.load(info['clean_path'],map_location='cpu',weights_only=True)
    split=core.read(s.HERE/'PROXY_SPLIT.json');public=raw['test_x'][split['fit_ids']];held=torch.tensor(split['heldout_ids'])
    summary={'state':'running','large_passed_arms':[],'cases':{},'new_FL_seeds':0,
             'scope':'one_existing_BadFU_seed_three_case_necessary_test','FedUBA_evaluated':False}
    for pair,a,b in [('benign_big19336','clean_pre','clean_big_post'),('attack_cover850','pre','post'),('benign_same850','clean_pre','clean_post')]:
        root=OUT/pair;root.mkdir(exist_ok=False);tick=time.monotonic()
        def deadline():assert time.monotonic()-tick<3600 and time.monotonic()-whole<10800,'bounded profile runtime'
        hp=s.OUT/(pair+'_aligned_model.pt')
        assert core.sha(hp)==core.read(s.OUT/'CANDIDATES_BEFORE_EVALUATION.json')['models'][hp.name]
        write(root,'SOURCE_INPUTS.json',{'case_id':selected['case_id'],'purpose':'purification_pilot',
            'pre_role':a,'post_role':b,'post_sha256':selected['server_inputs'][b]['sha256'],'teacher_sha256':core.sha(hp)})
        bankroot=s.HERE/'sourcepair_pilot'/pair
        if not (bankroot/'COMPLETED.json').exists():
            assert pair=='benign_same850','never regenerate completed parent banks'
            bankroot=root/'query_generation';bankroot.mkdir(exist_ok=False)
            generate_bank(pair,states[b],torch.load(hp,map_location='cpu',weights_only=True),public,cls,bankroot,deadline)
        receipt=core.read(bankroot/'COMPLETED.json')
        bankpath=bankroot/'private_teacher_source_bank.pt';initialpath=bankroot/'private_initials.pt'
        declaration=train_and_select(states[b],public,cls,root,deadline,bankpath,initialpath,
            receipt['files'][bankpath.name],receipt['files'][initialpath.name])
        report=evaluate(pair,a,b,states,declaration,cls,root,info,raw['test_y'].long(),held,large_passed,deadline)
        write(root,'COMPLETED.json',{'result_sha256':core.sha(root/'RESULT.json'),
            'bank_receipt_path':str(bankroot/'COMPLETED.json'),'bank_receipt_sha256':core.sha(bankroot/'COMPLETED.json'),
            'files':{p.name:core.sha(p) for p in root.iterdir() if p.is_file() and p.name!='COMPLETED.json'}})
        summary['cases'][pair]=report;write(OUT,'RESULT.json',summary)
        sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
        if pair in ['benign_big19336','attack_cover850']:
            survivors=[arm for arm in large_passed if report.get('cases',{}).get(arm,{}).get('necessary_gate',False)]
            if pair=='benign_big19336':
                summary['large_passed_arms']=survivors;write(OUT,'RESULT.json',summary)
            if not survivors:break
            large_passed=survivors
    assert not torch.cuda.is_initialized()
    summary['method_necessary_gates']={arm:arm in summary['large_passed_arms'] and
        all(summary['cases'].get(pair,{}).get('cases',{}).get(arm,{}).get('necessary_gate',False)
            for pair in ['benign_big19336','attack_cover850','benign_same850']) for arm in ARMS}
    summary.update(state='completed',same850_executed='benign_same850' in summary['cases'],finished_unix=time.time(),CUDA_initialized=False)
    write(OUT,'RESULT.json',summary);write(OUT,'COMPLETED.json',{'result_sha256':core.sha(OUT/'RESULT.json'),
        'source_freeze_sha256':core.sha(s.HERE/'POST_ANCHOR_FREEZE.json')})
    print('POST_ANCHOR_COMPLETED',flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True);write(OUT,'FAILURE.json',{'traceback':traceback.format_exc()});raise
