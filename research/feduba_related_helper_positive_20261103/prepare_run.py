"""One stdlib-only binding of preserved baselines and same selection, before new FU."""
import ast,json,os,shutil,subprocess,sys,traceback
from pathlib import Path
from pair_binding import ROOT,FOUNDATION,read,sha,checked,source_profile

def once(n,v):
    with (ROOT/n).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def meta(path):return {'path':str(path),'sha256':sha(path),'bytes':path.stat().st_size}
def main():
    p=source_profile();assert read(ROOT/'SOURCE_PUBLICATION.json')['state']=='published_related_helper_positive_source_before_contract_and_prepare'
    assert read(ROOT/'SOURCE_REVIEW_RESULT.json')['state']=='passed_sign_only_source_review'
    assert read(ROOT/'SIGN_CONTRACT_RESULT.json')['state']=='passed'
    for m in p['baseline_receipts'].values():checked(m)
    baseline=Path(p['baseline_root']);sss=Path(p['sss_root'])
    terminal=read(ROOT/'UPSTREAM_TERMINAL_CHECK.json')
    assert len(terminal['tasks'])==4 and all(v['state']=='Ready' and v['last_result']==0 and v['native_process_count']==0 and v['level']=='Limited' for v in terminal['tasks'])
    for directory,names in [(baseline,['CONTROLLER_FAILURE.json','FU_benign_FAILURE.json','FU_benign_AUDIT_FAILURE.json','FU_attack_FAILURE.json','FU_attack_AUDIT_FAILURE.json','PAIR_EVAL_FAILURE.json','PAIR_EVAL_AUDIT_FAILURE.json','EXPORT_FAILURE.json']), (FOUNDATION,['FOUNDATION_CONTROLLER_FAILURE.json','CLEAN_FL_FAILURE.json','CLEAN_FL_AUDIT_FAILURE.json']), (sss,['SSS_CONTROLLER_FAILURE.json','SSS_FAILURE.json','SSS_AUDIT_FAILURE.json'])]:
        for n in names:assert not (directory/n).exists(),str(directory/n)
    # Historical transport/readback failures live in separate local metadata and do not replace producer terminal evidence.
    assert read(baseline/'COMPLETION.json')['evaluation_sha256']==p['baseline_receipts']['PAIR_EVAL_RESULT.json']['sha256']
    for b in ['benign','attack']:
        r=read(baseline/('FU_'+b+'_RESULT.json'));v=read(baseline/('FU_'+b+'_VERIFIED.json'))
        assert r['state']=='completed_FU20' and v['state']=='passed'
        assert (v['rounds'],v['new_trained_roles'],v['actual_local_epochs'],v['actual_batches'])==(20,200,1000,20000)
        assert len(v['history_hashes'])==420 and r['after']==v['after']
        checked(dict(r['after'],path=str(baseline/r['after']['path'])))
    assert read(baseline/'PAIR_EVAL_VERIFIED.json')['state']=='passed'
    assert sha(FOUNDATION/'SOURCE_FREEZE.json')==p['foundation_source_freeze_sha256'] and sha(FOUNDATION/'RUN_FREEZE.json')==p['foundation_run_freeze_sha256']
    assert sha(sss/'SOURCE_FREEZE.json')==p['SSS_source_freeze_sha256']
    assert sha(sss/'SSS_RESULT.json')==p['reused_SSS_result_sha256'] and sha(sss/'SSS_VERIFIED.json')==p['reused_SSS_verified_sha256']
    selection=read(sss/'SSS_RESULT.json');audit=read(sss/'SSS_VERIFIED.json')
    assert selection['observed_samples']==5000 and selection['query_batches']==40 and selection['actual_forward_calls']==80
    assert selection['eligible_class']==2 and selection['selected_class_counts']==[0,0,125,0,0,0,0,0,0,0]
    assert audit['state']=='passed' and selection['selected_by_owner']==audit['selected_by_owner'] and audit['float64_top125_same_ID_sets']
    assert selection['delta']['sha256']==p['required_delta_sha256'] and selection['trigger_binding_sha256']==audit['trigger_binding_sha256']==sha(ROOT/'TRIGGER_SOURCE_BINDING.json')
    selected=json.loads(subprocess.check_output([sys.executable,'-B',str(Path(p['catalog_root'])/'select_case.py'),p['normal_case_id'],'--purpose','diagnostic'],text=True,encoding='utf-8'))
    assert selected['guard_state']=='all_snapshot_files_verified_on_this_host' and selected['case_id']==p['normal_case_id']
    assert selected['server_inputs']['pre']['sha256']==selection['pre_checkpoint']['sha256']==read(ROOT/'FOUNDATION_INPUT_BINDING.json')['pre']['sha256']
    checked(selected['server_inputs']['pre'])
    data_root=Path(read(ROOT/'CLEAN_FL_PROFILE.json')['data_root'])/'cifar-10-batches-py'
    for n,digest in read(ROOT/'CLEAN_FL_READY.json')['data_files_sha256'].items():assert sha(data_root/n)==digest,n
    binding=read(ROOT/'FOUNDATION_INPUT_BINDING.json')
    for m in binding['receipts'].values():checked(m)
    checked(binding['manifest']);checked(binding['split'])
    history=read(binding['manifest']['path']);parts=read(binding['split']['path'])['indices']
    counts={int(k):len(v) for k,v in selection['selected_by_owner'].items()}
    assert counts=={5:63,7:62}
    for c,ids in selection['selected_by_owner'].items():assert len(ids)==len(set(ids)) and set(ids).issubset(parts[int(c)])
    assert all(row['clients']==p['fixed_selected_clients'] for row in history['rounds'])
    batches=sum(5*((len(parts[c])+127)//128) for row in history['rounds'] for c in row['clients'])
    exposures=sum(5*counts.get(c,0) for row in history['rounds'] for c in row['clients'])
    assert len(history['rounds'])==20 and batches==20000 and exposures==12500
    fu=read(ROOT/'FU_PROFILE.json');old=read(baseline/'FU_LAUNCH_PROFILE.json')
    assert fu['history_global_payload_key'] is None and fu['history_role_payload_key']=='model'
    assert fu['minimum_operational_latent_pair_gate']==old['minimum_operational_latent_pair_gate']
    required={n.slice.value for f in ['fu_runner.py','verify_fu.py'] for n in ast.walk(ast.parse((ROOT/f).read_text(encoding='utf-8'))) if isinstance(n,ast.Subscript) and isinstance(n.value,ast.Name) and n.value.id=='p' and isinstance(n.slice,ast.Constant) and isinstance(n.slice.value,str)}
    assert required.issubset(set(fu)|{'history_manifest_sha256','trigger_binding_sha256'})
    once('PREPARE_ONCE.json',{'pid':os.getpid(),'model_loads':0,'queries':0})
    for n in ['SSS_RESULT.json','SSS_VERIFIED.json']:
        assert not (ROOT/n).exists();shutil.copyfile(sss/n,ROOT/n)
    once('NORMAL_CASE_SELECTION.json',selected)
    receipts=dict(p['baseline_receipts'])
    receipts['source_review']=meta(ROOT/'SOURCE_REVIEW_RESULT.json');receipts['sign_contract']=meta(ROOT/'SIGN_CONTRACT_RESULT.json')
    once('BASELINE_INPUT_BINDING.json',{'state':'original_normal_minus_and_eval_explicitly_reused_not_retrained','receipts':receipts,'old_sealed_review_unchanged':True,'source_helper_sign_only_alternative_not_Eq8_conformant':True})
    fu.update(launch_enabled=True,history_manifest_sha256=binding['manifest']['sha256'],trigger_binding_sha256=sha(ROOT/'TRIGGER_SOURCE_BINDING.json'))
    once('FU_LAUNCH_PROFILE.json',fu)
    once('PREPARATION_RESULT.json',{'state':'positive_sign_attack_prepared_model0','source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'selected_counts_by_owner':{'5':63,'7':62},'expected_attack_batches':batches,'selected_sample_epoch_exposures':exposures,'reused_normal_training_batches':20000,'new_normal_training_batches':0,'new_SSS_queries':0,'new_model_loads':0})
    once('LAUNCH_PROFILE.json',{'id':'feduba.related_helper_positive.FU20.s42.20261103','launch_enabled':True,'execution_root':str(ROOT),'selected_IDs':125,'new_FU_branches':['attack'],'case_id':p['normal_case_id'],'pre_sha256':selection['pre_checkpoint']['sha256'],'selection_sha256':sha(ROOT/'SSS_RESULT.json'),'selection_audit_sha256':sha(ROOT/'SSS_VERIFIED.json'),'FU_attack_batches':20000,'FU_attack_rounds':20,'FU_attack_epochs':1000,'selected_sample_epoch_exposures':12500,'baseline_binding_sha256':sha(ROOT/'BASELINE_INPUT_BINDING.json'),'later_performance_evaluation_required':True,'overall_goal_complete':False})
    files=dict(read(ROOT/'SOURCE_FREEZE.json')['files'])
    for n in ['SOURCE_FREEZE.json','SSS_RESULT.json','SSS_VERIFIED.json','NORMAL_CASE_SELECTION.json','SOURCE_REVIEW_RESULT.json','SIGN_CONTRACT_RESULT.json','FU_LAUNCH_PROFILE.json','LAUNCH_PROFILE.json','BASELINE_INPUT_BINDING.json','PREPARATION_RESULT.json','UPSTREAM_TERMINAL_CHECK.json']:files[n]=sha(ROOT/n)
    for n in ['RUN_FREEZE.json','FU_RUN_FREEZE.json']:once(n,{'state':'positive_sign_actual_inputs_frozen_before_training','files':files})
    assert 'torch' not in sys.modules
    print(json.dumps(read(ROOT/'LAUNCH_PROFILE.json')))
if __name__=='__main__':
    try:main()
    except BaseException:
        once('PREPARE_FAILURE.json',{'state':'failed_preserved','traceback':traceback.format_exc()});raise
