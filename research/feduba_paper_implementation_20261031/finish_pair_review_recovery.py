"""New finite CPU finish of an immutable copied prefix after callback instrumentation failure."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import shutil
import stat
import sys
import traceback
import zipfile
sys.dont_write_bytecode = True
from pair_review_common import ROOT, REMOTE_PACKET, CASES, read, write, digest, safe, freeze, cpu_check, verify


def main():
    freeze()  # Original failed export code/helper/freeze remain byte-identical.
    for name, sha in read(ROOT / 'PAIR_REVIEW_RECOVERY_FREEZE.json')['files'].items():
        assert digest(ROOT / name) == sha, name
    assert not (ROOT / 'PAIR_REVIEW_DELIVERY_REMOTE.json').exists()
    assert not (ROOT / 'PAIR_REVIEW_DELIVERY.zip').exists()
    prefix = read(ROOT / 'PAIR_REVIEW_FAILED_PREFIX.json')
    assert prefix['state'] == 'failed_export_copied_prefix_preserved'
    assert {p.relative_to(REMOTE_PACKET).as_posix() for p in REMOTE_PACKET.rglob('*') if p.is_file()} == set(prefix['files'])
    for name, meta in prefix['files'].items():
        path = safe(REMOTE_PACKET, name)
        assert digest(path) == meta['sha256'] and path.stat().st_size == meta['bytes']
        assert path.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY
    write(ROOT / 'PAIR_REVIEW_RECOVERY_ONCE.json', {'pid': os.getpid(),
          'failed_prefix_sha256': digest(ROOT / 'PAIR_REVIEW_FAILED_PREFIX.json'), 'original_export_restarted': False})
    scope = read(REMOTE_PACKET / 'DELIVERY_SCOPE.json'); payloads = []
    def add(name, **details):
        payloads.append({'file': name, **prefix['files'][name], **details})
    for name in ['initial', 'before', 'benign_after', 'attack_after']:
        add(f'run/{name}.pt', kind='model', classes=10, payload_key=None)
    add('run/fixed_surrogate201.pt', kind='model', classes=201, payload_key=None)
    add('run/delta.pt', kind='delta', payload_key=None)
    for owner in [5, 7]:
        round_number = scope['representative_roles'][str(owner)]['round']
        add(f'roles/old_owner{owner}.pt', kind='model', classes=10, payload_key='model', role_kind='baseline')
        for branch in CASES:
            history = read(REMOTE_PACKET / f'evidence/fu/{branch}/MANIFEST.json')
            row = history['rounds'][round_number - 1]
            role = next(v for v in row['trained_roles'] if v['client'] == owner)
            add(f'roles/{branch}_owner{owner}_trained.pt', kind='model', classes=10, payload_key='model',
                role_kind='fu', round=round_number, client=owner, source_N=role['source_N'], batches=role['batches'])
            add(f'roles/{branch}_owner{owner}_calibrated.pt', kind='model', classes=10, payload_key=None)
    for name in sorted(prefix['files']):
        if name.startswith('private_tensor_evidence/') and name.endswith('.pt'):
            add(name, kind='tensor_evidence', payload_key=None)
    assert {r['file'] for r in payloads} == {name for name in prefix['files'] if name.endswith('.pt')}
    # The original first model's check was uncommitted; complete a new storage check on this prefix.
    # No callback is passed, leaving the original frozen helper and failed caller unchanged.
    checks = cpu_check(REMOTE_PACKET, payloads)
    write(REMOTE_PACKET / 'CPU_VERIFIED.json', checks)
    incident = ROOT / 'incidents/pair_review_export_callback_v1'
    for path in sorted(incident.rglob('*')):
        if path.is_file():
            target = REMOTE_PACKET / 'recovery_evidence/original_incident' / path.relative_to(incident)
            target.parent.mkdir(parents=True, exist_ok=True); assert not target.exists()
            shutil.copyfile(path, target); assert digest(path) == digest(target)
    for name in ['finish_pair_review_recovery.py', 'preserve_pair_review_failure.py', 'launch_pair_review_recovery.ps1',
                 'PAIR_REVIEW_RECOVERY_PROTOCOL.txt', 'PAIR_REVIEW_RECOVERY_FREEZE.json', 'PAIR_REVIEW_RECOVERY_PUBLICATION.json',
                 'PAIR_EVALUATION_REPORT_KO.txt', 'PAIR_EVALUATION_COMPLETION.json',
                 'FU_ATTACK_COMPLETION.json', 'FU_BENIGN_COMPLETION.json']:
        target = REMOTE_PACKET / 'recovery_evidence' / name
        assert not target.exists(); shutil.copyfile(ROOT / name, target)
    write(REMOTE_PACKET / 'RECOVERY_SCOPE.json', {'state': 'new_storage_finish_after_original_export_callback_failure',
          'failed_prefix_sha256': digest(ROOT / 'PAIR_REVIEW_FAILED_PREFIX.json'),
          'original_export_failure_sha256': digest(ROOT / 'PAIR_REVIEW_EXPORT_FAILURE.json'),
          'original_scope_sha256': prefix['files']['DELIVERY_SCOPE.json']['sha256'],
          'all_copied_prefix_bytes_unchanged': True, 'all_copied_payloads_reused_without_recopy': True,
          'original_export_restarted': False, 'original_uncommitted_first_zero_forward_rechecked': True,
          'new_training_gradients_queries_or_performance_evaluation': False,
          'CPU_helper_unchanged_and_progress_callback_omitted': True})
    files = {p.relative_to(REMOTE_PACKET).as_posix(): {'sha256': digest(p), 'bytes': p.stat().st_size}
             for p in sorted(REMOTE_PACKET.rglob('*')) if p.is_file()}
    write(REMOTE_PACKET / 'DELIVERY_MANIFEST.json', {'case_ids': CASES, 'files': files, 'payloads': payloads})
    msha = digest(REMOTE_PACKET / 'DELIVERY_MANIFEST.json')
    write(REMOTE_PACKET / 'DELIVERY_SEAL.json', {'case_ids': CASES, 'manifest_sha256': msha, 'hashed_files': len(files)})
    for path in REMOTE_PACKET.rglob('*'):
        if path.is_file(): path.chmod(0o444)
    guard = verify(REMOTE_PACKET, msha)
    archive = ROOT / 'PAIR_REVIEW_DELIVERY.zip'
    with archive.open('xb') as stream, zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as zipped:
        for path in sorted(REMOTE_PACKET.rglob('*')):
            if path.is_file(): zipped.write(path, path.relative_to(REMOTE_PACKET).as_posix())
    result = read(ROOT / 'PAIR_EVAL_RESULT.json')
    receipt = {'state': 'exported_verified_diagnostic_pair_review', 'case_ids': CASES,
          'packet_root': str(REMOTE_PACKET), 'archive_path': str(archive), 'archive_sha256': digest(archive),
          'archive_bytes': archive.stat().st_size, 'manifest_sha256': msha,
          'seal_sha256': digest(REMOTE_PACKET / 'DELIVERY_SEAL.json'), 'hashed_files': len(files),
          'packet_total_files': len(files) + 2, 'tensor_payload_count': len(payloads), 'guard': guard,
          'models': result['source_models'], 'delta': result['delta'], 'local_delivery_complete': False,
          'catalogue_registered': False, 'minimum_latent_pair_performance_passed': False,
          'original_export_instrumentation_failure_preserved': True,
          'new_recovery_finish_completed': True, 'overall_goal_complete': False}
    write(ROOT / 'PAIR_REVIEW_DELIVERY_REMOTE.json', receipt)
    write(ROOT / 'PAIR_REVIEW_RECOVERY_RESULT.json', {'state': 'passed_new_recovery_finish',
          'receipt_sha256': digest(ROOT / 'PAIR_REVIEW_DELIVERY_REMOTE.json'),
          'prefix_unchanged': True, 'original_export_restarted': False, 'tensor_payload_count': len(payloads)})


if __name__ == '__main__':
    try: main()
    except BaseException:
        write(ROOT / 'PAIR_REVIEW_RECOVERY_FAILURE.json', {'state': 'failed_preserved', 'traceback': traceback.format_exc()})
        raise
