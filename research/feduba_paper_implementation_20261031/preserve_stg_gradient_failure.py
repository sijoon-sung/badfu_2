"""Copy original closed-run failure evidence; no model evaluation or training."""
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '00_trajectories'))
import dislab_audit as t

ps = r'''
$ErrorActionPreference='Stop'
$r='D:/FEDUBA_PAPER_IMPLEMENTATION_20261031'
$d=$r+'/incidents/stg_cpu_gradient_v1'
if(Test-Path -LiteralPath $d){throw 'Incident exists; inspect instead of copying again'}
New-Item -ItemType Directory -Path $d | Out-Null
$names=@('STG_CONTROLLER_STATE.json','STG_CONTROLLER_ONCE.json','STG_STATE.json','STG_RESULT.json','STG_AUDIT_STATE.json','STG_AUDIT_FAILURE.json','STG_AUDIT_ONCE.json','STG_STARTED.json','STG_FREEZE.json','STG_LAUNCH_PROFILE.json','STG_LAUNCH_PROTOCOL.txt','STG_READY.json','stg_controller.py','trigger_runner.py','verify_stg.py','stg_training.py','core.py','model_reference.py','runtime_common.py','stg_console.log','stg/MANIFEST.json','stg/events.jsonl','stg/delta.pt','stg/fixed_surrogate.pt','stg/trigger_steps/epoch001_batch1.pt','stg/trigger_steps/epoch100_batch2.pt')
$rows=@()
foreach($n in $names){
    $src=$r+'/'+$n
    if(-not(Test-Path -LiteralPath $src)){throw ('Missing original: '+$n)}
    $dst=$d+'/'+$n
    New-Item -ItemType Directory -Path (Split-Path -Parent $dst) -Force | Out-Null
    Copy-Item -LiteralPath $src -Destination $dst
    $h=(Get-FileHash -Algorithm SHA256 -LiteralPath $src).Hash.ToLower()
    if((Get-FileHash -Algorithm SHA256 -LiteralPath $dst).Hash.ToLower() -ne $h){throw ('Copy mismatch: '+$n)}
    $rows+=@{path=$n;sha256=$h;bytes=(Get-Item -LiteralPath $dst).Length}
    (Get-Item -LiteralPath $dst).IsReadOnly=$true
}
$meta=@{state='original_audit_failure_preserved';original_root=$r;scope='26 copied evidence files including first/last step and frozen surrogate; all205epoch/200step raw history remains original DISLAB root';files=$rows;training_restarted=$false;original_audit_repeated=$false}
$meta|ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 -LiteralPath ($d+'/MANIFEST.json')
Get-ScheduledTask -TaskName 'Codex-FedUBA-STG100-5-100-20261031' | Select-Object TaskName,State | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath ($d+'/TASK_STATE.json')
Get-ScheduledTaskInfo -TaskName 'Codex-FedUBA-STG100-5-100-20261031' | Select-Object LastRunTime,LastTaskResult,NumberOfMissedRuns | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath ($d+'/TASK_INFO.json')
@{state=$meta.state;copied_files=$rows.Count;failed_PID=47072}|ConvertTo-Json -Compress
'''
print(t.remote(ps))
r = Path(__file__).resolve().parent / 'incidents/stg_cpu_gradient_v1'
r.mkdir(parents=True, exist_ok=False)
names = ['MANIFEST.json', 'TASK_STATE.json', 'TASK_INFO.json', 'STG_CONTROLLER_STATE.json', 'STG_STATE.json',
         'STG_RESULT.json', 'STG_AUDIT_STATE.json', 'STG_AUDIT_FAILURE.json', 'STG_AUDIT_ONCE.json',
         'STG_FREEZE.json', 'STG_LAUNCH_PROFILE.json', 'STG_LAUNCH_PROTOCOL.txt', 'stg_console.log']
for n in names:
    t.run(['scp.exe', '-q', *t.FLAGS, t.REMOTE + ':D:/FEDUBA_PAPER_IMPLEMENTATION_20261031/incidents/stg_cpu_gradient_v1/' + n, str(r / n)])
print('Original incident metadata/log received; raw tensor copies remain DISLAB. No rerun or tolerance change.')
