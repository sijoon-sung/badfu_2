"""Matched all-class query study; large benign, attack, then same850."""
import hashlib,json,os,shutil,subprocess,time,traceback
from pathlib import Path
import numpy as np
import torch
import stage05_common as s
import stage05_delete as removed
from stage08 import norm,loss
from stage09 import mix,proxy_metrics
core=s.core
OUT=s.HERE/'stage11'
ARMS=['matched_kl','all_class_disjoint']


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


from stage11_method import train_and_select


def evaluate(pair,a,b,states,declaration,cls,root,info,labels,held,large_passed,deadline):
    """Evaluator-only: never passes truth or results into training/selection."""
    selected_path=root/'SELECTION_BEFORE_PRIVATE_EVALUATION.json';fixed=core.sha(selected_path)
    datasets,extra=removed.data();member,my,ids,key,ny=datasets[pair]
    complete=core.read(extra[key]['path'])
    assert hashlib.sha256(np.asarray(sorted(ids),dtype=np.int64).tobytes()).hexdigest()==complete['audit']['removed_indices_sha256']
    assert complete['checkpoint_sha256']==core.read(root/'SOURCE_INPUTS.json')['post_sha256']
    if pair=='attack_cover850':clean,y,attack=core.load_data(info)
    else:
        assert core.sha(info['clean_path'])==info['clean_path_sha256']
        raw=torch.load(info['clean_path'],map_location='cpu',weights_only=True)
        clean=raw['test_x'];y=raw['test_y'].long();attack=None
    assert torch.equal(y,labels)
    result={'state':'running','cases':{},'selection_sha256':fixed,'formal_deletion_certificate':False}
    model=cls().eval()
    if pair=='attack_cover850':
        original_record=torch.load(info['record_path'],map_location='cpu',weights_only=False)
        test_ids=[int(i) for i in original_record['bd_test']['bd_data_container']['data_dict']]
        held_set=set(held.tolist());heldmask=torch.tensor([i in held_set for i in test_ids])
        assert int(heldmask.sum())==core.read(s.HERE/'heldout_reference_audit/RESULT.json')['nonmember_trigger_n']
        asr={}
        for arm in ARMS:
            asr[arm]={}
            for variant,entry in [('raw',declaration['raw_models'][arm]),('selected',declaration['models'][arm])]:
                deadline();path=root/entry['path'];assert core.sha(path)==entry['sha256']
                state=torch.load(path,map_location='cpu',weights_only=True);model.load_state_dict(state,strict=True)
                if core.tensor_digest(state)==core.tensor_digest(states[b]):
                    previous=next(r for r in core.read(s.HERE/'stage03/RESULT.json')['rows']
                                  if r['pair']==pair and r['W']==r['BN']==r['head']==1)
                    old_logits=s.logits(s.feature_cache(pair,False)['attack'],s.head(states[b]))
                    hn=int((old_logits.argmax(1)[heldmask]==0).sum());hN=int(heldmask.sum())
                    asr[arm][variant]={'target_n':previous['attack_target_n'],'n':previous['attack_n'],
                        'ASR_pct':previous['ASR_pct'],'identity_original_counts_reused':True,
                        'heldout_target_n':hn,'heldout_n':hN,'heldout_ASR_pct':100*hn/hN}
                    continue
                z=forward(model,attack,root,arm+'_'+variant+'_attack')
                assert core.tensor_digest(state)==core.tensor_digest(model.state_dict())
                torch.save({'attack_logits':z},root/('private_'+arm+'_'+variant+'_attack.pt'))
                asr[arm][variant]={'target_n':int((z.argmax(1)==0).sum()),'n':len(z),'ASR_pct':100*float((z.argmax(1)==0).double().mean()),
                    'heldout_target_n':int((z.argmax(1)[heldmask]==0).sum()),'heldout_n':int(heldmask.sum()),
                    'heldout_ASR_pct':100*float((z.argmax(1)[heldmask]==0).double().mean())}
        result['all_ASR']=asr
        eligible=[arm for arm in ARMS if arm in large_passed and declaration['models'][arm]['alpha']>0 and asr[arm]['selected']['ASR_pct']<=10 and asr[arm]['selected']['heldout_ASR_pct']<=10]
        if not eligible:
            result.update(state='failed_necessary_ASR',extension_permitted=False,clean_member_audits='skipped_by_preregistered_ASR_stop')
            assert core.sha(selected_path)==fixed;write(root,'RESULT.json',result);return result
    else:eligible=[arm for arm in ARMS if arm in large_passed and declaration['models'][arm]['alpha']>0]
    before=s.feature_cache(pair,True);after=s.feature_cache(pair,False)
    p=s.logits(before['clean'],s.head(states[a]));q=s.logits(after['clean'],s.head(states[b]))
    base=core.metrics(q,labels,p,q,held)
    privacybase=core.read(s.HERE/'heldout_reference_audit/RESULT.json')['original_interventions'][pair]['native_post']['corrected_heldout_reference']
    for arm in ARMS:
        if arm not in eligible:
            result['cases'][arm]={'necessary_gate':False,'reason':'failed prior necessary gate or identity'};continue
        deadline();entry=declaration['models'][arm];path=root/entry['path'];assert core.sha(path)==entry['sha256']
        state=torch.load(path,map_location='cpu',weights_only=True);model.load_state_dict(state,strict=True)
        cz=forward(model,clean,root,arm+'_clean');mz=forward(model,member,root,arm+'_removed')
        assert core.tensor_digest(state)==core.tensor_digest(model.state_dict())
        torch.save({'clean_logits':cz,'member_logits':mz,'member_labels':my},root/('private_'+arm+'_evaluation.pt'))
        if pair.startswith('attack'):
            za=torch.load(root/('private_'+arm+'_selected_attack.pt'),weights_only=True)['attack_logits']
            nonmember=za[heldmask];nonmember_y=ny[heldmask]
        else:nonmember=cz[held];nonmember_y=ny[held]
        metric=core.metrics(cz,labels,p,q,held);audit=s.membership(mz,my,nonmember,nonmember_y)
        increases={name:{measure:audit['scores'][name][measure]-privacybase['scores'][name][measure] for measure in ['advantage','weighted_class_advantage']} for name in privacybase['scores']}
        gap=abs(audit['weighted_accuracy_gap'])-abs(privacybase['weighted_accuracy_gap'])
        drop=base['CA_pct']-metric['CA_pct'];worst=max(u-v for u,v in zip(base['class_CA_pct'],metric['class_CA_pct']))
        result['cases'][arm]={'alpha':entry['alpha'],'clean':metric,'deletion_audit':audit,'increase_over_post':increases,
            'absolute_accuracy_gap_increase':gap,'overall_drop_pp':drop,'worst_class_drop_pp':worst,
            'necessary_gate':drop<=.5+1e-10 and worst<=2+1e-10 and gap<=.02+1e-12 and all(v<=.04+1e-12 for scores in increases.values() for v in scores.values())}
        write(root,'RESULT.json',result)
    assert core.sha(selected_path)==fixed
    result.update(state='completed',extension_permitted=any(v['necessary_gate'] for v in result['cases'].values()))
    write(root,'RESULT.json',result);return result


def main():
    OUT.mkdir(exist_ok=True);s.verify_sources()
    freeze=core.read(s.HERE/'STAGE11_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    prior=core.read(s.HERE/'stage10/RESULT.json');fidelity=core.read(s.HERE/'fidelity_diagnosis/RESULT.json')
    corrected=core.read(s.HERE/'heldout_reference_audit/RESULT.json')
    assert prior['state']=='completed' and fidelity['state']=='completed' and corrected['state']=='completed'
    objective_check=core.read(s.HERE/'STAGE11_OBJECTIVE_VERIFICATION.json')
    assert objective_check['state']=='passed' and objective_check['source_sha256']==core.sha(s.HERE/'stage11_method.py')
    assert prior['cases']['attack_cover850']['state']=='failed_necessary_ASR'
    large_passed=ARMS.copy()
    cpu=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command','Get-CimInstance Win32_Processor | Select-Object NumberOfLogicalProcessors,LoadPercentage | ConvertTo-Json -Compress'],text=True))
    assert cpu['NumberOfLogicalProcessors']>=8 and cpu['LoadPercentage']<=60 and not torch.cuda.is_initialized()
    assert shutil.disk_usage(OUT).free>=4*1024**3
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time(),'CPU':cpu,'candidate_arms':ARMS},f)
    whole=time.monotonic();selected,sealed,states=s.snapshot();cls=sealed.model_class(Path(selected['source_root']))
    info=core.read(s.HERE/'STAGE03_INPUTS.json');assert core.sha(info['clean_path'])==info['clean_path_sha256']
    raw=torch.load(info['clean_path'],map_location='cpu',weights_only=True)
    split=core.read(s.HERE/'PROXY_SPLIT.json');public=raw['test_x'][split['fit_ids']];held=torch.tensor(split['heldout_ids'])
    summary={'state':'running','large_passed_arms':[],'cases':{},'new_FL_seeds':0,
             'scope':'one_existing_BadFU_seed_three_case_necessary_test','FedUBA_evaluated':False}
    for pair,a,b in [('benign_big19336','clean_pre','clean_big_post'),('attack_cover850','pre','post'),('benign_same850','clean_pre','clean_post')]:
        root=OUT/pair;root.mkdir(exist_ok=False);tick=time.monotonic()
        def deadline():assert time.monotonic()-tick<3600 and time.monotonic()-whole<10500,'bounded profile runtime'
        hp=s.OUT/(pair+'_aligned_model.pt')
        assert core.sha(hp)==core.read(s.OUT/'CANDIDATES_BEFORE_EVALUATION.json')['models'][hp.name]
        teacher=torch.load(hp,map_location='cpu',weights_only=True)
        write(root,'SOURCE_INPUTS.json',{'case_id':selected['case_id'],'purpose':'purification_pilot',
            'pre_role':a,'post_role':b,'post_sha256':selected['server_inputs'][b]['sha256'],'teacher_sha256':core.sha(hp)})
        declaration=train_and_select(states[b],teacher,public,cls,root,deadline)
        report=evaluate(pair,a,b,states,declaration,cls,root,info,raw['test_y'].long(),held,large_passed,deadline)
        write(root,'COMPLETED.json',{'result_sha256':core.sha(root/'RESULT.json'),
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
        'source_freeze_sha256':core.sha(s.HERE/'STAGE11_FREEZE.json')})
    print('STAGE11_COMPLETED',flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True);write(OUT,'FAILURE.json',{'traceback':traceback.format_exc()});raise
