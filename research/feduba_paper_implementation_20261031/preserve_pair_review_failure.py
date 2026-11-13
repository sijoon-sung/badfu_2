"""One metadata/hash preservation of a stopped export; no tensor inference or recopy."""
import json
import shutil
import subprocess
from pair_review_common import ROOT, REMOTE_PACKET, read, write, digest


def main():
    failure = read(ROOT / 'PAIR_REVIEW_EXPORT_FAILURE.json')
    assert 'multiple values for argument' in failure['traceback']
    assert not (ROOT / 'PAIR_REVIEW_DELIVERY_REMOTE.json').exists()
    assert not (ROOT / 'PAIR_REVIEW_DELIVERY.zip').exists()
    assert not (REMOTE_PACKET / 'CPU_VERIFIED.json').exists()
    assert not (REMOTE_PACKET / 'DELIVERY_MANIFEST.json').exists()
    query = "Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'python.exe' -and $_.CommandLine -like '*export_pair_review.py*'} | Select-Object ProcessId | ConvertTo-Json -Compress"
    assert not subprocess.check_output(['powershell', '-NoProfile', '-Command', query], text=True).strip()
    incident = ROOT / 'incidents/pair_review_export_callback_v1'
    incident.mkdir(parents=True, exist_ok=False)
    files = list(read(ROOT / 'PAIR_REVIEW_FREEZE.json')['files']) + [
        'PAIR_REVIEW_FREEZE.json', 'PAIR_REVIEW_PUBLICATION.json', 'PAIR_REVIEW_SOURCE_CHECKS.json',
        'PAIR_REVIEW_EXPORT_ONCE.json', 'PAIR_REVIEW_EXPORT_FAILURE.json', 'PAIR_REVIEW_EXPORT_EVENTS.jsonl']
    for name in files:
        dest = incident / 'original' / name; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest); assert digest(dest) == digest(ROOT / name)
    rows = {p.relative_to(REMOTE_PACKET).as_posix(): {'sha256': digest(p), 'bytes': p.stat().st_size}
            for p in sorted(REMOTE_PACKET.rglob('*')) if p.is_file()}
    scope = read(REMOTE_PACKET / 'DELIVERY_SCOPE.json')
    assert set(rows) == set(scope['source_map']) | {'DELIVERY_SCOPE.json'}
    for name, meta in scope['source_map'].items():
        assert rows[name]['sha256'] == meta['sha256'] and rows[name]['bytes'] == meta['bytes']
    prefix = {'state': 'failed_export_copied_prefix_preserved', 'packet_root': str(REMOTE_PACKET),
              'files': rows, 'file_count': len(rows), 'total_bytes': sum(v['bytes'] for v in rows.values()),
              'original_export_task_stopped': True,
              'failure_phase': 'first_zero_input_model_check_finished_then_progress_callback_TypeError',
              'completed_storage_CPU_receipt': False, 'training_or_evaluation_repeated': False}
    write(ROOT / 'PAIR_REVIEW_FAILED_PREFIX.json', prefix)
    shutil.copyfile(ROOT / 'PAIR_REVIEW_FAILED_PREFIX.json', incident / 'FAILED_PREFIX.json')
    for path in REMOTE_PACKET.rglob('*'):
        if path.is_file(): path.chmod(0o444)
    files = {p.relative_to(incident).as_posix(): {'sha256': digest(p), 'bytes': p.stat().st_size}
             for p in sorted(incident.rglob('*')) if p.is_file()}
    write(incident / 'MANIFEST.json', {'state': 'preserved_original_export_instrumentation_failure',
          'files': files, 'original_copied_prefix_files': len(rows), 'original_copied_prefix_bytes': prefix['total_bytes']})
    for path in incident.rglob('*'):
        if path.is_file(): path.chmod(0o444)
    (ROOT / 'PAIR_REVIEW_FAILED_PREFIX.json').chmod(0o444)
    print(json.dumps({'state': 'preserved', 'incident_files': len(files) + 1,
          'prefix_files': len(rows), 'prefix_bytes': prefix['total_bytes'],
          'prefix_sha256': digest(ROOT / 'PAIR_REVIEW_FAILED_PREFIX.json'), 'export_task_restarted': False}))


if __name__ == '__main__': main()
