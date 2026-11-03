"""Compact repeatable metadata only; avoids oversized encoded command transport."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'00_trajectories'))
import dislab_audit as t
def observe():
    return json.loads(t.remote(r"""
$r='D:/FEDUBA_RELATED_HELPER_POSITIVE_EVALUATION_20261103';$task=Get-ScheduledTask -TaskName 'Codex-FedUBA-related-helper-positive-newmodel-eval-review-20261103' -ErrorAction SilentlyContinue;$row=$null
if($task){$i=$task|Get-ScheduledTaskInfo;$row=@{state=[string]$task.State;last_result=$i.LastTaskResult;action=$task.Actions.Arguments;user=$task.Principal.UserId;level=[string]$task.Principal.RunLevel}}
$o=@{};foreach($n in @('CONTROLLER_STATE','CONTROLLER_FAILURE','FU_benign_STATE','FU_benign_FAILURE','FU_benign_AUDIT_STATE','FU_benign_AUDIT_FAILURE','FU_attack_STATE','FU_attack_FAILURE','FU_attack_AUDIT_STATE','FU_attack_AUDIT_FAILURE','PAIR_EVAL_STATE','PAIR_EVAL_FAILURE','PAIR_EVAL_AUDIT_STATE','PAIR_EVAL_AUDIT_FAILURE','EXPORT_FAILURE','COMPLETION')){$p="$r/$n.json";$o[$n]=$null;if(Test-Path -LiteralPath $p){$o[$n]=[string](Get-Content -LiteralPath $p -Raw -Encoding UTF8)|ConvertFrom-Json}}
$a=@{};foreach($b in @('benign','attack')){$p="$r/FU_$($b)_VERIFIED.json";if(Test-Path -LiteralPath $p){$v=[string](Get-Content -LiteralPath $p -Raw -Encoding UTF8)|ConvertFrom-Json;$a[$b]=@{state=$v.state;rounds=$v.rounds;roles=$v.new_trained_roles;batches=$v.actual_batches}}}
$proc=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'"|Where-Object{([string]$_.CommandLine).Replace([char]92,[char]47).ToLowerInvariant().Contains('d:/feduba_related_helper_positive_evaluation_20261103/')}|Select-Object ProcessId,ParentProcessId,CommandLine)
@{utc=[DateTime]::UtcNow.ToString('o');task=$row;processes=$proc;receipts=$o;audits=$a}|ConvertTo-Json -Depth 9 -Compress
"""))
if __name__=='__main__':
    s=json.dumps(observe(),ensure_ascii=True);assert len(s)<25000;print(s)
