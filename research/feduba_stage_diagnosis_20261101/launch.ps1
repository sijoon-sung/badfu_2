$ErrorActionPreference='Stop'
$root='D:/FEDUBA_STAGE_DIAGNOSIS_20261101'
$name='Codex-FedUBA-stage-diagnosis-CPU8-20261101'
if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){throw 'Exact CPU8 task exists; inspect, never repeat'}
if(Test-Path -LiteralPath "$root/CONTROLLER_ONCE.json"){throw 'CPU8 diagnosis already started'}
$p=Get-Content -LiteralPath "$root/PUBLICATION.json" -Encoding UTF8 -Raw | ConvertFrom-Json
if($p.state -ne 'published_before_new_CPU8_diagnosis'){throw 'New diagnostic contract not published'}
if((Get-FileHash -LiteralPath "$root/FREEZE.json" -Algorithm SHA256).Hash.ToLower() -ne $p.freeze_sha256){throw 'Published freeze mismatch'}
if(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('python.exe','pythonw.exe') -and $_.CommandLine -match 'FEDUBA_PAPER_IMPLEMENTATION_20261031' }){throw 'Old research process active; inspect before new bounded diagnosis'}
$action=New-ScheduledTaskAction -Execute 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -Argument '-B -u D:/FEDUBA_STAGE_DIAGNOSIS_20261101/stage_mode_controller.py' -WorkingDirectory $root
$principal=New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings -Description 'One CPU8 forward-only frozen-surrogate mode diagnosis; no SGD/backward, then independent stored-logit arithmetic; no retries' | Out-Null
Start-ScheduledTask -TaskName $name
Get-ScheduledTask -TaskName $name | Select-Object TaskName,State | ConvertTo-Json
