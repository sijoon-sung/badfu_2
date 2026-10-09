$ErrorActionPreference = 'Stop'
$TaskPython = 'C:\Users\sijoo\.conda\envs\pytorch\python.exe'
Set-Location $PSScriptRoot
& $TaskPython -u experiment.py --output results/pilot --seeds 11 22 33 --alphas 0.5
if ($LASTEXITCODE -ne 0) { throw 'Pilot experiment failed; inspect output and checkpoints.' }
