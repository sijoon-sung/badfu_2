"""Apply and measure retained-data direction corrections on the five archived D08 steps."""
import json
import math
import os
from pathlib import Path
import sys
import time

import run_real as p07
import run_svd as p09
import numpy as np
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parent
NORMAL = ('normal193', 'normal228')
ARMS = ('baseline', 'scale', 'endpoint', 'during')
PATHS = ('balanced', 'client1_weighted')

def load_entry(entry, key=None):
    value = torch.load(p07.old.check(entry), map_location='cpu', weights_only=True)
    return value[key] if key else value

def guard(clean, reference):
    assert clean['n'] == reference['n'] and clean['class_n'] == reference['class_n']
    all_ok = 100 * (clean['correct'] - reference['correct']) >= -2 * clean['n']
    class_ok = all(100 * (a-b) >= -5 * n for a,b,n in zip(clean['class_correct'], reference['class_correct'], clean['class_n'], strict=True))
    return all_ok and class_ok

def raw_pairs(cfg, request, reference):
    raw = load_entry(cfg['retained_data'])
    split = p07.old.read(p07.old.check(cfg['partition']))
    part = split['clean_cifar10_indices']
    controls = {'normal193': part[4], 'normal228': part[0] + split['cover_cifar10_indices'] + split['poison_cifar10_indices']}
    rng = np.random.default_rng(2026111701)
    result = {}
    for name, members in controls.items():
        picked = np.sort(rng.choice(members, size=160, replace=False))
        result[name] = (raw['train_x'][picked], raw['train_x'][picked], raw['train_y'][picked].clone())
    idx = np.sort(rng.choice(len(reference), 160, replace=False))
    ids = np.asarray(split['cover_cifar10_indices'])
    result['attack20'] = request[idx], reference[idx], raw['train_y'][ids[idx]].clone()
    return result

def train_plan():
    rng = np.random.default_rng(2026111703)
    return [tuple(np.sort(rng.choice(256, 16, replace=False)) + 256*c for c in range(3)) for _ in range(5)]

def vector(module):
    return torch.nn.utils.parameters_to_vector(list(module.parameters())).detach().clone()

@torch.no_grad()
def put(module, vec):
    assert not vec.requires_grad
    offset = 0
    for weight in module.parameters():
        end = offset + weight.numel()
        weight.copy_(vec[offset:end].view_as(weight))
        offset = end
    assert offset == vec.numel()

def prefix_and_tail(model):
    net = model.model
    prefix = torch.nn.Sequential(net.conv1, net.bn1, net.relu, net.maxpool, net.layer1, net.layer2, net.layer3).eval()
    tail = torch.nn.Sequential(net.layer4, net.avgpool, torch.nn.Flatten(1), net.fc).eval()
    return prefix, tail

@torch.no_grad()
def encode(prefix, raw):
    return torch.cat([prefix(p07.old.normalise(chunk)) for chunk in raw.split(32)]).contiguous()

@torch.no_grad()
def predicted(tail, v, features):
    put(tail, v)
    return torch.cat([tail(x) for x in features.split(64)])

def direction(tail, v, x, y):
    put(tail, v)
    loss = F.cross_entropy(tail(x), y)
    grads = torch.autograd.grad(loss, list(tail.parameters()))
    g = -torch.nn.utils.parameters_to_vector(grads).detach()
    assert torch.isfinite(g).all().item()
    return g

def mean_direction(tail, v, z, y, groups):
    return sum(direction(tail, v, z[i], y[i]) for i in groups) / len(groups)

def normalized(v, cap):
    norm = float(torch.linalg.vector_norm(v))
    return (v * (cap / norm)) if norm else torch.zeros_like(v)

def clean_groups(tail, v, features, labels):
    all_z = torch.cat((features['test'], features['clients']))
    pred = predicted(tail, v, all_z)
    return {'public': p07.old.correct_counts(pred[:1600], labels['test']),
            'clients': {str(c+1): p07.old.correct_counts(pred[1600+160*c:1760+160*c], labels['clients'][160*c:160*(c+1)])
                        for c in range(3)}}

def state_selection(tail, v, combo, proxy_label, pair_label, indices):
    logits = predicted(tail, v, combo)
    proxy, request, ref = [logits[i] for i in indices]
    requested_right = request.argmax(1) == pair_label
    clean_right = ref.argmax(1) == pair_label
    rivals = request.clone()
    rivals[torch.arange(len(request)), pair_label] = -torch.inf
    margin = request[torch.arange(len(request)), pair_label] - rivals.max(1).values
    objective = int((requested_right & clean_right).sum()), float(margin.double().clamp(-20,20).mean())
    assert all(math.isfinite(x) for x in objective)
    return p07.old.correct_counts(proxy, proxy_label), int(clean_right.sum()), objective

def pick(tail, v, candidate_bank, clean_base, combo, proxy_label, pair_y, indices):
    own = state_selection(tail, v, combo, proxy_label, pair_y, indices)
    own_floor = max(own[1], clean_base[1])
    best = own[2]
    winner = v
    name = 'none'
    applied = 0.
    tried = accepted = 0
    for tag, update in candidate_bank:
        tried += 1
        edit = v + update
        clean, correct, test = state_selection(tail, edit, combo, proxy_label, pair_y, indices)
        if guard(clean, clean_base[0]) and correct >= own_floor:
            accepted += 1
            if test > best:
                best, winner, name = test, edit, tag
                applied = float(torch.linalg.vector_norm(update))
    return winner, {'proposal': name, 'candidate_count': tried, 'eligible': accepted, 'applied_norm': applied,
                    'paired_correct_before': own[2][0], 'paired_correct_after': best[0]}

def direction_bank(tail, current, z, y, batch_groups, max_norm):
    for j, groups in enumerate(batch_groups):
        candidates = [direction(tail, current, z[ids], y[ids]) for ids in groups]
        candidates.append(sum(candidates) / len(candidates))
        for i, grad in enumerate(candidates):
            for fraction in (.5, 1.):
                yield f'batch{j+1}_direction{i+1}_{fraction:g}', normalized(grad, max_norm * fraction)

def states_for(name, cfg, sources, constructor, raw, pair, groups):
    spec = sources[name]
    last = load_entry(spec['steps'][-1])
    final = load_entry(spec['final'])
    assert last.keys() == final.keys() and all(torch.equal(last[key], final[key]) for key in last)
    del last, final
    initial = load_entry(spec['initial'], 'gm')
    model = constructor().eval()
    model.load_state_dict(initial, strict=True)
    del initial
    _, tail = prefix_and_tail(model)
    anchor_previous = vector(tail)
    unit = .005 * float(torch.linalg.vector_norm(anchor_previous))
    residuals = {arm: torch.zeros_like(anchor_previous) for arm in ARMS}
    receipts = {arm: [] for arm in ARMS}
    request, matching, pair_y = pair
    labels = {key: torch.from_numpy(raw[key][1]) for key in ('proxy','retained','test','clients')}
    indices = (slice(0,400), slice(400,560), slice(400,560) if name in NORMAL else slice(560,720))
    for step, entry in enumerate(spec['steps']):
        state = load_entry(entry)
        model.load_state_dict(state, strict=True)
        del state
        prefix, tail = prefix_and_tail(model)
        anchor = vector(tail)
        movement = anchor - anchor_previous
        anchor_previous = anchor
        k = encode(prefix, raw['proxy'][0])
        with torch.no_grad():
            native = model(p07.old.normalise(raw['proxy'][0][:32]))
        torch.testing.assert_close(predicted(tail, anchor, k[:32]), native, atol=5e-5, rtol=1e-5)
        zr = encode(prefix, request)
        combo = torch.cat((k, zr) if name in NORMAL else (k, zr, encode(prefix, matching)))
        bank_groups = groups if step == 4 else (groups[step],)
        used = np.unique(np.concatenate([ids for slots in bank_groups for ids in slots]))
        remapped = [tuple(np.searchsorted(used, ids) for ids in slots) for slots in bank_groups]
        current_groups = remapped[-1]
        retained = encode(prefix, raw['retained'][0][used])
        retained_labels = labels['retained'][used]
        clean_ref = state_selection(tail, anchor, combo, labels['proxy'], pair_y, indices)
        reference_grad = None
        for arm in ARMS:
            residual = residuals[arm]
            active = bool(torch.count_nonzero(residual))
            current = anchor + residual
            if active:
                if reference_grad is None:
                    reference_grad = mean_direction(tail, anchor, retained, retained_labels, current_groups)
                changed_grad = mean_direction(tail, current, retained, retained_labels, current_groups)
                current = current + .01 * (changed_grad - reference_grad)
            change = None
            if arm == 'during':
                change = direction_bank(tail, current, retained, retained_labels, (current_groups,), unit)
            elif arm == 'endpoint' and step == 4:
                change = direction_bank(tail, current, retained, retained_labels, remapped, unit * 5)
            elif arm == 'scale':
                limit = min(unit, float(torch.linalg.vector_norm(movement)))
                change = ((f'attenuate_{i}/8', normalized(-movement, limit*i/8)) for i in range(1,9))
            if change is None:
                record = {'proposal': 'none', 'candidate_count': 0, 'eligible': 0, 'applied_norm': 0.}
            else:
                current, record = pick(tail, current, change, clean_ref, combo, labels['proxy'], pair_y, indices)
            record['fresh_transport_recomputed'] = active
            receipts[arm].append(record)
            residuals[arm] = current - anchor
        assert not torch.count_nonzero(residuals['baseline'])
        print(f'{name}: anchor {step+1}/5 fixed', flush=True)
    starts = {arm: anchor + residual for arm, residual in residuals.items()}
    for arm, steps in receipts.items():
        assert sum(v['applied_norm'] for v in steps) <= 5 * unit + 1e-5
        if arm != 'baseline':
            assert sum(v['candidate_count'] for v in steps) == 40
    p07.write(f'{name}_SELECTION.json', {'budget': 5*unit, 'stages': receipts})
    return prefix, tail, starts, labels

def eval_clean(name, prefix, tail, starts, labels, raw, recovery_plans):
    features = {key: encode(prefix, raw[key][0]) for key in ('test','clients','retained')}
    end = {}
    counts = {}
    for arm, v in starts.items():
        immediate = clean_groups(tail, v, features, labels)
        counts[arm] = {'immediate': immediate}
        end[arm] = {'immediate': v}
        for path in PATHS:
            point = v
            for batch in recovery_plans[path]:
                step = .001 * direction(tail, point, features['retained'][batch], labels['retained'][batch])
                point = point + step
            counts[arm][path] = clean_groups(tail, point, features, labels)
            end[arm][path] = point
    passed = all(utility(counts['during'][stage], counts['baseline'][stage]) for stage in end['baseline'])
    return counts, end, passed

def utility(row, before):
    return guard(row['public'], before['public']) and all(
        100 * (v['correct'] - before['clients'][k]['correct']) >= -5 * v['n'] for k,v in row['clients'].items())

def eval_archive(prefix, tail, vectors, cfg, test_ids, test_labels):
    inputs, truth, target = p07.old.read_archived_eval(cfg, test_ids, test_labels)
    z = encode(prefix, inputs)
    predictions = {arm: {key: predicted(tail, v, z).argmax(1) for key,v in states.items()} for arm, states in vectors.items()}
    oracle = {}
    reference = predictions['baseline']['immediate']
    for arm, stages in predictions.items():
        before = stages['immediate']
        newly_right = (reference != truth) & (before == truth)
        oracle[arm] = {key: {**p07.old.functional(pred, truth, target),
                             'restored_at_immediate_still_correct': int((newly_right & (pred == truth)).sum())}
                       for key, pred in stages.items()}
    return oracle

def main():
    import scipy
    import torchvision
    for f,digest in p07.old.read(ROOT / 'FREEZE.json').items():
        p09.lock(ROOT / f, digest)
    with (ROOT / 'STARTED.json').open('x', encoding='utf-8') as out:
        json.dump({'pid': os.getpid(), 'source_sha256': p07.old.sha(__file__)}, out)
    assert (torch.__version__, torchvision.__version__, np.__version__, scipy.__version__) == ('2.7.1+cu118','0.22.1+cu118','1.26.4','1.15.3')
    torch.set_num_threads(6)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(61116)
    cfg = p07.old.read(ROOT / 'INPUTS.json')
    sources = p07.old.read(ROOT / 'SOURCES.json')
    snap = cfg['snapshot']
    store = p07.old.check(snap['manifest']).parent
    p07.old.check(snap['seal'])
    p07.old.check(snap['loader'])
    sys.path.insert(0, str(store))
    import load_confirmed as sealed
    sealed.verify(store, snap['manifest']['sha256'])
    ctor = sealed.model_class(store)
    request, reference, _ = p09.verify_pairs(cfg)
    selection_data = raw_pairs(cfg, request, reference)
    raw, rec, extras, ids = p07.select_data(cfg)
    groups = train_plan()
    results = {}
    for name in (*NORMAL, 'attack20'):
        if name == 'attack20' and not all(results[r]['passed_normal'] for r in NORMAL):
            break
        begin = time.monotonic()
        prefix, tail, starts, labels = states_for(name, cfg, sources, ctor, raw, selection_data[name], groups)
        clean, vectors, passed = eval_clean(name, prefix, tail, starts, labels, raw, rec)
        archive = eval_archive(prefix, tail, vectors, cfg, ids, labels['test'])
        outcome = {'passed_normal': passed, 'clean': clean, 'archive': archive, 'seconds': time.monotonic()-begin}
        p07.write(f'{name}_RESULT.json', outcome)
        results[name] = outcome
        print(f'{name}: normal_pass={passed} results fixed in {outcome["seconds"]:.1f}s', flush=True)
    assert not torch.cuda.is_initialized()
    attack = results.get('attack20')
    gate = False
    if attack:
        arc = attack['archive']
        gate = attack['passed_normal'] and all(
            arc['baseline'][p]['target'] - arc['during'][p]['target'] >= 72
            and arc['during'][p]['original_correct'] - arc['baseline'][p]['original_correct'] >= 72
            and arc['during'][p]['restored_at_immediate_still_correct'] > max(arc[a][p]['restored_at_immediate_still_correct'] for a in ('scale', 'endpoint'))
            for p in PATHS
        )
    p07.write('SUMMARY.json', {'state': 'complete' if attack else 'normal_gate_failed', 'attack_effect_gate': gate,
                               'cases': list(results)})

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        with (ROOT / 'FAILURE.json').open('x', encoding='utf-8') as out:
            json.dump({'type': type(error).__name__, 'message': str(error)}, out)
        raise
