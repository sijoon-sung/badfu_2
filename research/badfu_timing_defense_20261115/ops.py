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

REMOTE = 'D:/BADFU_TIMING_DEFENSE_20261115'
PYTHON = 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe'
WORKSPACE = 'C:/Users/DISLAB/Documents/antigravity/dazzling-lovelace/research_20261020/stage1_migrated_20261020'
ASSETS = WORKSPACE + '/research/stage1_20261020/assets'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def selection(case, purpose, location='dislab'):
    return json.loads(subprocess.check_output([sys.executable, str(CATALOG / 'select_case.py'), case,
                                              '--purpose', purpose, '--location', location], encoding='utf-8'))


def location(path, digest, **more):
    return {'path': path, 'sha256': digest, **more}


def prepare():
    confirmed_id = 'badfu.confirmed.s20261023.v1'
    local = selection(confirmed_id, 'purification_pilot', 'local')
    assert local['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    confirmed = selection(confirmed_id, 'purification_pilot')
    big = selection('badfu.s20261023.normal_largest0.endpoint_audit20261030', 'diagnostic', 'local')
    assert big['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    paper = selection('badfu.paper32.s20261020', 'purification_pilot')
    ci, bi, pi = (case['server_inputs'] for case in (confirmed, big, paper))
    guard = confirmed['checkpoint_guard']
    cfg = {
        'models': {'normal193': ci['clean_big_post'], 'normal850': ci['clean_post'], 'attack23': ci['post'],
                   'normal228': location('D:/MULTISEED_ACTUAL_FU_20261022/badfu/seed_20261023/normal_largest0_FU/final.pt',
                                         bi['post']['sha256'], payload_key=bi['post']['payload_key']),
                   'infected_normal': pi['infected_benign_post'], 'attack20': pi['post']},
        'selection': [{k: case[k] for k in ('case_id', 'purpose', 'post_type')} for case in (confirmed, big, paper)],
        'snapshot': {'manifest': location(guard['manifest_path'], guard['manifest_sha256']),
                     'seal': location(guard['seal_path'], guard['seal_sha256']),
                     'loader': location(guard['loader_path'], sha(local['checkpoint_guard']['loader_path']))},
        'public_data': location(ASSETS + '/cifar_raw.pt', 'f6ba981b98087d3f8bc6507a45371c1a534cd85d8286a6c1120729b9fa61b820'),
        'retained_data': location(ASSETS + '/cifar_train_raw.pt', '9a0a8a58a74280c91fe4c729c410d5e1ec81a6fc6b8dc5fa992b0be28b237633'),
        'partition': location(ASSETS + '/badfu_full6_split.json', '1d83a25a93e946862f255a04ef623a223843da22127ec72fc7ab6842a08c9def'),
        'infected_normal_removal': location(str(Path(pi['infected_benign_post']['path']).parents[2] / 'benign_deletion_indices.json'),
                                            '44ccefd121daa209f7272009345d4e223750b8d84079381cbb6996b8476fb80b',
                                            format='local_positions', client=1),
        'evaluation_only': {
            'reader': location(WORKSPACE + '/research/stage1_fresh_20261020/badfu_fresh.py',
                               '60360f62c88b7e5021dcd819aca3f9bb3b26fd1e2aab638713c8d2b885b43993'),
            'record': location(WORKSPACE + '/upstream/data_prepare/record/badnet_original/pert_result.pt',
                               'f24015722dd994819578b8f388831199f0bf5a9b7a9d00171f72452efef4c9d6'),
            'table': location(ASSETS + '/badfu_record_inputs.json', '395343feeabcdacfff3d8407d5b18e0edc6488216d6e39da3517e56e7c0106d5'),
        },
    }
    for role, source in cfg['models'].items():
        cfg['models'][role] = {key: source[key] for key in ('path', 'sha256', 'payload_key')}
    (HERE / 'INPUTS.json').write_text(json.dumps(cfg, indent=2) + '\n', encoding='utf-8')
    hashes = {name: sha(HERE / name) for name in ('PROTOCOL.txt', 'timing.py', 'ops.py', 'INPUTS.json')}
    (HERE / 'FREEZE.json').write_text(json.dumps(hashes, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(hashes))


def upload():
    transport.remote(f"if (Test-Path '{REMOTE}') {{ throw 'Destination exists' }}\nNew-Item -ItemType Directory -Path '{REMOTE}' | Out-Null")
    sources = [str(HERE / name) for name in ('PROTOCOL.txt', 'timing.py', 'ops.py', 'INPUTS.json', 'FREEZE.json')]
    transport.run(['scp.exe', '-q', *transport.FLAGS, *sources, transport.REMOTE + ':' + REMOTE + '/'])


def run():
    script = rf'''
$dest='{REMOTE}'
$scriptPath="$dest/timing.py"
if (Test-Path "$dest/STARTED.json") {{ throw 'Attempt already started' }}
$existing = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {{ $_.CommandLine -match 'BADFU_TIMING_DEFENSE_20261115.*timing.py' }}
if ($existing) {{ throw 'Duplicate timing experiment' }}
$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor
$preflight=[PSCustomObject]@{{free_kib=$os.FreePhysicalMemory;commit_free_kib=$os.FreeVirtualMemory;cpu_load=($cpu | Measure-Object -Property LoadPercentage -Average).Average;logical=($cpu | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum}}
if ($preflight.free_kib -lt 5600000 -or $preflight.commit_free_kib -lt 10485760 -or $preflight.cpu_load -gt 65 -or $preflight.logical -lt 8) {{ throw "Resource admission: $preflight" }}
$preflight | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 "$dest/RESOURCE_RECEIPT.json"
$env:CUDA_VISIBLE_DEVICES=''
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONWARNINGS='ignore::UserWarning'
& '{PYTHON}' -u $scriptPath
exit $LASTEXITCODE
'''
    raise SystemExit(transport.remote(script, True))


def status():
    print(transport.remote(rf'''
$dest='{REMOTE}'
$py = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {{ $_.CommandLine -match 'BADFU_TIMING_DEFENSE_20261115.*timing.py' }} | Select-Object ProcessId, ParentProcessId
$steps = Get-ChildItem -LiteralPath $dest -File | Where-Object {{ $_.Name -match '^(STARTED|.*_RESULT|.*_FIT|TERMINAL|FAILURE|NORMAL_GATES|RESOURCE_RECEIPT)\.json$' }} | Select-Object -ExpandProperty Name
[PSCustomObject]@{{process=@($py);stage=@($steps)}} | ConvertTo-Json -Depth 4
foreach ($f in 'TERMINAL','FAILURE') {{ if (Test-Path "$dest/$f.json") {{ Get-Content -Raw "$dest/$f.json" }} }}
'''))


def fetch():
    allowed = ('DATA_RECEIPT.json', 'NORMAL_GATES.json', 'TERMINAL.json', 'FAILURE.json', 'RESOURCE_RECEIPT.json',
               'normal193_RESULT.json', 'normal228_RESULT.json', 'normal850_RESULT.json', 'infected_normal_RESULT.json',
               'attack20_RESULT.json', 'attack23_RESULT.json')
    found = set(transport.remote(f"Get-ChildItem -LiteralPath '{REMOTE}' -File | Select-Object -ExpandProperty Name").splitlines())
    names = [name for name in allowed if name in found]
    if not names:
        raise RuntimeError('No eligible results')
    out = HERE / 'receipts'
    out.mkdir(exist_ok=True)
    for name in names:
        target = out / name
        if target.exists():
            raise FileExistsError(target)
        transport.run(['scp.exe', '-q', *transport.FLAGS, transport.REMOTE + ':' + REMOTE + '/' + name, str(target)])
        expect = transport.remote(f"(Get-FileHash -LiteralPath '{REMOTE}/{name}').Hash.ToLower()").strip()
        assert sha(target) == expect
    print(json.dumps(names))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'upload', 'run', 'status', 'fetch'])
    action = parser.parse_args().action
    globals()[action]()
