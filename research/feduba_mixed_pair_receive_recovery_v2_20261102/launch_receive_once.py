"""Create and demand-start exactly one own Limited task, never update or retry."""
import os,sys
from pathlib import Path
from receive_ops import ROOT,now,read,write,digest,frozen,own_processes,absence,task,task_absent
def main():
    p=frozen();absence(p)
    assert not own_processes(),'Old/duplicate receiver alive'
    assert not (ROOT/'RECEIVE_ONCE.json').exists()
    assert not (ROOT/'RECEIVE_FAILURE.json').exists()
    before=task_absent(p['task_name'])
    write(ROOT/'TASK_ONCE.json',{'utc':now(),'state':'exclusive_task_creation_claim',
          'pid':os.getpid(),'task_name':p['task_name'],'task_absence':before,
          'publication_sha256':digest(ROOT/'RECEIVE_PUBLICATION.json')})
    created=task(['/Create','/TN',p['task_name'],'/XML',str(ROOT/'receive_task.xml')])
    write(ROOT/'private_run/TASK_CREATE_RESULT.json',created)
    assert created['returncode']==0,'Task create failed; no retry'
    actual=task(['/Query','/TN',p['task_name'],'/XML'])
    write(ROOT/'private_run/REGISTERED_TASK_QUERY.json',actual)
    assert actual['returncode']==0
    from source_checks import validate_xml
    validate_xml(actual['stdout'],p)
    started=task(['/Run','/TN',p['task_name']])
    write(ROOT/'private_run/TASK_RUN_RESULT.json',started)
    assert started['returncode']==0,'Task run failed; no retry'
    write(ROOT/'TASK_START_REQUESTED.json',{'utc':now(),'state':'demand_start_requested_once',
          'task_name':p['task_name'],'create_exit_code':0,'run_exit_code':0,
          'scheduled_restart':False,'model_or_storage_body_completion_claimed':False})
if __name__=='__main__':
    try:main()
    except BaseException:
        import traceback
        write(ROOT/'LAUNCH_FAILURE.json',{'utc':now(),'state':'failed_preserved_no_retry','traceback':traceback.format_exc()})
        raise
