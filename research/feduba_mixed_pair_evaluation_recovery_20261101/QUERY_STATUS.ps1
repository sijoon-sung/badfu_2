$ErrorActionPreference='Stop'
$r='D:/FEDUBA_MIXED_PAIR_EVALUATION_RECOVERY_20261101';$files=@{}
foreach($n in @('METADATA_PROBE_RESULT.json','METADATA_PROBE_FAILURE.json','PREPARE_RESULT.json','PREPARE_FAILURE.json','EVALUATION_CONTROLLER_STATE.json','EVALUATION_CONTROLLER_FAILURE.json','PAIR_EVAL_STATE.json','PAIR_EVAL_RESULT.json','PAIR_EVAL_VERIFIED.json','PAIR_EVAL_AUDIT_STATE.json','PAIR_EVAL_FAILURE.json','PAIR_EVAL_AUDIT_FAILURE.json','COMPLETION.json')){
 if(Test-Path -LiteralPath "$r/$n"){
  $v=([string](Get-Content -LiteralPath "$r/$n" -Raw -Encoding UTF8)) | ConvertFrom-Json
  $o=@{};foreach($k in @('state','pid','step','child_pid','model','batch','batches','actual_forward_calls','actual_sample_forwards','overall_goal_complete','minimum_operational_gate_passed')){$o[$k]=$v.$k}
  if($v.traceback){$s=[string]$v.traceback;$o.traceback_preview=$s.Substring(0,[Math]::Min(3000,$s.Length))};$files[$n]=$o
 }
}
$p=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" | Where-Object {$_.CommandLine -like '*FEDUBA_MIXED_PAIR_EVALUATION_RECOVERY_20261101*'} | Select-Object ProcessId,ParentProcessId,CommandLine)
[pscustomobject]@{utc=(Get-Date).ToUniversalTime().ToString('o');root=$r;files=$files;processes=$p} | ConvertTo-Json -Depth 4 -Compress
