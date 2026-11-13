$ErrorActionPreference='Stop'
$r=$PSScriptRoot;$name='Codex-FedUBA-mixed-pair-eval-native-v2-metadata-probe-20261101'
function Sha([string]$p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
$pub=Get-Content -LiteralPath "$r/SOURCE_PUBLICATION.json" -Raw -Encoding UTF8 | ConvertFrom-Json
if($pub.state -ne 'published_closed_evaluation_recovery_source_before_probe_prepare' -or $pub.source_freeze_sha256 -ne (Sha "$r/SOURCE_FREEZE.json")){throw 'Source not published'}
$f=Get-Content -LiteralPath "$r/SOURCE_FREEZE.json" -Raw -Encoding UTF8 | ConvertFrom-Json
foreach($kv in $f.files.PSObject.Properties){if((Sha "$r/$($kv.Name)") -ne $kv.Value){throw 'Source mismatch'}}
foreach($n in @('METADATA_PROBE_TASK_ONCE.json','METADATA_PROBE_ONCE.json','METADATA_PROBE_RESULT.json','METADATA_PROBE_FAILURE.json','LAUNCH_PROFILE.json')){if(Test-Path -LiteralPath "$r/$n"){throw 'Existing finite metadata probe or actual profile'}}
if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){throw 'Metadata probe task exists'}
$s=[IO.File]::Open("$r/METADATA_PROBE_TASK_ONCE.json",[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$b=[Text.Encoding]::UTF8.GetBytes('{"state":"first_S4U_limited_native_metadata_probe_launch"}');$s.Write($b,0,$b.Length)}finally{$s.Dispose()}
$a=New-ScheduledTaskAction -Execute 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -Argument '-B -u D:/FEDUBA_MIXED_PAIR_EVAL_NATIVE_V2_20261101/source_probe.py' -WorkingDirectory $r
$p=New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
$set=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -MultipleInstances IgnoreNew -RestartCount 0
Register-ScheduledTask -TaskName $name -Action $a -Principal $p -Settings $set -Description 'Once source/native commandline metadata probe, same limited principal as future eval, torch/model0' | Out-Null
Start-ScheduledTask -TaskName $name
[pscustomobject]@{state='first_metadata_probe_S4U_task_started';task=$name;model_forwards=0} | ConvertTo-Json -Compress
