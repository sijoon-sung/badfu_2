"""New-run audit: all optimizer steps; first/last CPU gradients; independent saved-logit arithmetic."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', PYTHONDONTWRITEBYTECODE='1')
import importlib.util
import math
import traceback
from io_guard import ROOT, read, write, check, profile, numeric_policy, resource_guard


def main():
    p = profile(); resource_guard()
    write('AUDIT_ONCE.json', {'pid': os.getpid(), 'all_new_optimizer_steps': True, 'independent_gradients': 2})
    import torch
    numeric_policy()
    result, manifest = read(ROOT / 'RESULT.json'), read(ROOT / 'MANIFEST.json')
    rows = manifest['epochs']; assert len(rows) == result['epochs']
    delta = torch.zeros(1, 3, 32, 32, requires_grad=True)
    optimizer = torch.optim.RAdam([delta], lr=.1)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=100)
    def same(a, b):
        if isinstance(a, torch.Tensor): assert torch.equal(a, b)
        elif isinstance(a, dict):
            assert a.keys() == b.keys()
            for k in a: same(a[k], b[k])
        elif isinstance(a, (list, tuple)):
            assert len(a) == len(b)
            for av, bv in zip(a, b): same(av, bv)
        else: assert a == b
    selected = []
    for epoch, row in enumerate(rows, 1):
        assert row['epoch'] == epoch and row['N'] == 200
        for batch, meta in enumerate(row['steps'], 1):
            step = torch.load(check(meta), map_location='cpu', weights_only=True)
            assert step['epoch'] == epoch and step['batch'] == batch
            same(delta.detach(), step['latent_before'])
            delta.grad = step['gradient'].clone(); optimizer.step()
            same(delta.detach(), step['latent_after']); same(optimizer.state_dict(), step['optimizer'])
            same(delta.detach().clamp(-32 / 255, 32 / 255), step['limited_after'])
            assert bool(torch.isfinite(delta).all()) and bool(torch.isfinite(delta.grad).all())
            if (epoch, batch) in [(1, 1), (len(rows), 2)]: selected.append(step)
        scheduler.step()
        endpoint = torch.load(check(row['checkpoint']), map_location='cpu', weights_only=True)
        same(optimizer.state_dict(), endpoint['optimizer']); same(scheduler.state_dict(), endpoint['scheduler'])
        same(delta.detach(), endpoint['latent'])
    final = torch.load(check(result['delta']), map_location='cpu', weights_only=True)
    same(final, delta.detach().clamp(-32 / 255, 32 / 255))
    spec = importlib.util.spec_from_file_location('audit_pinned_201', p['inputs']['architecture']['path'])
    architecture = importlib.util.module_from_spec(spec); spec.loader.exec_module(architecture)
    original = torch.load(check(p['inputs']['teacher']), map_location='cpu', weights_only=True)
    gradients = []
    for step in selected:
        model = architecture.ResNet18_201().cpu(); model.load_state_dict({**original, **step['BN_before']}, strict=True); model.train()
        for v in model.parameters(): v.requires_grad_(False)
        inp = torch.load(check(step['source_input']), map_location='cpu', weights_only=True)
        latent = step['latent_before'].clone().requires_grad_(True)
        torch.set_rng_state(step['rng_before'])
        logits = model((inp['x'].contiguous() + latent.clamp(-32 / 255, 32 / 255)).clamp(-1, 1))
        torch.nn.functional.cross_entropy(logits, inp['target']).backward()
        assert torch.allclose(latent.grad, step['gradient'], atol=2e-5, rtol=.001)
        assert torch.allclose(logits, step['logits'], atol=1e-6, rtol=1e-5)
        same(dict(model.named_buffers()), step['BN_after'])
        gradients.append({'epoch': step['epoch'], 'batch': step['batch'],
                          'max_abs': float((latent.grad - step['gradient']).abs().max())})
        del model
    CE_error = 0.
    for row in result['endpoint']:
        path = ROOT / ('private_run/endpoint/batch%d_%s.pt' % (row['batch'], row['perturbation']))
        value = torch.load(path, map_location='cpu', weights_only=True)
        values = value['logits'].tolist()
        assert all(len(v) == 201 and all(math.isfinite(x) for x in v) for v in values)
        hits = sum(max(range(201), key=lambda j: v[j]) == 200 for v in values)
        loss = math.fsum(max(v) + math.log(math.fsum(math.exp(x - max(v)) for x in v)) - v[200] for v in values) / len(values)
        assert hits == row['hits'] and len(values) == row['N']
        CE_error = max(CE_error, abs(loss - row['CE']))
        assert abs(loss - row['CE']) <= 5e-6 + 1e-5 * abs(loss)
    profile()
    write('VERIFIED.json', {'state': 'passed_new_public_STG_comparison_audit',
        'all_optimizer_steps': result['steps'], 'independent_gradient_calls': len(gradients),
        'independent_sample_forwards': 200, 'gradients': gradients,
        'max_endpoint_CE_error': CE_error, 'all_training_gradients_replayed': False,
        'victim_ASR_or_FU_validated': False, 'overall_goal_complete': False})


if __name__ == '__main__':
    try: main()
    except BaseException:
        write('AUDIT_FAILURE.json', {'state': 'failed_preserved', 'traceback': traceback.format_exc()})
        raise
