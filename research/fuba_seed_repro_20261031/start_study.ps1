$ErrorActionPreference = 'Stop'
$taskName = 'Codex-FUBA-ten-seed-repro-20261031'
$studyRoot = 'D:/FUBA_SEED_REPRO_20261031'
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    throw 'Task already registered; inspect actual processes and state rather than restarting'
}
if (Test-Path -LiteralPath "$studyRoot/STUDY_ONCE.json") {
    throw 'This finite study was already started; preserve it'
}
if (-not (Test-Path -LiteralPath "$studyRoot/PREPARED.json")) { throw 'Missing CPU preparation' }
$pythonPath = 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe'
$launchText = @'
$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:CUDA_VISIBLE_DEVICES = '0'
Set-Location -LiteralPath 'D:/FUBA_SEED_REPRO_20261031'
& 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -u 'D:/FUBA_SEED_REPRO_20261031/study_controller.py' *> 'D:/FUBA_SEED_REPRO_20261031/study_console.log'
exit $LASTEXITCODE
'@
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($launchText))
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -EncodedCommand $encoded" -WorkingDirectory $studyRoot
$principal = New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Days 3) -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $taskName -Action $action -Principal $principal -Settings $settings -Description 'Finite nine new MNIST DBA100R/KD10 seeds plus preserved baseline; no triggers or restarts' | Out-Null
Start-ScheduledTask -TaskName $taskName
Get-ScheduledTask -TaskName $taskName | Select-Object TaskName,State | ConvertTo-Json -Compress
