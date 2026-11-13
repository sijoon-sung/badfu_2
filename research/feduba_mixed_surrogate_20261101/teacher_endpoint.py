"""Four CPU forwards on a new teacher; same saved target x as the old CPU8 zero cells."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONDONTWRITEBYTECODE='1')
import argparse
import math
import sys
import traceback
sys.dont_write_bytecode = True
import torch
from mixed_common import (ROOT, read, write, sha, once, frozen, check_bindings, load_bound,
                          load_new, assets, MixedImages, model_class, save)


def run():
    p = frozen(); check_bindings(p)
    torch.set_num_threads(2); torch.backends.mkldnn.enabled = True; torch.set_float32_matmul_precision('highest')
    assert torch.get_num_threads() == 2 and not torch.cuda.is_initialized()
    verified = read(ROOT / 'TRAIN_VERIFIED.json'); assert verified['state'] == 'passed'
    fixed = verified['fixed_teacher']; state = load_new(fixed)
    model = model_class(p)().cpu().eval(); model.load_state_dict(state, strict=True)
    for parameter in model.parameters(): parameter.requires_grad_(False)
    tiny, target, labels, target_ids = assets(p)
    target_steps = [load_bound(p, key) for key in ['target_probe_step1', 'target_probe_step2']]
    assert [(v['epoch'], v['batch']) for v in target_steps] == [(100, 1), (100, 2)]
    expected_ids = torch.cat([v['external_original_IDs'] for v in target_steps])
    assert set(expected_ids.tolist()) == set(target_ids.tolist()) and len(set(expected_ids.tolist())) == 200
    deterministic = MixedImages(tiny, target, labels, target_ids, augment=False)
    tiny_positions = [int((labels == c).nonzero()[0]) for c in range(200)]
    once('ENDPOINT_ONCE.json', {'pid': os.getpid(), 'forward_calls_budget': 4, 'sample_forwards_budget': 400})
    cells = []
    for batch, value in enumerate(target_steps, 1):
        x, y = value['x'].contiguous(), value['target']
        assert x.shape == ((128 if batch == 1 else 72), 3, 32, 32) and x.dtype == torch.float32
        assert bool((y == 200).all()) and bool((x.abs() <= 1).all())
        cells.append({'group': 'target', 'batch': batch, 'x': x, 'labels': y,
                      'original_IDs': value['external_original_IDs']})
    for batch, start in enumerate([0, 128], 1):
        positions = tiny_positions[start:start + 128]
        items = [deterministic[i] for i in positions]
        cells.append({'group': 'Tiny_training_representatives', 'batch': batch,
                      'x': torch.stack([v[0] for v in items]), 'labels': torch.tensor([v[1] for v in items]),
                      'original_IDs': torch.tensor(positions)})
    records = []
    for v in cells:
        with torch.inference_mode(): logits = model(v['x']).cpu()
        assert logits.shape == (len(v['labels']), 201) and logits.dtype == torch.float32 and bool(torch.isfinite(logits).all())
        v['logits'] = logits
        records.append({'group': v['group'], 'batch': v['batch'], 'N': len(logits),
                        'correct': int((logits.argmax(1) == v['labels']).sum()),
                        'mean_CE': float(torch.nn.functional.cross_entropy(logits, v['labels']))})
    assert all(torch.equal(state[k], v) for k, v in model.state_dict().items())
    summaries = {}
    for group in ['target', 'Tiny_training_representatives']:
        subset = [r for r in records if r['group'] == group]
        summaries[group] = {'N': 200, 'correct': sum(v['correct'] for v in subset),
                            'mean_CE': math.fsum(v['N'] * v['mean_CE'] for v in subset) / 200}
    tiny_correct_classes = set()
    for v in cells:
        if v['group'] == 'Tiny_training_representatives':
            good = v['labels'][v['logits'].argmax(1) == v['labels']]
            tiny_correct_classes.update(good.tolist())
    old = read(p['bindings']['old_CPU8_result']['path'])['summary']['eval_frozen/zero']
    assert old['N'] == 200 and old['target_hits'] == 0
    rule = {'target_count_exceeds_old_zero': summaries['target']['correct'] > old['target_hits'],
            'at_least_two_distinct_Tiny_classes_correct': len(tiny_correct_classes) >= 2}
    outputs = save(ROOT / 'private_run/endpoint_inputs_logits.pt', cells)
    check_bindings(p); frozen(); assert not torch.cuda.is_initialized()
    once('ENDPOINT_RESULT.json', {'state': 'completed_CPU_teacher_endpoint_only', 'fixed_teacher': fixed,
         'teacher_audit_sha256': sha(ROOT / 'TRAIN_VERIFIED.json'), 'records': records, 'summary': summaries,
         'Tiny_correct_class_count': len(tiny_correct_classes), 'old_same_saved_target_zero_cell': old,
         'minimal_functional_checks': rule, 'minimal_functional_condition_passed': all(rule.values()),
         'condition_is_not_sufficient_for_transfer_or_attack': True, 'forward_calls': 4, 'sample_forwards': 400,
         'CPU_threads': 2, 'MKLDNN': torch.backends.mkldnn.enabled, 'CUDA_initialized': False,
         'torch_version': str(torch.__version__), 'raw_private_outputs': outputs,
         'no_independent_model_replay_claim': True, 'trigger_or_SSS_or_FU_started': False, 'overall_goal_complete': False})


def verify():
    p = frozen(); torch.set_num_threads(1)
    r = read(ROOT / 'ENDPOINT_RESULT.json')
    outputs = load_new(r['raw_private_outputs'])
    once('ENDPOINT_VERIFY_ONCE.json', {'pid': os.getpid(), 'model_forwards': 0})
    assert len(outputs) == 4 and r['forward_calls'] == 4 and r['sample_forwards'] == 400
    cells = set(); counts = {'target': 0, 'Tiny_training_representatives': 0}; losses = {k: [] for k in counts}
    ids = {k: [] for k in counts}; tiny_correct_classes = set(); max_error = 0.
    for v in outputs:
        cell = (v['group'], v['batch']); assert cell not in cells and v['group'] in counts and v['batch'] in [1, 2]
        cells.add(cell)
        n = 128 if v['batch'] == 1 else 72
        assert v['x'].dtype == torch.float32 and tuple(v['x'].shape) == (n, 3, 32, 32) and bool((v['x'].abs() <= 1).all())
        assert tuple(v['logits'].shape) == (n, 201) and bool(torch.isfinite(v['logits']).all())
        targets = v['labels'].tolist(); values = v['logits'].tolist()
        assert all(0 <= t < 201 for t in targets) and len(targets) == n
        if v['group'] == 'target': assert all(t == 200 for t in targets)
        hits, batch_losses = 0, []
        for row, y in zip(values, targets):
            hit = max(range(201), key=lambda j: row[j]) == y
            hits += hit
            if hit and v['group'] == 'Tiny_training_representatives': tiny_correct_classes.add(y)
            peak = max(row); batch_losses.append(peak + math.log(math.fsum(math.exp(x - peak) for x in row)) - row[y])
        counts[v['group']] += hits; losses[v['group']].extend(batch_losses); ids[v['group']].extend(v['original_IDs'].tolist())
        primary = next(z for z in r['records'] if (z['group'], z['batch']) == cell)
        assert primary['correct'] == hits and primary['N'] == n
        loss = math.fsum(batch_losses) / n; error = abs(loss - primary['mean_CE']); max_error = max(max_error, error)
        assert error <= p['endpoint_CE_atol'] + p['endpoint_CE_rtol'] * abs(loss)
    for group in counts:
        assert len(ids[group]) == len(set(ids[group])) == len(losses[group]) == 200
        assert counts[group] == r['summary'][group]['correct']
    assert len(cells) == 4 and len(tiny_correct_classes) == r['Tiny_correct_class_count']
    # Same saved target inputs/IDs, not a newly chosen favorable augmentation.
    for batch in [1, 2]:
        original = load_bound(p, 'target_probe_step' + str(batch))
        v = next(v for v in outputs if (v['group'], v['batch']) == ('target', batch))
        assert torch.equal(original['x'], v['x']) and torch.equal(original['external_original_IDs'], v['original_IDs'])
    raw_tiny = load_bound(p, 'tiny'); tiny_labels = torch.as_tensor(raw_tiny['labels'])
    expected_ids = torch.tensor([int((tiny_labels == c).nonzero()[0]) for c in range(200)])
    tiny_cells = sorted((v for v in outputs if v['group'] == 'Tiny_training_representatives'), key=lambda v: v['batch'])
    assert torch.equal(torch.cat([v['original_IDs'] for v in tiny_cells]), expected_ids)
    assert torch.equal(torch.cat([v['labels'] for v in tiny_cells]), torch.arange(200))
    raw_images = raw_tiny['images_HWC_uint8'][expected_ids]
    expected_images = raw_images.permute(0, 3, 1, 2).float().div(255).sub(.5).div(.5).contiguous()
    assert torch.equal(torch.cat([v['x'] for v in tiny_cells]), expected_images)
    old = read(p['bindings']['old_CPU8_result']['path'])['summary']['eval_frozen/zero']; assert old['target_hits'] == 0
    rule = counts['target'] > old['target_hits'] and len(tiny_correct_classes) >= 2
    assert rule == r['minimal_functional_condition_passed'] and not torch.cuda.is_initialized()
    check_bindings(p); frozen()
    once('ENDPOINT_VERIFIED.json', {'state': 'passed', 'endpoint_result_sha256': sha(ROOT / 'ENDPOINT_RESULT.json'),
         'independent_counts': counts, 'independent_CE': {k: math.fsum(v) / 200 for k, v in losses.items()},
         'max_CE_abs_error': max_error, 'model_forward_calls': 0, 'same_target_inputs_IDs_exact': True,
         'minimal_functional_condition_passed': rule, 'automatic_next_stage_authorized_by_this_check': False,
         'paper_performance_reproduction': False, 'overall_goal_complete': False})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--phase', choices=['run', 'verify'], required=True)
    a = parser.parse_args()
    try: run() if a.phase == 'run' else verify()
    except BaseException:
        once('ENDPOINT_FAILURE_' + a.phase + '.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
