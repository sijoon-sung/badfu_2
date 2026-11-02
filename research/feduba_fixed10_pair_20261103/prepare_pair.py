"""Bind completed new fixed10 history and new SSS, with no model loads or queries."""
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
from pair_binding import ROOT,FOUNDATION,read,sha,checked,source_profile
def once(n,v):
    with (ROOT/n).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def meta(p):return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
def main():
    p=source_profile();pub=read(ROOT/'SOURCE_PUBLICATION.json')
    assert pub['state']=='published_fixed10_pair_source_before_prepare' and pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    assert read(ROOT/'SOURCE_REVIEW_RESULT.json')['state']=='passed_fixed10_pair_source_only'
    for m in p['inputs'].values():checked(m)
    terminal=read(ROOT/'UPSTREAM_TERMINAL_CHECK.json')
    assert len(terminal['tasks'])==3
    assert [v['task_name'] for v in terminal['tasks']]==['Codex-FedUBA-public-fixed10-cleanFL20-20261103','Codex-FedUBA-public-fixed10-clean-review-export-CPU-20261103','Codex-FedUBA-public-fixed10-newSSS5000-20261103']
    assert all(v['state']=='Ready' and v['last_result']==0 and v['native_process_count']==0 for v in terminal['tasks'])
    assert sha(FOUNDATION/'SOURCE_FREEZE.json')==p['foundation_source_freeze_sha256'] and sha(FOUNDATION/'RUN_FREEZE.json')==p['foundation_run_freeze_sha256']
    sss=Path(p['sss_root']);assert sha(sss/'SOURCE_FREEZE.json')==p['SSS_source_freeze_sha256']
    for directory,names in [(FOUNDATION,['FOUNDATION_CONTROLLER_FAILURE.json','CLEAN_FL_FAILURE.json','CLEAN_FL_AUDIT_FAILURE.json']),
                            (sss,['SSS_CONTROLLER_FAILURE.json','SSS_FAILURE.json','SSS_AUDIT_FAILURE.json'])]:
        for n in names:assert not (directory/n).exists(),str(directory/n)
    fdone=read(FOUNDATION/'COMPLETION.json');faudit=read(FOUNDATION/'CLEAN_FL_VERIFIED.json');fresult=read(FOUNDATION/'CLEAN_FL_RESULT.json')
    assert fdone['state']=='completed_fixed10_cleanFL20_and_independent_audit' and fdone['result_sha256']==sha(FOUNDATION/'CLEAN_FL_RESULT.json') and fdone['verified_sha256']==sha(FOUNDATION/'CLEAN_FL_VERIFIED.json')
    assert faudit['state']=='passed' and (faudit['rounds'],faudit['roles'],faudit['actual_local_epoch_logs'],faudit['actual_batches'])==(20,200,2000,40000)
    assert len(faudit['history_hashes'])==220 and faudit['independent_N']==10000
    sd=read(sss/'COMPLETION.json');selection=read(sss/'SSS_RESULT.json');audit=read(sss/'SSS_VERIFIED.json')
    assert sd['state']=='completed_new_fixed10_SSS5000_and_independent_score_query_audit' and sd['result_sha256']==sha(sss/'SSS_RESULT.json') and sd['verified_sha256']==sha(sss/'SSS_VERIFIED.json')
    assert selection['case_id']==p['normal_case_id'] and selection['observed_samples']==5000 and selection['query_batches']==40 and selection['actual_forward_calls']==80
    assert selection['eligible_class']==2 and selection['selected_class_counts']==[0,0,125,0,0,0,0,0,0,0]
    assert audit['state']=='passed' and audit['SSS_result_sha256']==sha(sss/'SSS_RESULT.json') and audit['selected_by_owner']==selection['selected_by_owner'] and audit['float64_top125_same_ID_sets']
    assert selection['delta']['sha256']==p['required_delta_sha256'] and selection['trigger_binding_sha256']==audit['trigger_binding_sha256']==sha(ROOT/'TRIGGER_SOURCE_BINDING.json')
    selected=json.loads(subprocess.check_output([sys.executable,'-B',str(Path(p['catalog_root'])/'select_case.py'),p['normal_case_id'],'--purpose','diagnostic'],text=True,encoding='utf-8'))
    assert selected['case_id']==p['normal_case_id'] and selected['guard_state']=='all_snapshot_files_verified_on_this_host'
    pre=selected['server_inputs']['pre'];checked(pre)
    assert pre['payload_key'] is None and pre['sha256']==selection['pre_checkpoint']['sha256']==fresult['before']['sha256']
    history=read(FOUNDATION/'clean_fl/MANIFEST.json');parts=read(FOUNDATION/'CLEAN_SPLIT.json')['indices']
    assert len(history['rounds'])==20 and all(row['clients']==p['fixed_selected_clients'] for row in history['rounds'])
    counts={int(k):len(v) for k,v in selection['selected_by_owner'].items()}
    assert sorted(counts)==[5,7] and sum(counts.values())==125
    for owner,ids in selection['selected_by_owner'].items():
        assert len(ids)==len(set(ids)) and set(ids).issubset(set(parts[int(owner)]))
    attack_batches=benign_batches=exposures=0
    for row in history['rounds']:
        for client in row['clients']:
            n=len(parts[client]);assert n==2500
            removed=counts.get(client,0)
            attack_batches+=5*((n+127)//128)
            benign_batches+=5*((n-removed+127)//128)
            exposures+=5*removed
    assert attack_batches==20000 and exposures==12500
    fu=read(ROOT/'FU_PROFILE.json');old=read(p['inputs']['original_FU_actual_profile']['path'])
    for k in ['history_global_payload_key','history_role_payload_key']:assert k in fu and fu[k]==old[k]
    keys={node.slice.value for n in ['fu_runner.py','verify_fu.py'] for node in ast.walk(ast.parse((ROOT/n).read_text())) if isinstance(node,ast.Subscript) and isinstance(node.value,ast.Name) and node.value.id=='p' and isinstance(node.slice,ast.Constant) and isinstance(node.slice.value,str)}
    assert keys.issubset(set(fu)|{'history_manifest_sha256','trigger_binding_sha256'})
    once('PREPARE_ONCE.json',{'pid':os.getpid(),'new_model_loads':0,'new_queries':0,'new_SSS_selection_bound':True})
    for source,names in [(FOUNDATION,['CLEAN_FL_RESULT.json','CLEAN_FL_VERIFIED.json','CLEAN_FL_READY.json','CLEAN_FL_PROFILE.json']),
                         (sss,['SSS_RESULT.json','SSS_VERIFIED.json'])]:
        for n in names:
            assert not (ROOT/n).exists();shutil.copyfile(source/n,ROOT/n);assert sha(ROOT/n)==sha(source/n)
    once('NORMAL_CASE_SELECTION.json',selected)
    receipts={}
    for prefix,directory,names in [('foundation',FOUNDATION,['SOURCE_FREEZE.json','RUN_FREEZE.json','CLEAN_FL_RESULT.json','CLEAN_FL_VERIFIED.json','COMPLETION.json']),
                                   ('new_SSS',sss,['SOURCE_FREEZE.json','RUN_FREEZE.json','SSS_RESULT.json','SSS_VERIFIED.json','COMPLETION.json'])]:
        for n in names:receipts[prefix+'/'+n]=meta(directory/n)
    once('FOUNDATION_INPUT_BINDING.json',{'state':'completed_new_fixed10_foundation_and_new_SSS_bound_before_FU','pre':pre,
        'manifest':meta(FOUNDATION/'clean_fl/MANIFEST.json'),'split':meta(FOUNDATION/'CLEAN_SPLIT.json'),'receipts':receipts,
        'selected_counts_by_owner':{str(k):v for k,v in counts.items()},'expected_benign_batches':benign_batches,'expected_attack_batches':attack_batches,
        'selected_sample_epoch_exposures':exposures,'no_old_pre_SSS_rank_or_after_reuse':True})
    fu.update(launch_enabled=True,history_manifest_sha256=sha(FOUNDATION/'clean_fl/MANIFEST.json'),trigger_binding_sha256=sha(ROOT/'TRIGGER_SOURCE_BINDING.json'))
    once('FU_LAUNCH_PROFILE.json',fu)
    ev=read(ROOT/'PAIR_EVAL_PROFILE.json');ev.update(launch_enabled=True,trigger_binding_sha256=fu['trigger_binding_sha256']);once('PAIR_EVAL_LAUNCH_PROFILE.json',ev)
    once('PREPARATION_RESULT.json',{'state':'new_fixed10_newSSS125_pair_prepared_model0','selected_counts_by_owner':{str(k):v for k,v in counts.items()},
        'expected_benign_batches':benign_batches,'expected_attack_batches':attack_batches,'selected_sample_epoch_exposures':exposures,
        'new_model_loads':0,'new_queries':0,'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json')})
    once('LAUNCH_PROFILE.json',{'id':'feduba.public_fixed10.targetclass125.pairedFU20.s42.20261103','launch_enabled':True,'selected_IDs':125,
        'case_id':p['normal_case_id'],'execution_root':str(ROOT),'pre_sha256':pre['sha256'],'selection_sha256':sha(ROOT/'SSS_RESULT.json'),
        'selection_audit_sha256':sha(ROOT/'SSS_VERIFIED.json'),'foundation_binding_sha256':sha(ROOT/'FOUNDATION_INPUT_BINDING.json'),
        'preparation_sha256':sha(ROOT/'PREPARATION_RESULT.json'),'FU_benign_batches':benign_batches,'FU_attack_batches':attack_batches,
        'each_FU_rounds':20,'each_FU_epochs':1000,'primary_and_independent_each_calls':474,'primary_and_independent_each_sample_forwards':60000,
        'reuse_old_FU_after_models':False,'fixed_selected_clients':p['fixed_selected_clients']})
    files=dict(read(ROOT/'SOURCE_FREEZE.json')['files'])
    for n in ['SOURCE_FREEZE.json','SSS_RESULT.json','SSS_VERIFIED.json','CLEAN_FL_RESULT.json','CLEAN_FL_VERIFIED.json','CLEAN_FL_READY.json','CLEAN_FL_PROFILE.json','FU_LAUNCH_PROFILE.json','PAIR_EVAL_LAUNCH_PROFILE.json','LAUNCH_PROFILE.json','PREPARATION_RESULT.json','NORMAL_CASE_SELECTION.json','FOUNDATION_INPUT_BINDING.json','UPSTREAM_TERMINAL_CHECK.json']:files[n]=sha(ROOT/n)
    for n in ['RUN_FREEZE.json','FU_RUN_FREEZE.json','PAIR_EVAL_RUN_FREEZE.json']:once(n,{'state':'actual_fixed10_newSSS_pair_frozen_before_training','files':files})
    assert 'torch' not in sys.modules
    print(json.dumps(read(ROOT/'LAUNCH_PROFILE.json')))
if __name__=='__main__':
    try:main()
    except BaseException:
        once('PREPARE_FAILURE.json',{'state':'failed_preserved','traceback':traceback.format_exc()});raise
