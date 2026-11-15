$ErrorActionPreference='Stop'
$remoteCode=@'
$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
function Read-SharedJson([string]$p){
 $f=[IO.FileStream]::new($p,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
 $reader=[IO.StreamReader]::new($f)
 try{return ($reader.ReadToEnd()|ConvertFrom-Json)}finally{$reader.Dispose()}
}
$root='D:/FUBA_FULLBATCH_DIAGNOSTIC_20261115'
$state=if(Test-Path -LiteralPath ($root+'/STATE.json')){Read-SharedJson ($root+'/STATE.json')}else{@{state='not_started'}}
$manifest=if(Test-Path -LiteralPath ($root+'/MANIFEST.json')){Read-SharedJson ($root+'/MANIFEST.json')}else{$null}
$last=if($manifest){$manifest.rounds[-1]}else{$null}
$count=if($manifest){@($manifest.rounds).Count}else{0}
$processes=@(Get-CimInstance Win32_Process|Where-Object {$_.Name -eq 'python.exe' -and $_.CommandLine -like '*FUBA_FULLBATCH*'}|Select-Object ProcessId,ParentProcessId,CommandLine)
$stages=@{}
foreach($file in @('RESULT.json','CPU_AUDIT.json','INDEPENDENT_RESULT.json','GAMMA_AUDIT.json','delivery/SEAL.json')){
 if(Test-Path -LiteralPath ($root+'/'+$file)){$j=Read-SharedJson ($root+'/'+$file);$stages[$file]=@{state=$j.state;checks=$j.checks;files=$j.files;hypothesis=$j.behavioral_hypothesis_supported}}
}
$ops=if(Test-Path -LiteralPath 'D:/FUBA_FULLBATCH_OPS_20261115'){@(Get-ChildItem -LiteralPath 'D:/FUBA_FULLBATCH_OPS_20261115' -File|Select-Object Name,Length)}else{@()}
@{state=$state;committed_rounds=$count;last_round=$last;processes=$processes;stages=$stages;ops_files=$ops;GPU=(& nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.free --format=csv,noheader,nounits)}|ConvertTo-Json -Depth 7
'@
$encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($remoteCode))
ssh -o ConnectTimeout=10 -o ServerAliveInterval=10 -o ServerAliveCountMax=1 dislab "powershell -NoProfile -EncodedCommand $encoded"
if($LASTEXITCODE -ne 0){throw 'Read-only status failed; inspect without restarting the finite task'}
