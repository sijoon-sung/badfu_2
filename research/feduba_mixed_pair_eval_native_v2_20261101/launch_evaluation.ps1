$ErrorActionPreference='Stop'
$r=$PSScriptRoot;$name='Codex-FedUBA-mixed-pair-eval-native-v2-20261101'
function Sha([string]$p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
$pub=Get-Content -LiteralPath "$r/RUN_PUBLICATION.json" -Raw -Encoding UTF8 | ConvertFrom-Json
if($pub.state -ne 'published_actual_evaluation_only_nativeguard_recovery_before_execution' -or $pub.run_freeze_sha256 -ne (Sha "$r/RUN_FREEZE.json") -or $pub.source_freeze_sha256 -ne (Sha "$r/SOURCE_FREEZE.json")){throw 'Actual evaluation recovery not published'}
$f=Get-Content -LiteralPath "$r/RUN_FREEZE.json" -Raw -Encoding UTF8 | ConvertFrom-Json
foreach($kv in $f.files.PSObject.Properties){if((Sha "$r/$($kv.Name)") -ne $kv.Value){throw 'Actual frozen source/input mismatch'}}
$p=Get-Content -LiteralPath "$r/PREPARE_RESULT.json" -Raw -Encoding UTF8 | ConvertFrom-Json
if($p.state -ne 'passed_actual_evaluation_only_metadata_preparation'){throw 'Metadata preparation not passed'}
foreach($n in @('EVALUATION_TASK_ONCE.json','EVALUATION_CONTROLLER_ONCE.json','EVALUATION_CONTROLLER_FAILURE.json','PAIR_EVAL_ONCE.json','PAIR_EVAL_RESULT.json')){if(Test-Path -LiteralPath "$r/$n"){throw ('Existing finite evaluation artifact '+$n)}}
if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){throw 'Exact new task already exists'}
$sp=Get-Content -LiteralPath "$r/SOURCE_PROFILE.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$alive=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe' OR Name='mpiexec.exe'" | Where-Object {$cmd=([string]$_.CommandLine).ToLowerInvariant();$hit=$cmd.Contains('feduba_mixed_pair_eval_native_v2_20261101');foreach($token in $sp.known_training_process_tokens){if($cmd.Contains([string]$token)){$hit=$true}};$hit} | Select-Object ProcessId,ParentProcessId,CommandLine)
if($alive.Count){throw 'Original fixed competing-trainer or current recovery process exists'}
$once=[IO.File]::Open("$r/EVALUATION_TASK_ONCE.json",[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$b=[Text.Encoding]::UTF8.GetBytes('{"state":"first_evaluation_only_recovery_controller_task_launch"}');$once.Write($b,0,$b.Length)}finally{$once.Dispose()}
$a=New-ScheduledTaskAction -Execute 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -Argument '-B -u D:/FEDUBA_MIXED_PAIR_EVAL_NATIVE_V2_20261101/evaluation_controller.py' -WorkingDirectory $r
$principal=New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Hours 48) -MultipleInstances IgnoreNew -RestartCount 0
Register-ScheduledTask -TaskName $name -Action $a -Principal $principal -Settings $settings -Description 'Once primary and independent same-condition mixed pair evaluations only; native process guard; no training/audit reruns' | Out-Null
Start-ScheduledTask -TaskName $name
[pscustomobject]@{state='first_evaluation_only_recovery_task_started';task=$name} | ConvertTo-Json -Compress
