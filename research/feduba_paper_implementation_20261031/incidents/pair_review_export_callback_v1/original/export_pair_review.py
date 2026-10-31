"""One new CPU export after terminal, independently verified paired evaluation."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import shutil
import subprocess
import sys
import traceback
import zipfile
sys.dont_write_bytecode = True
from pair_review_common import ROOT, REMOTE_PACKET, CASES, read, write, digest, safe, freeze, cpu_check, verify


def main():
    freeze()
    state = read(ROOT / 'PAIR_CONTROLLER_STATE.json')
    assert state['state'] == 'completed_pair_evaluation_delivery_pending'
    query = "Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'python.exe' -and $_.CommandLine -like '*FEDUBA_PAPER_IMPLEMENTATION_20261031*'} | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    import json
    raw = subprocess.check_output(['powershell', '-NoProfile', '-Command', query], text=True).strip()
    rows = json.loads(raw) if raw else []
    if isinstance(rows, dict): rows = [rows]
    assert all(v['ProcessId'] == os.getpid() for v in rows), rows
    result, audited = read(ROOT / 'PAIR_EVAL_RESULT.json'), read(ROOT / 'PAIR_EVAL_VERIFIED.json')
    assert audited['state'] == 'passed' and audited['primary_result_sha256'] == digest(ROOT / 'PAIR_EVAL_RESULT.json')
    assert audited['independent_counts_exactly_equal'] and audited['all_sample_predictions_exactly_equal']
    assert result['models'] == audited['models'] and result['minimum_operational_gate'] == audited['minimum_operational_gate']
    selected = json.loads(subprocess.check_output([sys.executable, '-B',
                 'D:/TRAJECTORY_CATALOG_20261023/select_case.py', result['case_id'],
                 '--purpose', 'diagnostic'], text=True, encoding='utf-8'))
    assert selected['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    assert selected['server_inputs']['pre']['sha256'] == result['source_models']['pre']['sha256']
    assert not (ROOT / 'STG_VERIFIED.json').exists() and read(ROOT / 'STG_AUDIT_FAILURE.json')['state'] == 'failed_preserved'
    for name, sha in result['source_receipt_hashes'].items(): assert digest(ROOT / name) == sha, name
    audited_hashes = dict(read(ROOT / 'CLEAN_FL_VERIFIED.json')['history_hashes'])
    audited_hashes.update(read(ROOT / 'STG_CPU_TRIGGER_VERIFIED.json')['history_hashes'])
    for branch in CASES:
        a = read(ROOT / f'FU_{branch}_VERIFIED.json')
        assert a['state'] == 'passed' and a['rounds'] == 20 and a['new_trained_roles'] == 200
        assert a['actual_local_epochs'] == 1000 and len(a['history_hashes']) == 420
        audited_hashes.update(a['history_hashes'])
    assert not REMOTE_PACKET.exists() and not (ROOT / 'PAIR_REVIEW_DELIVERY.zip').exists()
    write(ROOT / 'PAIR_REVIEW_EXPORT_ONCE.json', {'pid': os.getpid(), 'case_ids': CASES})
    REMOTE_PACKET.mkdir(parents=True, exist_ok=False)
    def event(kind, **details):
        with (ROOT / 'PAIR_REVIEW_EXPORT_EVENTS.jsonl').open('a', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps({'kind': kind, **details}, allow_nan=False) + '\n'); stream.flush()
    payloads, sources = [], {}
    def copy(source, name, expected=None, **description):
        from pathlib import Path
        source = Path(source); source = source if source.is_absolute() else ROOT / source
        assert source.is_file() and not source.is_symlink()
        meta = {'sha256': digest(source), 'bytes': source.stat().st_size}
        if source.is_relative_to(ROOT):
            key = source.relative_to(ROOT).as_posix()
            if key in audited_hashes: assert meta['sha256'] == audited_hashes[key], key
        if expected:
            assert meta['sha256'] == expected['sha256']
            if 'bytes' in expected: assert meta['bytes'] == expected['bytes']
        target = safe(REMOTE_PACKET, name); target.parent.mkdir(parents=True, exist_ok=True)
        assert not target.exists(); shutil.copyfile(source, target)
        assert digest(target) == meta['sha256']
        sources[name] = {'original': str(source), **meta}
        event('copied', file=name, bytes=meta['bytes'])
        if description: payloads.append({'file': name, **meta, **description})
    clean = read(ROOT / 'clean_fl/MANIFEST.json')
    assert digest(ROOT / 'clean_fl/MANIFEST.json') == read(ROOT / 'FU_LAUNCH_PROFILE.json')['history_manifest_sha256']
    copy(clean['fresh_initial']['path'], 'run/initial.pt', clean['fresh_initial'], kind='model', classes=10, payload_key=None)
    for key, meta in result['source_models'].items():
        copy(meta['path'], 'run/' + ('before' if key == 'pre' else key + '_after') + '.pt', meta,
             kind='model', classes=10, payload_key=meta['payload_key'])
    copy(result['delta']['path'], 'run/delta.pt', result['delta'], kind='delta', payload_key=None)
    fixed = read(ROOT / 'STG_CPU_TRIGGER_PROFILE.json')['reused_fixed_surrogate']
    copy(fixed['path'], 'run/fixed_surrogate201.pt', fixed, kind='model', classes=201, payload_key=None)
    selected_roles = {}
    for owner in [5, 7]:
        original = next(r for r in reversed(clean['rounds']) if owner in r['clients'])
        round_number = original['round']; old = next(x for x in original['roles'] if x['client'] == owner)
        copy(old['checkpoint']['path'], f'roles/old_owner{owner}.pt', old['checkpoint'],
             kind='model', classes=10, payload_key='model', role_kind='baseline')
        selected_roles[str(owner)] = {'round': round_number, 'client': owner, 'original': old['checkpoint']}
        for branch in CASES:
            history = read(ROOT / f'fu/{branch}/MANIFEST.json')
            assert len(history['rounds']) == 20
            assert [r['clients'] for r in history['rounds']] == [r['clients'] for r in clean['rounds']]
            row = history['rounds'][round_number - 1]
            trained = next(x for x in row['trained_roles'] if x['client'] == owner)
            calibrated = next(x for x in row['calibrated_roles'] if x['client'] == owner)
            copy(trained['checkpoint']['path'], f'roles/{branch}_owner{owner}_trained.pt', trained['checkpoint'],
                 kind='model', classes=10, payload_key='model', role_kind='fu', round=round_number,
                 client=owner, source_N=trained['source_N'], batches=trained['batches'])
            copy(calibrated['checkpoint']['path'], f'roles/{branch}_owner{owner}_calibrated.pt', calibrated['checkpoint'],
                 kind='model', classes=10, payload_key=None)
    # Private query and evaluation packets keep original bytes, IDs and complete logits.
    evidence_packets = [v['packet'] for v in read(ROOT / 'SSS_RESULT.json')['query_packets']]
    assert len(evidence_packets) == 40 and len(result['input_packets']) == 79
    evidence_packets += result['input_packets']
    for name, packets in result['logit_packets'].items():
        assert len(packets) == 79
        evidence_packets += packets
    for meta in evidence_packets:
        copy(meta['path'], 'private_tensor_evidence/' + meta['path'], meta,
             kind='tensor_evidence', payload_key=None)
    # Preserve full new CPU trigger epoch/step records, without replaying gradients.
    for path in sorted((ROOT / 'stg_cpu_trigger_recovery').rglob('*.pt')):
        if path.name == 'delta.pt': continue
        copy(path, 'private_tensor_evidence/' + path.relative_to(ROOT).as_posix(),
             kind='tensor_evidence', payload_key=None)
    # All study-level metadata/source/logs; raw source sample IDs remain in this private packet.
    for path in sorted(ROOT.iterdir()):
        if path.is_file() and path.suffix in ['.json', '.txt', '.py', '.ps1', '.log']:
            if path.name.startswith('PAIR_REVIEW_') and path.name not in [
                    'PAIR_REVIEW_FREEZE.json', 'PAIR_REVIEW_EXECUTION_CONTRACT.txt',
                    'PAIR_REVIEW_PUBLICATION.json', 'PAIR_REVIEW_SOURCE_CHECKS.json']: continue
            copy(path, 'evidence/root/' + path.name)
    for folder in ['clean_fl', 'stg', 'stg_cpu_trigger_recovery', 'sss', 'fu/benign', 'fu/attack', 'pair_evaluation']:
        for path in sorted((ROOT / folder).glob('*')):
            if path.is_file() and path.suffix in ['.json', '.jsonl', '.log']:
                copy(path, 'evidence/' + path.relative_to(ROOT).as_posix())
    copy(ROOT / 'model_reference.py', 'model_reference.py')
    copy(ROOT / 'pair_review_common.py', 'load_checkpoint.py')
    write(REMOTE_PACKET / 'DELIVERY_SCOPE.json', {'case_ids': CASES, 'representative_roles': selected_roles,
          'all_original_raw_retained_at': str(ROOT), 'all400_trained_tensors_in_packet': False,
          'all400_calibrated_tensors_in_packet': False, 'local_full_history_use_approved': False,
          'all_FU_epoch_event_logs_included': True, 'all_SSS_queries_and_evaluation_packets_included': True,
          'all_CPU_trigger100_epoch_and200step_records_included': True,
          'source_map': sources, 'minimum_latent_pair_performance_passed': audited['minimum_operational_gate']['passed'],
          'original_GPU_STG_audit_failure_preserved': True, 'diagnostic_only': True})
    checks = cpu_check(REMOTE_PACKET, payloads, lambda check: event('CPU_checked', **check))
    write(REMOTE_PACKET / 'CPU_VERIFIED.json', checks)
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
    write(ROOT / 'PAIR_REVIEW_DELIVERY_REMOTE.json', {'state': 'exported_verified_diagnostic_pair_review',
          'case_ids': CASES, 'packet_root': str(REMOTE_PACKET), 'archive_path': str(archive),
          'archive_sha256': digest(archive), 'archive_bytes': archive.stat().st_size,
          'manifest_sha256': msha, 'seal_sha256': digest(REMOTE_PACKET / 'DELIVERY_SEAL.json'),
          'hashed_files': len(files), 'packet_total_files': len(files) + 2, 'tensor_payload_count': len(payloads),
          'guard': guard, 'models': result['source_models'], 'delta': result['delta'],
          'local_delivery_complete': False, 'catalogue_registered': False,
          'minimum_latent_pair_performance_passed': audited['minimum_operational_gate']['passed'], 'overall_goal_complete': False})


if __name__ == '__main__':
    try: main()
    except BaseException:
        write(ROOT / 'PAIR_REVIEW_EXPORT_FAILURE.json', {'state': 'failed_preserved', 'traceback': traceback.format_exc()})
        raise
