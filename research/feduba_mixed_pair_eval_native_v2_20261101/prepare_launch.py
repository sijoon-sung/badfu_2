"""One stdlib metadata preparation for evaluation-only recovery, never starts training/audits."""
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
from evaluation_io import ROOT, OLD, RECOVERY, read, sha, once, source_check, aliases, original_recovery, tensor_path, competing_processes
from native_processes import processes


def meta(path):
    path=Path(path);return {'path':str(path),'sha256':sha(path),'bytes':path.stat().st_size}


def main():
    p=source_check();publication=read(ROOT/'SOURCE_PUBLICATION.json')
    assert publication['state']=='published_closed_evaluation_recovery_source_before_probe_prepare'
    assert publication['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    assert read(ROOT/'METADATA_PROBE_RESULT.json')['state']=='passed_new_native_metadata_source_probe'
    assert read(ROOT/'METADATA_PROBE_DONE.json')['state']=='native_metadata_probe_completed_no_model'
    assert read(ROOT/'METADATA_PROBE_CIM_MATCH.json')['state']=='passed_native_self_PID_parent_commandline_match_external_CIM'
    once('PREPARE_ONCE.json',{'pid':os.getpid(),'model_loads':0,'model_forwards':0})
    original_recovery().require_published_run()
    peers=competing_processes()
    assert not peers,peers
    for n in ['PAIR_EVAL_ONCE.json','PAIR_EVAL_RESULT.json','PAIR_EVAL_AUDIT_ONCE.json','pair_evaluation']:
        assert not (RECOVERY/n).exists(),n
    assert sha(RECOVERY/'FU_attack_VERIFIED.json')==p['required_attack_verified_sha256']
    assert sha(RECOVERY/'FU_attack_RESULT.json')==p['required_attack_result_sha256']
    a=read(RECOVERY/'FU_attack_VERIFIED.json');result=read(RECOVERY/'FU_attack_RESULT.json')
    assert a['state']=='passed' and a['after']==result['after']
    assert (a['rounds'],a['new_trained_roles'],a['actual_local_epochs'],a['actual_batches'])==(20,200,1000,20000)
    assert (a['reused_original_roles'],a['executed_here_roles'])==(46,154)
    selected=json.loads(subprocess.check_output([sys.executable,'-B',str(Path(p['catalog_root'])/'select_case.py'),
        p['case_id'],'--purpose','diagnostic'],text=True,encoding='utf-8',timeout=60))
    assert selected['guard_state']=='all_snapshot_files_verified_on_this_host'
    models={'pre':selected['server_inputs']['pre'],'benign':read(OLD/'FU_benign_RESULT.json')['after'],'attack':result['after']}
    models['pre']=dict(models['pre'],bytes=Path(models['pre']['path']).stat().st_size)
    for name,m in models.items():
        assert m['sha256']==p['required_models'][name]
        path=tensor_path(m);assert sha(path)==m['sha256'] and path.stat().st_size==m['bytes']
    delta=read(OLD/'SSS_RESULT.json')['delta'];assert delta['sha256']==p['required_delta_sha256']
    assert sha(tensor_path(delta))==delta['sha256']
    once('CASE_GUARD.json',{'state':selected['guard_state'],'case_id':p['case_id'],'purpose':'diagnostic','pre':models['pre']})
    inputs=set(aliases().values())|{RECOVERY/'SOURCE_FREEZE.json',RECOVERY/'RUN_FREEZE.json',RECOVERY/'RUN_PUBLICATION.json',
        RECOVERY/'PAIR_EVAL_FAILURE.json',RECOVERY/'RECOVERY_CONTROLLER_FAILURE.json',
        ROOT/'PRIOR_EVALUATION_GUARD_FAILURE_TERMINAL.json',ROOT/'METADATA_PROBE_RESULT.json',
        ROOT/'METADATA_PROBE_DONE.json',ROOT/'METADATA_PROBE_CIM_MATCH.json',ROOT/'CASE_GUARD.json'}
    receipts={str(v):meta(v) for v in sorted(inputs)}
    once('EVALUATION_INPUT_BINDING.json',{'state':'prepared_actual_evaluation_only_recovery_inputs',
        'receipts':receipts,'models':models,'delta':delta,'model_loads':0,'model_forwards':0,
        'training_or_completed_audit_reexecution':False,'old_evaluation_forward_calls':0,
        'original_failure_before_PAIR_EVAL_ONCE':True,'competing_training_processes':0})
    once('LAUNCH_PROFILE.json',{'id':p['id']+'.actual','launch_enabled':True,'input_binding_sha256':sha(ROOT/'EVALUATION_INPUT_BINDING.json'),
        'catalog_root':p['catalog_root'],'case_id':p['case_id'],'primary_sample_forwards':60000,
        'independent_sample_forwards':60000,'primary_calls':474,'independent_calls':474,'numeric_profile_source':str(OLD/'PAIR_EVAL_LAUNCH_PROFILE.json'),
        'training_launch_enabled':False,'full_CPU_FU_audit_launch_enabled':False})
    names=set(read(ROOT/'SOURCE_FREEZE.json')['files'])|{'SOURCE_FREEZE.json','SOURCE_PUBLICATION.json',
        'EVALUATION_INPUT_BINDING.json','LAUNCH_PROFILE.json','METADATA_PROBE_RESULT.json','METADATA_PROBE_DONE.json',
        'METADATA_PROBE_CIM_MATCH.json','CASE_GUARD.json'}
    once('RUN_FREEZE.json',{'state':'frozen_actual_evaluation_only_recovery_inputs','files':{n:sha(ROOT/n) for n in sorted(names)}})
    assert 'torch' not in sys.modules
    once('PREPARE_RESULT.json',{'state':'passed_actual_evaluation_only_metadata_preparation','model_loads':0,'model_forwards':0,
        'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'run_freeze_sha256':sha(ROOT/'RUN_FREEZE.json')})
    print(json.dumps({'state':'passed_actual_evaluation_only_metadata_preparation','model_loads':0,'model_forwards':0}))


if __name__=='__main__':
    try:main()
    except BaseException:
        once('PREPARE_FAILURE.json',{'state':'failed_preserved','pid':os.getpid(),'traceback':traceback.format_exc()});raise
