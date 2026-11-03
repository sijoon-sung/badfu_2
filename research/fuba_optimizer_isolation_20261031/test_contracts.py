"""Meaningful CPU contracts before the finite GPU comparison."""
import hashlib
import json
from pathlib import Path
import torch
from optimizer_policy import apply_weights, make_reweighted_optimizer

root = Path(__file__).resolve().parent
torch.set_num_threads(1)
initial = torch.tensor([[1., 2.]], dtype=torch.float64)
gradient = torch.tensor([[.5, -2.]], dtype=torch.float64)
weight = torch.tensor([[.2, .7]], dtype=torch.float64)
observed = {}
for mode in ['algorithm_sgd', 'experimental_adam']:
    model = torch.nn.Linear(2, 1, bias=False, dtype=torch.float64)
    with torch.no_grad():
        model.weight.copy_(initial)
    optimizer = make_reweighted_optimizer(model.parameters(), interpretation=mode, learning_rate=.001)
    model.weight.grad = gradient.clone()
    apply_weights(model, {'weight': weight})
    optimizer.step()
    observed[mode] = model.weight.detach().clone()
expected_sgd = initial - .001 * gradient * weight
assert torch.allclose(observed['algorithm_sgd'], expected_sgd, atol=1e-15, rtol=0)
expected_adam = initial - .001 * (gradient * weight) / ((gradient * weight).abs() + 1e-8)
assert torch.allclose(observed['experimental_adam'], expected_adam, atol=1e-15, rtol=0)
assert not torch.equal(observed['algorithm_sgd'], observed['experimental_adam'])
try:
    make_reweighted_optimizer([], interpretation='implicit_default', learning_rate=.001)
except ValueError:
    pass
else:
    raise AssertionError('Implicit interpretation accepted')
assert not torch.cuda.is_initialized()
result = {'state': 'passed', 'CPU_only': True,
          'contracts': ['weighted_SGD_exact_equation', 'weighted_Adam_first_step_equation',
                        'different_optimizer_paths', 'explicit_interpretation_required'],
          'code_sha256': {n: hashlib.sha256((root / n).read_bytes()).hexdigest()
                          for n in ['optimizer_policy.py', 'test_contracts.py']}}
(root / 'CPU_CONTRACTS.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps(result))
