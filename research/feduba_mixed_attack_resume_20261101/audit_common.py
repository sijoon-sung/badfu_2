"""Closed, separately published CPU prefix-audit inputs; no numerical imports."""
import base64
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
OLD = Path('D:/FEDUBA_MIXED_PAIR_20261101')
FOUNDATION = Path('D:/FEDUBA_PAPER_IMPLEMENTATION_20261031')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    buffer = bytearray(65536)
    with Path(path).open('rb', buffering=0) as stream:
        while (n := stream.readinto(buffer)):
            h.update(memoryview(buffer)[:n])
    return h.hexdigest()


def once(name, value):
    with (ROOT / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def progress(value):
    target = ROOT / 'AUDIT_STATE.json'
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, allow_nan=False), encoding='utf-8')
    os.replace(temporary, target)


def ps_json(query):
    encoded = base64.b64encode(query.encode('utf-16le')).decode()
    value = subprocess.check_output(['powershell', '-NoProfile', '-NonInteractive',
                                     '-EncodedCommand', encoded], text=True, encoding='utf-8', timeout=30)
    assert len(value) < 10000
    return json.loads(value)


def published_inputs():
    assert ROOT == Path('D:/FEDUBA_MIXED_ATTACK_RESUME_20261101')
    p = read(ROOT / 'CPU_AUDIT_PROFILE.json')
    assert p['CPU_audit_enabled'] is True and p['GPU_resume_launch_enabled'] is False
    assert list(sys.version_info[:3]) == p['python_version']
    for name, version in p['package_versions'].items():
        assert importlib.metadata.version(name) == version, name
    frozen = read(ROOT / 'CPU_AUDIT_FREEZE.json')
    for name, digest in frozen['files'].items():
        assert sha(ROOT / name) == digest, name
    publication = read(ROOT / 'CPU_AUDIT_PUBLICATION.json')
    assert publication['state'] == 'published_finite_CPU_prefix46_audit_before_execution'
    assert publication['freeze_sha256'] == sha(ROOT / 'CPU_AUDIT_FREEZE.json')
    binding = read(ROOT / 'AUDIT_INPUT_BINDING.json')
    assert sha(ROOT / 'AUDIT_INPUT_BINDING.json') == p['input_binding_sha256']
    for meta in binding['external_files'].values():
        assert sha(meta['path']) == meta['sha256'], meta['path']
        assert Path(meta['path']).stat().st_size == meta['bytes']
    preserved = read(binding['external_files']['PREFIX_PRESERVED.json']['path'])
    assert preserved['state'] == 'passed_terminal_original_attack_prefix_hash_preservation'
    assert preserved['committed_rounds'] == 4 and preserved['trained_files'] == 46
    assert not preserved['round5_client10_bundle_exists']
    for name, meta in preserved['all_original_prefix_files'].items():
        path = (OLD / name).resolve()
        assert path.is_relative_to(OLD.resolve())
        assert sha(path) == meta['sha256'] and path.stat().st_size == meta['bytes'], name
    assert read(OLD / 'FU_attack_FAILURE.json')['state'] == 'failed_preserved'
    assert read(OLD / 'PAIR_CONTROLLER_FAILURE.json')['state'] == 'failed_preserved'
    assert read(OLD / 'FU_benign_VERIFIED.json')['state'] == 'passed'
    live = ps_json("$v=@(Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | Where-Object {$_.CommandLine -like '*FEDUBA_MIXED_PAIR_20261101*' -or $_.CommandLine -like '*FEDUBA_MIXED_PAIR_MEMORY_RECOVERY_20261101*preserve_prefix.py*'} | Select-Object -ExpandProperty ProcessId);ConvertTo-Json -InputObject $v -Compress")
    assert not live, live
    sys.path.insert(0, str(OLD))
    import pair_binding
    pair_binding.require_published_run()
    assert 'torch' not in sys.modules
    selected = json.loads(subprocess.check_output([sys.executable, '-B',
        str(Path(p['catalog_root']) / 'select_case.py'), p['case_id'], '--purpose', 'diagnostic'],
        text=True, encoding='utf-8', timeout=60))
    assert selected['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    assert selected['server_inputs']['pre']['sha256'] == p['pre_checkpoint_sha256']
    memory = ps_json("$m=Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory;[pscustomobject]@{availableBytes=[long]$m.AvailableBytes;committedBytes=[long]$m.CommittedBytes;commitLimit=[long]$m.CommitLimit} | ConvertTo-Json -Compress")
    assert memory['availableBytes'] >= p['available_RAM_min_bytes']
    assert memory['commitLimit'] - memory['committedBytes'] >= p['commit_free_min_bytes']
    return p, binding, preserved, pair_binding.foundation_history(), selected, memory
