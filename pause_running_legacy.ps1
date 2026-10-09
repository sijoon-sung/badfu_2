# One-time adapter for the process started before cooperative pause support was added.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$TaskPython = Join-Path $PSScriptRoot 'envs/badfu-original/python.exe'
$TaskOutput = Join-Path $PSScriptRoot 'results/reference'
$TaskRunning = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object {
    $_.ExecutablePath -eq $TaskPython -and $_.CommandLine -match 'reference_runner\.py'
})
if ($TaskRunning.Count -ne 1) { throw 'Expected exactly one original runner; no processes stopped.' }
$TaskProcessId = $TaskRunning[0].ProcessId
$TaskBefore = @{}
Get-ChildItem -LiteralPath $TaskOutput -Filter '*_latest.pt' | ForEach-Object {
    $TaskBefore[$_.Name] = $_.LastWriteTimeUtc.Ticks
}
& (Join-Path $PSScriptRoot 'pause_reference.ps1')
while (Get-Process -Id $TaskProcessId -ErrorAction SilentlyContinue) {
    $TaskChanged = @(Get-ChildItem -LiteralPath $TaskOutput -Filter '*_latest.pt' | Where-Object {
        -not $TaskBefore.ContainsKey($_.Name) -or $_.LastWriteTimeUtc.Ticks -gt $TaskBefore[$_.Name]
    })
    if ($TaskChanged.Count -gt 0) {
        $TaskCheck = Get-CimInstance Win32_Process -Filter "ProcessId = $TaskProcessId"
        if ($TaskCheck.ExecutablePath -ne $TaskPython -or $TaskCheck.CommandLine -notmatch 'reference_runner\.py') {
            throw 'Process identity changed; no process stopped.'
        }
        Stop-Process -Id $TaskProcessId
        @{ reason = 'User requested pause; legacy process stopped after atomic round checkpoint';
           checkpoint = $TaskChanged[0].Name; time = (Get-Date).ToString('o') } |
            ConvertTo-Json | Set-Content -LiteralPath (Join-Path $TaskOutput 'paused.json')
        Write-Output "Paused safely after checkpoint: $($TaskChanged[0].Name)"
        exit 0
    }
    Start-Sleep -Seconds 1
}
