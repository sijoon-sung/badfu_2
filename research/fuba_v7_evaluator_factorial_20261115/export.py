"""Seal new evaluation artifacts; reference original models already on both hosts."""
import json
from pathlib import Path
import zipfile
from run import ROOT, frozen, read, sha, write

for name, digest in read(ROOT / 'EXPORT_FREEZE.json')['files'].items():
    assert sha(ROOT / name) == digest
frozen()
assert read(ROOT / 'EXECUTION_RESULT.json')['exit_code'] == 0
result = read(ROOT / 'RESULT.json')
assert result['state'] == 'complete' and result['all_independent_counts_exact'] and len(result['rows']) == 4
assert sha(ROOT / 'predictions.npz') == result['predictions_sha256']
assert sha(ROOT / 'generator_buffers_after.pt') == result['buffers_sha256']
binding = read(ROOT / 'INPUT_BINDING.json')
external = {}
for name, record in binding['files'].items():
    assert sha(record['path']) == record['sha256'] == sha(ROOT / 'inputs' / name)
    if name.endswith('.pt'):
        external[name] = record
write('PACKET_SCOPE.json', {'included': 'new source, protocol, input metadata, results, predictions, BN copies and logs',
    'external_immutable_model_inputs': external, 'local_original_packet': binding['local_original_packet'],
    'new_classifier_models': False, 'new_FU_steps': 0})
excluded = {'inputs/' + name for name in external}
files = {p.relative_to(ROOT).as_posix(): {'sha256': sha(p), 'bytes': p.stat().st_size}
    for p in sorted(ROOT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and 'delivery' not in p.parts
    and p.relative_to(ROOT).as_posix() not in excluded}
write('REVIEW_MANIFEST.json', {'files': files, 'external_immutable_model_inputs': external})
delivery = ROOT / 'delivery'
delivery.mkdir(exist_ok=False)
archive = delivery / 'FUBA_V7_EVALUATOR_FACTORIAL_20261115.zip'
with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for name in files: z.write(ROOT / name, name)
    z.write(ROOT / 'REVIEW_MANIFEST.json', 'REVIEW_MANIFEST.json')
write('delivery/SEAL.json', {'files': len(files), 'archive_bytes': archive.stat().st_size,
    'archive_sha256': sha(archive), 'manifest_sha256': sha(ROOT / 'REVIEW_MANIFEST.json')})
print(json.dumps(read(delivery / 'SEAL.json')), flush=True)
