$r='D:/FEDUBA_MIXED_ATTACK_RECOVERY_RUN_20261101'
$files=@{}
foreach($n in @('PREPARE_ONCE.json','PREPARE_RESULT.json','PREPARE_FAILURE.json','RECOVERY_CONTROLLER_STATE.json','RECOVERY_CONTROLLER_FAILURE.json','FU_attack_STATE.json','FU_attack_RESULT.json','FU_attack_VERIFIED.json','FU_attack_FAILURE.json','FU_attack_AUDIT_STATE.json','FU_attack_AUDIT_FAILURE.json','PAIR_EVAL_STATE.json','PAIR_EVAL_RESULT.json','PAIR_EVAL_VERIFIED.json','PAIR_EVAL_FAILURE.json','PAIR_EVAL_AUDIT_STATE.json','PAIR_EVAL_AUDIT_FAILURE.json','COMPLETION.json')){
  if(Test-Path -LiteralPath "$r/$n"){
    $v=Get-Content -LiteralPath "$r/$n" -Raw -Encoding UTF8 | ConvertFrom-Json
    $x=$v | Select-Object state,pid,step,child_pid,round,rounds,client,epoch,examples,cumulative_role_batches,effective_cumulative_batches,executed_here_roles,executed_here_roles_completed,executed_here_batches,executed_here_batches_before_role,actual_epochs,actual_batches,checked_roles,model,batch,batches,actual_forward_calls,model_loads,model_forwards,overall_goal_complete,minimum_operational_gate_passed
    if($v.traceback){$x | Add-Member -NotePropertyName traceback_preview -NotePropertyValue ([string]$v.traceback).Substring(0,[Math]::Min(3000,([string]$v.traceback).Length))}
    $files[$n]=$x
  }
}
$processes=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" | Where-Object {$_.CommandLine -like '*FEDUBA_MIXED_ATTACK_RECOVERY_RUN_20261101*'} | Select-Object ProcessId,ParentProcessId,CommandLine)
$rounds=0;$event=$null
if(Test-Path -LiteralPath "$r/fu/attack/MANIFEST.json"){$m=Get-Content -LiteralPath "$r/fu/attack/MANIFEST.json" -Raw -Encoding UTF8 | ConvertFrom-Json;$rounds=@($m.rounds).Count}
if(Test-Path -LiteralPath "$r/fu/attack/events.jsonl"){$line=Get-Content -LiteralPath "$r/fu/attack/events.jsonl" -Tail 1 -Encoding UTF8;if($line){$event=([string]$line | ConvertFrom-Json | Select-Object kind,round,client,epoch,examples,batches,cumulative_role_batches,actual_cumulative_batches)}}
[pscustomobject]@{utc=(Get-Date).ToUniversalTime().ToString('o');root=$r;files=$files;processes=$processes;committed_rounds=$rounds;last_event=$event} | ConvertTo-Json -Depth 4 -Compress
