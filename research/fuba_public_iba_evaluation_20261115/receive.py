"""Verify the delivered archive and stored integer predictions without inference."""
import json
from pathlib import Path
import shutil
import stat
import zipfile
import numpy as np
from check_inputs import sha, verify

ROOT = Path(__file__).resolve().parent
delivery = ROOT / 'delivery'
seal = json.loads((delivery / 'SEAL.json').read_text(encoding='utf-8'))
archive = delivery / 'FUBA_PUBLIC_IBA_EVALUATION_20261115.zip'
assert sha(archive) == seal['archive_sha256'] and archive.stat().st_size == seal['archive_bytes']
payload = delivery / 'payload'
with zipfile.ZipFile(archive) as z:
    items = z.infolist()
    names = [x.filename for x in items]
    assert len(names) == len(set(names))
    raw = z.read('REVIEW_MANIFEST.json')
    import hashlib
    assert hashlib.sha256(raw).hexdigest() == seal['manifest_sha256']
    files = json.loads(raw)['files']
    assert set(names) == set(files) | {'REVIEW_MANIFEST.json'}
    payload.mkdir(exist_ok=False)
    for item in items:
        path = (payload / item.filename).resolve()
        assert path.is_relative_to(payload.resolve()) and not item.is_dir()
        assert not stat.S_ISLNK(item.external_attr >> 16)
        path.parent.mkdir(parents=True, exist_ok=True)
        with z.open(item) as src, path.open('xb') as dst:
            shutil.copyfileobj(src, dst)
verify(payload, seal['manifest_sha256'])
result = json.loads((payload / 'RESULT.json').read_text(encoding='utf-8'))
with np.load(payload / 'predictions.npz', allow_pickle=False) as p:
    labels = p['labels']
    assert labels.shape == (10000,) and int((labels != 8).sum()) == 9026
    for row in result['rows']:
        for model in ['post', 'normal']:
            key = f"{row['method']}_{row['generator_mode']}_{model}"
            clean, trigger = p[key + '_clean'], p[key + '_trigger']
            assert int((clean == labels).sum()) == row[model]['clean_correct']
            assert int(((trigger == 8) & (labels != 8)).sum()) == row[model]['target_successes']
            assert int(((clean == 8) & (labels != 8)).sum()) == row[model]['clean_target_bias']
receipt = {'state': 'passed', 'files': len(files), 'manifest_sha256': seal['manifest_sha256'],
           'archive_sha256': seal['archive_sha256'], 'all_hashes_and_sizes_verified': True,
           'prediction_rows_verified': len(result['rows']), 'model_inference': 0, 'new_training': 0}
with (ROOT / 'LOCAL_DELIVERY.json').open('x') as f:
    json.dump(receipt, f, indent=2)
print(json.dumps(receipt))
