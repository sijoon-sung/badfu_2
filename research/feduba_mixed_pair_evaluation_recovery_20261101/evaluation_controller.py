"""Once primary plus independent evaluation only; no completed producer is called."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
import subprocess
import sys
import time
import traceback
from evaluation_io import ROOT,read,write,once,require_published_run,guard,ResourceBusy


def run(name,profile,log):
    deadline=time.time()+86400
    while True:
        require_published_run()
        try:resources=guard(4000);break
        except ResourceBusy as e:
            write(ROOT/'EVALUATION_CONTROLLER_STATE.json',{'state':'waiting_for_fixed_resources','pid':os.getpid(),'step':name,'reason':str(e)})
            if time.time()>deadline:raise RuntimeError('Fixed 24h wait exhausted; no automatic retry')
            time.sleep(15)
    env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0',CUBLAS_WORKSPACE_CONFIG=':4096:8')
    child=subprocess.Popen([sys.executable,'-B','-u',str(ROOT/name),'--catalog-root',profile['catalog_root'],
        '--case-id',profile['case_id']],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    write(ROOT/'EVALUATION_CONTROLLER_STATE.json',{'state':'running','pid':os.getpid(),'step':name,'child_pid':child.pid,'resources':resources})
    if child.wait():raise RuntimeError(name+' failed; preserved; no retry')


def main():
    require_published_run();p=read(ROOT/'LAUNCH_PROFILE.json')
    once('EVALUATION_CONTROLLER_ONCE.json',{'pid':os.getpid(),'started_unix':time.time()})
    for n in ['PAIR_EVAL_ONCE.json','PAIR_EVAL_RESULT.json','PAIR_EVAL_AUDIT_ONCE.json']:
        assert not (ROOT/n).exists(),n
    with (ROOT/'evaluation_console.log').open('x',encoding='utf-8',newline='\n',buffering=1) as log:
        run('evaluate_pair.py',p,log)
        run('verify_pair_evaluation.py',p,log)
    assert read(ROOT/'PAIR_EVAL_VERIFIED.json')['state']=='passed'
    v={'state':'completed_new_mixed_pair_evaluation_independently_verified_delivery_pending',
        'pid':os.getpid(),'minimum_operational_gate_passed':read(ROOT/'PAIR_EVAL_RESULT.json')['minimum_operational_gate']['passed'],
        'overall_goal_complete':False,'readonly_delivery_completed':False,'detection_success_implied':False}
    write(ROOT/'COMPLETION.json',v);write(ROOT/'EVALUATION_CONTROLLER_STATE.json',v)


if __name__=='__main__':
    try:main()
    except BaseException:
        write(ROOT/'EVALUATION_CONTROLLER_FAILURE.json',{'state':'failed_preserved','pid':os.getpid(),'traceback':traceback.format_exc()});raise
