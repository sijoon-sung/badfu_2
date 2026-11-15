"""Prepare and run this single DISLAB CPU experiment using the existing transport."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CATALOG = HERE.parent / '00_trajectories'
sys.path.insert(0, str(CATALOG))
import dislab_audit as transport

REMOTE = 'D:/BADFU_RECOVERY_MARGIN_REAL_20261115'
PYTHON = 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe'

PRIOR = HERE.parent / 'badfu_timing_defense_20261115'
P06 = HERE.parent / 'badfu_recovery_margin_20261115'
SOURCES = {
    'timing.py': (PRIOR, '1c7461b4f7372afa868b939ce37c992286dfb65af6f41bb4c891ac1e06bcdb33'),
    'INPUTS.json': (PRIOR, 'a0073c6fc8bec852589cc987f1b3b5eddf4dbe2cfb327cc8eb413912a96725c8'),
    'recovery_margin.py': (P06, '40a6a82cb528557e16e42f8a1f562b990ab11a1fb66ca6235cfc86c3fa447590'),
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def selection(case, purpose, location='dislab'):
    cmd = [sys.executable, str(CATALOG / 'select_case.py'), case, '--purpose', purpose, '--location', location]
    return json.loads(subprocess.check_output(cmd, encoding='utf-8'))


def prepare():
    if (HERE / 'FREEZE.json').exists():
        raise FileExistsError('Already frozen')
    for name, (folder, expected) in SOURCES.items():
        assert sha(folder / name) == expected
    cfg = json.loads((PRIOR / 'INPUTS.json').read_text(encoding='utf-8'))
    confirmed_id = 'badfu.confirmed.s20261023.v1'
    local = selection(confirmed_id, 'purification_pilot', 'local')
    confirmed = selection(confirmed_id, 'purification_pilot')
    big = selection('badfu.s20261023.normal_largest0.endpoint_audit20261030', 'diagnostic', 'local')
    paper = selection('badfu.paper32.s20261020', 'purification_pilot')
    assert all(r['guard_state'] == 'all_snapshot_files_verified_on_this_host' for r in (local, big))
    roles = {'normal193': (confirmed, 'clean_big_post'), 'normal850': (confirmed, 'clean_post'),
             'attack23': (confirmed, 'post'), 'normal228': (big, 'post'),
             'infected_normal': (paper, 'infected_benign_post'), 'attack20': (paper, 'post')}
    for name, (catalogue, key) in roles.items():
        entry = catalogue['server_inputs'][key]
        fields = ('sha256', 'payload_key') if name == 'normal228' else ('path', 'sha256', 'payload_key')
        assert all(entry[field] == cfg['models'][name][field] for field in fields), name
    for name, (folder, expected) in SOURCES.items():
        with (HERE / name).open('xb') as f:
            f.write((folder / name).read_bytes())
        assert sha(HERE / name) == expected
    files = ('PROTOCOL_KO.txt', 'run_real.py', 'ops_real.py', *SOURCES)
    with (HERE / 'FREEZE.json').open('x', encoding='utf-8') as f:
        json.dump({name: sha(HERE / name) for name in files}, f, indent=2)
        f.write('\n')
    print((HERE / 'FREEZE.json').read_text())


def upload():
    transport.remote(f"if (Test-Path '{REMOTE}') {{ throw 'Destination exists' }}\nNew-Item -ItemType Directory -Path '{REMOTE}' | Out-Null")
    freeze = json.loads((HERE / 'FREEZE.json').read_text(encoding='utf-8'))
    for name, expected in freeze.items():
        assert sha(HERE / name) == expected
    files = [str(HERE / name) for name in (*freeze, 'FREEZE.json')]
    transport.run(['scp.exe', '-q', *transport.FLAGS, *files, transport.REMOTE + ':' + REMOTE + '/'])


def run():
    script = rf'''
$dest='{REMOTE}'
if ((Test-Path "$dest/STARTED.json") -or (Test-Path "$dest/FAILURE.json")) {{ throw 'Attempt already started' }}
$existing = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {{ $_.CommandLine -match '(BADFU_TIMING_DEFENSE_20261115.*timing.py|BADFU_RECOVERY_MARGIN_REAL_20261115.*run_real.py)' }}
if ($existing) {{ throw 'Experiment already active' }}
$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor
$preflight=[PSCustomObject]@{{free_kib=$os.FreePhysicalMemory;commit_free_kib=$os.FreeVirtualMemory;cpu_load=($cpu | Measure-Object -Property LoadPercentage -Average).Average;logical=($cpu | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum;disk_bytes=(Get-PSDrive D).Free;cpu_threads=4;cuda_visible=$false}}
if ($preflight.free_kib -lt 5600000 -or $preflight.commit_free_kib -lt 10485760 -or $preflight.cpu_load -gt 65 -or $preflight.logical -lt 8 -or $preflight.disk_bytes -lt 104857600) {{ throw "Resource admission: $preflight" }}
$preflight | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 "$dest/RESOURCE_RECEIPT.json"
$env:CUDA_VISIBLE_DEVICES=''
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONWARNINGS='ignore::UserWarning'
& '{PYTHON}' -u "$dest/run_real.py"
exit $LASTEXITCODE
'''
    raise SystemExit(transport.remote(script, True))


def status():
    print(transport.remote(rf'''
$dest='{REMOTE}'
$py = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {{ $_.CommandLine -match 'BADFU_RECOVERY_MARGIN_REAL_20261115.*run_real.py' }} | Select-Object ProcessId,ParentProcessId
$files = Get-ChildItem -LiteralPath $dest -File | Select-Object -ExpandProperty Name
[PSCustomObject]@{{process=@($py);stage=@($files)}} | ConvertTo-Json -Depth 4
foreach ($f in 'TERMINAL','FAILURE') {{ if (Test-Path "$dest/$f.json") {{ Get-Content -Raw "$dest/$f.json" }} }}
'''))


def fetch():
    allowed = {'RESOURCE_RECEIPT.json', 'STARTED.json', 'DATA_RECEIPT.json', 'TERMINAL.json', 'FAILURE.json'}
    allowed.update(f'{name}_{kind}.json' for name in ('normal193', 'normal228', 'normal850', 'infected_normal', 'attack20', 'attack23')
                   for kind in ('FIT', 'RESULT'))
    rows = transport.remote(f'''
Get-ChildItem -LiteralPath '{REMOTE}' -File -Filter '*.json' | ForEach-Object {{
    $_.Name + ' ' + (Get-FileHash -LiteralPath $_.FullName).Hash.ToLower()
}}
''').splitlines()
    seen = dict(row.split() for row in rows)
    expected = {name: seen[name] for name in sorted(allowed & seen.keys())}
    if not expected.keys() & {'TERMINAL.json', 'FAILURE.json'}:
        raise RuntimeError('No terminal receipt')
    out = HERE / 'receipts'
    out.mkdir(exist_ok=True)
    missing = [name for name in expected if not (out / name).exists()]
    if missing:
        files = [transport.REMOTE + ':' + REMOTE + '/' + name for name in missing]
        transport.run(['scp.exe', '-q', *transport.FLAGS, *files, str(out)])
    for name, digest in expected.items():
        assert sha(out / name) == digest, name
    manifest = out / 'REMOTE_SHA256.json'
    with manifest.open('x', encoding='utf-8') as f:
        json.dump(expected, f, indent=2)
        f.write('\n')
    print(json.dumps(expected))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'upload', 'run', 'status', 'fetch'])
    globals()[parser.parse_args().action]()
