"""CPU inspection of delivered BN copies; no model or real-data forward."""
import json
from pathlib import Path
import torch

root = Path(__file__).resolve().parent
payload = root / 'delivery/payload'
binding = json.loads((root / 'INPUT_BINDING.json').read_text(encoding='utf-8'))
original = torch.load(Path(binding['local_original_packet']) / 'fixed_generator.pt',
                      map_location='cpu', weights_only=True)
buffers = torch.load(payload / 'generator_buffers_after.pt', map_location='cpu', weights_only=True)
assert set(buffers) == {'legacy_eval', 'legacy_train', 'public_eval', 'public_train'}
for key, state in buffers.items():
    assert all(bool(torch.isfinite(v).all()) for v in state.values())
    if key.endswith('_eval'):
        assert all(torch.equal(v, original[name]) for name, v in state.items())
    else:
        assert all(int(v - original[name]) == 313 for name, v in state.items() if name.endswith('num_batches_tracked'))
for mode in ['eval', 'train']:
    assert all(torch.equal(v, buffers['public_' + mode][name]) for name, v in buffers['legacy_' + mode].items())
assert not torch.cuda.is_initialized()
result = {'state': 'passed', 'buffer_sets': 4, 'cross_operator_G_buffers_exact': True,
          'eval_buffers_match_original': True, 'train_batches_per_BN': 313,
          'model_forward_calls': 0, 'CUDA_initialized': False, 'torch': str(torch.__version__)}
with (root / 'LOCAL_BUFFER_CONTRACT.json').open('x') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result))
