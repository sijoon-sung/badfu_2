"""Metadata-only same-selection recovery; no torch or checkpoint load."""
import json
import os
from pathlib import Path
import shutil
import traceback
from pair_binding import ROOT, source_profile, read, sha, checked

def once(n,v):
    with (ROOT/n).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())

def main():
    p=source_profile();pub=read(ROOT/'SOURCE_PUBLICATION.json')
    assert pub['state']=='published_targetclass_source_before_metadata_preparation'
    assert pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    for v in p['inputs'].values():checked(v)
    prior=read(p['inputs']['prior_preparation']['path'])
    assert prior['new_selected_class_counts']==[0,0,125,0,0,0,0,0,0,0]
    assert prior['selected_counts_by_owner']=={'5':58,'7':67}
    assert prior['expected_benign_batches']==prior['expected_attack_batches']==20000
    assert 'history_global_payload_key' in read(p['inputs']['prior_FU_failure']['path'])['traceback']
    once('PREPARE_ONCE.json',{'pid':os.getpid(),'model_loads':0,'model_queries':0,'reused_selection':True})
    for key,n in [('prior_selection','SSS_RESULT.json'),('prior_selection_audit','SSS_VERIFIED.json'),('prior_case','NORMAL_CASE_SELECTION.json')]:
        assert not (ROOT/n).exists();shutil.copyfile(p['inputs'][key]['path'],ROOT/n)
        assert sha(ROOT/n)==p['inputs'][key]['sha256']
    selection,audit=read(ROOT/'SSS_RESULT.json'),read(ROOT/'SSS_VERIFIED.json')
    assert audit['state']=='passed' and audit['SSS_result_sha256']==sha(ROOT/'SSS_RESULT.json')
    assert selection['selected_by_owner']==audit['selected_by_owner'] and sum(map(len,selection['selected_by_owner'].values()))==125
    fu=read(ROOT/'FU_PROFILE.json');old=read(p['inputs']['original_FU_actual_profile']['path'])
    for key in ['history_global_payload_key','history_role_payload_key']:assert fu[key]==old[key]
    fu.update(launch_enabled=True,history_manifest_sha256=p['foundation_history_manifest']['sha256'],trigger_binding_sha256=sha(ROOT/'TRIGGER_SOURCE_BINDING.json'))
    once('FU_LAUNCH_PROFILE.json',fu)
    ev=read(ROOT/'PAIR_EVAL_PROFILE.json');ev.update(launch_enabled=True,trigger_binding_sha256=fu['trigger_binding_sha256']);once('PAIR_EVAL_LAUNCH_PROFILE.json',ev)
    once('PREPARATION_RESULT.json',dict(prior,state='same_condition_targetclass_selection_reused_payload_binding_restored',source_freeze_sha256=sha(ROOT/'SOURCE_FREEZE.json'),prior_preparation_sha256=p['inputs']['prior_preparation']['sha256'],new_model_loads=0,new_model_queries=0))
    once('LAUNCH_PROFILE.json',{'id':'feduba.targetclass125.pairedFU20.payload_binding_recovery.20261102','launch_enabled':True,'execution_root':str(ROOT),'selected_IDs':125,
        'selection_sha256':sha(ROOT/'SSS_RESULT.json'),'selection_audit_sha256':sha(ROOT/'SSS_VERIFIED.json'),'preparation_sha256':sha(ROOT/'PREPARATION_RESULT.json'),
        'FU_benign_batches':20000,'FU_attack_batches':20000,'each_FU_rounds':20,'each_FU_epochs':1000,'primary_and_independent_each_calls':474,
        'primary_and_independent_each_sample_forwards':60000,'reuse_old_FU_after_models':False,'recovery_only_payload_binding':True})
    files=dict(read(ROOT/'SOURCE_FREEZE.json')['files'])
    for n in ['SOURCE_FREEZE.json','SSS_RESULT.json','SSS_VERIFIED.json','FU_LAUNCH_PROFILE.json','PAIR_EVAL_LAUNCH_PROFILE.json','LAUNCH_PROFILE.json','PREPARATION_RESULT.json','NORMAL_CASE_SELECTION.json']:files[n]=sha(ROOT/n)
    for n in ['RUN_FREEZE.json','FU_RUN_FREEZE.json','PAIR_EVAL_RUN_FREEZE.json']:once(n,{'state':'actual_targetclass_pair_frozen_before_training','files':files})
    print(json.dumps(read(ROOT/'LAUNCH_PROFILE.json')))

if __name__=='__main__':
    try:main()
    except BaseException:
        once('PREPARE_FAILURE.json',{'state':'failed_preserved','traceback':traceback.format_exc()});raise
