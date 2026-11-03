"""One explicitly published transport-only recovery; unchanged PS/task/model source."""
import base64,hashlib,json,os,sys,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'00_trajectories'));import dislab_audit as t
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(n):return json.loads((HERE/n).read_text(encoding='utf-8'))
def main():
    p=read('LAUNCH_TRANSPORT_RECOVERY_PROFILE.json');pub=read('LAUNCH_TRANSPORT_RECOVERY_PUBLICATION.json')
    assert p['launch_enabled'] and pub['state']=='published_transport_only_recovery_before_existing_PS_invocation'
    assert pub['recovery_freeze_sha256']==h(HERE/'LAUNCH_TRANSPORT_RECOVERY_FREEZE.json')
    for n,d in read('LAUNCH_TRANSPORT_RECOVERY_FREEZE.json')['files'].items():assert h(HERE/n)==d,n
    assert h(HERE/'LOCAL_LAUNCH_FAILURE.json')==p['original_failure_sha256']
    assert not (HERE/'LOCAL_LAUNCH_ONCE.json').exists() and not (HERE/'LOCAL_LAUNCH_RESULT.json').exists()
    assert h(HERE/'RUN_PUBLICATION.json')==p['run_publication_sha256'] and h(HERE/'EVAL_RUN_FREEZE.json')==p['eval_run_freeze_sha256']
    root=p['execution_root']
    before=json.loads(t.remote("$r='"+root+"';$n='"+p['task_name']+"';$task=Get-ScheduledTask -TaskName $n -ErrorAction SilentlyContinue;$c=@(Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\"|Where-Object{([string]$_.CommandLine).Replace([char]92,[char]47).ToLowerInvariant().Contains($r.ToLowerInvariant()+'/')}).Count;if($task -or $c -ne 0){throw 'Task/process already exists'};foreach($n in @('TASK_ONCE','CONTROLLER_ONCE','PAIR_EVAL_ONCE','LAUNCH_FAILURE','CONTROLLER_FAILURE')){if(Test-Path -LiteralPath ($r+'/'+$n+'.json')){throw 'Execution artifact exists'}};@{state='existing_PS_not_yet_invoked';task_exists=$false;root_processes=$c}|ConvertTo-Json -Compress"))
    assert before['root_processes']==0 and before['task_exists'] is False
    raw=(HERE/'launch_once.ps1').read_text(encoding='utf-8');assert h(HERE/'launch_once.ps1')==p['existing_launcher_sha256'] and raw.count('$r=$PSScriptRoot')==1
    replacement="$r='"+root+"'";expected=hashlib.sha256(raw.replace('$r=$PSScriptRoot',replacement).encode('utf-8')).hexdigest();literal=base64.b64encode(replacement.encode()).decode()
    command=("$f='"+root+"/launch_once.ps1';if((Get-FileHash -LiteralPath $f -Algorithm SHA256).Hash.ToLowerInvariant() -ne '"+p['existing_launcher_sha256']+"'){throw 'Launcher hash mismatch'};"
        "$b=[IO.File]::ReadAllText($f);$v=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"+literal+"'));$b=$b.Replace('$r=$PSScriptRoot',$v);"
        "$a=[Security.Cryptography.SHA256]::Create();$x=([BitConverter]::ToString($a.ComputeHash([Text.Encoding]::UTF8.GetBytes($b)))).Replace('-','').ToLowerInvariant();if($x -ne '"+expected+"'){throw 'Invocation-body hash mismatch'}; & ([ScriptBlock]::Create($b))")
    with (HERE/'LOCAL_TRANSPORT_RECOVERY_ONCE.json').open('x',encoding='utf-8') as f:json.dump({'pid':os.getpid(),'before':before,'transformed_body_sha256':expected,'recovery_publication_sha256':h(HERE/'LAUNCH_TRANSPORT_RECOVERY_PUBLICATION.json')},f);f.flush();os.fsync(f.fileno())
    value=t.remote(command)
    with (HERE/'LOCAL_TRANSPORT_RECOVERY_RESULT.json').open('x',encoding='utf-8') as f:json.dump({'state':'first_existing_frozen_PS_invocation_returned','stdout':value},f)
    print(value)
if __name__=='__main__':
    try:main()
    except BaseException:
        with (HERE/'LOCAL_TRANSPORT_RECOVERY_FAILURE.json').open('x',encoding='utf-8') as f:json.dump({'state':'failed_preserved','traceback':traceback.format_exc()},f)
        raise
