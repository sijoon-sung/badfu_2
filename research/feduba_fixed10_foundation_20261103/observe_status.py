"""Repeatable exact-task/native-process/receipt metadata only; no model access."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'00_trajectories'))
import dislab_audit as t
def observe():
    return json.loads(t.remote(r"""
$r='D:/FEDUBA_FIXED10_FOUNDATION_20261103'
$task=Get-ScheduledTask -TaskName 'Codex-FedUBA-public-fixed10-cleanFL20-20261103' -ErrorAction SilentlyContinue
$tr=$null
if($task){$i=$task|Get-ScheduledTaskInfo;$tr=[pscustomobject]@{state=[string]$task.State;last_result=$i.LastTaskResult;execute=$task.Actions.Execute;arguments=$task.Actions.Arguments;working_directory=$task.Actions.WorkingDirectory;user=$task.Principal.UserId;logon_type=[string]$task.Principal.LogonType;run_level=[string]$task.Principal.RunLevel}}
$out=[ordered]@{}
foreach($n in @('TASK_ONCE.json','LAUNCH_FAILURE.json','FOUNDATION_CONTROLLER_ONCE.json','FOUNDATION_CONTROLLER_STATE.json','FOUNDATION_CONTROLLER_FAILURE.json','CLEAN_FL_STARTED.json','CLEAN_FL_STATE.json','CLEAN_FL_FAILURE.json','CLEAN_FL_RESULT.json','COMPLETION.json')){
 $p=Join-Path $r $n
 if(Test-Path -LiteralPath $p){$out[$n]=[string](Get-Content -LiteralPath $p -Raw -Encoding UTF8)|ConvertFrom-Json}else{$out[$n]=$null}
}
$verified=$null
if(Test-Path -LiteralPath "$r/CLEAN_FL_VERIFIED.json"){$v=[string](Get-Content -LiteralPath "$r/CLEAN_FL_VERIFIED.json" -Raw -Encoding UTF8)|ConvertFrom-Json;$verified=[pscustomobject]@{state=$v.state;rounds=$v.rounds;roles=$v.roles;actual_local_epoch_logs=$v.actual_local_epoch_logs;actual_batches=$v.actual_batches;history_hashes_count=$v.history_hashes.PSObject.Properties.Count;independent_N=$v.independent_N;independent_clean_correct=$v.independent_clean_correct;CA_pct=$v.CA_pct;utility_gate=$v.utility_gate}}
$proc=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'"|Where-Object{([string]$_.CommandLine).Replace('\','/').ToLowerInvariant().Contains('d:/feduba_fixed10_foundation_20261103/')}|Select-Object Name,ProcessId,ParentProcessId,CommandLine)
[pscustomobject]@{observed_utc=[DateTime]::UtcNow.ToString('o');task=$tr;processes=$proc;receipts=$out;verified_summary=$verified}|ConvertTo-Json -Depth 10 -Compress
"""))
if __name__=='__main__':
    s=json.dumps(observe(),ensure_ascii=True)
    assert len(s)<25000
    print(s)
