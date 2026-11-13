$ErrorActionPreference='Stop'
$r=$PSScriptRoot
function Sha([string]$p) { (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() }
$p=Get-Content -LiteralPath "$r/OPS_PROFILE.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$f=Get-Content -LiteralPath "$r/SOURCE_FREEZE.json" -Raw -Encoding UTF8 | ConvertFrom-Json
foreach($kv in $f.files.PSObject.Properties) {if((Sha "$r/$($kv.Name)") -ne $kv.Value){throw 'Source hash mismatch'}}
$pub=Get-Content -LiteralPath "$r/PUBLICATION.json" -Raw -Encoding UTF8 | ConvertFrom-Json
if($pub.state -ne 'published_memory_failure_preservation_and_exact_own_observer_stop_before_execution' -or $pub.source_freeze_sha256 -ne (Sha "$r/SOURCE_FREEZE.json")){throw 'Unpublished operation'}
$own=$p.own_observer
$proc=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$own.pid)
if(!$proc -or $proc.Name -ne 'powershell.exe' -or $proc.ParentProcessId -ne $own.parent_pid){throw 'Own observer identity mismatch'}
$created=([DateTimeOffset]$proc.CreationDate).ToUnixTimeMilliseconds()
$h=[Security.Cryptography.SHA256]::Create()
$digest=([BitConverter]::ToString($h.ComputeHash([Text.Encoding]::UTF8.GetBytes([string]$proc.CommandLine)))).Replace('-','').ToLowerInvariant()
if($created -ne $own.creation_unix_ms -or $digest -ne $own.commandline_sha256){throw 'Own observer creation/command mismatch'}
$alive=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" | Where-Object {$_.CommandLine -like '*FEDUBA_MIXED_PAIR_20261101*'})
if($alive.Count -ne 0){throw 'Original scientific process still alive'}
if(!(Test-Path -LiteralPath "$($p.failed_root)/FU_attack_FAILURE.json") -or !(Test-Path -LiteralPath "$($p.failed_root)/PAIR_CONTROLLER_FAILURE.json")){throw 'Failure records absent'}
function Memory { $o=Get-CimInstance Win32_OperatingSystem; $m=Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory; @{utc=(Get-Date).ToUniversalTime().ToString('o');freePhysicalKiB=[long]$o.FreePhysicalMemory;freeVirtualKiB=[long]$o.FreeVirtualMemory;availableBytes=[long]$m.AvailableBytes;committedBytes=[long]$m.CommittedBytes;commitLimit=[long]$m.CommitLimit} }
$before=Memory
$record=@{state='exact_own_observer_stop_once_started';pid=[int]$own.pid;parent_pid=[int]$own.parent_pid;creation_unix_ms=$created;commandline_sha256=$digest;before=$before}
$once=[IO.File]::Open("$r/OPS_ONCE.json",[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {$bytes=[Text.Encoding]::UTF8.GetBytes(($record | ConvertTo-Json -Depth 4));$once.Write($bytes,0,$bytes.Length)}finally{$once.Dispose()}
$target=Get-Process -Id ([int]$own.pid)
Stop-Process -InputObject $target
$exited=$target.WaitForExit(10000)
if(!$exited){throw 'Own observer did not exit in 10 seconds'}
$after=Memory
$result=@{state='completed_exact_own_historical_readonly_observer_stop';stopped_pid=[int]$own.pid;commandline_sha256=$digest;before=$before;after=$after;other_apps_closed=0;new_training_launched=0;old_source_modified=$false;memory_error_unique_cause_proved=$false}
[IO.File]::WriteAllText("$r/OPS_RESULT.json",($result | ConvertTo-Json -Depth 4),[Text.UTF8Encoding]::new($false))
$result | ConvertTo-Json -Depth 4 -Compress
