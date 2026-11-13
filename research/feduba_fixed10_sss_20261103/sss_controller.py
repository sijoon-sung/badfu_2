"""Exactly one fresh SSS5000 and one independent CPU audit; no FU launch here."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
import json
import shutil
import subprocess
import sys
import time
import traceback
from pair_binding import require_published_run
from runtime_common import ROOT,read,write,sha,guard,ResourceBusy
def once(n,v):
    with (ROOT/n).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def main():
    p,a=require_published_run();once('SSS_CONTROLLER_ONCE.json',{'pid':os.getpid(),'started_unix':time.time(),'publication_sha256':sha(ROOT/'RUN_PUBLICATION.json')})
    for name in ['sss_runner.py','verify_sss.py']:
        require_published_run();started=time.monotonic()
        while True:
            try:
                resources=guard();assert shutil.disk_usage(ROOT).free>=80*2**30;break
            except ResourceBusy as error:
                elapsed=time.monotonic()-started
                write(ROOT/'SSS_CONTROLLER_STATE.json',{'state':'waiting_fixed_resources','pid':os.getpid(),'step':name,'elapsed_seconds':elapsed,'reason':str(error)})
                assert elapsed<86400;time.sleep(15)
        args=[sys.executable,'-B','-u',str(ROOT/name)]
        if name=='sss_runner.py':args+=['--catalog-root',p['catalog_root'],'--case-id',p['normal_case_id']]
        env=dict(os.environ,CUDA_VISIBLE_DEVICES='0' if name=='sss_runner.py' else '-1')
        with (ROOT/('console_'+name+'.log')).open('x',encoding='utf-8') as f:
            child=subprocess.Popen(args,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
            write(ROOT/'SSS_CONTROLLER_STATE.json',{'state':'running','pid':os.getpid(),'child':child.pid,'step':name,'guard':resources})
            code=child.wait()
        assert code==0,name+' exit='+str(code)
    assert read(ROOT/'SSS_VERIFIED.json')['state']=='passed'
    once('COMPLETION.json',{'state':'completed_new_fixed10_SSS5000_and_independent_score_query_audit',
        'result_sha256':sha(ROOT/'SSS_RESULT.json'),'verified_sha256':sha(ROOT/'SSS_VERIFIED.json'),
        'actual_paired_FU_still_required':True,'overall_goal_complete':False})
    write(ROOT/'SSS_CONTROLLER_STATE.json',{'state':'completed','pid':os.getpid(),'exit_code':0})
if __name__=='__main__':
    try:main()
    except BaseException:
        once('SSS_CONTROLLER_FAILURE.json',{'state':'failed_preserved','pid':os.getpid(),'traceback':traceback.format_exc()});raise
