"""Run the fixed saved-query arithmetic and separate scalar verifier once."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
import json,subprocess,sys,time,traceback
from common import ROOT,read,sha,once,published,guard,ResourceBusy

def main():
    p,b=published();once('CONTROLLER_ONCE.json',{'pid':os.getpid(),'source_publication_sha256':sha(ROOT/'SOURCE_PUBLICATION.json')})
    begin=time.monotonic()
    while True:
        try:resources=guard();break
        except ResourceBusy as error:
            elapsed=time.monotonic()-begin
            (ROOT/'STATE.json').write_text(json.dumps({'state':'waiting_fixed_native_resources','elapsed_seconds':elapsed,'pid':os.getpid(),'reason':str(error)}),encoding='utf-8')
            assert elapsed<p['resources']['max_wait_seconds'];time.sleep(p['resources']['wait_seconds'])
    for name in ['derive_direction.py','verify_direction.py']:
        with (ROOT/(name+'.log')).open('x',encoding='utf-8') as out:
            child=subprocess.Popen([sys.executable,'-B','-u',str(ROOT/name)],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
            (ROOT/'STATE.json').write_text(json.dumps({'state':'running','pid':os.getpid(),'child':child.pid,'step':name}),encoding='utf-8')
            code=child.wait()
        assert code==0,name+' exit='+str(code)
    done={'state':'completed_saved_SSS_direction_diagnosis_and_independent_scalar_check','result_sha256':sha(ROOT/'RESULT.json'),'verified_sha256':sha(ROOT/'VERIFIED.json'),'resources':resources,'model_loads':0,'forward_calls':0,'new_selection_or_training_allowed':False,'overall_goal_complete':False}
    once('COMPLETION.json',done);(ROOT/'STATE.json').write_text(json.dumps({'state':'completed','pid':os.getpid(),'exit_code':0}),encoding='utf-8');print(json.dumps(done))
if __name__=='__main__':
    try:main()
    except BaseException:once('CONTROLLER_FAILURE.json',{'state':'failed_preserved_no_retry','traceback':traceback.format_exc()});raise
