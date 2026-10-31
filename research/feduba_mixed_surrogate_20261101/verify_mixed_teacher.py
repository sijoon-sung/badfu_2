"""Independent CPU metadata/state/ID/optimizer/RNG audit, not SGD replay."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONDONTWRITEBYTECODE='1')
import json
import math
import random
import sys
import traceback
sys.dont_write_bytecode = True
import numpy as np
import torch
from torch.utils.data import DataLoader
from mixed_common import ROOT, read, write, sha, once, frozen, check_bindings, model_class


def load(meta, external=False):
    path = meta['path'] if external else ROOT / meta['path']
    from pathlib import Path
    path = Path(path)
    assert sha(path) == meta['sha256'] and path.stat().st_size == meta['bytes']
    value = torch.load(path, map_location='cpu', weights_only=True)
    return value


def equal(a, b):
    if isinstance(a, torch.Tensor): return isinstance(b, torch.Tensor) and torch.equal(a, b)
    if isinstance(a, dict): return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    if isinstance(a, (tuple, list)): return type(a) is type(b) and len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    return a == b


def finite(value):
    if isinstance(value, torch.Tensor): assert value.device.type == 'cpu' and bool(torch.isfinite(value).all())
    elif isinstance(value, dict):
        for x in value.values(): finite(x)
    elif isinstance(value, (tuple, list)):
        for x in value: finite(x)
    elif isinstance(value, float): assert math.isfinite(value)


def main():
    p = frozen(); check_bindings(p)
    torch.set_num_threads(1); assert not torch.cuda.is_initialized()
    once('AUDIT_ONCE.json', {'pid': os.getpid(), 'model_forward_calls': 0, 'CPU_threads': 1})
    result, m = read(ROOT / 'TRAIN_RESULT.json'), read(ROOT / 'MANIFEST.json')
    assert result['state'] == 'completed_mixed100_warmup5_teacher_only'
    assert sha(ROOT / 'MANIFEST.json') == result['manifest_sha256']
    assert m['profile_sha256'] == sha(ROOT / 'PROFILE.json') and m['freeze_sha256'] == sha(ROOT / 'FREEZE.json')
    expected = [('mixed_surrogate', i) for i in range(1, 101)] + [('warmup', i) for i in range(1, 6)]
    assert [(v['phase'], v['epoch']) for v in m['epochs']] == expected and m['bindings'] == p['bindings']
    # Independently construct domain / original-ID / label tables, no training dataset helper.
    tiny, target = load(p['bindings']['tiny'], True), load(p['bindings']['target'], True)
    tiny_labels = torch.as_tensor(tiny['labels'], dtype=torch.long)
    external_ids = torch.as_tensor(target['external_original_IDs'], dtype=torch.long)
    assert tiny_labels.shape == (100000,) and external_ids.shape == (200,)
    assert len(set(external_ids.tolist())) == 200
    assert torch.equal(torch.bincount(tiny_labels, minlength=200), torch.tensor([500] * 200))
    original_ids = torch.cat([torch.arange(100000), external_ids])
    labels = torch.cat([tiny_labels, torch.full((200,), 200)])
    initial = load(p['bindings']['initial'], True)[p['bindings']['initial']['payload_key']]
    model = model_class(p)().cpu(); model.load_state_dict(initial, strict=True)
    shapes = [tuple(v.shape) for v in model.parameters()]
    initial_counters = {k: int(v) for k, v in initial.items() if k.endswith('num_batches_tracked')}
    assert initial_counters
    incoming = p['bindings']['initial']; previous_phase = previous_rng = previous_loader = None
    cumulative = 0; hashes = {}; final_state = None
    for row in m['epochs']:
        phase, epoch = row['phase'], row['epoch']; value = load(row['checkpoint']); finite(value)
        assert value['incoming_checkpoint'] == incoming
        assert (value['phase'], value['epoch']) == (phase, epoch)
        n, batches, offset = (100200, 783, 1000) if phase == 'mixed_surrogate' else (200, 2, 2000)
        assert value['examples'] == row['examples'] == n and value['batches'] == row['batches'] == batches
        assert value['profile_sha256'] == sha(ROOT / 'PROFILE.json') and math.isfinite(row['loss'])
        assert row['target_seen'] == 200 and row['Tiny_seen'] == (100000 if phase == 'mixed_surrogate' else 0)
        assert 0 <= row['target_correct'] <= 200 and 0 <= row['Tiny_correct'] <= row['Tiny_seen']
        assert row['train_correct'] == row['target_correct'] + row['Tiny_correct']
        cumulative += batches; assert row['cumulative_batches'] == cumulative
        before, after = value['rng_before_epoch'], value['rng']
        assert len(before['torch_CUDA']) == len(after['torch_CUDA']) == 1
        if phase == previous_phase:
            assert equal(before, previous_rng) and torch.equal(value['loader_rng_before_epoch'], previous_loader)
        else:
            state = torch.Generator().manual_seed(p['seed'] + offset).get_state()
            assert torch.equal(before['torch_CPU'], state) and torch.equal(value['loader_rng_before_epoch'], state)
            assert before['python'] == random.Random(p['seed'] + offset).getstate()
            ns = np.random.RandomState(p['seed'] + offset).get_state()
            assert before['numpy'] == (ns[0], ns[1].tolist(), int(ns[2]), int(ns[3]), float(ns[4]))
        g = torch.Generator().set_state(value['loader_rng_before_epoch'])
        order = torch.cat(list(DataLoader(torch.arange(n), batch_size=128, shuffle=True, generator=g, num_workers=0)))
        if phase == 'warmup': order = order + 100000
        assert torch.equal(value['source_positions'], order)
        assert torch.equal(value['source_domains'], (order >= 100000).long())
        assert torch.equal(value['source_original_IDs'], original_ids[order])
        assert torch.equal(value['source_labels'], labels[order])
        assert torch.equal(value['loader_rng'], g.get_state())
        model.load_state_dict(value['model'], strict=True)
        for k, v in value['model'].items():
            if k in initial_counters:
                assert v.dtype == torch.int64 and int(v) == initial_counters[k] + cumulative
            else: assert v.dtype == torch.float32
        opt = value['optimizer']; assert len(opt['param_groups']) == 1
        group = opt['param_groups'][0]; params = group['params']
        assert len(params) == len(shapes) and set(params) == set(opt['state'])
        assert not group['maximize'] and not group['differentiable']
        if phase == 'mixed_surrogate':
            assert group['momentum'] == .9 and group['weight_decay'] == .0005 and group['dampening'] == 0 and not group['nesterov']
            expected_lr = .1 * (1 + math.cos(math.pi * epoch / 100)) / 2
            expected_before = .1 * (1 + math.cos(math.pi * (epoch - 1) / 100)) / 2
            assert abs(group['lr'] - expected_lr) <= 1e-14 and abs(row['lr_before'] - expected_before) <= 1e-14
            assert value['scheduler']['last_epoch'] == epoch and value['scheduler']['T_max'] == 100 and value['scheduler']['eta_min'] == 0
            for key, shape in zip(params, shapes): assert tuple(opt['state'][key]['momentum_buffer'].shape) == shape
        else:
            assert group['lr'] == row['lr_before'] == .001 and group['betas'] == (.9, .999)
            assert group['weight_decay'] == 0 and group['eps'] == 1e-8 and value['scheduler'] is None
            for key, shape in zip(params, shapes):
                slot = opt['state'][key]; assert int(slot['step']) == epoch * 2
                assert tuple(slot['exp_avg'].shape) == tuple(slot['exp_avg_sq'].shape) == shape
        assert group['lr'] == row['lr_after']
        hashes[row['checkpoint']['path']] = row['checkpoint']['sha256']
        incoming = row['checkpoint']; previous_phase, previous_rng, previous_loader = phase, after, value['loader_rng']
        if phase == 'warmup' and epoch == 5: final_state = value['model']
        write(ROOT / 'AUDIT_STATE.json', {'state': 'auditing', 'pid': os.getpid(), 'checked_epochs': len(hashes), 'batches': cumulative})
    assert cumulative == result['actual_batches'] == 78310 and len(hashes) == 105
    fixed = load(result['fixed_teacher']); assert equal(fixed, final_state)
    events = [json.loads(s) for s in (ROOT / 'private_run/events.jsonl').read_text(encoding='utf-8').splitlines()]
    assert [(v['phase'], v['epoch']) for v in events] == expected and sum(v['batches'] for v in events) == 78310
    assert sum(v['target_seen'] for v in events) == result['target_exposures'] == 21000
    assert sum(v['examples'] for v in events) == result['sample_exposures'] == 10021000
    check_bindings(p); frozen(); assert not torch.cuda.is_initialized()
    once('TRAIN_VERIFIED.json', {'state': 'passed', 'CPU_only': True, 'CPU_threads': 1,
         'train_result_sha256': sha(ROOT / 'TRAIN_RESULT.json'), 'manifest_sha256': sha(ROOT / 'MANIFEST.json'),
         'model_epochs': 105, 'batches': 78310, 'history_hashes': hashes, 'fixed_teacher': result['fixed_teacher'],
         'source_domain_ID_label_loader_RNG_checks': 105, 'optimizer_state_checks': 105,
         'BN_counter_exact_to_actual_batches': True, 'fixed_teacher_exact_to_warmup5': True,
         'all_SGD_gradients_or_raw_augmentations_independently_replayed': False, 'model_forwards': 0,
         'trigger_or_SSS_or_FU_started': False, 'overall_goal_complete': False})
    write(ROOT / 'AUDIT_STATE.json', {'state': 'passed', 'pid': os.getpid(), 'checked_epochs': 105, 'batches': 78310})


if __name__ == '__main__':
    try: main()
    except BaseException:
        once('AUDIT_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
