$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$root='D:/FUBA_RETRAIN_FU_RECOVERY_20261115'
$launch='D:/FUBA_RETRAIN_FU_FINALIZER_LAUNCH_20261115'
$freeze=Get-Content -LiteralPath ($root+'/FINALIZATION_FREEZE.json') -Raw|ConvertFrom-Json
if((Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath).Hash.ToLowerInvariant() -ne $freeze.files.'finalize_once.ps1'){throw 'Finalizer launcher hash mismatch'}
New-Item -ItemType Directory -Path $launch -ErrorAction Stop | Out-Null
@{PID=$PID;time_UTC=(Get-Date).ToUniversalTime().ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath ($launch+'/STARTED.json') -Encoding UTF8
$child=Start-Process -FilePath 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -ArgumentList @('-u','-B',($root+'/finalize_once.py')) -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput ($launch+'/stdout.log') -RedirectStandardError ($launch+'/stderr.log') -PassThru -Wait
@{PID=$child.Id;exit_code=$child.ExitCode;time_UTC=(Get-Date).ToUniversalTime().ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath ($launch+'/RESULT.json') -Encoding UTF8
exit $child.ExitCode
