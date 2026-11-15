"""Portability of transferred states: CPU and one synthetic image, no dataset."""
import json
from pathlib import Path
import torch
from run import module, sha

ROOT = Path(__file__).resolve().parent
payload = ROOT / 'delivery/payload'
inputs = payload / 'inputs'
torch.set_num_threads(1)
author = module('local_author', inputs / 'author_model.py')
baseline = module('local_baseline', inputs / 'benchmark.py')
binding = json.loads((payload / 'INPUT_BINDING.json').read_text(encoding='utf-8'))
count = 0
for name in binding['public_states'] + ['benign_before.pt']:
    state = torch.load(inputs / name, map_location='cpu', weights_only=True)
    model = (baseline.Net() if name == 'benign_before.pt' else author.MNISTAutoencoder()
             if name.startswith('backdoor_') else author.Net())
    model.load_state_dict(state, strict=True)
    model.eval()
    assert all(bool(torch.isfinite(v).all()) for v in state.values())
    with torch.inference_mode():
        assert bool(torch.isfinite(model(torch.zeros(1, 1, 28, 28))).all())
    count += 1
buffers = torch.load(payload / 'generator_buffers_after.pt', map_location='cpu', weights_only=True)
assert len(buffers) == 12 and all(bool(torch.isfinite(v).all()) for row in buffers.values() for v in row.values())
assert not torch.cuda.is_initialized()
out = {'state': 'passed', 'strict_CPU_states': count, 'generator_buffer_sets': len(buffers),
       'synthetic_images_per_model': 1, 'real_data_inference': 0, 'CUDA_initialized': False,
       'torch': str(torch.__version__)}
with (ROOT / 'LOCAL_MODEL_CONTRACT.json').open('x') as f:
    json.dump(out, f, indent=2)
print(json.dumps(out))
