"""One-time CPU-only packet for the NEW completed run; never trains/evaluates data."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = ''
import torch
from common import ROOT, load_model_class, read, sha, write

PACKET = ROOT / 'delivery_packet'


def finite_cpu(value):
    if isinstance(value, torch.Tensor):
        assert value.device.type == 'cpu' and bool(torch.isfinite(value).all())
    elif isinstance(value, dict):
        for item in value.values():
            finite_cpu(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            finite_cpu(item)


def main():
    assert not PACKET.exists(), 'Existing packet is preserved; do not overwrite'
    assert PACKET.resolve().is_relative_to(ROOT.resolve())
    assert not (ROOT / 'DELIVERY_MANIFEST.json').exists()
    assert not (ROOT / 'DELIVERY_SEAL.json').exists()
    for name, digest in read(ROOT / 'DELIVERY_SOURCE_FREEZE.json')['files'].items():
        assert sha(ROOT / name) == digest, name
    r, v, a = (read(ROOT / name) for name in ['RESULT.json', 'VERIFIED.json', 'CPU_AUDIT_through0100.json'])
    assert r['state'] == 'completed100R_KD10' and r['rounds'] == 100 and r['roles'] == 800
    assert v['state'] == a['state'] == 'passed' and a['through_round'] == 100
    assert a['counts']['roles'] == 800 and v['KD_batches'] == r['KD_batches'] == 470
    assert read(ROOT / 'CONTROLLER_STATE.json')['state'] == 'complete_verified'
    for label in ['before', 'after']:
        for key in ['clean_correct', 'target_successes', 'non_target_N']:
            assert v['independent_counts'][label][key] == r[label][key]
    command = "Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python' -and $_.CommandLine -like '*FUBA_REFERENCE_MNIST_DBA_20261031*'} | Select-Object ProcessId,CommandLine | ConvertTo-Json"
    raw = subprocess.check_output(['powershell', '-NoProfile', '-Command', command], text=True).strip()
    processes = json.loads(raw) if raw else []
    if isinstance(processes, dict):
        processes = [processes]
    for process in processes:
        if process['ProcessId'] != os.getpid():
            assert not any(name in process.get('CommandLine', '') for name in ['runner.py', 'controller.py', 'verify.py', 'audit_committed.py', 'package_delivery.py']), process
    ready = read(ROOT / 'READY.json')
    for name, digest in ready['source_hashes'].items():
        assert sha(ROOT / name) == digest, name
    assert shutil.disk_usage(ROOT).free >= 1 << 30
    model_payloads = {}
    for name in ['before.pt', 'after.pt', 'after_subtraction.pt']:
        model_payloads['run/' + name] = ['$']
    model_payloads['run/removed_delta.pt'] = []
    model_payloads['initial.pt'] = ['$']
    for epoch in range(1, 11):
        model_payloads[f'run/KD/epoch{epoch:02d}.pt'] = ['model']
    for round_number in [1, 6, 7, 100]:
        model_payloads[f'run/rounds/round{round_number:04d}.pt'] = ['incoming', 'after'] + [f'submitted/{i}' for i in range(8)]
    # Select roles by declared chronology/role, never by measured ASR.
    roles = [read(path) for path in sorted((ROOT / 'run/roles').glob('*.json'))]
    assert len(roles) == 800
    selected = []
    for label in ['attacker', 'defender']:
        selected.append(next(role for role in roles if role['role'] == label))
    selected += [role for role in roles if role['round'] == 100 and role['role'] != 'benign']
    for role in selected:
        for phase in role['phases'] + [role['submitted']]:
            assert sha(ROOT / phase['path']) == phase['sha256']
            model_payloads[phase['path'].replace('\\', '/')] = ['model']
    snapshot = {}
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path.is_relative_to(PACKET):
            continue
        assert not path.name.endswith('.tmp'), path
        rel = path.relative_to(ROOT).as_posix()
        snapshot[rel] = {'sha256': sha(path), 'bytes': path.stat().st_size}
    selected_files = set(model_payloads)
    selected_files.update(rel for rel in snapshot if not rel.endswith('.pt'))
    assert selected_files.issubset(snapshot), sorted(selected_files - snapshot.keys())
    assert 'run/events.jsonl' in selected_files and 'run/MANIFEST.json' in selected_files
    torch.set_num_threads(1)
    model = load_model_class()().cpu().eval()
    checks = []
    sample = torch.stack([torch.zeros(1, 28, 28), torch.linspace(0, 1, 784).reshape(1, 28, 28)])
    for rel, keys in sorted(model_payloads.items()):
        value = torch.load(ROOT / rel, map_location='cpu', weights_only=True)
        finite_cpu(value)
        for key in keys:
            state = value
            if key != '$':
                for part in key.split('/'):
                    state = state[int(part)] if isinstance(state, list) else state[part]
            model.load_state_dict(state, strict=True)
            with torch.no_grad():
                logits = model(sample)
            assert logits.shape == (2, 10) and bool(torch.isfinite(logits).all())
            checks.append({'path': rel, 'payload_key': key, 'strict_CPU_finite_forward': True})
    PACKET.mkdir()
    for rel in sorted(selected_files):
        source, target = ROOT / rel, PACKET / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        assert sha(target) == snapshot[rel]['sha256'] and target.stat().st_size == snapshot[rel]['bytes']
    write(PACKET / 'FULL_REMOTE_RAW_MANIFEST.json', {'remote_root': str(ROOT), 'files': snapshot,
          'raw_all_intermediate_models_local': False, 'packet_model_payloads': model_payloads})
    write(PACKET / 'PACKET_CPU_CHECKS.json', {'state': 'passed', 'CPU_only': True, 'models': checks,
          'all_exported_tensor_payloads_finite_CPU': True, 'delta_is_not_a_trained_model': True})
    write(PACKET / 'SCOPE.json', {'profile': r['profile'], 'related_cards': ['R02', 'D08', 'D15', 'N02'],
          'verified_single_run_gate_passed': bool(r['before_gate'] and r['after_gate']),
          'paper_ten_seed_mean_reproduced': False, 'CIFAR_IBA_reproduced': False,
          'trigger_independent_detection_demonstrated': False, 'all_gamma_independent_inference': False,
          'full_remote_history_retained': True, 'packet_model_payloads': model_payloads,
          'role_selection': 'first actual attacker and defender, plus round100 malicious roles',
          'local_transfer_verified': False})
    before, after = r['before'], r['after']
    report = (f"Actual MNIST/DBA100R + client4 historical subtraction/KD10 completed and independently checked.\n"
              f"Before: CA {before['CA_pct']}%, ASR {before['ASR_pct']}% ({before['target_successes']}/{before['non_target_N']}).\n"
              f"After: CA {after['CA_pct']}%, ASR {after['ASR_pct']}% ({after['target_successes']}/{after['non_target_N']}).\n"
              f"Registered single-run gates: before={r['before_gate']}, after={r['after_gate']}.\n"
              f"Actual client4 contributions: {r['forgotten_contribution_count']}; KD10/470 batches.\n"
              "Declared paper interpretation, not author-certified unique code or ten-seed paper reproduction.\n"
              "CIFAR/IBA failures and D08/D15 large benign non-IID counterexamples remain unresolved.\n"
              "Full raw phase history stays on DISLAB; this packet has explicitly selected tensors and all logs/role records.\n"
              "Export verification is not local transfer completion or catalogue approval.\n")
    (PACKET / 'FINAL_PACKET_REPORT.txt').write_text(report, encoding='utf-8', newline='\n')
    exported = {}
    for path in sorted(PACKET.rglob('*')):
        if path.is_file():
            rel = path.relative_to(PACKET).as_posix()
            exported[rel] = {'sha256': sha(path), 'bytes': path.stat().st_size}
    manifest = ROOT / 'DELIVERY_MANIFEST.json'
    seal = ROOT / 'DELIVERY_SEAL.json'
    assert not manifest.exists() and not seal.exists()
    write(manifest, {'schema': 'fuba-mnist-dba-packet-v1', 'packet_root': str(PACKET),
          'files': exported, 'model_payloads': model_payloads, 'state': 'remote_packet_CPU_verified',
          'file_count': len(exported), 'total_bytes': sum(e['bytes'] for e in exported.values())})
    write(seal, {'schema': 'external-manifest-sha256-v1', 'manifest_sha256': sha(manifest),
          'manifest_bytes': manifest.stat().st_size, 'created_unix': time.time()})
    print(json.dumps({'state': 'remote_packet_CPU_verified', 'files': len(exported),
                     'model_payloads': len(checks), 'manifest_sha256': sha(manifest)}))


if __name__ == '__main__':
    main()
