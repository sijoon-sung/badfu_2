$ErrorActionPreference='Stop'
$root='D:/FEDUBA_PAPER_IMPLEMENTATION_20261031'
$name='Codex-FedUBA-pair-review-finish-CPU-recovery-20261031'
if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){throw 'Exact recovery exists; inspect rather than duplicate'}
if(Test-Path -LiteralPath "$root/PAIR_REVIEW_RECOVERY_ONCE.json"){throw 'Review recovery already started'}
$p=Get-Content -LiteralPath "$root/PAIR_REVIEW_RECOVERY_PUBLICATION.json" -Encoding UTF8 -Raw | ConvertFrom-Json
if($p.state -ne 'new_recovery_source_published_before_execution'){throw 'Recovery not published'}
if((Get-FileHash -LiteralPath "$root/PAIR_REVIEW_RECOVERY_FREEZE.json" -Algorithm SHA256).Hash.ToLower() -ne $p.freeze_sha256){throw 'Published recovery freeze mismatch'}
$action=New-ScheduledTaskAction -Execute 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -Argument '-B -u D:/FEDUBA_PAPER_IMPLEMENTATION_20261031/finish_pair_review_recovery.py' -WorkingDirectory $root
$principal=New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Hours 4) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings -Description 'New CPU finish of preserved copied prefix after export progress-callback collision; no recopy, no training, no retries' | Out-Null
Start-ScheduledTask -TaskName $name
Get-ScheduledTask -TaskName $name | Select-Object TaskName,State | ConvertTo-Json
