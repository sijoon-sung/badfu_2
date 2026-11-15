"""Run the fixed, clean-only recovery timing comparison on sealed BadFU endpoints."""

import ast
import copy
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['OMP_NUM_THREADS'] = '4'
os.environ['MKL_NUM_THREADS'] = '4'
sys.dont_write_bytecode = True

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

ROOT = Path(__file__).resolve().parent
SCHEDULES = {'none': (0, 0, 0, 0), 'early': (48, 0, 0, 0),
             'late': (0, 0, 0, 48), 'split': (16, 0, 16, 16)}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(name, value):
    path = ROOT / name
    temp = path.with_suffix('.tmp')
    with temp.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
    temp.replace(path)


def check(info):
    path = Path(info['path'])
    if sha(path) != info['sha256']:
        raise ValueError(f'Input checksum mismatch: {path.name}')
    return path


def tensor_digest(state):
    digest = hashlib.sha256()
    for key, value in state.items():
        digest.update(key.encode())
        digest.update(value.detach().contiguous().numpy().tobytes())
    return digest.hexdigest()


def index_digest(values):
    return hashlib.sha256(np.asarray(values, dtype='<i8').tobytes()).hexdigest()


def normalise(images):
    mean = torch.tensor([.4914, .4822, .4465])[None, :, None, None]
    std = torch.tensor([.2023, .1994, .2010])[None, :, None, None]
    return ((images.permute(0, 3, 1, 2).float() / 255 - mean) / std).contiguous()


def pick(rng, pool, count):
    return rng.choice(np.asarray(pool), count, replace=False)


def prepare(cfg):
    raw = torch.load(check(cfg['public_data']), map_location='cpu', weights_only=True)
    retained = torch.load(check(cfg['retained_data']), map_location='cpu', weights_only=True)
    partitions = read(check(cfg['partition']))['clean_cifar10_indices']
    cfg_removal = cfg['infected_normal_removal']
    removed = read(check(cfg_removal))
    assert len(removed) == 850 and len(set(removed)) == 850
    if cfg_removal['format'] == 'local_positions':
        removed = [partitions[cfg_removal['client']][int(pos)] for pos in removed]
    rng = np.random.default_rng(61115)
    train_ids, retain_eval_ids = {}, {}
    for client in (1, 2, 3):
        pool = sorted(set(partitions[client]) - set(removed))
        samples = pick(rng, pool, 416)
        train_ids[client], retain_eval_ids[client] = samples[:256], samples[256:]
    recovery_ids = np.concatenate([train_ids[c] for c in (1, 2, 3)])
    assert len(set(recovery_ids)) == 768 and not set(recovery_ids) & set(removed)
    recovery_plan = np.stack([pick(rng, np.arange(len(recovery_ids)), 32) for _ in range(48)])

    labels = raw['test_y']
    chosen = [pick(rng, torch.where(labels == cls)[0].numpy(), 240) for cls in range(10)]
    repair_ids = np.concatenate([part[:80] for part in chosen])
    public_ids = np.sort(np.concatenate([part[80:] for part in chosen]))
    assert len(set(repair_ids) & set(public_ids)) == 0
    repair_views = raw['test_x'][repair_ids].clone()
    for i, image in enumerate(repair_views):
        if rng.random() < .5:
            image.copy_(image.flip(1))
        if i % 2:
            width = int(rng.choice([10, 14, 18]))
            y, x = rng.integers(0, 33 - width, size=2)
            image[y:y + width, x:x + width] = torch.tensor([125, 123, 114], dtype=torch.uint8)
    repair_plan = np.stack([pick(rng, np.arange(len(repair_ids)), 32) for _ in range(48)])
    eval_ids = np.concatenate([retain_eval_ids[c] for c in (1, 2, 3)])
    assert not set(eval_ids) & set(recovery_ids)
    # These benign deleted samples are reserved for the independent finite audit.
    normal_members = {'normal193': partitions[4], 'normal228': sorted(set(range(50000)) - set(sum(partitions[1:], [])))}
    assert {key: len(ids) for key, ids in normal_members.items()} == {'normal193': 9668, 'normal228': 11395}
    member_ids = {key: pick(rng, ids, 400) for key, ids in normal_members.items()}
    for ids in member_ids.values():
        assert not set(ids) & (set(recovery_ids) | set(eval_ids))

    return {'public_ids': public_ids, 'public_x': raw['test_x'][public_ids], 'public_y': labels[public_ids],
            'repair_x': repair_views, 'repair_y': labels[repair_ids], 'repair_plan': repair_plan,
            'recover_x': retained['train_x'][recovery_ids], 'recover_y': retained['train_y'][recovery_ids],
            'recover_plan': recovery_plan, 'client_x': retained['train_x'][eval_ids], 'client_y': retained['train_y'][eval_ids],
            'membership': {key: (retained['train_x'][ids], retained['train_y'][ids]) for key, ids in member_ids.items()},
            'receipt': {'public': index_digest(public_ids), 'correction': index_digest(repair_ids),
                        'retained': index_digest(recovery_ids), 'heldout_clients': index_digest(eval_ids),
                        'correction_batches': index_digest(repair_plan), 'recovery_batches': index_digest(recovery_plan),
                        'deleted_review_ids': {k: index_digest(v) for k, v in member_ids.items()},
                        'clean_overlap_deleted': 0}}


@torch.no_grad()
def features(prefix, images):
    return torch.cat([prefix(x) for x in normalise(images).split(32)]).contiguous()


@torch.inference_mode()
def logits(tail, matrix):
    result = torch.cat([tail(x) for x in matrix.split(32)])
    assert torch.isfinite(result).all()
    return result


def advance(model, optimizer, matrix, labels, plan, start, end):
    for ids in plan[start:end]:
        optimizer.zero_grad(set_to_none=True)
        loss = F.cross_entropy(model(matrix[ids]), labels[ids])
        if not torch.isfinite(loss).item():
            raise ValueError('Nonfinite training loss')
        loss.backward()
        optimizer.step()


def fit_schedule(tail, data, recovery, correction, schedule):
    model = copy.deepcopy(tail)
    restore = torch.optim.SGD(model.parameters(), lr=.005)
    repair = torch.optim.SGD(model.parameters(), lr=.01)
    n = 0
    first = None
    for boundary, count in enumerate(schedule):
        if count:
            advance(model, repair, correction, data['repair_y'], data['repair_plan'], n, n + count)
            if n == 0 and boundary < 3:
                first = copy.deepcopy(model)
            n += count
        if boundary < 3:
            advance(model, restore, recovery, data['recover_y'], data['recover_plan'], boundary * 12, (boundary + 1) * 12)
    anchor = copy.deepcopy(model)
    advance(model, restore, recovery, data['recover_y'], data['recover_plan'], 36, 42)
    half = copy.deepcopy(model)
    advance(model, restore, recovery, data['recover_y'], data['recover_plan'], 42, 48)
    assert n == sum(schedule)
    checkpoints = {'anchor': anchor, 'tail6': half, 'tail12': model}
    if first is not None:
        checkpoints['first_repair'] = first
    return checkpoints


def correct_counts(values, labels):
    hits = values.argmax(1) == labels
    return {'n': len(labels), 'correct': int(hits.sum()),
            'class_correct': torch.bincount(labels[hits], minlength=10).tolist(),
            'class_n': torch.bincount(labels, minlength=10).tolist()}


def auc_by_class(member, other, ym, yo):
    sm = member.log_softmax(1)[torch.arange(len(ym)), ym]
    so = other.log_softmax(1)[torch.arange(len(yo)), yo]
    levels = []
    for cls in range(10):
        neg = so[yo == cls].sort().values
        pos = sm[ym == cls].contiguous()
        if len(pos) == 0 or len(neg) == 0:
            continue
        lo = torch.searchsorted(neg, pos)
        hi = torch.searchsorted(neg, pos, right=True)
        levels.append(float((lo + hi).double().mean() / (2 * len(neg))))
    assert len(levels) > 0
    return {'classes': len(levels), 'macro_auc': sum(levels) / len(levels), 'member_n': len(ym)}


def load_endpoint(entry, constructor):
    state = torch.load(check(entry), map_location='cpu', weights_only=True)
    if entry['payload_key'] is not None:
        state = state[entry['payload_key']]
    assert all(torch.isfinite(v).all().item() for v in state.values())
    model = constructor().eval()
    model.load_state_dict(state, strict=True)
    base = model.model
    prefix = nn.Sequential(base.conv1, base.bn1, base.relu, base.maxpool, base.layer1, base.layer2, base.layer3)
    tail = nn.Sequential(base.layer4, base.avgpool, nn.Flatten(1), base.fc)
    return model, prefix.eval(), tail.eval()


def read_archived_eval(cfg, public_ids, public_labels):
    # Open pre-existing, hash-anchored test data only in the evaluation stage.
    from PIL import Image
    archive = cfg['evaluation_only']
    source = check(archive['reader'])
    table = check(archive['table'])
    record = torch.load(check(archive['record']), map_location='cpu', weights_only=False)
    container = record['bd_test']['bd_data_container']['data_dict']
    assert len(container) == 9000
    lookup = {int(k): k for k in container}
    keep = np.asarray([i for i, idx in enumerate(public_ids) if int(idx) in lookup])
    subset = {lookup[int(public_ids[i])]: container[lookup[int(public_ids[i])]] for i in keep}
    node = next(n for n in ast.parse(source.read_text(encoding='utf-8')).body
                if isinstance(n, ast.FunctionDef) and n.name == 'record_images')
    scope = dict(ROOT=source.parents[2], ASSETS=table.parent, json=json, np=np, torch=torch, Image=Image, sha256=sha)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), scope)
    inputs, targets, ids = scope['record_images'](subset)
    assert len(keep) == 1440 and targets.unique().numel() == 1
    assert ids == public_ids[keep].tolist() and (public_labels[keep] != targets).all()
    return inputs, public_labels[keep], int(targets[0])


def functional(predicted, true, target):
    n = len(true)
    right, target_hits = int((predicted == true).sum()), int((predicted == target).sum())
    return {'n': n, 'original_correct': right, 'target': target_hits, 'other_wrong': n - right - target_hits}


def evaluate_case(name, entry, constructor, data, cfg, attack_evaluation):
    start = time.monotonic()
    whole, prefix, tail = load_endpoint(entry, constructor)
    public = features(prefix, data['public_x'])
    with torch.inference_mode():
        native = whole(normalise(data['public_x'][:32]))
        cached = tail(public[:32])
        assert torch.equal(native.argmax(1), cached.argmax(1)) and torch.allclose(native, cached, atol=1e-5, rtol=1e-5)
    recovery, correction = features(prefix, data['recover_x']), features(prefix, data['repair_x'])
    clients = features(prefix, data['client_x'])
    member = data['membership'].get(name)
    deleted = features(prefix, member[0]) if member else None
    models = {key: fit_schedule(tail, data, recovery, correction, schedule) for key, schedule in SCHEDULES.items()}
    model_hashes = {key: {stage: tensor_digest(model.state_dict()) for stage, model in phases.items()}
                    for key, phases in models.items()}
    frozen = {'source': entry['sha256'], 'actual_recovery_steps': 48, 'actual_repair_steps': {k: sum(v) for k, v in SCHEDULES.items()},
              'model_hashes': model_hashes}
    write(f'{name}_FIT.json', frozen)

    result = {'fit': frozen, 'clean_original': correct_counts(logits(tail, public), data['public_y']), 'arms': {}}
    for key, phases in models.items():
        after = logits(phases['tail12'], public)
        row = {'public_anchor': correct_counts(logits(phases['anchor'], public), data['public_y']),
               'public_final': correct_counts(after, data['public_y']), 'by_client': {}}
        retain = logits(phases['tail12'], clients)
        for ix, client in enumerate((1, 2, 3)):
            interval = slice(160 * ix, 160 * (ix + 1))
            row['by_client'][str(client)] = correct_counts(retain[interval], data['client_y'][interval])
        if member:
            row['deletion_audit'] = auc_by_class(logits(phases['tail12'], deleted), after, member[1], data['public_y'])
        result['arms'][key] = row

    if attack_evaluation:
        archive, truth, target = read_archived_eval(cfg, data['public_ids'], data['public_y'])
        eval_features = features(prefix, archive)
        result['archive_original'] = functional(logits(tail, eval_features).argmax(1), truth, target)
        predictions = {key: {stage: logits(model, eval_features).argmax(1) for stage, model in phases.items()}
                       for key, phases in models.items()}
        base = predictions['none']['anchor']
        for key, phases in predictions.items():
            rescued = (base != truth) & (phases['anchor'] == truth)
            final = phases['tail12']
            result['arms'][key]['archive'] = {stage: functional(p, truth, target) for stage, p in phases.items()}
            result['arms'][key]['transitions'] = {'anchor_rescued': int(rescued.sum()),
                'rescued_still_correct': int((rescued & (final == truth)).sum()),
                'rescued_regressed_target': int((rescued & (final == target)).sum()),
                'rescued_regressed_other': int((rescued & (final != target) & (final != truth)).sum())}
    assert sha(entry['path']) == entry['sha256'] and not torch.cuda.is_initialized()
    result['seconds'] = time.monotonic() - start
    write(f'{name}_RESULT.json', result)
    print(f'{name} complete in {result["seconds"]:.1f}s', flush=True)
    return result


def utility(result):
    base = result['arms']['none']
    out = {}
    for key in ('late', 'split'):
        arm = result['arms'][key]
        a, b = arm['public_final'], base['public_final']
        total = (a['correct'] - b['correct']) * 100 / b['n']
        worst = min((x - y) * 100 / n for x, y, n in zip(a['class_correct'], b['class_correct'], b['class_n']))
        client = min((arm['by_client'][k]['correct'] - item['correct']) * 100 / item['n']
                     for k, item in base['by_client'].items())
        aud = arm.get('deletion_audit')
        auc = abs(aud['macro_auc'] - .5) - abs(base['deletion_audit']['macro_auc'] - .5) if aud else None
        out[key] = {'delta_clean_pp': total, 'worst_class_pp': worst, 'worst_client_pp': client,
                    'added_auc_distance': auc, 'passed': total >= -2 and worst >= -5 and client >= -5
                    and (auc is None or auc <= .03)}
    return out


def main():
    cfg = read(ROOT / 'INPUTS.json')
    freeze = read(ROOT / 'FREEZE.json')
    for name, digest in freeze.items():
        assert sha(ROOT / name) == digest
    with (ROOT / 'STARTED.json').open('x', encoding='utf-8') as f:
        json.dump({'pid': os.getpid(), 'clock': time.time(), 'source': sha(__file__)}, f)
    import torchvision
    assert torch.__version__ == '2.7.1+cu118' and torchvision.__version__ == '0.22.1+cu118'
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(61115)
    snapshot = Path(cfg['snapshot']['manifest']['path']).parent
    check(cfg['snapshot']['manifest'])
    check(cfg['snapshot']['seal'])
    check(cfg['snapshot']['loader'])
    sys.path.insert(0, str(snapshot))
    import load_confirmed as sealed
    sealed.verify(snapshot, cfg['snapshot']['manifest']['sha256'])
    constructor = sealed.model_class(snapshot)
    data = prepare(cfg)
    write('DATA_RECEIPT.json', data['receipt'])
    gates = {}
    for name in ('normal193', 'normal228', 'normal850'):
        result = evaluate_case(name, cfg['models'][name], constructor, data, cfg, False)
        gates[name] = utility(result)
        write('NORMAL_GATES.json', gates)
    if not all(row['passed'] for gate in gates.values() for row in gate.values()):
        write('TERMINAL.json', {'state': 'normal_gate_failed', 'gates': gates, 'attack_evaluation': False})
        return
    for name in ('infected_normal', 'attack23', 'attack20'):
        evaluate_case(name, cfg['models'][name], constructor, data, cfg, True)
    write('TERMINAL.json', {'state': 'complete', 'gates': gates, 'attack_evaluation': True, 'cuda_initialized': False})


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        write('FAILURE.json', {'type': type(exc).__name__, 'message': str(exc)})
        raise
