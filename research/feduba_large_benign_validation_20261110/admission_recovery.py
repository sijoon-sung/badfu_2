"""Fresh one-shot recovery after an admission stop, never a completed FU replay."""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from bindings import ROOT,read,write,sha,require_publication


def main():
    (ROOT/'ADMISSION_RECOVERY_ONCE').open('x').write(str(os.getpid()))
    require_publication()
    before=read(ROOT/'PROFILE_BEFORE_SHARED.json');current=read(ROOT/'PROFILE.json')
    assert all(current[k]==v for k,v in before.items())
    assert not (ROOT/'fu').exists() and not (ROOT/'STATE.json').exists()
    assert read(ROOT/'CONTROLLER_STATE.json')['state']=='failed_preserved'
    text=subprocess.check_output(['powershell','-NoProfile','-Command',
          "@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'python.exe' -and $_.CommandLine -like '*FEDUBA_LARGE_BENIGN_VALIDATION_20261110*'}|Select-Object ProcessId,CommandLine)|ConvertTo-Json -Compress"],text=True)
    peers=json.loads(text) if text.strip() else []
    if isinstance(peers,dict):peers=[peers]
    assert not [p for p in peers if p['ProcessId']!=os.getpid()]
    archive=ROOT/'incidents'/'admission_external_workload';archive.mkdir(parents=True,exist_ok=False)
    hashes={}
    names=['CONTROLLER_ONCE','CONTROLLER_STATE.json','CONTROLLER_FAILURE.json','FU_balanced5000_ONCE',
           'FU_balanced5000_FAILURE.json','train_fu_balanced5000.stdout.txt','train_fu_balanced5000.stderr.txt']
    for name in names:
        source=ROOT/name
        if source.exists():
            target=archive/name
            assert source.resolve().is_relative_to(ROOT.resolve()) and target.resolve().is_relative_to(archive.resolve())
            hashes[name]=sha(source);source.rename(target)
    write(ROOT/'ADMISSION_INCIDENT.json',dict(time=time.time(),stage='before_torch_import_and_checkpoint_tensor_load',
          preserved_raw_files=hashes,raw_arguments_not_public=True,CPU_only_hypothesis_rejected=True,
          scientific_profile_fields_unchanged=True,numerical_resource_limits_unchanged=True,
          exact_external_commands_added=len(read(ROOT/'SHARED_WORKLOAD_OBSERVATION.json')['identities']),
          old_training_repeated=False,original_models_changed=False))
    with (ROOT/'recovery_controller.stdout.txt').open('xb') as out,(ROOT/'recovery_controller.stderr.txt').open('xb') as err:
        result=subprocess.run([sys.executable,'-u',str(ROOT/'controller.py')],cwd=ROOT,stdout=out,stderr=err,
                              creationflags=subprocess.CREATE_NO_WINDOW)
    write(ROOT/'ADMISSION_RECOVERY_RESULT.json',dict(exit_code=result.returncode,time=time.time(),pid=os.getpid()))
    return result.returncode


if __name__=='__main__':sys.exit(main())
