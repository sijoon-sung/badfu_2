$ErrorActionPreference='Stop'
$remoteCode=@'
$ProgressPreference='SilentlyContinue'
function Read-SharedJson([string]$p){
    $f=[IO.FileStream]::new($p,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    $r=[IO.StreamReader]::new($f)
    try{return ($r.ReadToEnd()|ConvertFrom-Json)}finally{$r.Dispose()}
}
$root='D:/FUBA_RETRAIN_FU_RECOVERY_20261115'
$state=if(Test-Path -LiteralPath ($root+'/STATE.json')){Read-SharedJson ($root+'/STATE.json')}else{@{state='not_started'}}
$manifest=Read-SharedJson ($root+'/MANIFEST.json')
$processes=@(Get-CimInstance Win32_Process|Where-Object {$_.Name -eq 'python.exe' -and ($_.CommandLine -like '*FUBA_RETRAIN_FU_RECOVERY_20261115/run.py train*' -or $_.CommandLine -like '*FUBA_RETRAIN_FU_RECOVERY_20261115/retry_preflight.py*')}|Select-Object ProcessId,ParentProcessId,CommandLine)
$failures=@(Get-ChildItem -LiteralPath $root -Filter 'FAILURE*.json' -File|Select-Object Name,Length)
@{host_time_UTC=(Get-Date).ToUniversalTime().ToString('o');state=$state;processes=$processes;committed_rounds=$manifest.rounds.Count;last_round=$manifest.rounds[-1];failures=$failures;GPU=(& nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.free --format=csv,noheader,nounits)}|ConvertTo-Json -Depth 8
'@
$encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($remoteCode))
& ssh -o ConnectTimeout=10 -o ConnectionAttempts=1 dislab "powershell -NoProfile -EncodedCommand $encoded"
if($LASTEXITCODE -ne 0){throw 'Read-only status connection failed; do not infer trainer state or restart it'}
