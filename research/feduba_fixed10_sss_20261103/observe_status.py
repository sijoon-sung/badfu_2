"""Repeatable exact-task/native-process/receipt metadata only; no model access."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'00_trajectories'))
import dislab_audit as t
def observe():
    return json.loads(t.remote(r"""
$r='D:/FEDUBA_FIXED10_SSS_20261103'
$task=Get-ScheduledTask -TaskName 'Codex-FedUBA-public-fixed10-newSSS5000-20261103' -ErrorAction SilentlyContinue
$tr=$null
if($task){$i=$task|Get-ScheduledTaskInfo;$tr=[pscustomobject]@{state=[string]$task.State;last_result=$i.LastTaskResult;execute=$task.Actions.Execute;arguments=$task.Actions.Arguments;working_directory=$task.Actions.WorkingDirectory;user=$task.Principal.UserId;logon_type=[string]$task.Principal.LogonType;run_level=[string]$task.Principal.RunLevel}}
$out=[ordered]@{}
foreach($n in @('TASK_ONCE.json','LAUNCH_FAILURE.json','SSS_CONTROLLER_ONCE.json','SSS_CONTROLLER_STATE.json','SSS_CONTROLLER_FAILURE.json','SSS_ONCE.json','SSS_STATE.json','SSS_FAILURE.json','SSS_AUDIT_ONCE.json','SSS_AUDIT_FAILURE.json','COMPLETION.json')){
 $p=Join-Path $r $n
 if(Test-Path -LiteralPath $p){$out[$n]=[string](Get-Content -LiteralPath $p -Raw -Encoding UTF8)|ConvertFrom-Json}else{$out[$n]=$null}
}
$verified=$null
if(Test-Path -LiteralPath "$r/SSS_VERIFIED.json"){$v=[string](Get-Content -LiteralPath "$r/SSS_VERIFIED.json" -Raw -Encoding UTF8)|ConvertFrom-Json;$verified=[pscustomobject]@{state=$v.state;all_score_rows=$v.all_score_rows;actual_forward_calls=$v.actual_forward_calls;float64_top125_same_ID_sets=$v.float64_top125_same_ID_sets;all5000_model_queries_independently_recomputed=$v.all5000_model_queries_independently_recomputed}}
$result=$null
if(Test-Path -LiteralPath "$r/SSS_RESULT.json"){$v=[string](Get-Content -LiteralPath "$r/SSS_RESULT.json" -Raw -Encoding UTF8)|ConvertFrom-Json;$counts=[ordered]@{};foreach($p in $v.selected_by_owner.PSObject.Properties){$counts[$p.Name]=$p.Value.Count};$result=[pscustomobject]@{state=$v.state;observed_samples=$v.observed_samples;query_batches=$v.query_batches;actual_forward_calls=$v.actual_forward_calls;eligible_class=$v.eligible_class;selected_class_counts=$v.selected_class_counts;selected_counts_by_owner=$counts}}
$proc=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'"|Where-Object{([string]$_.CommandLine).Replace('\','/').ToLowerInvariant().Contains('d:/feduba_fixed10_sss_20261103/')}|Select-Object Name,ProcessId,ParentProcessId,CommandLine)
[pscustomobject]@{observed_utc=[DateTime]::UtcNow.ToString('o');task=$tr;processes=$proc;receipts=$out;verified_summary=$verified;result_summary=$result}|ConvertTo-Json -Depth 10 -Compress
"""))
if __name__=='__main__':
    s=json.dumps(observe(),ensure_ascii=True)
    assert len(s)<25000
    print(s)
