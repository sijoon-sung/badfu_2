"""One foreground recovery; no original finite script execution or original writes."""
import json,os,shutil,subprocess,sys,time,traceback
from pathlib import Path
from recovery_contract import ROOT,read,sha,require_recovery_publication
from native_memory import memory_information
from native_processes import processes
def write(name,v):
    tmp=ROOT/(name+'.tmp')
    with tmp.open('w',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,ROOT/name)
def snapshot_old(p,b):
    for m in b['inputs'].values():assert sha(m['path'])==m['sha256']
    assert not (Path(p['original_root'])/'PAIR_EVAL_VERIFIED.json').exists()
    assert not (Path(p['original_root'])/'COMPLETION.json').exists()
def guard(p):
    m=memory_information();raw=subprocess.check_output(['C:/Windows/System32/nvidia-smi.exe','--query-gpu=utilization.gpu,memory.free,memory.used','--format=csv,noheader,nounits'],text=True).strip()
    util,free,used=map(lambda s:int(s.strip()),raw.split(','))
    ps=processes();peers=[r for r in ps if r['ProcessId'] not in [os.getpid(),os.getppid()] and any(t in r['CommandLine'].lower() for t in p['known_training_process_tokens'])]
    disk=shutil.disk_usage(ROOT.anchor).free
    ready=m['availableBytes']>=8*2**30 and m['commitLimit']-m['committedBytes']>=16*2**30 and disk>=80*2**30 and util<=5 and free>=4000 and used<=6000 and not peers
    return ready,{'utc_unix':time.time(),'memory':m,'GPU_util':util,'GPU_free_MiB':free,'GPU_used_MiB':used,'disk_free_bytes':disk,'competitors':len(peers)}
def main():
    p,b=require_recovery_publication()
    with (ROOT/'CONTROLLER_ONCE.json').open('x',encoding='utf-8') as f:json.dump({'pid':os.getpid(),'created_unix':time.time()},f)
    snapshot_old(p,b);deadline=time.time()+86400
    while True:
        ok,g=guard(p);write('GUARD_STATE.json',dict(g,admitted=ok,deadline_unix=deadline))
        if ok:break
        assert time.time()<deadline,'Finite resource deadline reached'
        time.sleep(15)
    env=os.environ.copy();env.update(OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='0',CUBLAS_WORKSPACE_CONFIG=':4096:8',PYTHONDONTWRITEBYTECODE='1')
    args=[sys.executable,'-B','-u',str(ROOT/'verify_recovery.py'),'--catalog-root',p['catalog_root'],'--case-id',p['case_id']]
    with (ROOT/'recovery.stdout.log').open('xb') as out,(ROOT/'recovery.stderr.log').open('xb') as err:
        child=subprocess.Popen(args,env=env,stdout=out,stderr=err)
        write('CONTROLLER_STATE.json',{'state':'running_recovery_only','pid':os.getpid(),'child_pid':child.pid,'command':args,'guard':g})
        code=child.wait()
    write('CHILD_EXIT.json',{'exit_code':code,'pid':child.pid,'ended_unix':time.time()});assert code==0,'New recovery child failed; no retry'
    snapshot_old(p,b);v=read(ROOT/'RECOVERY_VERIFIED.json')
    assert v['state']=='passed' and v['independent_forward_calls']==158 and v['independent_sample_forwards']==20000
    assert v['source_models']['attack']['sha256']==p['explicit_new_endpoint_sha256']
    assert v['original_independent_VERIFIED_absent'] and not v['original_verifier_completed_successfully']
    result={'state':'completed_separate_independent_writer_recovery','exit_code':0,'recovery_verified_sha256':sha(ROOT/'RECOVERY_VERIFIED.json'),'primary_result_sha256':v['primary_result_sha256'],'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'run_freeze_sha256':sha(ROOT/'RUN_FREEZE.json'),'original_task_exit':1,'original_VERIFIED_still_absent':True,'original_failure_bytes_preserved':True,'additional_recovery_sample_forwards':20000,'additional_recovery_calls':158,'models':v['models'],'performance_gate':v['minimum_operational_gate'],'performance_success':v['minimum_operational_gate']['passed'],'overall_goal_complete':False,'local_delivery_complete':False,'finished_unix':time.time()}
    write('COMPLETION.json',result);write('CONTROLLER_STATE.json',{'state':'completed','pid':os.getpid(),'exit_code':0});print(json.dumps(result))
if __name__=='__main__':
    try:main()
    except BaseException:
        write('CONTROLLER_FAILURE.json',{'state':'failed_preserved','pid':os.getpid(),'traceback':traceback.format_exc()});raise
