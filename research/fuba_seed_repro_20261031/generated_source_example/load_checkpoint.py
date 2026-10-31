"""Hash-only loader for one separately sealed, newly trained seed packet."""
import hashlib
import json
from pathlib import Path
CASE = 'fuba.algorithm_sgd.mnist.dba.s5129832.pre100.post.kd10.seed_repro20261031'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 << 20), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def verify(root, expected_manifest_sha256):
    root = Path(root).resolve()
    m, seal = read(root / 'DELIVERY_MANIFEST.json'), read(root / 'DELIVERY_SEAL.json')
    assert sha(root / 'DELIVERY_MANIFEST.json') == expected_manifest_sha256 == seal['manifest_sha256']
    assert m['case_id'] == CASE and m['actual_pre_post_pair'] and m['rounds'] == 100 and m['KD_batches'] == 470
    assert {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} == set(m['files']) | {'DELIVERY_MANIFEST.json', 'DELIVERY_SEAL.json'}
    for name, entry in m['files'].items():
        p = (root / name).resolve()
        assert p.is_relative_to(root) and p.stat().st_size == entry['bytes'] and sha(p) == entry['sha256'], name
    r, v = read(root / 'RESULT.json'), read(root / 'VERIFIED.json')
    assert r['profile'] == read(root / 'PROFILE.json')['id'] and r['state'] == 'completed100R_KD10'
    assert v['state'] == read(root / 'CPU_AUDIT_through0100.json')['state'] == 'passed'
    assert read(root / 'PACKET_CPU_CHECKS.json')['state'] == 'passed'
    for label in ['before', 'after']:
        assert sha(root / 'run' / (label + '.pt')) == r[label + '_checkpoint']['sha256']
        assert all(v['independent_counts'][label][k] == r[label][k] for k in ['clean_correct', 'target_successes', 'non_target_N'])
    return m
