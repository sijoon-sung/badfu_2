$ErrorActionPreference='Stop'
$root='D:/FEDUBA_PAPER_IMPLEMENTATION_20261031'
$name='Codex-FedUBA-STG100-5-100-20261031'
if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) { throw 'Exact task exists; inspect and do not duplicate' }
if (Test-Path "$root/STG_CONTROLLER_ONCE.json") { throw 'STG controller already started' }
if (-not (Test-Path "$root/STG_FREEZE.json")) { throw 'Source freeze missing' }
$action=New-ScheduledTaskAction -Execute 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -Argument '-u D:/FEDUBA_PAPER_IMPLEMENTATION_20261031/stg_controller.py' -WorkingDirectory $root
$principal=New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Hours 72) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings -Description 'One FedUBA external-only STG100/5/100 after verified clean-FL; no triggers/retries; fixed literal SGD contract' | Out-Null
Start-ScheduledTask -TaskName $name
Get-ScheduledTask -TaskName $name | Select-Object TaskName,State | ConvertTo-Json
