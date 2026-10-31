"""Independent CPU algebra/source/RNG audit and the fixed first/last gradient replays."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONDONTWRITEBYTECODE='1')
import sys
sys.dont_write_bytecode = True
import json
import math
import traceback
import torch
from torch.utils.data import DataLoader
import binding_gate as gate
from trigger_common import ROOT, read, sha, write, load, policy, check_inputs, model_and_target, finite
from stg_training import ExternalImages


def equal(a, b):
    if isinstance(a, torch.Tensor): return isinstance(b, torch.Tensor) and torch.equal(a, b)
    if isinstance(a, dict): return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    if isinstance(a, (tuple, list)): return type(a) is type(b) and len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    return a == b


def optimizer_check(value):
    assert len(value['param_groups']) == 1 and not value['state']
    g = value['param_groups'][0]
    assert len(g['params']) == 1 and g['lr'] == .1 and g['momentum'] == g['weight_decay'] == g['dampening'] == 0
    assert not g['nesterov'] and not g['maximize'] and not g['differentiable']
    assert g['foreach'] is False and g['fused'] is False


def main():
    source, launch = gate.run_profile(); check_inputs(source, launch); numeric = policy()
    gate.once('AUDIT_ONCE.json', {'pid': os.getpid(), 'fixed_gradient_replays_budget': 2, 'CPU_threads': 2})
    result, m = read(ROOT / 'TRIGGER_RESULT.json'), read(ROOT / 'MANIFEST.json')
    assert result['state'] == 'completed_CPU_mixed_teacher_trigger100'
    assert result['actual_batches'] == 200 and result['new_epochs'] == 100 and result['sample_exposures'] == 20000
    assert m['teacher'] == result['teacher'] == launch['teacher_bindings']['teacher']
    assert m['source_target'] == source['inputs']['target']
    assert m['launch_profile_sha256'] == sha(ROOT / 'LAUNCH_PROFILE.json')
    assert m['source_freeze_sha256'] == sha(ROOT / 'SOURCE_FREEZE.json') and m['run_freeze_sha256'] == sha(ROOT / 'RUN_FREEZE.json')
    assert sha(ROOT / 'MANIFEST.json') == result['manifest_sha256'] and len(m['epochs']) == 100
    model, theta, target, ids = model_and_target(source, launch)
    current = torch.zeros(1, 3, 32, 32); previous_meta = previous_payload = None
    steps, hashes, max_error = [], {}, 0.
    for e, row in enumerate(m['epochs'], 1):
        payload = load(row['checkpoint']); finite(payload); optimizer_check(payload['optimizer'])
        assert row['epoch'] == payload['epoch'] == e and math.isfinite(row['loss'])
        assert row['examples'] == payload['examples'] == 200 and row['batches'] == payload['batches'] == 2
        assert payload['incoming_checkpoint'] == previous_meta and payload['teacher'] == result['teacher']
        if previous_payload is None:
            expected_rng = torch.Generator().manual_seed(3000).get_state()
            assert torch.equal(payload['rng_before_epoch']['torch_CPU'], expected_rng)
            assert torch.equal(payload['loader_rng_before_epoch'], expected_rng)
        else:
            assert equal(payload['rng_before_epoch'], previous_payload['rng'])
            assert torch.equal(payload['loader_rng_before_epoch'], previous_payload['loader_rng'])
        assert payload['rng_before_epoch']['torch_CUDA'] == payload['rng']['torch_CUDA'] == []
        g = torch.Generator().set_state(payload['loader_rng_before_epoch'])
        order = torch.cat(list(DataLoader(torch.arange(200), batch_size=128, shuffle=True, generator=g, num_workers=0)))
        expected_ids = ids[order]
        assert torch.equal(payload['source_ids'], expected_ids) and torch.equal(g.get_state(), payload['loader_rng'])
        assert len(payload['steps']) == 2
        for batch, meta in enumerate(payload['steps'], 1):
            v = load(meta); finite(v); optimizer_check(v['optimizer'])
            n = 128 if batch == 1 else 72
            assert (v['epoch'], v['batch']) == (e, batch) and v['teacher'] == result['teacher']
            assert v['x'].shape == (n, 3, 32, 32) and v['x'].dtype == torch.float32 and v['x'].is_contiguous()
            assert bool((v['x'].abs() <= 1).all()) and torch.equal(v['target'], torch.full((n,), 200))
            assert torch.equal(v['external_original_IDs'], expected_ids[(batch - 1) * 128:batch * 128])
            assert v['gradient'].shape == v['delta_before'].shape == v['delta_after'].shape == (1, 3, 32, 32)
            assert torch.equal(current, v['delta_before'])
            expected_delta = (v['delta_before'] - v['gradient'] * .1).clamp(-32 / 255, 32 / 255)
            error = float((expected_delta - v['delta_after']).abs().max()); max_error = max(max_error, error)
            assert error <= 1e-7 and float(v['delta_after'].abs().max()) <= 32 / 255 + 1e-7
            current = v['delta_after']; steps.append(meta); hashes[meta['path']] = meta['sha256']
        assert torch.equal(current, payload['delta'])
        previous_meta, previous_payload = row['checkpoint'], payload
        hashes[previous_meta['path']] = previous_meta['sha256']
        write(ROOT / 'AUDIT_STATE.json', {'state': 'auditing', 'pid': os.getpid(), 'checked_epochs': e, 'checked_steps': len(steps)})
    assert len(steps) == 200 and len(hashes) == 300 and torch.equal(load(result['delta']), current)
    events = [json.loads(line) for line in (ROOT / 'private_run/events.jsonl').read_text(encoding='utf-8').splitlines()]
    assert events == m['epochs']
    data = ExternalImages(target['images_HWC_uint8'], torch.full((200,), 200))
    positions = {int(v): i for i, v in enumerate(ids)}; replays = []
    for meta in [steps[0], steps[-1]]:
        v = load(meta)
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(v['augmentation_CPU_rng_before_fetch'])
            images = torch.stack([data[positions[int(i)]][0] for i in v['external_original_IDs']])
        assert torch.equal(images, v['x'])
        delta = v['delta_before'].clone().requires_grad_(True)
        logits = model((images + delta).clamp(-1, 1))
        # Independent mean-CE expression; does not call core.trigger_step or optimizer.step.
        loss = -torch.log_softmax(logits, dim=1).gather(1, v['target'].reshape(-1, 1)).mean()
        gradient, = torch.autograd.grad(loss, delta)
        difference = (gradient - v['gradient']).abs()
        assert bool((difference <= 2e-5 + 1e-3 * v['gradient'].abs()).all()), float(difference.max())
        replays.append({'epoch': v['epoch'], 'batch': v['batch'], 'examples': len(images),
                        'CPU_mean_CE': float(loss.detach()), 'max_abs_gradient_error': float(difference.max()),
                        'augmentation_exact': True, 'atol': 2e-5, 'rtol': 1e-3})
    assert all(torch.equal(v, theta[k]) for k, v in model.state_dict().items()) and not torch.cuda.is_initialized()
    check_inputs(source, launch); gate.run_profile()
    gate.once('TRIGGER_VERIFIED.json', {'state': 'passed_new_mixed_teacher_CPU_trigger100', 'CPU_only': True,
         'CPU_threads': 2, 'numeric_environment': numeric, 'result_sha256': sha(ROOT / 'TRIGGER_RESULT.json'),
         'teacher': result['teacher'], 'delta': result['delta'], 'epochs': 100, 'batches': 200, 'sample_exposures': 20000,
         'all200_projection_algebra_checked': True, 'max_projection_algebra_error': max_error,
         'fixed_independent_gradient_replays': replays, 'all200_gradients_independently_recomputed': False,
         'history_hashes': hashes, 'original_GPU_STG_failure_preserved': True,
         'new_SSS_FU_or_attack_performance_completed': False, 'overall_goal_complete': False})
    write(ROOT / 'AUDIT_STATE.json', {'state': 'passed', 'pid': os.getpid(), 'checked_epochs': 100, 'checked_steps': 200})


if __name__ == '__main__':
    try: main()
    except BaseException:
        gate.once('AUDIT_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
