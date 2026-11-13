"""New run verification and independent same-trigger integer-count evaluation."""
import copy
import json
import math
from pathlib import Path
import torch
from common import ROOT, read, sha, write, exact, load_model_class
from reference_core import stamp

torch.set_num_threads(1)
r = read(ROOT / 'RESULT.json')
assert r['state'] == 'completed100R_KD10' and r['rounds'] == 100 and r['KD_batches'] == 470
ready = read(ROOT / 'READY.json')
for name, digest in ready['source_hashes'].items():
    assert sha(ROOT / name) == digest
manifest = read(ROOT / 'run/MANIFEST.json')
assert [v['round'] for v in manifest['rounds']] == list(range(1, 101))
current = torch.load(ROOT / 'initial.pt', map_location='cpu', weights_only=True)
delta = {k: torch.zeros_like(v, dtype=torch.float64) for k, v in current.items()}
role_count = 0
expected_epochs = 0
input_files = {}
for record in manifest['rounds']:
    path = ROOT / record['path']
    assert sha(path) == record['sha256']
    bundle = torch.load(path, map_location='cpu', weights_only=True)
    exact(bundle['incoming'], current)
    expected = {k: torch.stack([s[k] for s in bundle['submitted']]).mean(0) for k in current}
    exact(bundle['after'], expected)
    for meta in record['roles']:
        rp = ROOT / meta['path']
        assert sha(rp) == meta['sha256']
        role = read(rp)
        assert role['state'] == 'complete'
        for phase in role['phases']:
            pp = ROOT / phase['path']
            assert sha(pp) == phase['sha256']
            payload = torch.load(pp, map_location='cpu', weights_only=True)
            assert payload['epochs'] == 50
            assert payload['batches'] == 50 * math.ceil(role['train_N'] / 64)
            assert all(torch.isfinite(v).all() for v in payload['model'].values())
            expected_epochs += 50
        expected_phases = 4 if role['role'] != 'benign' else 1
        assert len(role['phases']) == expected_phases
        role_count += 1
    if 4 in bundle['clients']:
        pos = bundle['clients'].index(4)
        for k in delta:
            delta[k].add_((bundle['submitted'][pos][k].double() - bundle['incoming'][k].double()) * .125)
    current = bundle['after']
    input_files[record['path']] = record['sha256']
assert role_count == 800
exact(current, torch.load(ROOT / 'run/before.pt', map_location='cpu', weights_only=True))
exact(delta, torch.load(ROOT / 'run/removed_delta.pt', map_location='cpu', weights_only=True))
exact({k: (v.double() - delta[k]).to(v.dtype) for k, v in current.items()},
      torch.load(ROOT / 'run/after_subtraction.pt', map_location='cpu', weights_only=True))
events = [json.loads(s) for s in (ROOT / 'run/events.jsonl').read_text(encoding='utf-8').splitlines()]
assert sum(e['kind'] == 'phase_epoch' for e in events) == expected_epochs
assert sum(e['kind'] == 'KD_batch' for e in events) == 470
Net = load_model_class()
last = torch.load(ROOT / 'run/KD/epoch10.pt', map_location='cpu', weights_only=True)
after = torch.load(ROOT / 'run/after.pt', map_location='cpu', weights_only=True)
exact(last['model'], after)
assert last['optimizer']['state'] and last['rng']['torch_CPU'].numel()
P = read(ROOT / 'PROFILE.json')
from torchvision.datasets import MNIST
test = MNIST(P['data_root'], train=False, download=False)
x = test.data.cuda().float().unsqueeze(1) / 255
y = test.targets.cuda()
results = {}
for label, state, expected in [('before', current, r['before']), ('after', after, r['after'])]:
    model = Net().cuda().eval()
    model.load_state_dict(state, strict=True)
    clean_correct = success = non_n = 0
    with torch.inference_mode():
        for start in range(0, 10000, 512):
            xb, yb = x[start:start + 512], y[start:start + 512]
            clean = model(xb).argmax(1)
            attacked = model(stamp(xb, 4)).argmax(1)
            non = yb != 8
            clean_correct += int((clean == yb).sum())
            success += int(((attacked == 8) & non).sum())
            non_n += int(non.sum())
    assert (clean_correct, success, non_n) == (expected['clean_correct'], expected['target_successes'], expected['non_target_N'])
    results[label] = {'clean_correct': clean_correct, 'target_successes': success, 'non_target_N': non_n}
write(ROOT / 'VERIFIED.json', {'state': 'passed', 'roles': 800, 'actual_phase_epochs': expected_epochs,
      'rounds': 100, 'exact_aggregation': True, 'KD_batches': 470,
      'historical_subtraction_exact': True, 'independent_counts': results, 'round_hashes': input_files,
      'scope': 'One MNIST/DBA run; no IBA or detection success asserted.'})
print('Verified all100R and independent pre/post counts')
