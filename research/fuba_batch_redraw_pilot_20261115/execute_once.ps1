$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$root='D:/FUBA_BATCH_REDRAW_PILOT_20261115'
$launch='D:/FUBA_BATCH_REDRAW_LAUNCH_20261115'
$freeze=Get-Content -LiteralPath ($root+'/EXECUTION_FREEZE.json') -Raw|ConvertFrom-Json
if((Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $freeze.files.'execute_once.ps1'){throw 'Launcher hash mismatch'}
New-Item -ItemType Directory -Path $launch -ErrorAction Stop|Out-Null
@{PID=$PID;time_UTC=(Get-Date).ToUniversalTime().ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath ($launch+'/STARTED.json') -Encoding UTF8
$child=Start-Process -FilePath 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -ArgumentList @('-u','-B',($root+'/execute_once.py')) -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput ($launch+'/stdout.log') -RedirectStandardError ($launch+'/stderr.log') -PassThru -Wait
@{PID=$child.Id;exit_code=$child.ExitCode;time_UTC=(Get-Date).ToUniversalTime().ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath ($launch+'/RESULT.json') -Encoding UTF8
exit $child.ExitCode
