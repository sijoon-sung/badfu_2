$ErrorActionPreference='Stop'
$r=$PSScriptRoot;$name='Codex-FedUBA-mixed-attack-recovery154-FU20-pair-eval-20261101'
function Sha([string]$p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
$pub=Get-Content -LiteralPath "$r/RUN_PUBLICATION.json" -Raw -Encoding UTF8 | ConvertFrom-Json
if($pub.state -ne 'published_actual_attack_recovery154_and_pair_evaluation_before_execution' -or $pub.run_freeze_sha256 -ne (Sha "$r/RUN_FREEZE.json") -or $pub.source_freeze_sha256 -ne (Sha "$r/SOURCE_FREEZE.json")){throw 'Actual recovery not published'}
$f=Get-Content -LiteralPath "$r/RUN_FREEZE.json" -Raw -Encoding UTF8 | ConvertFrom-Json
foreach($kv in $f.files.PSObject.Properties){if((Sha "$r/$($kv.Name)") -ne $kv.Value){throw 'Actual frozen input/source mismatch'}}
$ready=Get-Content -LiteralPath "$r/PREPARE_RESULT.json" -Raw -Encoding UTF8 | ConvertFrom-Json
if($ready.state -ne 'passed_actual_recovery_metadata_preparation'){throw 'Preparation incomplete'}
foreach($n in @('RECOVERY_TASK_ONCE.json','RECOVERY_CONTROLLER_ONCE.json','RECOVERY_CONTROLLER_FAILURE.json','RECOVERY_ATTACK_ONCE.json','FU_attack_RESULT.json','PAIR_EVAL_ONCE.json')){if(Test-Path -LiteralPath "$r/$n"){throw ('Existing finite recovery artifact '+$n)}}
if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){throw 'Exact recovery task exists'}
$alive=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" | Where-Object {$_.CommandLine -like '*FEDUBA_MIXED_ATTACK_RECOVERY_RUN_20261101*' -or $_.CommandLine -like '*FEDUBA_MIXED_PAIR_20261101*' -or $_.CommandLine -like '*FEDUBA_MIXED_ATTACK_PREFIX_GUARD_V2_20261101*verify_prefix.py*'})
if($alive.Count){throw 'Existing original, prepare, audit, or recovery process'}
$once=[IO.File]::Open("$r/RECOVERY_TASK_ONCE.json",[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$b=[Text.Encoding]::UTF8.GetBytes('{"state":"first_recovery154_controller_task_launch"}');$once.Write($b,0,$b.Length)}finally{$once.Dispose()}
$action=New-ScheduledTaskAction -Execute 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -Argument '-B -u D:/FEDUBA_MIXED_ATTACK_RECOVERY_RUN_20261101/recovery_controller.py' -WorkingDirectory $r
$principal=New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Hours 72) -MultipleInstances IgnoreNew -RestartCount 0
Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings -Description 'Once same-condition remaining154 attack roles, fullCPU audit and two full pair evaluations; no SSS/benign repeat or retries' | Out-Null
Start-ScheduledTask -TaskName $name
[pscustomobject]@{state='first_recovery_controller_task_started';task=$name} | ConvertTo-Json -Compress
