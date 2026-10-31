"""Read-only DISLAB status; never launches or resumes a job."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '00_trajectories'))
from dislab_audit import remote

sys.stdout.reconfigure(encoding='utf-8')
print(remote(r'''
$ErrorActionPreference='Stop'
$root='D:/FUBA_REFERENCE_MNIST_DBA_20261031'
foreach($name in @('CONTROLLER_STATE.json','STATE.json','FIRST_ROLE_VERIFIED.json','FAILURE.json','RESULT.json','VERIFIED.json','DELIVERY_COMPLETE.json')) {
  if(Test-Path "$root/$name") {Write-Output $name; Get-Content -LiteralPath "$root/$name"}
}
Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python' -and $_.CommandLine -like '*FUBA_REFERENCE_MNIST_DBA_20261031*'} | Select-Object ProcessId,CommandLine | ConvertTo-Json
$task=Get-ScheduledTask -TaskName 'Codex-FUBA-reference-MNIST-DBA100-KD10-20261031' -ErrorAction SilentlyContinue
if($task) {$task | Select-Object TaskName,State | ConvertTo-Json; Get-ScheduledTaskInfo -TaskName $task.TaskName | Select-Object LastTaskResult,LastRunTime | ConvertTo-Json}
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.free --format=csv,noheader,nounits
exit 0
'''))
