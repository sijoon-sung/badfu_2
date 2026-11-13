"""Transfer only this frozen study and report actual DISLAB outcomes."""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, 'C:/Users/sijoo/Documents/ChatGPT/badFU/research/00_trajectories')
from dislab_audit import FLAGS, REMOTE, remote, run

DEST = 'D:/LOW_RECURRENCE_CONFIRMATION_20261112'
PYTHON = 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe'
BASE = 'D:/BADFU_FC_PCA_MATCHED_CONTROL_20261112'


def remote_status():
    print(remote(f"""
$r='{DEST}'
$s=[ordered]@{{}}
$s.exists=Test-Path $r
$s.gpu=(& nvidia-smi --query-gpu=memory.free,utilization.gpu --format=csv,noheader,nounits)
$s.active=@(Get-CimInstance Win32_Process | Where-Object {{ $_.CommandLine -match 'LOW_RECURRENCE_CONFIRMATION_20261112' -and $_.Name -eq 'python.exe' }} | Select-Object ProcessId,Name)
foreach($n in @('ONCE','PROGRESS.json','FAILURE.json','PROCESS.json')) {{
    if(Test-Path "$r/$n") {{ $s[$n]=[IO.File]::ReadAllText("$r/$n") }}
}}
$s.result=Test-Path "$r/RESULT.json"
$s|ConvertTo-Json -Depth 5 -Compress
"""))


def main(action):
    if action == 'status':
        remote_status()
    elif action == 'upload':
        remote(f"if(Test-Path '{DEST}') {{ throw 'Destination exists' }}\nNew-Item -ItemType Directory '{DEST}' | Out-Null")
        freeze = json.loads((HERE / 'FREEZE.json').read_text(encoding='utf-8'))
        for name in list(freeze['files']) + ['FREEZE.json', 'PUBLICATION.json']:
            run(['scp.exe', '-q', *FLAGS, str(HERE / name), REMOTE + ':' + DEST + '/' + name])
    elif action == 'execute':
        script = f"""
if(Test-Path '{DEST}/ONCE') {{ throw 'Already executed' }}
$p=Start-Process -FilePath '{PYTHON}' -ArgumentList '-u','{DEST}/evaluate.py' -WorkingDirectory '{DEST}' -WindowStyle Hidden -PassThru -Wait -RedirectStandardOutput '{DEST}/stdout.txt' -RedirectStandardError '{DEST}/stderr.txt'
@{{pid=$p.Id;exit=$p.ExitCode}} | ConvertTo-Json -Compress | Set-Content -LiteralPath '{DEST}/PROCESS.json' -Encoding ascii
exit $p.ExitCode
"""
        raise SystemExit(remote(script, foreground=True))
    elif action == 'fetch':
        for name in ('RESULT.json', 'NEW_SPLITS.json', 'ADMISSION.json', 'PROCESS.json'):
            expected = remote(f"(Get-FileHash -LiteralPath '{DEST}/{name}' -Algorithm SHA256).Hash.ToLower()").strip()
            run(['scp.exe', '-q', *FLAGS, REMOTE + ':' + DEST + '/' + name, str(HERE / name)])
            assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == expected, name
            print(name, expected)
    else:
        raise ValueError(action)


if __name__ == '__main__':
    main(sys.argv[1])
