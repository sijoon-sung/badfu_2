"""New literal-SGD contracts, distinct from completed generic RAdam core fixture."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import json
import torch
from stg_training import freeze_trigger_surrogate, projected_sgd_batch, ExternalImages
from runtime_common import ROOT, read, write, freeze_check

assert not (ROOT / 'STG_SGD_CPU_RESULT.json').exists()
freeze_check('STG_SGD_CPU_FREEZE.json')
torch.set_num_threads(1)
assert not torch.cuda.is_initialized()
# Two-class linear CE has the independently derived gradient (softmax(z)-onehot) @ W.
model = torch.nn.Sequential(torch.nn.Flatten(), torch.nn.Linear(2, 2, bias=False)).double()
with torch.no_grad():
    model[1].weight.copy_(torch.tensor([[2., -1.], [-.5, 1.5]], dtype=torch.float64))
freeze_trigger_surrogate(model)
original = {k: v.clone() for k, v in model.state_dict().items()}
x = torch.tensor([[.1, .2], [-.4, .3]], dtype=torch.float64).view(2, 1, 1, 2)
delta = torch.zeros(1, 1, 1, 2, dtype=torch.float64, requires_grad=True)
target = torch.tensor([1, 1])
logits = x.flatten(1) @ model[1].weight.T
exp = torch.exp(logits - logits.max(1, keepdim=True).values)
probability = exp / exp.sum(1, keepdim=True)
probability[:, 1] -= 1
gradient = (probability @ model[1].weight).mean(0).view_as(delta)
expected = (-.1 * gradient).clamp(-.02, .02)
optimizer = torch.optim.SGD([delta], lr=.1, momentum=0, weight_decay=0)
loss = projected_sgd_batch(model, x, target, delta, optimizer, .02)
assert torch.allclose(delta, expected, atol=1e-15, rtol=0)
assert torch.allclose(delta.grad, gradient, atol=1e-15, rtol=0)
assert all(torch.equal(v, original[k]) for k, v in model.state_dict().items())
assert not optimizer.state and all(parameter.grad is None for parameter in model.parameters())
# A batch-normalized surrogate stays eval; both learned weights and running buffers remain identical.
bn_model = torch.nn.Sequential(torch.nn.Flatten(), torch.nn.BatchNorm1d(2), torch.nn.Linear(2, 2)).double()
freeze_trigger_surrogate(bn_model)
before = {k: v.clone() for k, v in bn_model.state_dict().items()}
other_delta = torch.zeros_like(delta, requires_grad=True)
projected_sgd_batch(bn_model, x, target, other_delta, torch.optim.SGD([other_delta], lr=.1), .1)
assert all(torch.equal(v, before[k]) for k, v in bn_model.state_dict().items())
# Input clipping independently cancels the gradient for every saturated first coordinate.
saturated = torch.tensor([[2., .2], [3., -.2]], dtype=torch.float64).view(2, 1, 1, 2)
clipped_delta = torch.zeros_like(delta, requires_grad=True)
projected_sgd_batch(model, saturated, target, clipped_delta, torch.optim.SGD([clipped_delta], lr=.1), .1)
assert clipped_delta.grad[0, 0, 0, 0] == 0
images = torch.zeros(3, 32, 32, 3, dtype=torch.uint8)
dataset = ExternalImages(images, torch.tensor([0, 1, 200]), augment=False)
image, label = dataset[2]
assert image.shape == (3, 32, 32) and image.is_contiguous() and torch.equal(image, torch.full_like(image, -1)) and label == 200
assert not torch.cuda.is_initialized()
write(ROOT / 'STG_SGD_CPU_RESULT.json', {'state': 'passed', 'CPU_only': True,
      'contracts': ['independent_analytic_mean_CE_gradient_and_literal_SGD_projection',
                    'surrogate_weights_and_BN_buffers_frozen', 'input_clamp_chain_rule',
                    'external_dataset_normalization_and_target_label200'], 'count': 4,
      'source_hashes': read(ROOT / 'STG_SGD_CPU_FREEZE.json')['files'],
      'core_RAdam_fixture_repeated': False, 'real_STG_training_executed': False})
print(json.dumps({'state': 'passed', 'contracts': 4, 'CPU_only': True}))
