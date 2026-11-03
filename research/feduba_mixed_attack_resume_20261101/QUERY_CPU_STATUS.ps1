$r='D:/FEDUBA_MIXED_ATTACK_RESUME_20261101'
$files=@{}
foreach($n in @('AUDIT_ONCE.json','AUDIT_STATE.json','AUDIT_RESULT.json','AUDIT_FAILURE.json')) {
  if(Test-Path -LiteralPath "$r/$n") {
    $v=Get-Content -LiteralPath "$r/$n" -Raw -Encoding UTF8 | ConvertFrom-Json
    $x=$v | Select-Object state,pid,roles,epochs,batches,last_round,last_client,saved_roles,saved_epochs,saved_batches,committed_rounds,partial_round5_saved_roles,forward_calls,new_training_launched
    if($v.traceback){$x | Add-Member -NotePropertyName traceback_preview -NotePropertyValue ([string]$v.traceback).Substring(0,[Math]::Min(3000,([string]$v.traceback).Length))}
    $files[$n]=$x
  }
}
$processes=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" | Where-Object {$_.CommandLine -like '*FEDUBA_MIXED_ATTACK_RESUME_20261101*verify_prefix.py*'} | Select-Object ProcessId,ParentProcessId,CommandLine)
[pscustomobject]@{utc=(Get-Date).ToUniversalTime().ToString('o');root=$r;files=$files;processes=$processes} | ConvertTo-Json -Depth 4 -Compress
