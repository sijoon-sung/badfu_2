$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path 'upstream/badfu.py')) {
    & git clone https://github.com/BingguangLu/BadFU.git upstream
    if ($LASTEXITCODE -ne 0) { throw 'Upstream clone failed.' }
}
& git -C upstream checkout 0a2117feab58faf5b7e2a1e5e1759112087d6049
if ($LASTEXITCODE -ne 0) { throw 'Could not select the recorded upstream commit.' }
$TaskEnv = Join-Path $PSScriptRoot 'envs/badfu-original'
if (-not (Test-Path (Join-Path $TaskEnv 'python.exe'))) {
    & conda create --prefix $TaskEnv python=3.11 pip -y
    if ($LASTEXITCODE -ne 0) { throw 'Conda environment creation failed; use a Conda-enabled PowerShell.' }
}
$TaskPython = Join-Path $TaskEnv 'python.exe'
& $TaskPython -m pip install --extra-index-url https://download.pytorch.org/whl/cu118 -r original-environment-lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Original environment installation failed.' }
& $TaskPython download_data.py
if ($LASTEXITCODE -ne 0) { throw 'CIFAR-10 download or verification failed.' }
& $TaskPython -m unittest test_reference.py
if ($LASTEXITCODE -ne 0) { throw 'Compatibility checks failed.' }
