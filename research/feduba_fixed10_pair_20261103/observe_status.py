"""Repeatable metadata-only observer; never imports torch or executes finite jobs."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'00_trajectories'))
import dislab_audit as t

def observe():
    return json.loads(t.remote(r"""
$r='D:/FEDUBA_FIXED10_PAIR_20261103'
$task=Get-ScheduledTask -TaskName 'Codex-FedUBA-public-fixed10-targetclass125-pairedFU20-20261103' -ErrorAction SilentlyContinue
$taskrow=$null
if($task){$info=$task|Get-ScheduledTaskInfo;$taskrow=[pscustomobject]@{state=[string]$task.State;last_result=$info.LastTaskResult;last_run=$info.LastRunTime.ToUniversalTime().ToString('o');execute=$task.Actions.Execute;arguments=$task.Actions.Arguments;working_directory=$task.Actions.WorkingDirectory;user=$task.Principal.UserId;logon_type=[string]$task.Principal.LogonType;run_level=[string]$task.Principal.RunLevel}}
$receipts=[ordered]@{}
foreach($n in @('TASK_ONCE.json','LAUNCH_FAILURE.json','CONTROLLER_ONCE.json','CONTROLLER_STATE.json','CONTROLLER_FAILURE.json','FU_benign_ONCE.json','FU_benign_STATE.json','FU_benign_FAILURE.json','FU_benign_RESULT.json','FU_benign_AUDIT_STATE.json','FU_benign_AUDIT_FAILURE.json','FU_attack_ONCE.json','FU_attack_STATE.json','FU_attack_FAILURE.json','FU_attack_RESULT.json','FU_attack_AUDIT_STATE.json','FU_attack_AUDIT_FAILURE.json','PAIR_EVAL_STATE.json','PAIR_EVAL_FAILURE.json','PAIR_EVAL_AUDIT_STATE.json','PAIR_EVAL_AUDIT_FAILURE.json','EXPORT_FAILURE.json','REMOTE_CHECKPOINT_REVIEW.json','COMPLETION.json')){
 $p=Join-Path $r $n
 if(Test-Path -LiteralPath $p){$receipts[$n]=[string](Get-Content -LiteralPath $p -Raw -Encoding UTF8)|ConvertFrom-Json}else{$receipts[$n]=$null}
}
$audits=[ordered]@{}
foreach($branch in @('benign','attack')){$p=Join-Path $r ("FU_"+$branch+"_VERIFIED.json");if(Test-Path -LiteralPath $p){$v=[string](Get-Content -LiteralPath $p -Raw -Encoding UTF8)|ConvertFrom-Json;$audits[$branch]=[pscustomobject]@{state=$v.state;rounds=$v.rounds;new_trained_roles=$v.new_trained_roles;actual_local_epochs=$v.actual_local_epochs;actual_batches=$v.actual_batches;history_hashes_count=$v.history_hashes.PSObject.Properties.Count}}else{$audits[$branch]=$null}}
$eval=$null
if(Test-Path -LiteralPath "$r/PAIR_EVAL_RESULT.json"){$v=[string](Get-Content -LiteralPath "$r/PAIR_EVAL_RESULT.json" -Raw -Encoding UTF8)|ConvertFrom-Json;$eval=[pscustomobject]@{state=$v.state;models=$v.models;minimum_operational_gate=$v.minimum_operational_gate;performance_gates=$v.performance_gates}}
$evalaudit=$null
if(Test-Path -LiteralPath "$r/PAIR_EVAL_VERIFIED.json"){$v=[string](Get-Content -LiteralPath "$r/PAIR_EVAL_VERIFIED.json" -Raw -Encoding UTF8)|ConvertFrom-Json;$evalaudit=[pscustomobject]@{state=$v.state;independent_counts_exactly_equal=$v.independent_counts_exactly_equal;all_sample_predictions_exactly_equal=$v.all_sample_predictions_exactly_equal;primary_result_sha256=$v.primary_result_sha256}}
$proc=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe' OR Name='mpiexec.exe'"|Where-Object{([string]$_.CommandLine).Replace('\','/').ToLowerInvariant().Contains('d:/feduba_fixed10_pair_20261103/')}|Select-Object Name,ProcessId,ParentProcessId,CommandLine)
[pscustomobject]@{observed_utc=[DateTime]::UtcNow.ToString('o');task=$taskrow;processes=$proc;receipts=$receipts;FU_audits=$audits;evaluation=$eval;evaluation_audit=$evalaudit}|ConvertTo-Json -Depth 12 -Compress
"""))

if __name__=='__main__':
    value=observe()
    rendered=json.dumps(value,ensure_ascii=True)
    assert len(rendered)<25000
    print(rendered)
