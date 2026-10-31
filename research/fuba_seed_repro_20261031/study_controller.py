"""Finite, sequential 9-new-seed study. Never retries a completed or failed trainer."""
import importlib.util
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
import traceback
import zipfile
from study_common import ROOT, read, sha, write, once, verify_freeze

ROWS = []


def state(status, **values):
    write(ROOT / 'STUDY_STATE.json', {'state': status, 'pid': os.getpid(),
          'updated_unix': time.time(), 'completed_rows': ROWS, **values})


def resource_guard():
    raw = subprocess.check_output(['nvidia-smi', '--query-gpu=utilization.gpu,memory.free,memory.used',
                                   '--format=csv,noheader,nounits'], text=True).strip()
    util, free, used = [int(v.strip()) for v in raw.split(',')]
    command = "Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python|mpiexec'} | Select-Object ProcessId,CommandLine | ConvertTo-Json"
    raw_proc = subprocess.check_output(['powershell', '-NoProfile', '-Command', command], text=True).strip()
    processes = json.loads(raw_proc) if raw_proc else []
    if isinstance(processes, dict):
        processes = [processes]
    busy = []
    for row in processes:
        if row['ProcessId'] in [os.getpid(), os.getppid()]:
            continue
        cmd = (row.get('CommandLine') or '').lower()
        if any(n in cmd for n in ['mpiexec.exe', 'badfu_train.py', 'train_method_iba.py',
                                  '/runner.py', '\\runner.py', 'independent_evaluate.py',
                                  '/verify.py', '\\verify.py', 'study_controller.py']):
            busy.append(row['ProcessId'])
    return util <= 5 and free >= 7000 and used <= 2048 and not busy, {
        'utilization_pct': util, 'free_MiB': free, 'used_MiB': used, 'competing_PIDs': busy}


def run_child(root, name, seed, *arguments, cpu=False):
    logpath = ROOT / f'seed_{seed}_{name}.log'
    with logpath.open('x', encoding='utf-8', newline='\n', buffering=1) as log:
        env = dict(os.environ, CUDA_VISIBLE_DEVICES='' if cpu else '0',
                   PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
        child = subprocess.Popen([sys.executable, '-u', str(root / name), *arguments],
                                 cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
        state('running', seed=seed, step=name, child_pid=child.pid, root=str(root))
        code = child.wait()
        if code:
            raise RuntimeError(f'seed {seed} {name} exited {code}; preserve this run without automatic retry')


def result_row(seed, result, **extra):
    return {'seed': seed, 'before_CA': result['before']['CA_pct'],
            'before_ASR': result['before']['ASR_pct'], 'after_CA': result['after']['CA_pct'],
            'after_ASR': result['after']['ASR_pct'],
            'qualified_pair': bool(result['before_gate'] and result['after_gate']), **extra}


def main():
    verify_freeze()
    p, prepared = read(ROOT / 'PROFILE.json'), read(ROOT / 'PREPARED.json')
    assert prepared['state'] == 'passed' and read(ROOT / 'STORAGE_CONTRACT.json')['state'] == 'passed'
    assert [r['seed'] for r in prepared['seeds']] == p['new_seeds']
    base = Path(p['baseline_review_root'])
    assert sha(base / 'DELIVERY_MANIFEST.json') == p['baseline_manifest_sha256']
    assert sha(base / 'RESULT.json') == prepared['baseline_RESULT_sha256']
    ROWS.append(result_row(p['baseline_seed'], read(base / 'RESULT.json'),
                         source='already delivered baseline, not rerun', case_id=p['baseline_case_id']))
    archive_root = ROOT / 'archives'
    archive_root.mkdir(exist_ok=False)
    for item in prepared['seeds']:
        seed, root = item['seed'], Path(item['root'])
        verify_freeze()
        assert sha(root / 'READY.json') == item['READY_sha256']
        assert sha(root / 'FREEZE.json') == item['FREEZE_sha256']
        while True:
            okay, resources = resource_guard()
            if okay:
                break
            state('waiting_for_resources', seed=seed, resources=resources)
            time.sleep(30)
        run_child(root, 'controller.py', seed)
        run_child(root, 'audit_committed.py', seed, '--through-round', '100', cpu=True)
        run_child(root, 'package_delivery.py', seed, cpu=True)
        packet = root / 'delivery_packet'
        spec = importlib.util.spec_from_file_location(f'seed_guard_{seed}', root / 'load_checkpoint.py')
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        manifest_sha = sha(packet / 'DELIVERY_MANIFEST.json')
        guard.verify(packet, manifest_sha)
        archive = archive_root / f'seed_{seed}.zip'
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as z:
            for path in sorted(packet.rglob('*')):
                if path.is_file():
                    z.write(path, path.relative_to(packet).as_posix())
        receipt = {'case_id': item['case_id'], 'root': str(root), 'packet_root': str(packet),
                   'manifest_sha256': manifest_sha, 'seal_sha256': sha(packet / 'DELIVERY_SEAL.json'),
                   'archive': str(archive), 'archive_sha256': sha(archive), 'archive_bytes': archive.stat().st_size,
                   'full_CPU_audit_sha256': sha(root / 'CPU_AUDIT_through0100.json'),
                   'independent_verification_sha256': sha(root / 'VERIFIED.json'),
                   'local_delivery_complete': False, 'catalogue_registration_complete': False}
        write(ROOT / f'DELIVERY_seed_{seed}.json', receipt)
        ROWS.append(result_row(seed, read(root / 'RESULT.json'), source='new actual100R_KD10', **receipt))
        state('seed_remote_verified', seed=seed)
    assert len(ROWS) == 10
    stats = {k: {'mean': statistics.mean(row[k] for row in ROWS),
                 'sample_SD': statistics.stdev(row[k] for row in ROWS)}
             for k in ['before_CA', 'before_ASR', 'after_CA', 'after_ASR']}
    mean_gate = (stats['before_CA']['mean'] >= 97 and stats['before_ASR']['mean'] <= 10
                 and stats['after_CA']['mean'] >= 97 and stats['after_ASR']['mean'] >= 60)
    write(ROOT / 'STUDY_RESULTS.json', {'state': 'ten_actual_seeds_remote_verified', 'rows': ROWS,
          'statistics': stats, 'H1_new_qualified_pair': any(row['qualified_pair'] for row in ROWS[1:]),
          'H2_ten_mean_minimum_gate': mean_gate, 'qualified_pairs': sum(row['qualified_pair'] for row in ROWS),
          'all_failed_seeds_included': True, 'exact_author_Adam_reproduction_claim': False,
          'D08_D15_unresolved': True, 'overall_user_goal_complete': False})
    state('complete_remote_verified_pending_local_delivery')


if __name__ == '__main__':
    verify_freeze()
    once('STUDY_ONCE.json')
    try:
        main()
    except BaseException:
        state('failed_preserved_no_auto_retry', traceback=traceback.format_exc())
        raise
