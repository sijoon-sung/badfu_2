"""Explicit encoded-command invocation of the already-frozen launcher body."""
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
sys.path.insert(0,str(BASE/'research/00_trajectories'))
import dislab_audit as t

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def once(name,value):
    with (HERE/name).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())

def main():
    p=read(HERE/'PROFILE.json');pub=read(HERE/'PUBLICATION.json')
    assert pub['state']=='published_encoded_command_launch_recovery_before_invocation'
    assert pub['source_freeze_sha256']==sha(HERE/'SOURCE_FREEZE.json')
    for n,d in read(HERE/'SOURCE_FREEZE.json')['files'].items():assert sha(HERE/n)==d,n
    source=BASE/'research/feduba_targetclass_pair_20261102/launch_once.ps1'
    assert sha(source)==p['original_launcher_sha256']
    raw=source.read_text(encoding='utf-8')
    assert raw.count('$r=$PSScriptRoot')==1
    body=raw.replace('$r=$PSScriptRoot',"$r='D:/FEDUBA_TARGETCLASS_PAIR_20261102'")
    # No execution-policy option, settings change, privilege change or numeric-code edit.
    observation=json.loads(t.remote(r"""
$r='D:/FEDUBA_TARGETCLASS_PAIR_20261102'
$task=Get-ScheduledTask -TaskName 'Codex-FedUBA-targetclass125-pairedFU20-20261102' -ErrorAction SilentlyContinue
$p=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'"|Where-Object{([string]$_.CommandLine).ToLowerInvariant().Contains('d:/feduba_targetclass_pair_20261102/')})
$artifacts=@('TASK_ONCE.json','LAUNCH_FAILURE.json','CONTROLLER_ONCE.json','CONTROLLER_FAILURE.json','FU_benign_ONCE.json')|Where-Object{Test-Path -LiteralPath (Join-Path $r $_)}
[pscustomobject]@{task_present=[bool]$task;process_count=$p.Count;artifacts=@($artifacts);launcher_sha=(Get-FileHash -LiteralPath "$r/launch_once.ps1" -Algorithm SHA256).Hash.ToLowerInvariant()}|ConvertTo-Json -Compress
"""))
    assert observation==dict(task_present=False,process_count=0,artifacts=[],launcher_sha=p['original_launcher_sha256'])
    once('INVOCATION_ONCE.json',{'pid':os.getpid(),'observation':observation,'publication_sha256':sha(HERE/'PUBLICATION.json')})
    result=t.remote(body)
    once('INVOCATION_RESULT.json',{'state':'encoded_launch_body_returned','stdout':result,'source_policy_settings_changed':False})
    print(result)

if __name__=='__main__':
    try:main()
    except BaseException:
        once('INVOCATION_FAILURE.json',{'state':'failed_preserved','traceback':traceback.format_exc()})
        raise
