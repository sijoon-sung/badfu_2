$ErrorActionPreference='Stop'
$root='D:/FEDUBA_MIXED_SURROGATE_20261101'
$name='Codex-FedUBA-mixed-surrogate100-warmup5-20261101'
if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){throw 'Exact task exists; inspect, never duplicate'}
if(Test-Path -LiteralPath "$root/CONTROLLER_ONCE.json"){throw 'Exclusive controller already started'}
$p=Get-Content -LiteralPath "$root/PUBLICATION.json" -Raw -Encoding UTF8 | ConvertFrom-Json
if($p.state -ne 'published_before_mixed_teacher_training'){throw 'New contract not published'}
if((Get-FileHash -LiteralPath "$root/FREEZE.json" -Algorithm SHA256).Hash.ToLower() -ne $p.freeze_sha256){throw 'Published freeze mismatch'}
$action=New-ScheduledTaskAction -Execute 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -Argument '-B -u D:/FEDUBA_MIXED_SURROGATE_20261101/mixed_controller.py' -WorkingDirectory $root
$principal=New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Hours 72) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings -Description 'One mixed100/warmup5 teacher-only branch, CPU audit and four CPU endpoint forwards; no trigger/SSS/FU or retries' | Out-Null
Start-ScheduledTask -TaskName $name
Get-ScheduledTask -TaskName $name | Select-Object TaskName,State | ConvertTo-Json
