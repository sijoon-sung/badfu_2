$ErrorActionPreference='Stop'
$r=$PSScriptRoot
$name='Codex-FedUBA-public-fixed10-clean-review-export-CPU-20261103'
function Sha([string]$p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
try {
 $pub=Get-Content -LiteralPath "$r/RUN_PUBLICATION.json" -Raw -Encoding UTF8|ConvertFrom-Json
 if($pub.state -ne 'published_actual_fixed10_clean_review_before_export' -or $pub.source_freeze_sha256 -ne (Sha "$r/SOURCE_FREEZE.json") -or $pub.run_freeze_sha256 -ne (Sha "$r/RUN_FREEZE.json")){throw 'Actual target-class profiles not published'}
 $f=Get-Content -LiteralPath "$r/RUN_FREEZE.json" -Raw -Encoding UTF8|ConvertFrom-Json
 foreach($kv in $f.files.PSObject.Properties){if((Sha "$r/$($kv.Name)") -ne $kv.Value){throw 'Frozen source/input mismatch'}}
 foreach($n in @('TASK_ONCE.json','CLEAN_EXPORT_ONCE.json','CLEAN_EXPORT_FAILURE.json','CLEAN_REVIEW_DELIVERY_REMOTE.json')){if(Test-Path -LiteralPath "$r/$n"){throw ('Existing artifact '+$n)}}
 if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){throw 'Exact new task already exists'}
 $sp=Get-Content -LiteralPath "$r/SOURCE_PROFILE.json" -Raw -Encoding UTF8|ConvertFrom-Json
 $alive=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe' OR Name='mpiexec.exe'"|Where-Object {$cmd=([string]$_.CommandLine).ToLowerInvariant();$hit=$cmd.Contains('feduba_fixed10_clean_delivery_20261103');foreach($token in $sp.known_training_process_tokens){if($cmd.Contains([string]$token)){$hit=$true}};$hit})
 if($alive.Count){throw 'Competing/current trainer exists'}
 $stream=[IO.File]::Open("$r/TASK_ONCE.json",[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$b=[Text.Encoding]::UTF8.GetBytes('{"state":"first_new_targetclass_pair_controller_launch"}');$stream.Write($b,0,$b.Length);$stream.Flush($true)}finally{$stream.Dispose()}
 $action=New-ScheduledTaskAction -Execute 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -Argument '-B -u D:/FEDUBA_FIXED10_CLEAN_DELIVERY_20261103/export_clean_review.py' -WorkingDirectory $r
 $principal=New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
 $settings=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Hours 48) -MultipleInstances IgnoreNew -RestartCount 0
 Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings -Description 'One new public-fixed10 normal review packet, CPU3 zero1 only; no performance reevaluation'|Out-Null
 Start-ScheduledTask -TaskName $name
 [pscustomobject]@{state='first_targetclass_pair_task_started';task=$name}|ConvertTo-Json -Compress
} catch {
 $value=[pscustomobject]@{state='launch_failed_preserved';message=$_.Exception.Message;stack=$_.ScriptStackTrace}
 if(-not(Test-Path -LiteralPath "$r/LAUNCH_FAILURE.json")){[IO.File]::WriteAllText("$r/LAUNCH_FAILURE.json",($value|ConvertTo-Json),(New-Object Text.UTF8Encoding($false)))}
 throw
}
