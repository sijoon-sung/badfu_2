import math
from pathlib import Path
import torch
from torchvision.datasets import CIFAR10
import model_reference
from runtime_common import ROOT, read, write, save, sha, freeze_check

freeze_check('CLEAN_FL_FREEZE.json')
assert read(ROOT / 'CORE_CPU_RESULT.json')['state'] == 'passed'
assert read(ROOT / 'GPU_PREFLIGHT_RESULT.json')['state'] == 'passed'
assert not (ROOT / 'CLEAN_FL_READY.json').exists()
p = read(ROOT / 'CLEAN_FL_PROFILE.json')
train = CIFAR10(p['data_root'], train=True, download=False)
test = CIFAR10(p['data_root'], train=False, download=False)
assert len(train) == 50000 and len(test) == 10000
order = torch.randperm(50000, generator=torch.Generator().manual_seed(p['partition_seed'])).tolist()
parts = [order[i * 2500:(i + 1) * 2500] for i in range(20)]
assert sorted(sum(parts, [])) == list(range(50000))
write(ROOT / 'CLEAN_SPLIT.json', {'seed': p['partition_seed'], 'indices': parts, 'sizes': [2500] * 20})
torch.manual_seed(p['seed'])
model = model_reference.ResNet18().cpu().eval()
initial = save(ROOT / 'private_assets/clean_initial.pt', model.state_dict())
with torch.inference_mode():
    assert bool(torch.isfinite(model(torch.zeros(2, 3, 32, 32))).all())
raw = Path(p['data_root']) / 'cifar-10-batches-py'
data_files = {name: sha(raw / name) for name, _ in train.train_list + train.test_list + [('batches.meta', '')]}
write(ROOT / 'CLEAN_FL_READY.json', {'state': 'passed', 'profile': p['id'], 'fresh_initial': initial,
      'split_sha256': sha(ROOT / 'CLEAN_SPLIT.json'), 'official_CIFAR10_integrity_checks_passed': True,
      'data_files_sha256': data_files, 'train_N': 50000, 'test_N': 10000,
      'source_hashes': read(ROOT / 'CLEAN_FL_FREEZE.json')['files'], 'model_parameters': sum(v.numel() for v in model.parameters())})
print('Prepared fresh FedUBA cleanFL20 initial, official data, disjoint20x2500 and source hashes')
