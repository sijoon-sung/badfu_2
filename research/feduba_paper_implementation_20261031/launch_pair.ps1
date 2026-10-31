$ErrorActionPreference='Stop'
$root='D:/FEDUBA_PAPER_IMPLEMENTATION_20261031'
$name='Codex-FedUBA-SSS-pairedFU20-20261031'
if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) { throw 'Exact paired task exists; inspect rather than duplicate' }
if (Test-Path -LiteralPath "$root/PAIR_CONTROLLER_ONCE.json") { throw 'Paired controller already started' }
$prepared=Get-Content -Raw -LiteralPath "$root/PAIR_PREPARE_RESULT.json" | ConvertFrom-Json
if ($prepared.state -ne 'passed_profiles_prepared_not_started') { throw 'Paired preparation incomplete' }
$published=Get-Content -Raw -LiteralPath "$root/PAIR_PUBLICATION.json" | ConvertFrom-Json
if ($published.state -ne 'published_to_existing_draft_PR') { throw 'Exact profiles not published' }
foreach ($item in $published.profiles_and_freezes_sha256.PSObject.Properties) {
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath ($root+'/'+$item.Name)).Hash.ToLower() -ne $item.Value) { throw ('Published file mismatch: '+$item.Name) }
}
$action=New-ScheduledTaskAction -Execute 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -Argument '-u D:/FEDUBA_PAPER_IMPLEMENTATION_20261031/paired_controller.py' -WorkingDirectory $root
$principal=New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType S4U -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Hours 72) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings -Description 'One fixed SSS, benign/attack FedEraser20 and independent same-delta full evaluation; no triggers or retries' | Out-Null
Start-ScheduledTask -TaskName $name
Get-ScheduledTask -TaskName $name | Select-Object TaskName,State | ConvertTo-Json
