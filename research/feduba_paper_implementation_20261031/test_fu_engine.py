"""One new tiny CPU integration of the exact local engine used by full FU."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import io
import json
import torch
from torch.utils.data import TensorDataset, DataLoader
from fu_core import branch_dataset, local_schedule
from fu_training import train_role
from runtime_common import ROOT, read, write, freeze_check

assert not (ROOT / 'FU_ENGINE_CPU_RESULT.json').exists()
freeze_check('FU_ENGINE_CPU_FREEZE.json')
torch.set_num_threads(1)
assert not torch.cuda.is_initialized()
torch.manual_seed(773)
images = torch.arange(16 * 3 * 32 * 32).reshape(16, 3, 32, 32).float().remainder_(31).div_(32).sub_(.5)
labels = torch.arange(16).remainder_(10)
data = TensorDataset(images, labels)
delta = torch.full((1, 3, 32, 32), .125)
source_ids, selected_ids = list(range(16)), [3, 12]
base = torch.nn.Sequential(torch.nn.Flatten(), torch.nn.Linear(3072, 10))
initial = {k: v.clone() for k, v in base.state_dict().items()}
rows = []
for branch in ['benign', 'attack']:
    dataset = branch_dataset(data, source_ids, selected_ids, delta, branch)
    retained = [i for i in source_ids if branch == 'attack' or i not in selected_ids]
    model = torch.nn.Sequential(torch.nn.Flatten(), torch.nn.Linear(3072, 10))
    model.load_state_dict(initial, strict=True)
    events = []
    payload = train_role(model, dataset, retained, local_schedule(1, 5, len(dataset)), 'cpu', events.append)
    assert len(events) == len(payload['epochs']) == payload['batches'] == 5
    assert sum(v['examples'] for v in events) == 5 * len(dataset)
    assert payload['optimizer']['param_groups'][0]['momentum'] == .9 and payload['optimizer']['state']
    assert all(bool(torch.isfinite(v['momentum_buffer']).all()) for v in payload['optimizer']['state'].values())
    previous = None
    for epoch in payload['epochs']:
        assert sorted(epoch['source_ids'].tolist()) == retained
        generator = torch.Generator().set_state(epoch['loader_rng_before_epoch'])
        order = torch.cat(list(DataLoader(torch.arange(len(dataset)), batch_size=128, shuffle=True, generator=generator)))
        assert torch.equal(torch.tensor(retained)[order], epoch['source_ids'])
        assert torch.equal(generator.get_state(), epoch['loader_rng'])
        if previous:
            assert torch.equal(epoch['loader_rng_before_epoch'], previous['loader_rng'])
            assert torch.equal(epoch['rng_before_epoch']['torch_CPU'], previous['rng']['torch_CPU'])
        assert epoch['rng']['torch_CUDA'] == []
        previous = epoch
    for edge in payload['edge_batches']:
        for row, source_id in enumerate(edge['source_ids'].tolist()):
            expected = (images[source_id] - .125).clamp(-1, 1) if branch == 'attack' and source_id in selected_ids else images[source_id]
            assert torch.equal(edge['x'][row], expected) and edge['labels'][row] == labels[source_id]
    assert any(not torch.equal(v, initial[k]) for k, v in payload['model'].items())
    stream = io.BytesIO(); torch.save(payload, stream); stream.seek(0)
    decoded = torch.load(stream, map_location='cpu', weights_only=True)
    model.load_state_dict(decoded['model'], strict=True)
    assert all(torch.equal(v, payload['model'][k]) for k, v in model.state_dict().items())
    rows.append({'branch': branch, 'source_N': len(dataset), 'actual_epochs': 5, 'actual_batches': 5,
                 'sample_exposures': sum(v['examples'] for v in events), 'strict_CPU_roundtrip': True})
assert not torch.cuda.is_initialized()
write(ROOT / 'FU_ENGINE_CPU_RESULT.json', {'state': 'passed', 'CPU_only': True, 'rows': rows,
      'new_actual_SGD_epochs': 10, 'actual_batches': 10, 'actual_sample_exposures': 150,
      'model': 'synthetic_Linear3072_to10_not_paper_victim', 'source_hashes': read(ROOT / 'FU_ENGINE_CPU_FREEZE.json')['files'],
      'real_SSS_or_FU_executed': False, 'prior_finite_contracts_repeated': False})
print(json.dumps({'state': 'passed', 'CPU_only': True, 'synthetic_actual_epochs': 10, 'synthetic_actual_batches': 10}))
