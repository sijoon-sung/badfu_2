$ErrorActionPreference='Stop'
$root='D:/FEDUBA_PAPER_IMPLEMENTATION_20261031'
$name='Codex-FedUBA-STG-CPU-trigger100-recovery-20261031'
if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){throw 'Exact CPU recovery task exists; do not repeat'}
if(Test-Path -LiteralPath "$root/STG_CPU_TRIGGER_CONTROLLER_ONCE.json"){throw 'CPU recovery already started'}
if(-not(Test-Path -LiteralPath "$root/STG_CPU_TRIGGER_FREEZE.json")){throw 'Recovery source freeze missing'}
$action=New-ScheduledTaskAction -Execute 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -Argument '-u D:/FEDUBA_PAPER_IMPLEMENTATION_20261031/cpu_trigger_controller.py' -WorkingDirectory $root
$principal=New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Hours 4) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings -Description 'New declared CPU-only literal SGD trigger100 from unchanged original100/5 surrogate; preserve failed CUDA branch, no retries' | Out-Null
Start-ScheduledTask -TaskName $name
Get-ScheduledTask -TaskName $name | Select-Object TaskName,State | ConvertTo-Json
