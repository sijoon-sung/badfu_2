$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$TaskOutput = Join-Path $PSScriptRoot 'results/reference'
$TaskPython = (Join-Path $PSScriptRoot 'envs/badfu-original/python.exe')
$TaskRunning = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object {
    $_.ExecutablePath -eq $TaskPython -and $_.CommandLine -match 'reference_runner\.py'
})
if ($TaskRunning.Count -gt 0) { throw 'An original run is already active; do not start a second run.' }
foreach ($TaskMarker in @('PAUSE', 'paused.json')) {
    $TaskMarkerPath = Join-Path $TaskOutput $TaskMarker
    if (Test-Path -LiteralPath $TaskMarkerPath) { Remove-Item -LiteralPath $TaskMarkerPath }
}
& (Join-Path $PSScriptRoot 'run_reference.ps1') *>> (Join-Path $PSScriptRoot 'reference.log')
