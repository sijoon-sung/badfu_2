"""Finite treatment and fixed audits; invoked only after actual FU delivery."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent
OPS=Path('D:/FUBA_BATCH_REDRAW_OPS_20261115')


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name,value):
    with (OPS/name).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)


def idle():
    stable=0
    for _ in range(600):
        util,free=[int(v.strip()) for v in subprocess.check_output(['nvidia-smi',
            '--query-gpu=utilization.gpu,memory.free','--format=csv,noheader,nounits'],text=True).split(',')]
        stable=stable+1 if util<=5 and free>=2500 else 0
        with (OPS/'resource_wait.jsonl').open('a') as f:
            f.write(json.dumps({'time':time.time(),'util':util,'free_MiB':free,'stable':stable})+'\n')
        if stable>=15:return
        time.sleep(1)
    raise RuntimeError('Resource window absent; preserve state and do not repeat completed stages')


def step(name,*args):
    with (OPS/(name+'.log')).open('x',encoding='utf-8') as log:
        result=subprocess.run([sys.executable,'-u','-B',str(ROOT/args[0]),*args[1:]],
                              stdout=log,stderr=subprocess.STDOUT)
    write(name+'.json',{'exit_code':result.returncode,'log_sha256':sha(OPS/(name+'.log')),'time':time.time()})
    if result.returncode:raise RuntimeError(name+' failed; no automatic restart')


def main():
    assert ROOT==Path('D:/FUBA_BATCH_REDRAW_PILOT_20261115').resolve()
    for name,digest in read(ROOT/'EXECUTION_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest,name
    for name in ['STARTED.json','RESULT.json','CPU_AUDIT_STARTED.json','INDEPENDENT_STARTED.json','delivery']:
        assert not (ROOT/name).exists(),'Stage already started: '+name
    # Read all required delivery receipts before creating an execution marker.
    from run import frozen,prerequisite
    frozen();delivered=prerequisite()
    OPS.mkdir(exist_ok=False)
    write('STARTED.json',{'pid':os.getpid(),'time':time.time(),'FU_delivery':delivered,'automatic_retry':False})
    idle();step('training','run.py','train')
    assert read(ROOT/'STATE.json')['state']=='complete'
    step('CPU_audit','verify.py');assert read(ROOT/'CPU_AUDIT.json')['state']=='passed'
    idle();step('independent_evaluation','independent_evaluate.py')
    assert read(ROOT/'INDEPENDENT_RESULT.json')['state']=='passed'
    idle();step('gamma_audit','verify_gamma.py')
    assert read(ROOT/'GAMMA_AUDIT.json')['state']=='passed'
    step('export','export.py')
    write('COMPLETE.json',{'state':'remote_complete','local_packet_pending':True,
                          'full_paper_reproduced':False,'time':time.time()})


if __name__=='__main__':main()
