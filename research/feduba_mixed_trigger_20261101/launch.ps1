$ErrorActionPreference='Stop'
$root='D:/FEDUBA_MIXED_TRIGGER_20261101'
$name='Codex-FedUBA-mixed-teacher-CPU-trigger100-20261101'
if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){throw 'Exact task already exists; inspect, never duplicate'}
if(Test-Path -LiteralPath "$root/CONTROLLER_ONCE.json"){throw 'Exclusive future controller already started'}
if(-not(Test-Path -LiteralPath "$root/RUN_FREEZE.json")){throw 'Source-only branch has no actual run freeze'}
$pub=Get-Content -LiteralPath "$root/RUN_PUBLICATION.json" -Raw -Encoding UTF8 | ConvertFrom-Json
if($pub.state -ne 'published_actual_mixed_teacher_trigger_profile_before_execution'){throw 'Actual profile not published'}
if((Get-FileHash -LiteralPath "$root/RUN_FREEZE.json" -Algorithm SHA256).Hash.ToLower() -ne $pub.run_freeze_sha256){throw 'Published run freeze mismatch'}
if((Get-FileHash -LiteralPath "$root/SOURCE_FREEZE.json" -Algorithm SHA256).Hash.ToLower() -ne $pub.source_freeze_sha256){throw 'Published source freeze mismatch'}
$action=New-ScheduledTaskAction -Execute 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -Argument '-B -u D:/FEDUBA_MIXED_TRIGGER_20261101/trigger_controller.py' -WorkingDirectory $root
$principal=New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Hours 4) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings -Description 'One future CPU trigger100 for an explicitly completed mixed teacher, then independent CPU audit; no retries/SSS/FU' | Out-Null
Start-ScheduledTask -TaskName $name
Get-ScheduledTask -TaskName $name | Select-Object TaskName,State | ConvertTo-Json
