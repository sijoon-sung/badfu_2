$r='D:/FEDUBA_MIXED_PAIR_20261101'
$states=@{}
foreach($name in @('PAIR_CONTROLLER_STATE.json','PAIR_CONTROLLER_FAILURE.json',
  'FU_benign_STATE.json','FU_benign_FAILURE.json','FU_benign_AUDIT_STATE.json','FU_benign_AUDIT_FAILURE.json',
  'FU_attack_STATE.json','FU_attack_FAILURE.json','FU_attack_AUDIT_STATE.json','FU_attack_AUDIT_FAILURE.json',
  'PAIR_EVAL_STATE.json','PAIR_EVAL_FAILURE.json','PAIR_EVAL_AUDIT_FAILURE.json')) {
  if(Test-Path -LiteralPath "$r/$name") {
    $value=Get-Content -LiteralPath "$r/$name" -Raw -Encoding UTF8 | ConvertFrom-Json
    $row=$value | Select-Object state,pid,step,branch,child_pid,round,rounds,client,epoch,examples,cumulative_role_batches,checked_roles,actual_epochs,actual_batches
    if($value.traceback) {$row | Add-Member -NotePropertyName traceback_preview -NotePropertyValue ([string]$value.traceback).Substring(0,[Math]::Min(4000,([string]$value.traceback).Length))}
    $states[$name]=$row
  }
}
$s=$states['PAIR_CONTROLLER_STATE.json'];$processes=@()
if($s.pid) {
  $filter='ProcessId='+[int]$s.pid
  if($s.child_pid) {$filter+=' OR ProcessId='+[int]$s.child_pid}
  $processes=@(Get-CimInstance Win32_Process -Filter $filter | Select-Object ProcessId,ParentProcessId,CommandLine)
}
$rounds=@{};$events=@{}
foreach($branch in @('benign','attack')) {
  if(Test-Path -LiteralPath "$r/fu/$branch/MANIFEST.json") {
    $m=Get-Content -LiteralPath "$r/fu/$branch/MANIFEST.json" -Raw -Encoding UTF8 | ConvertFrom-Json
    $rounds[$branch]=@($m.rounds).Count
  }
  if(Test-Path -LiteralPath "$r/fu/$branch/events.jsonl") {
    # Parse before embedding. A raw Get-Content string has ETS PSDrive/Provider properties.
    $line=Get-Content -LiteralPath "$r/fu/$branch/events.jsonl" -Tail 1 -Encoding UTF8
    if($line) {$events[$branch]=([string]$line | ConvertFrom-Json | Select-Object kind,branch,round,client,epoch,examples,batches,cumulative_role_batches)}
  }
}
$completed=@{}
foreach($name in @('FU_benign_RESULT.json','FU_benign_VERIFIED.json','FU_attack_RESULT.json','FU_attack_VERIFIED.json','PAIR_EVAL_VERIFIED.json')) {
  if(Test-Path -LiteralPath "$r/$name") {
    $value=Get-Content -LiteralPath "$r/$name" -Raw -Encoding UTF8 | ConvertFrom-Json
    $completed[$name]=$value | Select-Object state,branch,rounds,new_trained_roles,actual_local_epochs,actual_batches
  }
}
[pscustomobject]@{utc=(Get-Date).ToUniversalTime().ToString('o');root=$r;states=$states;processes=$processes;committed_rounds=$rounds;last_events=$events;completed=$completed} | ConvertTo-Json -Depth 6 -Compress
