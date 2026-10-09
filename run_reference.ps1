$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$TaskPython = Join-Path $PSScriptRoot 'envs/badfu-original/python.exe'
if (-not (Test-Path $TaskPython)) { throw 'Create the original Conda environment first.' }
New-Item -ItemType Directory -Path 'upstream/data_prepare/record' -Force | Out-Null
if (-not (Test-Path 'upstream/data_prepare/record/badnet_original/attack_result.pt')) {
    & $TaskPython -u legacy_prepare.py base --yaml_path ../config/attack/prototype/cifar10.yaml --save_folder_name badnet_original --add_cover 1 --epochs 0 --pratio 0.017 --cratio 0.017 --attack_target 0 --device cuda:0 --num_workers 0
    if ($LASTEXITCODE -ne 0) { throw 'Original base data preparation failed.' }
}
if (-not (Test-Path 'upstream/data_prepare/record/badnet_original/pert_result.pt')) {
    & $TaskPython -u legacy_prepare.py cover --dataset_folder ../record/badnet_original --device cuda:0 --ft_epochs 1 --ap_epochs 1 --num_workers 0
    if ($LASTEXITCODE -ne 0) { throw 'Original cover generation failed.' }
}
& $TaskPython -m unittest test_reference.py
if ($LASTEXITCODE -ne 0) { throw 'Reference compatibility checks failed.' }
& $TaskPython -u reference_runner.py --output results/reference
if ($LASTEXITCODE -ne 0) { throw 'Original execution failed; inspect results/reference/failure.json.' }
