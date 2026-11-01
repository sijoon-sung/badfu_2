$ErrorActionPreference='Stop'
$r=$PSScriptRoot;$name='Codex-FedUBA-mixed105-pairedFU20-review-export-CPU-20261101'
function Sha([string]$p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
$pub=Get-Content -LiteralPath "$r/DELIVERY_PUBLICATION.json" -Raw -Encoding UTF8 | ConvertFrom-Json
if($pub.state -ne 'published_actual_mixed_pair_delivery_source_and_profile_before_execution' -or $pub.source_freeze_sha256 -ne (Sha "$r/SOURCE_FREEZE.json") -or $pub.profile_sha256 -ne (Sha "$r/DELIVERY_PROFILE.json")){throw 'Delivery not published'}
$f=Get-Content -LiteralPath "$r/SOURCE_FREEZE.json" -Raw -Encoding UTF8 | ConvertFrom-Json
foreach($kv in $f.files.PSObject.Properties){if((Sha "$r/$($kv.Name)") -ne $kv.Value){throw 'Source mismatch'}}
if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){throw 'Export task exists'}
foreach($n in @('PAIR_REVIEW_EXPORT_ONCE.json','PAIR_REVIEW_EXPORT_FAILURE.json','PAIR_REVIEW_DELIVERY_REMOTE.json','PAIR_REVIEW_DELIVERY.zip')){if(Test-Path -LiteralPath "$r/$n"){throw 'Existing finite export'}}
$task=Get-ScheduledTask -TaskName 'Codex-FedUBA-mixed-pair-eval-native-v2-20261101'
$i=$task|Get-ScheduledTaskInfo
if([string]$task.State -ne 'Ready' -or $i.LastTaskResult -ne 0){throw 'Evaluation not actually terminal passed'}
$p=Get-Content -LiteralPath "$r/DELIVERY_PROFILE.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$alive=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe' OR Name='mpiexec.exe'" | Where-Object {$cmd=([string]$_.CommandLine).ToLowerInvariant().Replace('\','/');$hit=$cmd.Contains('feduba_mixed_pair_delivery_20261101');foreach($v in $p.roots.PSObject.Properties){if($cmd.Contains(([string]$v.Value).ToLowerInvariant())){$hit=$true}};$hit})
if($alive.Count){throw 'Completed producer or current delivery process exists'}
$s=[IO.File]::Open("$r/PAIR_REVIEW_TASK_ONCE.json",[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$b=[Text.Encoding]::UTF8.GetBytes('{"state":"first_mixed_pair_export_CPU_task_launch"}');$s.Write($b,0,$b.Length)}finally{$s.Dispose()}
$a=New-ScheduledTaskAction -Execute 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -Argument '-B -u D:/FEDUBA_MIXED_PAIR_DELIVERY_20261101/export_mixed_pair.py' -WorkingDirectory $r
$principal=New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Hours 48) -MultipleInstances IgnoreNew -RestartCount 0
Register-ScheduledTask -TaskName $name -Action $a -Principal $principal -Settings $settings -Description 'New mixed pair readonly packet export and strict CPU storage check; no training or performance evaluation' | Out-Null
Start-ScheduledTask -TaskName $name
[pscustomobject]@{state='first_mixed_pair_CPU_export_task_started';task=$name} | ConvertTo-Json -Compress
