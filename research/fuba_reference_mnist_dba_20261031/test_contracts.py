import copy
import torch
from common import ROOT, write
import reference_core as c

torch.set_num_threads(1)
image = torch.zeros(2, 1, 28, 28)
assert [int(c.stamp(image, i)[0].sum()) for i in range(5)] == [10, 10, 10, 10, 40]
assert not image.any()
a = torch.nn.Linear(2, 1, bias=False)
b = copy.deepcopy(a)
with torch.no_grad():
    a.weight.zero_()
    b.weight.copy_(torch.tensor([[0., 10.]]))
assert torch.equal(c.weights(a, b)['weight'], torch.tensor([[1., 0.]]))
assert torch.equal(c.affine(a, b, 0).weight, a.weight)
assert torch.allclose(c.affine(a, b, .1).weight, torch.tensor([[0., 1.]]))
assert torch.allclose(c.expected(a, b).weight, torch.tensor([[0., 7.5]]))
model = torch.nn.Linear(2, 2, bias=False, dtype=torch.float64)
ref = copy.deepcopy(model)
with torch.no_grad():
    model.weight.add_(.1)
x = torch.tensor([[1., 2.], [-1., .5]], dtype=torch.float64)
y = torch.tensor([0, 1])
before = model.weight.detach().clone()
loss = torch.nn.functional.cross_entropy(model(x), y)
grad = torch.autograd.grad(loss, model.weight)[0] + 4 * (before - ref.weight.detach())
trained, optimizer, _, n = c.learn(model, x, y, c.Settings(epochs=1, batch=2, lr=.01),
                                  phase_seed=7, phase='contract', reference=ref)
assert torch.allclose(trained.weight, before - .01 * grad, atol=1e-12, rtol=0)
assert type(optimizer).__name__ == 'SGD' and n == 1
model = torch.nn.Linear(2, 2, bias=False, dtype=torch.float64)
before = model.weight.detach().clone()
g = torch.autograd.grad(torch.nn.functional.cross_entropy(model(x), y), model.weight)[0]
w = {'weight': torch.tensor([[.2, 0.], [.7, 1.]], dtype=torch.float64)}
trained, _, _, n = c.learn(model, x, y, c.Settings(epochs=1, batch=2, lr=.01),
                           phase_seed=7, phase='contract', gradient_weights=w)
assert torch.allclose(trained.weight, before - .01 * w['weight'] * g, atol=1e-12, rtol=0)
assert not torch.cuda.is_initialized()
write(ROOT / 'CPU_CONTRACTS.json', {'state': 'passed', 'contracts': [
    'DBA_exact_local_and_global_coordinates', 'input_not_modified', 'Eq1_inverse_minmax',
    'gamma_zero_identity', 'gamma_interpolation', 'Eq3_mixture',
    'Eq4_clean_CE_plus_2_squared_L2_gradient', 'weighted_SGD_update_exact'], 'CPU_only': True})
print('8 CPU contracts passed')
