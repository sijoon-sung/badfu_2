$ErrorActionPreference='Stop'
$r=$PSScriptRoot;$name='Codex-FedUBA-mixed-attack-recovery-metadata-prepare-20261101'
function Sha([string]$p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
$pub=Get-Content -LiteralPath "$r/SOURCE_PUBLICATION.json" -Raw -Encoding UTF8 | ConvertFrom-Json
if($pub.state -ne 'published_closed_recovery_source_before_metadata_prepare' -or $pub.source_freeze_sha256 -ne (Sha "$r/SOURCE_FREEZE.json")){throw 'Source publication absent/mismatch'}
$f=Get-Content -LiteralPath "$r/SOURCE_FREEZE.json" -Raw -Encoding UTF8 | ConvertFrom-Json
foreach($kv in $f.files.PSObject.Properties){if((Sha "$r/$($kv.Name)") -ne $kv.Value){throw 'Frozen source mismatch'}}
foreach($n in @('PREPARE_TASK_ONCE.json','PREPARE_ONCE.json','PREPARE_FAILURE.json','LAUNCH_PROFILE.json','RUN_FREEZE.json')){if(Test-Path -LiteralPath "$r/$n"){throw ('Existing preparation artifact '+$n)}}
if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){throw 'Exact preparation task exists'}
$once=[IO.File]::Open("$r/PREPARE_TASK_ONCE.json",[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$b=[Text.Encoding]::UTF8.GetBytes('{"state":"first_metadata_prepare_task_launch"}');$once.Write($b,0,$b.Length)}finally{$once.Dispose()}
$action=New-ScheduledTaskAction -Execute 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -Argument '-B -u D:/FEDUBA_MIXED_ATTACK_RECOVERY_RUN_20261101/prepare_launch.py' -WorkingDirectory $r
$principal=New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Hours 4) -MultipleInstances IgnoreNew -RestartCount 0
Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings -Description 'Once stdlib metadata-only recovery input/profile preparation; zero model loads/forwards' | Out-Null
Start-ScheduledTask -TaskName $name
[pscustomobject]@{state='first_metadata_prepare_task_started';task=$name;model_loads=0;model_forwards=0} | ConvertTo-Json -Compress
