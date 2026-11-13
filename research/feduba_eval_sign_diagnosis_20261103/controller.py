"""One new primary and one fresh independent child; existing jobs remain closed."""
import os,subprocess,sys,time,traceback
from common import ROOT,read,write,once,sha,require_run,source_check,guard
def main():
    p,b,old=require_run()
    once('CONTROLLER_ONCE.json',{'pid':os.getpid(),'created':time.time()})
    env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0',CUBLAS_WORKSPACE_CONFIG=':4096:8',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
    children=[]
    for mode in ['primary','independent']:
        deadline=time.time()+86400
        while True:
            ok,g=guard(p);write('GUARD_STATE.json',dict(g,mode=mode,admitted=ok,deadline=deadline))
            if ok:break
            assert time.time()<deadline,'Finite guard deadline reached'
            time.sleep(15)
        require_run()
        args=[sys.executable,'-B','-u',str(ROOT/'sign_eval.py'),'--mode',mode]
        with (ROOT/(mode+'.stdout.log')).open('xb') as out,(ROOT/(mode+'.stderr.log')).open('xb') as err:
            child=subprocess.Popen(args,env=env,stdout=out,stderr=err)
            write('CONTROLLER_STATE.json',{'state':'running','mode':mode,'pid':os.getpid(),'child_pid':child.pid,'command':args})
            code=child.wait()
        children.append({'mode':mode,'pid':child.pid,'exit_code':code,'ended_unix':time.time()})
        write('CHILD_EXITS.json',children)
        assert code==0,mode+' failed; prefix preserved, no retry'
    v=read(ROOT/'VERIFIED.json');result=read(ROOT/'RESULT.json')
    assert v['state']=='passed_new_negative_sign_independent_evaluation' and v['primary_result_sha256']==sha(ROOT/'RESULT.json')
    assert v['actual_forward_calls']==result['actual_forward_calls']==316
    assert v['actual_sample_forwards']==result['actual_sample_forwards']==40000
    source_check()
    write('COMPLETION.json',{'state':'completed_fixed_endpoint_negative_sign_diagnosis','exit_code':0,'children':children,'primary_result_sha256':sha(ROOT/'RESULT.json'),'verified_sha256':sha(ROOT/'VERIFIED.json'),'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'run_freeze_sha256':sha(ROOT/'RUN_FREEZE.json'),'negative_models':v['models'],'positive_models_reused':v['positive_models_reused'],'alignment_rule_passed':v['alignment_rule_passed'],'diagnostic_negative_gates':v['diagnostic_negative_gates'],'each_primary_and_independent_calls':316,'each_primary_and_independent_sample_forwards':40000,'clean_and_positive_forward_calls':0,'new_training_steps':0,'standard_positive_failure_replaced':False,'author_intent_resolved':False,'new_checkpoint_selected':False,'local_delivery_complete':False,'overall_goal_complete':False,'finished_unix':time.time()})
    write('CONTROLLER_STATE.json',{'state':'completed','pid':os.getpid(),'exit_code':0})
    print('Completed new negative-sign diagnostic; standard failures unchanged')
if __name__=='__main__':
    try:main()
    except BaseException:
        write('CONTROLLER_FAILURE.json',{'state':'failed_preserved','pid':os.getpid(),'traceback':traceback.format_exc()});raise
