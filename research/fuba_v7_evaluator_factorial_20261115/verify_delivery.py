"""Verify new artifacts and existing local immutable input models; no inference."""
import hashlib
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import zipfile
import numpy as np

ROOT = Path(__file__).resolve().parent
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

delivery = ROOT / 'delivery'
seal = read(delivery / 'SEAL.json')
archive = delivery / 'FUBA_V7_EVALUATOR_FACTORIAL_20261115.zip'
assert sha(archive) == seal['archive_sha256'] and archive.stat().st_size == seal['archive_bytes']
payload = delivery / 'payload'
with zipfile.ZipFile(archive) as z:
    entries = z.infolist()
    names = [x.filename for x in entries]
    assert len(names) == len(set(names))
    raw = z.read('REVIEW_MANIFEST.json')
    assert hashlib.sha256(raw).hexdigest() == seal['manifest_sha256']
    files = json.loads(raw)['files']
    assert set(names) == set(files) | {'REVIEW_MANIFEST.json'}
    payload.mkdir(exist_ok=False)
    for item in entries:
        p = (payload / item.filename).resolve()
        assert p.is_relative_to(payload.resolve()) and not item.is_dir() and not stat.S_ISLNK(item.external_attr >> 16)
        p.parent.mkdir(exist_ok=True, parents=True)
        with z.open(item) as src, p.open('xb') as dst: shutil.copyfileobj(src, dst)
for name, record in files.items():
    p = payload / name
    assert sha(p) == record['sha256'] and p.stat().st_size == record['bytes'], name
scope = read(payload / 'PACKET_SCOPE.json')
old = Path(scope['local_original_packet'])
for name, record in scope['external_immutable_model_inputs'].items():
    p = old / record['path'].replace('\\', '/').split('/')[-1]
    assert sha(p) == record['sha256'], name
selector = old.parents[1] / 'research/00_trajectories/select_case.py'
selected = subprocess.check_output([sys.executable, '-B', str(selector), 'fuba.v7.s20261023.pre100.post.kd10',
    '--purpose', 'diagnostic', '--location', 'local'])
assert json.loads(selected)['guard_state'] == 'all_snapshot_files_verified_on_this_host'
(ROOT / 'LOCAL_SELECTION.json').write_bytes(selected)
result = read(payload / 'RESULT.json')
with np.load(payload / 'predictions.npz', allow_pickle=False) as p:
    labels = p['labels']
    assert labels.shape == (10000,) and int((labels != 8).sum()) == 9000
    for row in result['rows']:
        for endpoint in ['before', 'after']:
            prefix = f"{row['policy']}_{row['G_mode']}_{endpoint}"
            clean, triggered = p[prefix + '_clean'], p[prefix + '_trigger']
            assert int((clean == labels).sum()) == row[endpoint]['clean_correct']
            assert int(((triggered == 8) & (labels != 8)).sum()) == row[endpoint]['target_successes']
            assert int(((clean == 8) & (labels != 8)).sum()) == row[endpoint]['clean_target_bias']
receipt = {'state': 'passed', 'new_packet_files': len(files), 'external_original_models': 3,
    'all_hashes_and_sizes_verified': True, 'saved_prediction_conditions': 8,
    'local_catalogue_guard_passed': True, 'new_model_inference': 0,
    'manifest_sha256': seal['manifest_sha256'], 'archive_sha256': seal['archive_sha256']}
with (ROOT / 'LOCAL_DELIVERY.json').open('x') as f: json.dump(receipt, f, indent=2)
for name in ['RESULT.json', 'PACKET_SCOPE.json', 'REVIEW_MANIFEST.json', 'EXECUTION_RESULT.json',
             'EXECUTION_STARTED.json', 'EVALUATION_STARTED.json', 'LAUNCH_REQUEST.json', 'evaluation.log', 'resource_wait.jsonl']:
    shutil.copyfile(payload / name, ROOT / name)
print(json.dumps(receipt))
