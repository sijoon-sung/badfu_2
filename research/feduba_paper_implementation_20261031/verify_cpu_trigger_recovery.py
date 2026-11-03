"""Independent new CPU100 branch audit; does not repeat or relabel the old full STG audit."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import json
import traceback
import torch
from torch.utils.data import DataLoader
import model_reference
from stg_training import ExternalImages
from runtime_common import ROOT, read, sha, write, freeze_check


def load(meta):
    assert sha(ROOT / meta['path']) == meta['sha256']
    assert (ROOT / meta['path']).stat().st_size == meta['bytes']
    return torch.load(ROOT / meta['path'], map_location='cpu', weights_only=True)


def main():
    freeze_check('STG_CPU_TRIGGER_FREEZE.json'); freeze_check('STG_FREEZE.json')
    with (ROOT / 'STG_CPU_TRIGGER_AUDIT_ONCE.json').open('x', encoding='utf-8') as f:
        json.dump({'pid': os.getpid()}, f)
    torch.set_num_threads(2); torch.backends.mkldnn.enabled = True
    torch.set_float32_matmul_precision('highest')
    result = read(ROOT / 'STG_CPU_TRIGGER_RESULT.json')
    assert result['state'] == 'completed_CPU_trigger100' and result['new_actual_batches'] == 200
    original = read(ROOT / 'STG_RESULT.json'); fixed = result['fixed_surrogate']
    assert fixed == original['fixed_surrogate']
    assert read(ROOT / 'STG_AUDIT_STATE.json')['checked_epochs'] == 205
    assert read(ROOT / 'STG_AUDIT_STATE.json')['checked_trigger_steps'] == 200
    assert read(ROOT / 'STG_AUDIT_FAILURE.json')['state'] == 'failed_preserved'
    assert not (ROOT / 'STG_VERIFIED.json').exists()
    theta = load(fixed)
    old_manifest = read(ROOT / 'stg/MANIFEST.json')
    warmup5 = next(r['checkpoint'] for r in old_manifest['epochs'] if r['phase'] == 'warmup' and r['epoch'] == 5)
    original_warmup = load(warmup5)['model']
    assert all(torch.equal(v, original_warmup[k]) for k, v in theta.items())
    del original_warmup
    model = model_reference.ResNet18_201().cpu().eval(); model.load_state_dict(theta, strict=True)
    for parameter in model.parameters(): parameter.requires_grad_(False)
    target = load(result['source_target']); ids = target['external_original_IDs']
    manifest = read(ROOT / 'stg_cpu_trigger_recovery/MANIFEST.json')
    assert len(manifest['epochs']) == 100
    current = torch.zeros(1, 3, 32, 32); previous_meta = None; previous_payload = None
    all_steps, hashes = [], {}; max_algebra = 0.
    for e, record in enumerate(manifest['epochs'], 1):
        payload = load(record['checkpoint']); group = payload['optimizer']['param_groups'][0]
        assert record['epoch'] == payload['epoch'] == e and payload['incoming_checkpoint'] == previous_meta
        assert record['examples'] == payload['examples'] == 200 and record['batches'] == payload['batches'] == 2
        assert group['lr'] == .1 and group['momentum'] == group['weight_decay'] == 0
        assert group['foreach'] is False and group['fused'] is False and not payload['optimizer']['state']
        if previous_payload:
            assert torch.equal(payload['loader_rng_before_epoch'], previous_payload['loader_rng'])
            assert torch.equal(payload['rng_before_epoch']['torch_CPU'], previous_payload['rng']['torch_CPU'])
        else:
            seeded = torch.Generator().manual_seed(3000).get_state()
            assert torch.equal(payload['loader_rng_before_epoch'], seeded)
            assert torch.equal(payload['rng_before_epoch']['torch_CPU'], seeded)
        assert payload['rng']['torch_CUDA'] == payload['rng_before_epoch']['torch_CUDA'] == []
        gen = torch.Generator().set_state(payload['loader_rng_before_epoch'])
        order = torch.cat(list(DataLoader(torch.arange(200), batch_size=128, shuffle=True, generator=gen)))
        expected_ids = torch.tensor(ids)[order]
        assert torch.equal(expected_ids, payload['source_ids']) and torch.equal(gen.get_state(), payload['loader_rng'])
        for b, meta in enumerate(payload['steps'], 1):
            step = load(meta)
            assert step['epoch'] == e and step['batch'] == b and step['fixed_surrogate'] == fixed
            assert torch.equal(step['external_original_IDs'], expected_ids[(b-1)*128:b*128])
            assert torch.equal(current, step['delta_before']) and bool(torch.isfinite(step['gradient']).all())
            assert torch.equal(step['target'], torch.full((len(step['x']),), 200))
            assert step['x'].is_contiguous() and float(step['x'].abs().max()) <= 1
            expected = (step['delta_before'] - step['gradient'] * .1).clamp(-32/255, 32/255)
            error = float((expected - step['delta_after']).abs().max()); max_algebra = max(max_algebra, error)
            assert error <= 1e-7 and float(step['delta_after'].abs().max()) <= 32/255 + 1e-7
            current = step['delta_after']; all_steps.append(meta); hashes[meta['path']] = meta['sha256']
        assert torch.equal(current, payload['delta']) and bool(torch.isfinite(current).all())
        previous_meta, previous_payload = record['checkpoint'], payload
        hashes[previous_meta['path']] = previous_meta['sha256']
        write(ROOT / 'STG_CPU_TRIGGER_AUDIT_STATE.json', {'state': 'auditing', 'pid': os.getpid(), 'checked_epochs': e})
    assert len(all_steps) == 200 and torch.equal(load(result['delta']), current)
    events = [json.loads(v) for v in (ROOT/'stg_cpu_trigger_recovery/events.jsonl').read_text(encoding='utf-8').splitlines()]
    assert events == manifest['epochs']
    dataset = ExternalImages(target['images_HWC_uint8'], torch.full((200,), 200))
    positions = {value: i for i, value in enumerate(ids)}; replays = []
    for meta in [all_steps[0], all_steps[-1]]:
        step = load(meta)
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(step['augmentation_CPU_rng_before_fetch'])
            images = torch.stack([dataset[positions[int(i)]][0] for i in step['external_original_IDs']])
        assert torch.equal(images, step['x'])
        delta = step['delta_before'].clone().requires_grad_(True)
        loss = torch.nn.functional.cross_entropy(model((images+delta).clamp(-1,1)), step['target'], reduction='mean')
        gradient, = torch.autograd.grad(loss, delta)
        diff = (gradient - step['gradient']).abs()
        assert bool((diff <= 2e-5 + 1e-3 * step['gradient'].abs()).all()), float(diff.max())
        replays.append({'epoch': step['epoch'], 'batch': step['batch'], 'max_abs_gradient_error': float(diff.max()),
                        'atol': 2e-5, 'rtol': .001, 'augmentation_exact': True})
    assert not torch.cuda.is_initialized() and all(torch.equal(v, theta[k]) for k,v in model.state_dict().items())
    write(ROOT / 'STG_CPU_TRIGGER_VERIFIED.json', {'state': 'passed_CPU_trigger100_with_reused_fixed_surrogate',
          'CPU_only': True, 'new_epochs': 100, 'new_batches': 200, 'new_steps': 200,
          'max_projection_algebra_error': max_algebra, 'independent_gradient_replays': replays,
          'all200_gradients_independently_recomputed': False, 'delta': result['delta'], 'fixed_surrogate': fixed,
          'original_105_model_epochs_reused_not_retrained': True,
          'original_CPU_GPU_gradient_audit_remains_failed': True, 'history_hashes': hashes,
          'FedUBA_attack_completed': False, 'overall_goal_complete': False})


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        write(ROOT / 'STG_CPU_TRIGGER_AUDIT_FAILURE.json', {'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
