$ErrorActionPreference = 'Stop'
$taskName = 'Codex-FUBA-ten-seed-repro-recovery-20261031'
$studyRoot = 'D:/FUBA_SEED_REPRO_20261031'
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) { throw 'Recovery task already exists; inspect it' }
if (Test-Path -LiteralPath "$studyRoot/RECOVERY_ONCE.json") { throw 'Recovery already started; preserve it' }
if (-not (Test-Path -LiteralPath "$studyRoot/LAUNCH_RECOVERY_READY.json")) { throw 'Missing preservation/CPU ready evidence' }
$action = New-ScheduledTaskAction -Execute 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -Argument '-u D:/FUBA_SEED_REPRO_20261031/background_recovery.py' -WorkingDirectory $studyRoot
$principal = New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Days 3) -MultipleInstances IgnoreNew -Hidden -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $taskName -Action $action -Principal $principal -Settings $settings -Description 'One finite operational recovery of interrupted first role, same nine seeds and numeric source; no retries/triggers' | Out-Null
Start-ScheduledTask -TaskName $taskName
Get-ScheduledTask -TaskName $taskName | Select-Object TaskName,State | ConvertTo-Json -Compress
