$ErrorActionPreference = 'Stop'
$TaskPython = 'C:\Users\sijoo\.conda\envs\pytorch\python.exe'
Set-Location $PSScriptRoot
& $TaskPython -u experiment.py --output results/full --seeds 11 22 33 44 55 --alphas 0 0.1 0.5 1.0 --train-size 0 --rounds 40 --local-epochs 5 --xai-per-class 50 --shap-samples 50
if ($LASTEXITCODE -ne 0) { throw 'Full experiment failed; inspect output and checkpoints.' }
