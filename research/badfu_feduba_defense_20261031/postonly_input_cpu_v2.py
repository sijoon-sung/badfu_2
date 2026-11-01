"""New matched CUDA inference-only pilot; calibration has no Pre or private truth."""
import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
import gc,hashlib,json,shutil,time,traceback
from pathlib import Path
import numpy as np
import torch
import stage05_common as s
from stage08 import norm
from stage10 import write
from cpu_entry_postonly import guard
from postonly_inputs import ARMS,apply,calibrate
from attack_quality import metrics as attack_metrics
from correct_reference_audit import gate as privacy_gate,independent
core=s.core;OUT=s.HERE/'postonly_input_cpu_v2'


def key(config):
    return (config.get('threshold'),config.get('size',32))


def raw01(x):return x.permute(0,3,1,2).float().div(255).contiguous()


@torch.inference_mode()
def predict(model,raw,root,phase,deadline,config=None,uint8=False):
    chunks=[]
    for i in range(0,len(raw),32):
        deadline();x=raw01(raw[i:i+32]) if uint8 else raw[i:i+32]
        if config is not None:x=apply(x,config)
        z=model(norm(x));assert z.shape==(len(x),10) and torch.isfinite(z).all();chunks.append(z)
        if i%3200==0:write(root,'PROGRESS.json',{'phase':phase,'n':len(raw),'completed':min(i+32,len(raw)),'time':time.time()})
    return torch.cat(chunks).double()


def main():
    OUT.mkdir(exist_ok=True);s.verify_sources();freeze=core.read(s.HERE/'POST_ONLY_INPUT_CPU_V2_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    contract=core.read(s.HERE/'POST_ONLY_INPUT_CONTRACT.json')
    assert contract['state']=='passed' and contract['method_sha256']==core.sha(s.HERE/'postonly_inputs.py')
    parent=core.read(s.HERE/'shared_feature_run/INDEPENDENT_VERIFICATION.json')
    assert parent['state']=='passed' and parent['root_result_sha256']==core.sha(s.HERE/'shared_feature_run/RESULT.json')
    assert str(torch.__version__)=='2.7.1+cu118' and not torch.cuda.is_initialized()
    assert shutil.disk_usage(OUT).free>=8*1024**3
    resources=guard()
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time(),'resources':resources,'arms':ARMS},f,indent=2)
    selected,sealed,states=s.snapshot();base=sealed.model_class(Path(selected['source_root']))
    cls=base
    info=core.read(s.HERE/'STAGE03_INPUTS.json');assert core.sha(info['clean_path'])==info['clean_path_sha256']
    data=torch.load(info['clean_path'],map_location='cpu',weights_only=True)
    split=core.read(s.HERE/'PROXY_SPLIT.json');fit=torch.tensor(split['fit_ids']);held=torch.tensor(split['heldout_ids'])
    assert len(fit)==500 and len(held)==9500 and set(fit.tolist()).isdisjoint(held.tolist())
    public=raw01(data['test_x'][fit]);survivors=ARMS.copy();whole=time.monotonic()
    summary={'state':'running','cases':{},'method_scope':'controlled_inference_guard_only',
        'evaluator':'postonly_input_CPU2_FP32_NCHW_B32_noCUDA_20261101_v2',
        'new_training':False,'new_FL_seeds':0,'Pre_or_H5_method_input':False,'actual_FedUBA_evaluated':False,'raw_weights_purified':False}
    for pair,a,b in [('benign_big19336','clean_pre','clean_big_post'),('attack_cover850','pre','post'),('benign_same850','clean_pre','clean_post')]:
        root=OUT/pair;root.mkdir(exist_ok=False);start=time.monotonic()
        def deadline():assert time.monotonic()-start<3600 and time.monotonic()-whole<10800,'bounded new profile runtime'
        native=states[b];digest=core.tensor_digest(native);model=cls().eval();model.load_state_dict(native,strict=True)
        for p in model.parameters():p.requires_grad_(False)
        write(root,'SOURCE_INPUTS.json',{'case_id':selected['case_id'],'purpose':'purification_pilot','post_role':b,
            'post_path':selected['server_inputs'][b]['path'],'post_sha256':selected['server_inputs'][b]['sha256'],'payload_key':None})
        calls=0
        def public_prediction(x):
            nonlocal calls
            calls+=1;return predict(model,x,root,'public_candidate_'+str(calls),deadline)
        declaration,private=calibrate(public,public_prediction)
        torch.save(private,root/'private_public_calibration.pt')
        declaration.update({'post_sha256':selected['server_inputs'][b]['sha256'],'post_tensor_sha256':digest,
            'public_evidence_sha256':core.sha(root/'private_public_calibration.pt'),'source_module_sha256':core.sha(s.HERE/'postonly_inputs.py')})
        write(root,'CONFIG_BEFORE_PRIVATE_EVALUATION.json',declaration);config_sha=core.sha(root/'CONFIG_BEFORE_PRIVATE_EVALUATION.json')
        # All truth/member/trigger access below is evaluator-only, after config seal.
        import stage05_delete as removed
        datasets,extra=removed.data();member,my,ids,ck,ny=datasets[pair]
        complete=core.read(extra[ck]['path'])
        assert complete['checkpoint_sha256']==selected['server_inputs'][b]['sha256']
        assert hashlib.sha256(np.asarray(sorted(ids),dtype=np.int64).tobytes()).hexdigest()==complete['audit']['removed_indices_sha256']
        labels=data['test_y'].long();pre=s.logits(s.feature_cache(pair,True)['clean'],s.head(states[a]))
        historical=core.read(s.HERE/'heldout_reference_audit/RESULT.json')['original_interventions'][pair]['native_post']['corrected_heldout_reference']
        hf=s.feature_cache(pair,False);historical_clean=s.logits(hf['clean'],s.head(native))
        native_clean=predict(model,data['test_x'],root,'native_clean',deadline,uint8=True)
        native_error=float((native_clean-historical_clean).abs().max())
        native_disagreement=int((native_clean.argmax(1)!=historical_clean.argmax(1)).sum())
        assert native_error<=1e-3 and native_disagreement<=5,'new native evaluator differs from sealed historical profile'
        native_metrics=core.metrics(native_clean,labels,pre,native_clean,held)
        historical_metrics=core.metrics(historical_clean,labels,pre,historical_clean,held)
        private_native={'clean_logits':native_clean,'historical_clean_logits':historical_clean}
        clean_cache={(None,32):(native_clean,'native')};member_cache={};attack_cache={}
        result={'state':'running','cases':{},'selection_sha256':config_sha,'native_clean':native_metrics,
            'historical_clean':historical_metrics,'native_logit_max_abs_difference':native_error,
            'native_argmax_disagreement_n':native_disagreement,'formal_deletion_certificate':False,'independent_class_AUC_checks':0}
        active=survivors.copy();asrs={};quality_eligible=active.copy()
        if pair=='attack_cover850':
            clean,y,attack=core.load_data(info);assert torch.equal(clean,data['test_x']) and torch.equal(y,labels)
            record=torch.load(info['record_path'],map_location='cpu',weights_only=False)
            tids=[int(i) for i in record['bd_test']['bd_data_container']['data_dict']];heldset=set(held.tolist());mask=torch.tensor([i in heldset for i in tids])
            truth=labels[tids];assert len(tids)==9000 and int(mask.sum())==8542 and torch.equal(ny,truth) and bool((truth!=0).all())
            native_attack=predict(model,attack,root,'native_attack',deadline,uint8=True)
            attack_cache[(None,32)]=(native_attack,'native');private_native['attack_logits']=native_attack
            quality_eligible=[]
            for arm in active:
                cfg=declaration['selected'][arm]['config'];k=key(cfg)
                if k in attack_cache:z,origin=attack_cache[k]
                else:z=predict(model,attack,root,arm+'_attack',deadline,config=cfg,uint8=True);origin=None;attack_cache[k]=(z,arm)
                fresh=attack_metrics(z,truth,mask,native_clean.argmax(1)[tids],0)
                old=attack_metrics(z,truth,mask,historical_clean.argmax(1)[tids],0)
                asrs[arm]={'matched_reference':fresh,'historical_reference':old,'reused_logits_from':origin}
                torch.save({'attack_logits':z,'reused_from':origin},root/('private_'+arm+'_attack.pt'))
                if not declaration['selected'][arm]['identity'] and fresh['ASR_pct']<=10 and fresh['heldout_ASR_pct']<=10 and fresh['original_label_robustness_gate'] and old['original_label_robustness_gate']:
                    quality_eligible.append(arm)
            result['all_attack_quality']=asrs
            if not quality_eligible:
                result.update(state='failed_necessary_attack_behavior',clean_member_extension='skipped_by_preregistered_behavior_stop')
                torch.save(private_native,root/'private_native.pt')
                write(root,'RESULT.json',result)
        if pair!='attack_cover850' or quality_eligible:
            native_member=predict(model,member,root,'native_removed',deadline,uint8=True)
            member_cache[(None,32)]=(native_member,'native');private_native.update(member_logits=native_member,member_labels=my)
            nn=native_attack[mask] if pair=='attack_cover850' else native_clean[held]
            nlabel=truth[mask] if pair=='attack_cover850' else ny[held]
            privacy_native=s.membership(native_member,my,nn,nlabel)
            result['native_deletion_audit']=privacy_native
            for arm in active:
                if arm not in quality_eligible:
                    result['cases'][arm]={'necessary_gate':False,'reason':'failed necessary actual attack quality'};continue
                cfg=declaration['selected'][arm]['config'];k=key(cfg)
                if k in clean_cache:cz,co=clean_cache[k]
                else:cz=predict(model,data['test_x'],root,arm+'_clean',deadline,config=cfg,uint8=True);co=None;clean_cache[k]=(cz,arm)
                if k in member_cache:mz,mo=member_cache[k]
                else:mz=predict(model,member,root,arm+'_removed',deadline,config=cfg,uint8=True);mo=None;member_cache[k]=(mz,arm)
                if pair=='attack_cover850':nz=attack_cache[k][0][mask];nlabel=truth[mask]
                else:nz=cz[held];nlabel=ny[held]
                audit=s.membership(mz,my,nz,nlabel);nchecks=independent(audit,mz,my,nz,nlabel);result['independent_class_AUC_checks']+=nchecks
                freshgate=privacy_gate(audit,privacy_native);oldgate=privacy_gate(audit,historical)
                metric=core.metrics(cz,labels,pre,native_clean,held)
                drops=[native_metrics['CA_pct']-metric['CA_pct'],historical_metrics['CA_pct']-metric['CA_pct']]
                worsts=[max(u-v for u,v in zip(base['class_CA_pct'],metric['class_CA_pct'])) for base in [native_metrics,historical_metrics]]
                passed=max(drops)<=.5+1e-10 and max(worsts)<=2+1e-10 and freshgate['necessary_deletion_gate'] and oldgate['necessary_deletion_gate']
                result['cases'][arm]={'config':cfg,'clean':metric,'deletion_audit':audit,'matched_privacy_comparison':freshgate,
                    'historical_privacy_comparison':oldgate,'overall_drops_pp':drops,'worst_class_drops_pp':worsts,
                    'necessary_gate':passed,'identity':declaration['selected'][arm]['identity'],'clean_reused_from':co,'member_reused_from':mo}
                torch.save({'clean_logits':cz,'member_logits':mz,'member_labels':my},root/('private_'+arm+'_evaluation.pt'))
                write(root,'RESULT.json',result)
            result['state']='completed';torch.save(private_native,root/'private_native.pt');write(root,'RESULT.json',result)
        assert core.sha(root/'CONFIG_BEFORE_PRIVATE_EVALUATION.json')==config_sha
        assert not model.training and core.tensor_digest(model.state_dict())==digest
        write(root,'COMPLETED.json',{'result_sha256':core.sha(root/'RESULT.json'),'native_tensor_unchanged':True,
            'files':{p.name:core.sha(p) for p in root.iterdir() if p.is_file() and p.name!='COMPLETED.json'}})
        summary['cases'][pair]=result;survivors=[a for a in survivors if result.get('cases',{}).get(a,{}).get('necessary_gate',False)]
        write(OUT,'RESULT.json',summary);sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
        del model;gc.collect();assert not torch.cuda.is_initialized()
        if not survivors:break
    assert not torch.cuda.is_initialized()
    summary.update(state='completed',finished_unix=time.time(),same850_executed='benign_same850' in summary['cases'],
        CUDA_initialized=False,CPU_threads=torch.get_num_threads(),torch_version=str(torch.__version__),
        method_necessary_gates={a:all(summary['cases'].get(p,{}).get('cases',{}).get(a,{}).get('necessary_gate',False)
            for p in ['benign_big19336','attack_cover850','benign_same850']) for a in ARMS})
    write(OUT,'RESULT.json',summary);write(OUT,'COMPLETED.json',{'result_sha256':core.sha(OUT/'RESULT.json'),
        'source_freeze_sha256':core.sha(s.HERE/'POST_ONLY_INPUT_CPU_V2_FREEZE.json')})
    print('POST_ONLY_INPUT_CPU_V2_PILOT_COMPLETED',flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True);write(OUT,'FAILURE.json',{'traceback':traceback.format_exc()});raise
