"""Repeatable metadata-only observer; never imports torch or executes finite jobs."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'00_trajectories'))
import dislab_audit as t

def observe():
    return json.loads(t.remote(r"""
$r='D:/FEDUBA_TARGETCLASS_PAIR_20261102'
$task=Get-ScheduledTask -TaskName 'Codex-FedUBA-targetclass125-pairedFU20-20261102' -ErrorAction SilentlyContinue
$taskrow=$null
if($task){$info=$task|Get-ScheduledTaskInfo;$taskrow=[pscustomobject]@{state=[string]$task.State;last_result=$info.LastTaskResult;last_run=$info.LastRunTime.ToUniversalTime().ToString('o');action=$task.Actions;principal=$task.Principal}}
$receipts=[ordered]@{}
foreach($n in @('TASK_ONCE.json','LAUNCH_FAILURE.json','CONTROLLER_ONCE.json','CONTROLLER_STATE.json','CONTROLLER_FAILURE.json','FU_benign_ONCE.json','FU_benign_STATE.json','FU_benign_FAILURE.json','FU_benign_RESULT.json','FU_benign_AUDIT_STATE.json','FU_benign_AUDIT_FAILURE.json','FU_attack_ONCE.json','FU_attack_STATE.json','FU_attack_FAILURE.json','FU_attack_RESULT.json','FU_attack_AUDIT_STATE.json','FU_attack_AUDIT_FAILURE.json','PAIR_EVAL_STATE.json','PAIR_EVAL_FAILURE.json','PAIR_EVAL_AUDIT_STATE.json','PAIR_EVAL_AUDIT_FAILURE.json','EXPORT_FAILURE.json','REMOTE_CHECKPOINT_REVIEW.json','COMPLETION.json')){
 $p=Join-Path $r $n
 if(Test-Path -LiteralPath $p){$receipts[$n]=[string](Get-Content -LiteralPath $p -Raw -Encoding UTF8)|ConvertFrom-Json}else{$receipts[$n]=$null}
}
$proc=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe' OR Name='mpiexec.exe'"|Where-Object{([string]$_.CommandLine).ToLowerInvariant().Contains('d:/feduba_targetclass_pair_20261102/')}|Select-Object Name,ProcessId,ParentProcessId,CommandLine)
[pscustomobject]@{observed_utc=[DateTime]::UtcNow.ToString('o');task=$taskrow;processes=$proc;receipts=$receipts}|ConvertTo-Json -Depth 12 -Compress
"""))

if __name__=='__main__':
    value=observe()
    rendered=json.dumps(value,ensure_ascii=True)
    assert len(rendered)<25000
    print(rendered)
