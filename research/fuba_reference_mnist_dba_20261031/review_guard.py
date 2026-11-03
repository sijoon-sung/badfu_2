"""Hash-only guard for the separately sealed MNIST/DBA diagnostic review copy."""
import hashlib
import json
from pathlib import Path

CASE = 'fuba.reference.mnist.dba.s20261023.pre100.post.kd10'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def verify(root, expected_manifest_sha256):
    root = Path(root).resolve()
    m, seal = read(root / 'DELIVERY_MANIFEST.json'), read(root / 'DELIVERY_SEAL.json')
    assert sha(root / 'DELIVERY_MANIFEST.json') == expected_manifest_sha256 == seal['manifest_sha256']
    assert m['case_id'] == CASE and m['actual_pre_post_pair']
    assert m['rounds'] == 100 and m['KD_epochs'] == 10 and m['KD_batches'] == 470
    assert {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} == set(m['files']) | {'DELIVERY_MANIFEST.json', 'DELIVERY_SEAL.json'}
    for name, entry in m['files'].items():
        path = (root / name).resolve()
        assert path.is_relative_to(root) and path.is_file()
        assert path.stat().st_size == entry['bytes'] and sha(path) == entry['sha256'], name
    original = read(root / 'SOURCE_EXPORT_MANIFEST.json')
    assert sha(root / 'SOURCE_EXPORT_MANIFEST.json') == m['original_export']['manifest_sha256']
    assert read(root / 'SOURCE_EXPORT_SEAL.json')['manifest_sha256'] == m['original_export']['manifest_sha256']
    for name, entry in original['files'].items():
        assert m['files'][name] == entry, name
    r, v = read(root / 'RESULT.json'), read(root / 'VERIFIED.json')
    assert r['state'] == 'completed100R_KD10' and v['state'] == 'passed'
    assert read(root / 'CPU_AUDIT_through0100.json')['state'] == 'passed'
    assert read(root / 'PACKET_CPU_CHECKS.json')['state'] == 'passed'
    for label in ['before', 'after']:
        assert sha(root / 'run' / (label + '.pt')) == r[label + '_checkpoint']['sha256']
        assert all(v['independent_counts'][label][key] == r[label][key] for key in ['clean_correct', 'target_successes', 'non_target_N'])
    return m
