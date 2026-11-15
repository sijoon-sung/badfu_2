$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$root='D:/FUBA_RETRAIN_FU_RECOVERY_20261115'
$freeze=Get-Content -LiteralPath ($root+'/ATTEMPT2_FREEZE.json') -Raw|ConvertFrom-Json
$actual=(Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath).Hash.ToLowerInvariant()
if($actual -ne $freeze.files.'launch_attempt2.ps1'){throw 'Launcher hash mismatch'}
if(Test-Path -LiteralPath ($root+'/STARTED.json')){throw 'Training has already started'}
$active=@(Get-CimInstance Win32_Process|Where-Object {$_.Name -eq 'python.exe' -and ($_.CommandLine -like '*FUBA_RETRAIN_FU*run.py train*' -or $_.CommandLine -like '*FUBA_RETRAIN_FU_RECOVERY*retry_preflight.py*')})
if($active.Count -ne 0){throw 'Another FU trainer is active'}
$marker=[IO.FileStream]::new(($root+'/LAUNCH_ATTEMPT2_STARTED.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
$writer=[IO.StreamWriter]::new($marker)
try{$writer.Write((@{launcher_PID=$PID;time_UTC=(Get-Date).ToUniversalTime().ToString('o');task='Codex-FUBA-retrain-FU-recovery-20261115-attempt2';rounds='28-100'}|ConvertTo-Json))}finally{$writer.Dispose()}
$child=Start-Process -FilePath 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -ArgumentList @('-u','-B',($root+'/retry_preflight.py')) -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput ($root+'/stdout_attempt2.log') -RedirectStandardError ($root+'/stderr_attempt2.log') -PassThru -Wait
@{trainer_PID=$child.Id;exit_code=$child.ExitCode;time_UTC=(Get-Date).ToUniversalTime().ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath ($root+'/LAUNCH_ATTEMPT2_RESULT.json') -Encoding UTF8
exit $child.ExitCode
