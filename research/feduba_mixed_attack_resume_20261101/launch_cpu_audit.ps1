$ErrorActionPreference='Stop'
$r=$PSScriptRoot;$name='Codex-FedUBA-mixed-attack-prefix46-CPU-audit-20261101'
function Sha([string]$p) { (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() }
$pub=Get-Content -LiteralPath "$r/CPU_AUDIT_PUBLICATION.json" -Raw -Encoding UTF8 | ConvertFrom-Json
if($pub.state -ne 'published_finite_CPU_prefix46_audit_before_execution' -or $pub.freeze_sha256 -ne (Sha "$r/CPU_AUDIT_FREEZE.json")){throw 'CPU audit unpublished'}
$f=Get-Content -LiteralPath "$r/CPU_AUDIT_FREEZE.json" -Raw -Encoding UTF8 | ConvertFrom-Json
foreach($kv in $f.files.PSObject.Properties){if((Sha "$r/$($kv.Name)") -ne $kv.Value){throw 'CPU frozen source mismatch'}}
foreach($n in @('AUDIT_ONCE.json','AUDIT_STATE.json','AUDIT_RESULT.json','AUDIT_FAILURE.json','TASK_LAUNCH_ONCE.json')){if(Test-Path -LiteralPath "$r/$n"){throw ('Existing finite audit artifact '+$n)}}
if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){throw 'Exact CPU audit task exists'}
$alive=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" | Where-Object {$_.CommandLine -like '*FEDUBA_MIXED_PAIR_20261101*' -or $_.CommandLine -like '*FEDUBA_MIXED_ATTACK_RESUME_20261101*verify_prefix.py*'})
if($alive.Count){throw 'Existing original or new numerical process'}
$once=[IO.File]::Open("$r/TASK_LAUNCH_ONCE.json",[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$b=[Text.Encoding]::UTF8.GetBytes('{"state":"first_direct_CPU_prefix_audit_launch"}');$once.Write($b,0,$b.Length)}finally{$once.Dispose()}
$action=New-ScheduledTaskAction -Execute 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -Argument '-B -u D:/FEDUBA_MIXED_ATTACK_RESUME_20261101/verify_prefix.py' -WorkingDirectory $r
$principal=New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Hours 4) -MultipleInstances IgnoreNew -RestartCount 0
Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings -Description 'Once independent CPU1 saved attack-prefix46 audit; zero model forward/training and no retries' | Out-Null
Start-ScheduledTask -TaskName $name
[pscustomobject]@{state='first_direct_CPU_prefix46_audit_started';task=$name;GPU_resume_started=$false} | ConvertTo-Json -Compress
