"""Post-training finite audits/export only; operational logs stay outside the sealed root."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent
OPS=Path('D:/FUBA_RETRAIN_FU_FINALIZATION_OPS_20261115')


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def put(name,data):
    with (OPS/name).open('x',encoding='utf-8') as f:json.dump(data,f,indent=2)


def step(name,args):
    with (OPS/(name+'.log')).open('x',encoding='utf-8') as log:
        result=subprocess.run([sys.executable,'-u','-B',*args],stdout=log,stderr=subprocess.STDOUT)
    put(name+'.json',{'exit_code':result.returncode,'time':time.time(),'log_sha256':sha(OPS/(name+'.log'))})
    if result.returncode:raise RuntimeError(name+' failed; preserve and diagnose without rerunning completed stages')


def main():
    for name,digest in read(ROOT/'FINALIZATION_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest
    assert ROOT==Path('D:/FUBA_RETRAIN_FU_RECOVERY_20261115').resolve()
    assert read(ROOT/'STATE.json')['state']=='complete'
    assert read(ROOT/'RESULT.json')['rounds']==100
    assert read(ROOT/'LAUNCH_ATTEMPT2_RESULT.json')['exit_code']==0
    for name in ['CPU_AUDIT_STARTED.json','INDEPENDENT_STARTED.json','delivery','catalog']:
        assert not (ROOT/name).exists(),'Finite stage already started: '+name
    command="@(Get-CimInstance Win32_Process|Where-Object {$_.Name -eq 'python.exe' -and $_.CommandLine -like '*FUBA_RETRAIN_FU_RECOVERY*retry_preflight.py*'}|Select-Object ProcessId)|ConvertTo-Json"
    running=subprocess.check_output(['powershell','-NoProfile','-Command',command],text=True).strip()
    assert running in ('','[]'),'Original trainer is still active'
    OPS.mkdir(exist_ok=False)
    put('STARTED.json',{'pid':os.getpid(),'time':time.time(),'trained_rounds':0,'source_freeze_sha256':sha(ROOT/'FINALIZATION_FREEZE.json')})
    step('full_CPU_audit',[str(ROOT/'verify.py')])
    assert read(ROOT/'CPU_AUDIT.json')['state']=='passed'
    stable=0
    for _ in range(600):
        util,free=[int(v.strip()) for v in subprocess.check_output(['nvidia-smi','--query-gpu=utilization.gpu,memory.free','--format=csv,noheader,nounits'],text=True).split(',')]
        stable=stable+1 if util<=5 and free>=2500 else 0
        with (OPS/'resource_wait.jsonl').open('a') as f:f.write(json.dumps({'time':time.time(),'util':util,'free_MiB':free,'stable':stable})+'\n')
        if stable>=15:break
        time.sleep(1)
    else:raise RuntimeError('No GPU idle window; evaluator was not started')
    step('independent_evaluation',[str(ROOT/'independent_evaluate.py')])
    assert read(ROOT/'INDEPENDENT_RESULT.json')['state']=='passed'
    step('export',[str(ROOT/'export.py')])
    step('register_remote',[str(ROOT/'register_pair.py'),'--selector','D:/TRAJECTORY_CATALOG_20261023/select_case.py',
        '--selector-sha256','bac9f7ed02fd5adce93dc904ad369939f180e8258292c5333dcf97a0f1c649bf'])
    assert read(ROOT/'SELECTION_CHECK.json')['guard_state']=='all_snapshot_files_verified_on_this_host'
    put('COMPLETE.json',{'state':'remote_audits_export_catalogue_complete','time':time.time(),
         'local_delivery_pending':True,'full_paper_reproduced':False})


if __name__=='__main__':main()
