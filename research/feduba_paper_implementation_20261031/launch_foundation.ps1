$ErrorActionPreference='Stop'
$root='D:/FEDUBA_PAPER_IMPLEMENTATION_20261031'
$name='Codex-FedUBA-foundation-cleanFL20-20261031'
if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) { throw 'Exact task already exists; inspect, never duplicate' }
if (Test-Path "$root/FOUNDATION_ONCE.json") { throw 'Foundation has already started' }
if (-not (Test-Path "$root/FOUNDATION_FREEZE.json")) { throw 'Missing published source contract' }
$action=New-ScheduledTaskAction -Execute 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -Argument '-u D:/FEDUBA_PAPER_IMPLEMENTATION_20261031/foundation_controller.py' -WorkingDirectory $root
$principal=New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Hours 72) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings -Description 'One finite FedUBA foundation; preserved source, no triggers/retry; STG/attack still separate' | Out-Null
Start-ScheduledTask -TaskName $name
Get-ScheduledTask -TaskName $name | Select-Object TaskName,State | ConvertTo-Json
