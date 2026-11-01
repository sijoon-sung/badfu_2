$ErrorActionPreference='Stop'
$r=$PSScriptRoot;$name='Codex-FedUBA-mixed-pair-prefix-preservation-20261101'
function Sha([string]$path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
$pub=Get-Content -LiteralPath "$r/PREFIX_LAUNCH_PUBLICATION.json" -Raw -Encoding UTF8 | ConvertFrom-Json
if($pub.state -ne 'published_direct_scheduled_prefix_invocation_before_execution' -or $pub.invocation_freeze_sha256 -ne (Sha "$r/INVOCATION_FREEZE.json")){throw 'Invocation unpublished'}
$f=Get-Content -LiteralPath "$r/INVOCATION_FREEZE.json" -Raw -Encoding UTF8 | ConvertFrom-Json
foreach($kv in $f.files.PSObject.Properties){if((Sha "$r/$($kv.Name)") -ne $kv.Value){throw 'Invocation frozen byte mismatch'}}
foreach($n in @('PREFIX_ONCE.json','PREFIX_STATE.json','PREFIX_FAILURE.json','PREFIX_PRESERVED.json','PREFIX_TASK_LAUNCH_ONCE.json')){if(Test-Path -LiteralPath "$r/$n"){throw ('Existing preservation artifact '+$n)}}
if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){throw 'Exact preservation task exists'}
$alive=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" | Where-Object {$_.CommandLine -like '*FEDUBA_MIXED_PAIR_MEMORY_RECOVERY_20261101*preserve_prefix.py*'})
if($alive.Count){throw 'Existing preservation Python'}
$once=[IO.File]::Open("$r/PREFIX_TASK_LAUNCH_ONCE.json",[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$b=[Text.Encoding]::UTF8.GetBytes('{"state":"first_direct_scheduled_preservation_launch"}');$once.Write($b,0,$b.Length)}finally{$once.Dispose()}
$action=New-ScheduledTaskAction -Execute 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -Argument '-B -u D:/FEDUBA_MIXED_PAIR_MEMORY_RECOVERY_20261101/preserve_prefix.py' -WorkingDirectory $r
$principal=New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew -RestartCount 0
Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings -Description 'Once metadata-only streaming prefix hashes after exact own observer cleanup; no numerical training or retries' | Out-Null
Start-ScheduledTask -TaskName $name
[pscustomobject]@{state='first_direct_scheduled_preservation_started';task=$name;new_training=0} | ConvertTo-Json -Compress
