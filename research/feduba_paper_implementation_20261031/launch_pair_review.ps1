$ErrorActionPreference='Stop'
$root='D:/FEDUBA_PAPER_IMPLEMENTATION_20261031'
$name='Codex-FedUBA-pair-review-export-CPU-20261031'
if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){throw 'Exact export task exists; inspect, never repeat'}
if(Test-Path -LiteralPath "$root/PAIR_REVIEW_EXPORT_ONCE.json"){throw 'Review export already started'}
$publication=Get-Content -LiteralPath "$root/PAIR_REVIEW_PUBLICATION.json" -Encoding UTF8 -Raw | ConvertFrom-Json
if($publication.state -ne 'source_freeze_published_before_export'){throw 'Review code/freeze not published'}
if((Get-FileHash -LiteralPath "$root/PAIR_REVIEW_FREEZE.json" -Algorithm SHA256).Hash.ToLower() -ne $publication.freeze_sha256){throw 'Published freeze mismatch'}
$action=New-ScheduledTaskAction -Execute 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -Argument '-B -u D:/FEDUBA_PAPER_IMPLEMENTATION_20261031/export_pair_review.py' -WorkingDirectory $root
$principal=New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Hours 4) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings -Description 'One CPU readonly diagnostic review export; no training/inference reevaluation, no triggers/retries' | Out-Null
Start-ScheduledTask -TaskName $name
Get-ScheduledTask -TaskName $name | Select-Object TaskName,State | ConvertTo-Json
