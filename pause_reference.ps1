$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$TaskOutput = Join-Path $PSScriptRoot 'results/reference'
New-Item -ItemType Directory -Path $TaskOutput -Force | Out-Null
Set-Content -LiteralPath (Join-Path $TaskOutput 'PAUSE') -Value 'Pause at the next saved round.'
Write-Output 'Pause requested. Updated runners stop after saving the current round.'
