$ErrorActionPreference = 'Stop'
$TaskPython = 'C:\Users\sijoo\.conda\envs\pytorch\python.exe'
Set-Location $PSScriptRoot
New-Item -ItemType Directory -Path 'upstream/data_prepare/record' -Force | Out-Null
if (-not (Test-Path 'upstream/data_prepare/record/badnet_seed0/attack_result.pt')) {
    # Existing base output folder must be inspected before rerunning base preparation.
    & $TaskPython -u legacy_prepare.py base --yaml_path ../config/attack/prototype/cifar10.yaml --save_folder_name badnet_seed0 --add_cover 1 --epochs 0 --pratio 0.017 --cratio 0.017 --attack_target 0 --device cuda:0 --num_workers 0
    if ($LASTEXITCODE -ne 0) { throw 'Base preparation failed.' }
}
if (-not (Test-Path 'upstream/data_prepare/record/badnet_seed0/pert_result.pt')) {
    & $TaskPython -u legacy_prepare.py cover --dataset_folder ../record/badnet_seed0 --device cuda:0 --ft_epochs 1 --ap_epochs 1 --num_workers 0
    if ($LASTEXITCODE -ne 0) { throw 'Influence-crafted cover preparation failed.' }
}
& $TaskPython -u experiment.py --output results/pilot --seeds 11 22 33 --alphas 0.5
if ($LASTEXITCODE -ne 0) { throw 'Pilot experiment failed.' }
