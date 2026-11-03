"""One /Run only on existing V2 task; never create/update or replay a receiver."""
from start_ops import ROOT,V2,v2,freeze,preflight
def main():
    p=freeze();checked=preflight(p)
    v2.write(ROOT/'START_ONCE.json',{'utc':v2.now(),'state':'existing_unrun_task_start_claim',
             'task_name':p['task_name'],'preflight':checked,'source_freeze_sha256':v2.digest(ROOT/'SOURCE_FREEZE.json'),
             'publication_sha256':v2.digest(ROOT/'START_PUBLICATION.json')})
    result=v2.task(['/Run','/TN',p['task_name']])
    v2.write(ROOT/'private_run/TASK_RUN_RESULT.json',result)
    assert result['returncode']==0,'Start-only request failed; preserve without retry'
    v2.write(ROOT/'START_TERMINAL.json',{'utc':v2.now(),'state':'existing_V2_task_first_demand_start_requested',
             'run_request_exit_code':0,'task_name':p['task_name'],'task_created_or_updated':False,
             'receiver_body_completion_claimed':False,'V1_V2_failed_launchers_reinvoked':False})
if __name__=='__main__':
    try:main()
    except BaseException:
        import traceback
        v2.write(ROOT/'START_FAILURE.json',{'utc':v2.now(),'state':'failed_preserved_no_retry','traceback':traceback.format_exc()})
        raise
