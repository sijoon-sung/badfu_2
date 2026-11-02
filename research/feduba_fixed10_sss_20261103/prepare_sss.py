"""One stdlib preparation after actual new foundation and normal-case registration."""
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
def meta(p,payload_key=None):
    return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'payload_key':payload_key}
def main():
    p=source_profile();pub=read(ROOT/'SOURCE_PUBLICATION.json')
    assert pub['state']=='published_fixed10_newSSS_source_before_prepare'
    assert pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    assert read(ROOT/'SOURCE_REVIEW_RESULT.json')['state']=='passed_fixed10_newSSS_source_only'
    terminal=read(ROOT/'FOUNDATION_TERMINAL_CHECK.json')
    for t in terminal['tasks']:
        assert t['state']=='Ready' and t['last_result']==0 and t['native_process_count']==0
    assert [t['task_name'] for t in terminal['tasks']]==[p['foundation_task'],'Codex-FedUBA-public-fixed10-clean-review-export-CPU-20261103']
    assert sha(FOUNDATION/'SOURCE_FREEZE.json')==p['foundation_source_freeze_sha256']
    assert sha(FOUNDATION/'RUN_FREEZE.json')==p['foundation_run_freeze_sha256']
    for n in ['CLEAN_FL_FAILURE.json','CLEAN_FL_AUDIT_FAILURE.json','FOUNDATION_CONTROLLER_FAILURE.json']:
        assert not (FOUNDATION/n).exists(),n
    complete=read(FOUNDATION/'COMPLETION.json');result=read(FOUNDATION/'CLEAN_FL_RESULT.json');audit=read(FOUNDATION/'CLEAN_FL_VERIFIED.json')
    assert complete['state']=='completed_fixed10_cleanFL20_and_independent_audit'
    assert complete['result_sha256']==sha(FOUNDATION/'CLEAN_FL_RESULT.json') and complete['verified_sha256']==sha(FOUNDATION/'CLEAN_FL_VERIFIED.json')
    assert audit['state']=='passed' and audit['rounds']==20 and audit['roles']==200 and audit['actual_local_epoch_logs']==2000 and audit['actual_batches']==40000
    assert audit['independent_N']==10000 and len(audit['history_hashes'])==220
    manifest=read(FOUNDATION/'clean_fl/MANIFEST.json')
    assert len(manifest['rounds'])==20 and all(r['clients']==[2,3,5,7,9,12,13,16,18,19] for r in manifest['rounds'])
    delivery=Path('D:/FEDUBA_FIXED10_CLEAN_DELIVERY_20261103')
    assert not (delivery/'CLEAN_EXPORT_FAILURE.json').exists()
    assert read(delivery/'registrations/clean_dislab/REGISTERED.json')['case_id']==p['normal_case_id']
    selected=json.loads(subprocess.check_output([sys.executable,'-B',str(Path(p['catalog_root'])/'select_case.py'),p['normal_case_id'],'--purpose','diagnostic'],text=True,encoding='utf-8'))
    assert selected['guard_state']=='all_snapshot_files_verified_on_this_host' and selected['case_id']==p['normal_case_id']
    pre=selected['server_inputs']['pre'];checked(pre)
    assert pre['payload_key'] is None and pre['sha256']==result['before']['sha256']
    once('PREPARE_ONCE.json',{'pid':os.getpid(),'model_loads':0,'model_forwards':0,'new_pre_bound':True})
    once('NORMAL_CASE_SELECTION.json',selected)
    receipts={}
    for n in ['SOURCE_FREEZE.json','RUN_FREEZE.json','CLEAN_FL_RESULT.json','CLEAN_FL_VERIFIED.json','CLEAN_FL_READY.json','CLEAN_FL_PROFILE.json','COMPLETION.json']:
        receipts[n]=meta(FOUNDATION/n)
    for n in ['CLEAN_FL_RESULT.json','CLEAN_FL_VERIFIED.json','CLEAN_FL_READY.json','CLEAN_FL_PROFILE.json']:
        assert not (ROOT/n).exists();shutil.copyfile(FOUNDATION/n,ROOT/n)
    binding={'state':'new_fixed10_completed_foundation_and_sealed_registered_pre_bound','pre':pre,'split':meta(FOUNDATION/'CLEAN_SPLIT.json'),
        'manifest':meta(FOUNDATION/'clean_fl/MANIFEST.json'),'receipts':receipts,'case_selection_sha256':sha(ROOT/'NORMAL_CASE_SELECTION.json'),
        'normal_export_receipt':meta(delivery/'CLEAN_REVIEW_DELIVERY_REMOTE.json'),'registration_receipt':meta(delivery/'registrations/clean_dislab/REGISTERED.json'),
        'no_old_SSS_ranks_or_after_model_reuse':True}
    once('FOUNDATION_INPUT_BINDING.json',binding)
    s=read(ROOT/'SSS_PROFILE.json');s.update(launch_enabled=True,pre_checkpoint=pre,foundation_binding_sha256=sha(ROOT/'FOUNDATION_INPUT_BINDING.json'))
    once('SSS_LAUNCH_PROFILE.json',s)
    once('GPU_PREFLIGHT_RESULT.json',{'state':'fixed_guard_copied_no_new_GPU_probe','foundation_free_min_MiB':4000})
    once('LAUNCH_PROFILE.json',{'id':'feduba.public_fixed10.newSSS5000.targetclass125.s42.20261103','launch_enabled':True,
        'case_id':p['normal_case_id'],'new_SSS_samples':5000,'new_GPU_calls':80,'new_GPU_sample_forwards':10000,
        'CPU_fixed_batch_replay_calls':4,'CPU_fixed_batch_replay_sample_forwards':400,'eligible_class':2,'request_budget':125,
        'pre_sha256':pre['sha256'],'delta_sha256':s['bound_delta']['sha256'],'no_FU_started_by_this_task':True})
    files=dict(read(ROOT/'SOURCE_FREEZE.json')['files'])
    for n in ['SOURCE_FREEZE.json','FOUNDATION_INPUT_BINDING.json','FOUNDATION_TERMINAL_CHECK.json','NORMAL_CASE_SELECTION.json','CLEAN_FL_RESULT.json','CLEAN_FL_VERIFIED.json','CLEAN_FL_READY.json','CLEAN_FL_PROFILE.json','SSS_LAUNCH_PROFILE.json','GPU_PREFLIGHT_RESULT.json','LAUNCH_PROFILE.json']:files[n]=sha(ROOT/n)
    for n in ['RUN_FREEZE.json','SSS_FREEZE.json']:once(n,{'state':'actual_new_fixed10_SSS_frozen_before_query','files':files})
    assert 'torch' not in sys.modules
    print(json.dumps(read(ROOT/'LAUNCH_PROFILE.json')))
if __name__=='__main__':
    try:main()
    except BaseException:
        once('PREPARE_FAILURE.json',{'state':'failed_preserved','traceback':traceback.format_exc()});raise
