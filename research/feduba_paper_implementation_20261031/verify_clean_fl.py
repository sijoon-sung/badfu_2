"""Finite independent clean-FL tensor history/optimizer/RNG and full-data CA audit."""
import json
import math
import random
import torch
from torchvision.datasets import CIFAR10
import model_reference
from runtime_common import ROOT, read, write, sha, guard, freeze_check

assert not (ROOT / 'CLEAN_FL_VERIFIED.json').exists()
freeze_check('CLEAN_FL_FREEZE.json')
torch.set_num_threads(1)
p, ready, result = (read(ROOT / name) for name in ['CLEAN_FL_PROFILE.json', 'CLEAN_FL_READY.json', 'CLEAN_FL_RESULT.json'])
assert result['state'] == 'completed_clean_FL20' and result['rounds'] == 20
manifest = read(ROOT / 'clean_fl/MANIFEST.json')
assert len(manifest['rounds']) == 20
load = lambda meta: torch.load(ROOT / meta['path'], map_location='cpu', weights_only=True)
current = load(ready['fresh_initial'])
parts = read(ROOT / 'CLEAN_SPLIT.json')['indices']
assert sorted(sum(parts, [])) == list(range(50000)) and all(len(a) == 2500 for a in parts)
roles, keys, hashes = 0, set(), {}
model = model_reference.ResNet18().cpu().eval()
for record in manifest['rounds']:
    r = record['round']
    expected = sorted(random.Random(p['seed'] + 1000000 + r - 1).sample(range(20), 10))
    assert record['clients'] == expected and record['weights'] == [.1] * 10
    assert sha(ROOT / record['incoming']['path']) == record['incoming']['sha256']
    incoming = load(record['incoming'])
    assert all(torch.equal(incoming[k], current[k]) for k in current)
    states = []
    assert [item['client'] for item in record['roles']] == expected
    for item in record['roles']:
        client, meta = item['client'], item['checkpoint']
        assert sha(ROOT / meta['path']) == meta['sha256']
        value = load(meta)
        assert (value['round'], value['client'], value['epochs'], value['batches']) == (r, client, 10, 200)
        assert value['source_indices'] == parts[client]
        assert value['incoming'] == record['incoming']
        assert value['seed'] == p['seed'] + r * 10000 + client * 100
        assert value['rng']['torch_CPU'].numel() and len(value['rng']['torch_CUDA']) == 1 and value['loader_rng'].numel()
        optimizer = value['optimizer']
        assert optimizer['state'] and len(optimizer['param_groups']) == 1
        assert all(bool(torch.isfinite(slot['momentum_buffer']).all()) for slot in optimizer['state'].values())
        group = optimizer['param_groups'][0]
        assert group['momentum'] == .9 and group['weight_decay'] == 0
        assert group['lr'] == .01 * (1 + math.cos(math.pi * (r - 1) / 20)) / 2
        assert all(bool(torch.isfinite(v).all()) for v in value['model'].values())
        model.load_state_dict(value['model'], strict=True)
        states.append(value['model']); roles += 1
        hashes[meta['path']] = meta['sha256']
        keys.update((r, client, e) for e in range(1, 11))
    # Independent sequential reconstruction; no call to the training aggregation helper.
    averaged = {}
    for key in current:
        value = torch.zeros_like(current[key])
        for state in states:
            value.add_(state[key])
        averaged[key] = states[-1][key].clone() if 'num_batches_tracked' in key else value / 10
    assert sha(ROOT / record['after']['path']) == record['after']['sha256']
    after = load(record['after'])
    assert all(torch.equal(after[k], averaged[k]) for k in after)
    current = after
    hashes[record['after']['path']] = record['after']['sha256']
assert roles == 200
observed, batches = [], 0
for line in (ROOT / 'clean_fl/events.jsonl').read_text(encoding='utf-8').splitlines():
    event = json.loads(line)
    if event['kind'] == 'local_epoch':
        observed.append((event['round'], event['client'], event['epoch']))
        assert event['examples'] == 2500 and event['batches'] == event['epoch'] * 20
        assert math.isfinite(event['loss'])
        batches += 20
assert len(observed) == len(set(observed)) == 2000 and set(observed) == keys and batches == 40000
assert sha(ROOT / result['before']['path']) == result['before']['sha256']
final = load(result['before'])
assert all(torch.equal(final[k], current[k]) for k in final)
resources = guard(read(ROOT / 'GPU_PREFLIGHT_RESULT.json')['foundation_free_min_MiB'])
test = CIFAR10(p['data_root'], train=False, download=False)
# Separate raw-array loop, same CPU normalization arithmetic and same NCHW/FP32 batch128.
images = torch.as_tensor(test.data).permute(0, 3, 1, 2).contiguous().float().div_(255).sub_(.5).div_(.5)
labels = torch.tensor(test.targets)
model = model_reference.ResNet18().cuda().eval()
model.load_state_dict(final, strict=True)
correct = 0
with torch.inference_mode():
    for start in range(0, 10000, 128):
        logits = model(images[start:start + 128].cuda())
        assert bool(torch.isfinite(logits).all())
        correct += int((logits.argmax(1).cpu() == labels[start:start + 128]).sum())
assert correct == result['evaluation']['clean_correct'] and result['evaluation']['N'] == 10000
write(ROOT / 'CLEAN_FL_VERIFIED.json', {'state': 'passed', 'roles': roles, 'rounds': 20,
      'actual_local_epoch_logs': 2000, 'actual_batches': batches, 'history_hashes': hashes,
      'exact_independent_aggregation_and_lineage': True, 'optimizer_RNG_source_data_indices_verified': True,
      'independent_N': 10000, 'independent_clean_correct': correct, 'CA_pct': correct / 100,
      'utility_gate': correct >= 8000, 'GPU_guard': resources,
      'FedUBA_attack_completed': False, 'overall_goal_complete': False})
print(json.dumps({'state': 'passed', 'rounds': 20, 'roles': 200, 'CA_pct': correct / 100, 'FedUBA_attack_completed': False}))
