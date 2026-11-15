"""Finish only the failed Windows path-key preparation; training source stays frozen."""
import subprocess
import sys
import time
import torch
from run import ROOT, read, sha, write, frozen, exact

frozen()
write(ROOT / 'PREPARE_RECOVERY_STARTED.json', {'time': time.time()}, True)
failure = read(ROOT / 'FAILURE_prepare.json')
assert failure['error'] == "'inputs/reference_core.py'"
assert not (ROOT / 'STARTED.json').exists()
binding = read(ROOT / 'INPUT_BINDING.json')
import json
from pathlib import Path
selection = json.loads(subprocess.check_output([sys.executable, '-B',
    'D:/TRAJECTORY_CATALOG_20261023/select_case.py', binding['case_id'], '--purpose', 'diagnostic'],
    text=True, encoding='utf-8'))
assert selection['guard_state'] == 'all_snapshot_files_verified_on_this_host'
packet = Path(selection['source_root'])
assert sha(packet / 'FULL_REMOTE_RAW_MANIFEST.json') == binding['full_manifest_sha256']
manifest = read(packet / 'FULL_REMOTE_RAW_MANIFEST.json')
raw = Path(manifest['remote_root'])
files = {}
for name, digest in binding['files'].items():
    target = ROOT / 'inputs' / Path(name).name
    assert sha(target) == digest == manifest['files'][name]['sha256'] == sha(raw / name)
    files[target.relative_to(ROOT).as_posix()] = digest
assert sha(ROOT / 'reference_core.py') == files['inputs/reference_core.py']
bundle = torch.load(ROOT / 'inputs/round0020.pt', map_location='cpu', weights_only=True)
assert bundle['round'] == 20
exact(bundle['after'], {k: torch.stack([s[k] for s in bundle['submitted']]).mean(0) for k in bundle['after']})
assert all(bool(torch.isfinite(v).all()) for v in bundle['after'].values())
prior = {str(r): read(raw / f'run/evaluation/round{r:04d}.json') for r in range(20, 31)}
write(ROOT / 'PREPARED.json', {'state': 'passed', 'selection': selection, 'files': files,
    'historical_evaluations': prior, 'tensor_inference_count': 0,
    'preparation_recovery': 'Windows separator key only; no input/source tensor changed',
    'original_failure_sha256': sha(ROOT / 'FAILURE_prepare.json'), 'recovery_source_sha256': sha(__file__)}, True)
print('prepared existing round20 input; original preparation failure preserved', flush=True)
