"""One full CPU STG storage/count/state/algebra audit, two fixed gradient replays."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import json
import math
import traceback
import torch
from torch.utils.data import DataLoader
import model_reference
from stg_training import ExternalImages
from runtime_common import ROOT, read, write, sha, freeze_check


def load(meta):
    assert sha(ROOT / meta['path']) == meta['sha256'], meta['path']
    assert (ROOT / meta['path']).stat().st_size == meta['bytes']
    return torch.load(ROOT / meta['path'], map_location='cpu', weights_only=True)


def finite_tensors(value):
    if isinstance(value, torch.Tensor):
        assert value.device.type == 'cpu' and bool(torch.isfinite(value).all())
    elif isinstance(value, dict):
        for item in value.values():
            finite_tensors(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            finite_tensors(item)


def main():
    assert not (ROOT / 'STG_VERIFIED.json').exists()
    freeze_check('STG_FREEZE.json')
    with (ROOT / 'STG_AUDIT_ONCE.json').open('x', encoding='utf-8') as stream:
        json.dump({'pid': os.getpid()}, stream)
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    p, ready, result = (read(ROOT / n) for n in ['STG_LAUNCH_PROFILE.json', 'STG_READY.json', 'STG_RESULT.json'])
    assert result['state'] == 'completed_STG100_5_100'
    manifest = read(ROOT / 'stg/MANIFEST.json')
    expected_order = [(phase, e) for phase, count in [('surrogate', 100), ('warmup', 5), ('trigger', 100)] for e in range(1, count + 1)]
    assert [(v['phase'], v['epoch']) for v in manifest['epochs']] == expected_order
    assert manifest['asset_result_sha256'] == ready['asset_result_sha256'] == sha(ROOT / 'ASSET_CPU2_RESULT.json')
    asset = read(ROOT / 'ASSET_CPU2_RESULT.json')
    target = load(asset['target'])
    target_ids = target['external_original_IDs']
    incoming = ready['fresh_initial']
    initial = load(incoming)
    model = model_reference.ResNet18_201().cpu().eval()
    model.load_state_dict(initial['model'], strict=True)
    warmup_model = None
    steps = []; total_batches = 0; hashes = {}; max_algebra_error = 0.
    previous_delta = torch.zeros(1, 3, 32, 32)
    previous_phase = None; previous_rng = None; previous_loader_rng = None
    for record in manifest['epochs']:
        phase, epoch = record['phase'], record['epoch']
        payload = load(record['checkpoint']); finite_tensors(payload)
        assert payload['phase'] == phase and payload['epoch'] == epoch
        assert payload['incoming_checkpoint'] == incoming
        assert payload['source_hashes'] == ready['source_hashes']
        assert payload['asset_result_sha256'] == ready['asset_result_sha256']
        count, batches = (100000, 782) if phase == 'surrogate' else (200, 2)
        assert payload['examples'] == record['examples'] == count and payload['batches'] == record['batches'] == batches
        assert math.isfinite(record['loss'])
        total_batches += batches
        assert record['cumulative_batches'] == total_batches
        assert payload['rng']['torch_CPU'].numel() and len(payload['rng']['torch_CUDA']) == 1
        assert payload['rng_before_epoch']['torch_CPU'].numel() and len(payload['rng_before_epoch']['torch_CUDA']) == 1
        if phase == previous_phase:
            assert torch.equal(payload['loader_rng_before_epoch'], previous_loader_rng)
            assert torch.equal(payload['rng_before_epoch']['torch_CPU'], previous_rng['torch_CPU'])
            assert all(torch.equal(a, b) for a, b in zip(payload['rng_before_epoch']['torch_CUDA'], previous_rng['torch_CUDA']))
        else:
            offset = {'surrogate': 1000, 'warmup': 2000, 'trigger': 3000}[phase]
            seeded = torch.Generator().manual_seed(p['seed'] + offset).get_state()
            assert torch.equal(payload['loader_rng_before_epoch'], seeded)
            assert torch.equal(payload['rng_before_epoch']['torch_CPU'], seeded)
        generator = torch.Generator().set_state(payload['loader_rng_before_epoch'])
        order = torch.cat(list(DataLoader(torch.arange(count), batch_size=128, shuffle=True, generator=generator, num_workers=0)))
        source = order if phase == 'surrogate' else torch.tensor(target_ids)[order]
        assert torch.equal(source, payload['source_ids'])
        assert torch.equal(generator.get_state(), payload['loader_rng'])
        group = payload['optimizer']['param_groups'][0]
        assert len(payload['optimizer']['param_groups']) == 1
        if phase == 'surrogate':
            assert group['momentum'] == .9 and group['weight_decay'] == .0005
            assert abs(group['lr'] - .1 * (1 + math.cos(math.pi * epoch / 100)) / 2) <= 1e-14
            assert abs(record['lr_before'] - .1 * (1 + math.cos(math.pi * (epoch - 1) / 100)) / 2) <= 1e-14
            assert payload['scheduler']['last_epoch'] == epoch
            assert payload['optimizer']['state']
            model.load_state_dict(payload['model'], strict=True)
        elif phase == 'warmup':
            assert group['lr'] == .001 and payload['scheduler'] is None and group['betas'] == (.9, .999)
            assert payload['optimizer']['state']
            for slot in payload['optimizer']['state'].values():
                assert int(slot['step']) == epoch * 2
            model.load_state_dict(payload['model'], strict=True)
            if epoch == 5:
                warmup_model = payload['model']
        else:
            assert group['lr'] == .1 and group['momentum'] == 0 and group['weight_decay'] == 0
            assert group['foreach'] is False and group['fused'] is False and not payload['optimizer']['state']
            assert len(payload['steps']) == 2
            for batch, meta in enumerate(payload['steps'], 1):
                step = load(meta); finite_tensors(step)
                assert (step['phase'], step['epoch'], step['batch']) == ('trigger', epoch, batch)
                assert step['fixed_surrogate'] == result['fixed_surrogate']
                assert torch.equal(previous_delta, step['delta_before'])
                assert step['alpha'] == .1 and step['epsilon_model'] == p['epsilon_model']
                ids = source[(batch - 1) * 128:batch * 128]
                assert torch.equal(step['external_original_IDs'], ids)
                assert step['x'].shape == (len(ids), 3, 32, 32) and step['x'].is_contiguous()
                assert step['x'].abs().max() <= 1 and torch.equal(step['target'], torch.full((len(ids),), 200))
                # Independent CPU FP32 add and projection; CUDA rounding is bounded before the run.
                expected = torch.add(step['delta_before'], step['gradient'], alpha=-.1).clamp(-p['epsilon_model'], p['epsilon_model'])
                error = float((expected - step['delta_after']).abs().max())
                assert error <= 1e-7, error
                max_algebra_error = max(max_algebra_error, error)
                assert float(step['delta_after'].abs().max()) <= p['epsilon_model'] + 1e-7
                previous_delta = step['delta_after']
                steps.append((epoch, batch, meta)); hashes[meta['path']] = meta['sha256']
            assert torch.equal(payload['delta'], previous_delta)
        hashes[record['checkpoint']['path']] = record['checkpoint']['sha256']
        incoming = record['checkpoint']
        previous_phase, previous_rng, previous_loader_rng = phase, payload['rng'], payload['loader_rng']
        write(ROOT / 'STG_AUDIT_STATE.json', {'state': 'auditing', 'pid': os.getpid(), 'phase': phase, 'epoch': epoch,
              'checked_epochs': len(hashes) - len(steps), 'checked_trigger_steps': len(steps)})
    assert total_batches == result['actual_batches'] == 78410 and len(steps) == 200
    frozen = load(result['fixed_surrogate'])
    assert all(torch.equal(frozen[k], warmup_model[k]) for k in frozen)
    final = load(result['delta'])
    assert torch.equal(final, previous_delta) and final.shape == (1, 3, 32, 32)
    assert bool((final == 0).all()) == result['delta_is_exact_zero']
    events = [json.loads(line) for line in (ROOT / 'stg/events.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(events) == 205 and [(v['phase'], v['epoch']) for v in events] == expected_order
    assert sum(v['batches'] for v in events) == 78410
    model.load_state_dict(frozen, strict=True); model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    gradient_replays = []
    dataset = ExternalImages(target['images_HWC_uint8'], torch.full((200,), 200))
    positions = {value: index for index, value in enumerate(target_ids)}
    for epoch, batch, meta in [steps[0], steps[-1]]:
        step = load(meta)
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(step['augmentation_CPU_rng_before_fetch'])
            images = torch.stack([dataset[positions[int(i)]][0] for i in step['external_original_IDs']])
        assert torch.equal(images, step['x']), (epoch, batch, 'augmentation replay')
        delta = step['delta_before'].clone().requires_grad_(True)
        logits = model((images + delta).clamp(-1, 1))
        loss = torch.nn.functional.cross_entropy(logits, step['target'], reduction='mean')
        gradient, = torch.autograd.grad(loss, delta)
        diff = (gradient - step['gradient']).abs()
        assert bool((diff <= 2e-5 + 1e-3 * step['gradient'].abs()).all()), float(diff.max())
        gradient_replays.append({'epoch': epoch, 'batch': batch, 'examples': len(images),
              'CPU_loss': float(loss.detach()), 'gradient_max_abs_difference': float(diff.max()),
              'atol': 2e-5, 'rtol': .001, 'augmentation_exact': True})
    assert not torch.cuda.is_initialized()
    verified = {'state': 'passed', 'CPU_only': True, 'model_epochs': 105, 'trigger_epochs': 100,
                'actual_batches': total_batches, 'actual_source_ID_and_loader_RNG_checks': 205,
                'trigger_steps_algebra_checked': 200, 'max_SGD_projection_abs_error': max_algebra_error,
                'all_trigger_gradients_independently_recomputed': False,
                'fixed_independent_CPU_gradient_replays': gradient_replays,
                'fixed_surrogate_exact_to_warmup5': True, 'history_hashes': hashes,
                'delta': result['delta'], 'FedUBA_attack_completed': False, 'overall_goal_complete': False}
    write(ROOT / 'STG_VERIFIED.json', verified)
    write(ROOT / 'STG_AUDIT_STATE.json', {'state': 'passed', 'pid': os.getpid(), 'checked_epochs': 205, 'checked_steps': 200})
    print(json.dumps({k: verified[k] for k in ['state', 'CPU_only', 'actual_batches', 'trigger_steps_algebra_checked']}))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        write(ROOT / 'STG_AUDIT_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
