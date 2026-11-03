"""Exclusive safe local extraction and a new storage/CPU check, not reevaluation."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import shutil
import sys
import traceback
import zipfile
sys.dont_write_bytecode = True
from pair_review_common import ROOT, LOCAL_PACKET, CASES, read, write, digest, safe, freeze, verify, cpu_check


def main():
    freeze()
    r = read(ROOT / 'PAIR_REVIEW_DELIVERY_REMOTE.json'); archive = ROOT / 'PAIR_REVIEW_DELIVERY.zip'
    assert r['state'] == 'exported_verified_diagnostic_pair_review' and r['case_ids'] == CASES
    assert digest(archive) == r['archive_sha256'] and archive.stat().st_size == r['archive_bytes']
    assert not LOCAL_PACKET.exists()
    write(ROOT / 'PAIR_REVIEW_RECEIVE_ONCE.json', {'archive_sha256': r['archive_sha256']})
    LOCAL_PACKET.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive) as zipped:
        items = zipped.infolist(); names = [v.filename for v in items]
        assert len(names) == len(set(names)) == r['packet_total_files']
        assert len({x.casefold() for x in names}) == len(names)
        for item in items:
            target = safe(LOCAL_PACKET, item.filename)
            assert not item.is_dir() and (item.external_attr >> 16) & 0o170000 != 0o120000
            target.parent.mkdir(parents=True, exist_ok=True)
            with zipped.open(item) as source, target.open('xb') as out: shutil.copyfileobj(source, out)
    assert digest(LOCAL_PACKET / 'DELIVERY_MANIFEST.json') == r['manifest_sha256']
    assert digest(LOCAL_PACKET / 'DELIVERY_SEAL.json') == r['seal_sha256']
    for path in LOCAL_PACKET.rglob('*'):
        if path.is_file(): path.chmod(0o444)
    guard = verify(LOCAL_PACKET, r['manifest_sha256'])
    manifest = read(LOCAL_PACKET / 'DELIVERY_MANIFEST.json')
    checks = cpu_check(LOCAL_PACKET, manifest['payloads'])
    assert checks['payload_count'] == r['tensor_payload_count']
    write(ROOT / 'PAIR_REVIEW_LOCAL_COMPLETE.json', {'state': 'local_delivery_complete', 'case_ids': CASES,
          'packet_root': str(LOCAL_PACKET), 'archive_sha256': r['archive_sha256'], 'archive_bytes': r['archive_bytes'],
          'manifest_sha256': r['manifest_sha256'], 'seal_sha256': r['seal_sha256'],
          'packet_total_files': r['packet_total_files'], 'tensor_payload_count': r['tensor_payload_count'],
          'guard': guard, 'CPU_checks': checks, 'local_delivery_complete': True, 'catalogue_registered': False,
          'original_export_receipt_modified': False, 'overall_goal_complete': False})


if __name__ == '__main__':
    try: main()
    except BaseException:
        write(ROOT / 'PAIR_REVIEW_RECEIVE_FAILURE.json', {'state': 'failed_preserved', 'traceback': traceback.format_exc()})
        raise
