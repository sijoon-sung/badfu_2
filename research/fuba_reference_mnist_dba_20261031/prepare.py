import shutil
from pathlib import Path
import torch
from common import ROOT, read, sha, write, save, load_model_class

assert not (ROOT / 'READY.json').exists() and not (ROOT / 'STARTED.json').exists()
assert read(ROOT / 'CPU_CONTRACTS.json')['state'] == 'passed'
P = read(ROOT / 'PROFILE.json')
packet = Path(P['architecture_packet'])
manifest = read(packet / 'DELIVERY_MANIFEST.json')
assert sha(packet / 'DELIVERY_MANIFEST.json') == P['architecture_manifest_sha256']
assert sha(packet / 'source/model/model.py') == manifest['files']['source/model/model.py']['sha256']
shutil.copyfile(packet / 'source/model/model.py', ROOT / 'author_model.py')
from torchvision.datasets import MNIST
from torchvision.transforms import ToTensor
train = MNIST(P['data_root'], train=True, download=False)
test = MNIST(P['data_root'], train=False, download=False)
assert (len(train), len(test)) == (60000, 10000)
assert torch.equal(ToTensor()(train[0][0]), train.data[0].float().unsqueeze(0) / 255)
order = torch.randperm(60000, generator=torch.Generator().manual_seed(P['partition_seed'])).tolist()
splits = [order[i * 3000:(i + 1) * 3000] for i in range(20)]
assert len(set(sum(splits, []))) == 60000
write(ROOT / 'SPLIT.json', {'indices': splits, 'seed': P['partition_seed'], 'sizes': [3000] * 20})
torch.manual_seed(P['seed'])
model = load_model_class()().eval()
assert len(list(model.buffers())) == 0
save(ROOT / 'initial.pt', model.state_dict())
with torch.inference_mode():
    assert torch.isfinite(model(torch.zeros(2, 1, 28, 28))).all()
assert shutil.disk_usage(ROOT).free > 5 * 1024**3
names = list(read(ROOT / 'FREEZE.json')['files']) + ['author_model.py', 'initial.pt', 'SPLIT.json']
write(ROOT / 'READY.json', {'state': 'passed', 'source_hashes': {n: sha(ROOT / n) for n in names},
      'architecture_commit': 'bc233610aca36e1647d0c815597cc7148292139d', 'fresh_random_initialization': True,
      'dataset_sizes': [60000, 10000], 'model_has_BN_or_buffers': False})
print('Prepared fresh MNIST/DBA reference')
