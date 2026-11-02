"""Prepare metadata only after the new foundation really completed; no torch import."""
import json
import os
from pathlib import Path
import traceback
from clean_delivery_binding import ROOT,read,sha,source_profile
from native_processes import processes
def once(n,v):
    with (ROOT/n).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def main():
    p=source_profile();pub=read(ROOT/'SOURCE_PUBLICATION.json')
    assert pub['state']=='published_fixed10_clean_delivery_source_before_prepare'
    assert pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    foundation=Path(p['foundation_root'])
    assert sha(foundation/'SOURCE_FREEZE.json')==p['foundation_source_freeze_sha256']
    assert sha(foundation/'RUN_FREEZE.json')==p['foundation_run_freeze_sha256']
    assert not any(p['foundation_root'].lower() in r['CommandLine'].replace('\\','/').lower() for r in processes())
    assert not list(foundation.glob('*FAILURE.json'))
    done,result,audit,history,ready=[read(foundation/n) for n in ['COMPLETION.json','CLEAN_FL_RESULT.json','CLEAN_FL_VERIFIED.json','clean_fl/MANIFEST.json','CLEAN_FL_READY.json']]
    assert done['state']=='completed_fixed10_cleanFL20_and_independent_audit'
    assert done['result_sha256']==sha(foundation/'CLEAN_FL_RESULT.json') and done['verified_sha256']==sha(foundation/'CLEAN_FL_VERIFIED.json')
    assert result['state']=='completed_clean_FL20' and audit['state']=='passed'
    assert (audit['rounds'],audit['roles'],audit['actual_local_epoch_logs'],audit['actual_batches'],audit['independent_N'])==(20,200,2000,40000,10000)
    assert len(audit['history_hashes'])==220 and audit['independent_clean_correct']==result['evaluation']['clean_correct']
    assert len(history['rounds'])==20 and all(r['clients']==[2,3,5,7,9,12,13,16,18,19] for r in history['rounds'])
    terminal=read(ROOT/'FOUNDATION_TERMINAL_CHECK.json')
    assert terminal['task_name']==p['foundation_task'] and terminal['state']=='Ready' and terminal['last_result']==0 and terminal['native_process_count']==0
    once('PREPARE_ONCE.json',{'pid':os.getpid(),'model_loads':0,'model_forwards':0})
    def bound(meta,key):
        path=(foundation/meta['path']).resolve();assert path.is_relative_to(foundation.resolve())
        assert sha(path)==meta['sha256'] and path.stat().st_size==meta['bytes']
        return dict(meta,path=str(path),payload_key=key)
    payloads={'run/before.pt':bound(result['before'],None),'run/initial.pt':bound(ready['fresh_initial'],None),
              'run/last_role.pt':bound(history['rounds'][-1]['roles'][-1]['checkpoint'],'model')}
    receipts={n:sha(foundation/n) for n in ['SOURCE_FREEZE.json','RUN_FREEZE.json','RUN_PUBLICATION.json','CLEAN_FL_RESULT.json','CLEAN_FL_VERIFIED.json','COMPLETION.json','clean_fl/MANIFEST.json']}
    once('FOUNDATION_INPUT_BINDING.json',{'case_id':p['normal_case_id'],'foundation_root':str(foundation),'receipt_sha256':receipts,'payloads':payloads,
        'fixed_cohort':[2,3,5,7,9,12,13,16,18,19],'clean_correct':audit['independent_clean_correct'],'CA_pct':audit['CA_pct'],'last_role_client':19})
    once('LAUNCH_PROFILE.json',{'id':'feduba.public_fixed10.clean_review.actual.20261103','launch_enabled':True,'case_id':p['normal_case_id'],
        'CPU_threads':1,'CUDA_VISIBLE_DEVICES':'-1','CPU_zero1_calls':3,'performance_evaluation_calls':0,
        'input_binding_sha256':sha(ROOT/'FOUNDATION_INPUT_BINDING.json'),'foundation_terminal_sha256':sha(ROOT/'FOUNDATION_TERMINAL_CHECK.json')})
    files=dict(read(ROOT/'SOURCE_FREEZE.json')['files'])
    for n in ['SOURCE_FREEZE.json','FOUNDATION_INPUT_BINDING.json','FOUNDATION_TERMINAL_CHECK.json','LAUNCH_PROFILE.json']:files[n]=sha(ROOT/n)
    for n in ['RUN_FREEZE.json','CLEAN_EXPORT_FREEZE.json','CLEAN_REGISTRATION_FREEZE.json']:once(n,{'state':'actual_fixed10_clean_review_frozen_before_export','files':files})
    print(json.dumps(read(ROOT/'LAUNCH_PROFILE.json')))
if __name__=='__main__':
    try:main()
    except BaseException:
        once('PREPARE_FAILURE.json',{'state':'failed_preserved','traceback':traceback.format_exc()});raise
