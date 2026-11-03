$ErrorActionPreference='Stop'
$root='D:/FEDUBA_PAPER_IMPLEMENTATION_20261031'
$name='Codex-FedUBA-STG-gradient-diagnosis-20261031'
if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) { throw 'Exact diagnostic task exists; do not duplicate' }
if (Test-Path -LiteralPath "$root/STG_GRAD_DIAG_CONTROLLER_ONCE.json") { throw 'Numeric diagnostic already started' }
if (-not (Test-Path -LiteralPath "$root/STG_GRAD_DIAG_FREEZE.json")) { throw 'Diagnostic source freeze missing' }
if (Test-Path -LiteralPath "$root/STG_VERIFIED.json") { throw 'Unexpected verified result; inspect changed state' }
$action=New-ScheduledTaskAction -Execute 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -Argument '-u D:/FEDUBA_PAPER_IMPLEMENTATION_20261031/stg_gradient_diag_controller.py' -WorkingDirectory $root
$principal=New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings -Description 'Only two fixed stored STG steps in four numeric modes; no optimizer steps or training retries' | Out-Null
Start-ScheduledTask -TaskName $name
Get-ScheduledTask -TaskName $name | Select-Object TaskName,State | ConvertTo-Json
