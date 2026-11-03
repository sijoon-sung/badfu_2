"""New one-time native metadata-only receive-attempt observation; never launches receiver."""
import json,os,sys,time,traceback
from receive_common_v2 import ROOT,read,sha,record,source_checks,native_snapshot
PROFILE_NAME='NATIVE_ATTEMPT_PROFILE_20261103_1516.json'
FREEZE_NAME='NATIVE_ATTEMPT_SOURCE_FREEZE_20261103_1516.json'
PUBLICATION_NAME='NATIVE_ATTEMPT_PUBLICATION_20261103_1516.json'
def main():
    profile=read(ROOT/PROFILE_NAME);pub=read(ROOT/PUBLICATION_NAME)
    assert ROOT==__import__('pathlib').Path(profile['execution_root']) and not profile['actual_receiver_enabled'] and not profile['transfer_enabled'] and not profile['runtime_or_torch_probe_enabled']
    assert pub['state']=='published_new_native_receive_attempt_before_observation' and pub['native_source_freeze_sha256']==sha(ROOT/FREEZE_NAME)
    for n,h in read(ROOT/FREEZE_NAME)['files'].items():assert sha(ROOT/n)==h,n
    assert profile['source_freeze_v2_sha256']==sha(ROOT/'SOURCE_FREEZE_V2.json') and profile['source_profile_v2_sha256']==sha(ROOT/'PROFILE_V2.json')
    p=source_checks();assert not p['receive_enabled']
    record('NATIVE_ATTEMPT_ONCE_20261103_1516.json',{'pid':os.getpid(),'unix':time.time(),'source_freeze_sha256':sha(ROOT/FREEZE_NAME),'one_native_observation_only':True})
    value=native_snapshot(p);value.update(state='completed_native_readiness_observation_only',source_freeze_sha256=sha(ROOT/'SOURCE_FREEZE_V2.json'),native_attempt_source_freeze_sha256=sha(ROOT/FREEZE_NAME),native_attempt_profile_sha256=sha(ROOT/PROFILE_NAME),actual_native_getter=True,synthetic=False,receiver_started=False,runtime_probe_started=False,model_transfer_started=False)
    assert 'torch' not in sys.modules and 'numpy' not in sys.modules
    record(profile['observation_name'],value)
    record(profile['result_name'],{'state':'native_ready_actual_receiver_activation_still_unpublished' if value['native_ready'] else 'native_guard_unmet_actual_receiver_not_started','exit_code':0,'readiness_observation_path':str(ROOT/profile['observation_name']),'readiness_observation_sha256':sha(ROOT/profile['observation_name']),'native_ready':value['native_ready'],'observations':1,'receiver_started':False,'runtime_imported':False,'model_transfer_started':False,'catalogue_modified':False,'old_false_observation_overwritten':False,'waiter_started':False,'overall_goal_complete':False})
    print(json.dumps({'state':'completed_fresh_native_receive_attempt_only','native_ready':value['native_ready'],'available_GiB':value['memory']['availableBytes']/2**30,'commit_free_GiB':(value['memory']['commitLimit']-value['memory']['committedBytes'])/2**30,'receiver_started':False}))
if __name__=='__main__':
    try:main()
    except BaseException:record('NATIVE_ATTEMPT_FAILURE_20261103_1516.json',{'state':'failed_preserved_no_retry','traceback':traceback.format_exc()});raise
