"""CPU verification of newly derived models and complete epoch evidence."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
import torch

torch.set_num_threads(1)
root = Path(__file__).resolve().parent
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
r = read(root / 'RESULT.json')
p = read(root / 'PROFILE.json')
assert r['state'] == 'complete' and r['same_epoch_orders']
events = [json.loads(s) for s in (root / 'run/epochs.jsonl').read_text(encoding='utf-8').splitlines()]
assert len(events) == 100
source = Path(p['input_packet']) / 'source/model/resnet.py'
spec = importlib.util.spec_from_file_location('isolation_verification_resnet', source)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
model = module.resnet18().eval()
files = {}
for arm in p['arms']:
    record = r['arms'][arm]
    path = root / 'run' / record['checkpoint']['path']
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == record['checkpoint']['sha256']
    value = torch.load(path, map_location='cpu', weights_only=True)
    assert value['epochs'] == 50 and value['batches'] == 1800
    assert value['interpretation'] == arm
    assert value['optimizer']['state'] or arm == 'algorithm_sgd'
    assert value['rng']['torch_CPU'].numel() > 0 and len(value['rng']['torch_CUDA']) == 1
    model.load_state_dict(value['model'], strict=True)
    assert all(torch.isfinite(v).all() for v in value['model'].values())
    with torch.inference_mode():
        logits = model(torch.zeros(2, 3, 32, 32))
    assert logits.shape == (2, 10) and torch.isfinite(logits).all()
    own = [e for e in events if e['arm'] == arm]
    assert [e['epoch'] for e in own] == list(range(1, 51))
    assert all(e['examples'] == 2250 and e['batches_cumulative'] == e['epoch'] * 36 for e in own)
    assert [e['batch_order_sha256'] for e in own] == record['epoch_orders']
    metrics = record['full_test']
    assert (metrics['N'], metrics['non_target_N']) == (10000, 9000)
    assert metrics['CA_pct'] == 100 * metrics['clean_correct'] / 10000
    assert metrics['ASR_pct'] == 100 * metrics['triggered_target_count'] / 9000
    files[path.name] = {'sha256': digest, 'strict_CPU_finite_forward': True,
                        'optimizer_RNG_full_epochs_verified': True}
for field in ['fixed_generator', 'incoming_classifier']:
    path = root / 'run' / r[field]['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == r[field]['sha256']
    state = torch.load(path, map_location='cpu', weights_only=True)
    assert all(torch.isfinite(v).all() for v in state.values())
    files[path.name] = {'sha256': r[field]['sha256'], 'CPU_load_finite': True}
receipt = {'state': 'passed', 'CPU_only': not torch.cuda.is_initialized(),
           'actual_epoch_records': 100, 'actual_training_batches': 3600,
           'same_50_epoch_orders': True, 'files': files,
           'scope': 'Saved newly derived models and integer count arithmetic; not another independent full inference.'}
(root / 'VERIFIED.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps(receipt))
