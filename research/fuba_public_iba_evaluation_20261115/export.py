"""Seal completed results and input copies; never rerun evaluation."""
import json
from pathlib import Path
import zipfile
from run import ROOT, frozen, read, select, PUBLIC_ID, BENIGN_ID, sha, write

frozen()
assert read(ROOT / 'EXECUTION_RESULT.json')['exit_code'] == 0
result = read(ROOT / 'RESULT.json')
assert result['state'] == 'complete' and result['all_independent_counts_exact']
assert len(result['rows']) == 12
for name, key in [('predictions.npz', 'predictions_sha256'), ('generator_buffers_after.pt', 'buffers_sha256')]:
    assert sha(ROOT / name) == result[key]
select(PUBLIC_ID)
select(BENIGN_ID)
files = {p.relative_to(ROOT).as_posix(): {'sha256': sha(p), 'bytes': p.stat().st_size}
         for p in sorted(ROOT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts
         and 'delivery' not in p.parts and p.name != 'REVIEW_MANIFEST.json'}
# The nested input manifest is required by the independent catalogue guard.
p = ROOT / 'inputs/REVIEW_MANIFEST.json'
files['inputs/REVIEW_MANIFEST.json'] = {'sha256': sha(p), 'bytes': p.stat().st_size}
write('REVIEW_MANIFEST.json', {'files': files, 'state': 'sealed_diagnostic_evaluation', 'new_FU_steps': 0})
delivery = ROOT / 'delivery'
delivery.mkdir(exist_ok=False)
archive = delivery / 'FUBA_PUBLIC_IBA_EVALUATION_20261115.zip'
with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for name in files:
        z.write(ROOT / name, name)
    z.write(ROOT / 'REVIEW_MANIFEST.json', 'REVIEW_MANIFEST.json')
write('delivery/SEAL.json', {'manifest_sha256': sha(ROOT / 'REVIEW_MANIFEST.json'),
    'archive_sha256': sha(archive), 'archive_bytes': archive.stat().st_size, 'files': len(files)})
print(json.dumps(read(delivery / 'SEAL.json')), flush=True)
