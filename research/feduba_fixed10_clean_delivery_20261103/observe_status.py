"""Repeatable exact-task/native-process/storage-receipt metadata; model0."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'00_trajectories'))
import dislab_audit as t
def observe():
    return json.loads(t.remote(r"""
$r='D:/FEDUBA_FIXED10_CLEAN_DELIVERY_20261103'
$task=Get-ScheduledTask -TaskName 'Codex-FedUBA-public-fixed10-clean-review-export-CPU-20261103' -ErrorAction SilentlyContinue
$row=$null
if($task){$i=$task|Get-ScheduledTaskInfo;$row=[pscustomobject]@{state=[string]$task.State;last_result=$i.LastTaskResult;execute=$task.Actions.Execute;arguments=$task.Actions.Arguments;working_directory=$task.Actions.WorkingDirectory;user=$task.Principal.UserId;logon_type=[string]$task.Principal.LogonType;run_level=[string]$task.Principal.RunLevel}}
$out=[ordered]@{}
foreach($n in @('TASK_ONCE.json','LAUNCH_FAILURE.json','CLEAN_EXPORT_ONCE.json','CLEAN_EXPORT_FAILURE.json','CLEAN_REVIEW_DELIVERY_REMOTE.json','REGISTRATION_FAILURE.json')){$p=Join-Path $r $n;if(Test-Path -LiteralPath $p){$out[$n]=[string](Get-Content -LiteralPath $p -Raw -Encoding UTF8)|ConvertFrom-Json}else{$out[$n]=$null}}
$registered=$null
if(Test-Path -LiteralPath "$r/registrations/clean_dislab/REGISTERED.json"){$v=[string](Get-Content -LiteralPath "$r/registrations/clean_dislab/REGISTERED.json" -Raw -Encoding UTF8)|ConvertFrom-Json;$registered=[pscustomobject]@{state=$v.state;case_id=$v.case_id;host_label=$v.host_label;old_case_count=$v.old_case_count;new_case_count=$v.new_case_count;catalogue_sha256=$v.catalogue_sha256;all_old_cases_defaults_and_audits_preserved=$v.all_old_cases_defaults_and_audits_preserved}}
$proc=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'"|Where-Object{([string]$_.CommandLine).Replace('\','/').ToLowerInvariant().Contains('d:/feduba_fixed10_clean_delivery_20261103/')}|Select-Object Name,ProcessId,ParentProcessId,CommandLine)
[pscustomobject]@{observed_utc=[DateTime]::UtcNow.ToString('o');task=$row;processes=$proc;receipts=$out;registered_summary=$registered}|ConvertTo-Json -Depth 8 -Compress
"""))
if __name__=='__main__':
    rendered=json.dumps(observe(),ensure_ascii=True)
    assert len(rendered)<25000
    print(rendered)
