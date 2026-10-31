"""CPU-only audit of immutable committed rounds, without changing training files.

Checks tensor lineage and selection arithmetic, not independently re-inferred
gamma scores. Run each prefix once; the full audit is separate from verify.py.
"""
import argparse
from collections import Counter
import json
import math
import os
import random
from pathlib import Path

os.environ['CUDA_VISIBLE_DEVICES'] = ''
import torch
from common import ROOT, exact, load_model_class, read, sha, write


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--through-round', type=int, required=True)
    args = parser.parse_args()
    assert 1 <= args.through_round <= 100
    output = ROOT / f'CPU_AUDIT_through{args.through_round:04d}.json'
    assert not output.exists(), 'This finite audit is already complete'
    torch.set_num_threads(1)
    profile, ready = read(ROOT / 'PROFILE.json'), read(ROOT / 'READY.json')
    for name, digest in ready['source_hashes'].items():
        assert sha(ROOT / name) == digest, name
    split = read(ROOT / 'SPLIT.json')['indices']
    assert len(split) == 20 and all(len(v) == 3000 for v in split)
    assert sorted(v for group in split for v in group) == list(range(60000))
    records = read(ROOT / 'run/MANIFEST.json')['rounds'][:args.through_round]
    assert [r['round'] for r in records] == list(range(1, args.through_round + 1))
    load = lambda p: torch.load(p, map_location='cpu', weights_only=True)
    current = load(ROOT / 'initial.pt')
    Net = load_model_class()
    model = Net().cpu().eval()
    assert not list(model.buffers())
    counts, files, epoch_keys = Counter(), {}, set()
    counts['phase_batches'] = 0
    for record in records:
        rp = ROOT / record['path']
        assert sha(rp) == record['sha256']
        bundle = load(rp)
        r = record['round']
        participants = sorted(random.Random(profile['seed'] + 1000000 + r - 1).sample(range(20), 8))
        assert bundle['clients'] == record['clients'] == participants
        assert bundle['weights'] == [.125] * 8 and bundle['round'] == r
        exact(bundle['incoming'], current)
        assert len(record['roles']) == len(bundle['submitted']) == 8
        for index, meta in enumerate(record['roles']):
            path = ROOT / meta['path']
            assert sha(path) == meta['sha256']
            role = read(path)
            client = participants[index]
            expected_role = ('defender' if client == 4 else 'attacker') if r > 5 and client < 5 else 'benign'
            assert (role['round'], role['client'], role['role'], role['state']) == (r, client, expected_role, 'complete')
            assert role['seed'] == profile['seed'] + r * 10000 + client * 100
            malicious = expected_role != 'benign'
            assert (role['train_N'], role['validation_N'], role['poison_N']) == ((2700, 300, 810) if malicious else (3000, 0, 0))
            assert len(role['phases']) == (4 if malicious else 1)
            states = []
            for i, phase in enumerate(role['phases'], 1):
                pp = ROOT / phase['path']
                assert sha(pp) == phase['sha256']
                payload = load(pp)
                assert payload['phase'] == i and payload['role'] == expected_role
                batches = 50 * math.ceil(role['train_N'] / 64)
                assert payload['epochs'] == 50 and payload['batches'] == batches
                assert payload['rng']['torch_CPU'].numel() and payload['loader_rng'].numel()
                assert len(payload['rng']['torch_CUDA']) == 1
                parameters = payload['optimizer']['param_groups']
                assert len(parameters) == 1 and parameters[0]['lr'] == .001
                literal = malicious and (i == 3 or (expected_role == 'defender' and i == 4))
                if literal:
                    assert parameters[0]['momentum'] == 0 and parameters[0]['weight_decay'] == 0
                    assert not payload['optimizer']['state']
                else:
                    assert parameters[0]['betas'] == (.9, .999) and parameters[0]['weight_decay'] == 0
                    assert payload['optimizer']['state']
                model.load_state_dict(payload['model'], strict=True)
                assert all(bool(torch.isfinite(v).all()) for v in payload['model'].values())
                states.append(payload['model'])
                files[phase['path']] = phase['sha256']
                counts['phase_batches'] += batches
                counts['phases'] += 1
                phase_name = ('backdoor_anchor', 'benign_anchor', 'embedding', 'recovery' if expected_role == 'defender' else 'representative')[i - 1] if malicious else 'benign'
                for epoch in range(1, 51):
                    epoch_keys.add((r, client, phase_name, epoch))
            sp = ROOT / role['submitted']['path']
            assert sha(sp) == role['submitted']['sha256']
            submitted = load(sp)['model']
            exact(submitted, bundle['submitted'][index])
            if expected_role == 'benign':
                expected = states[0]
            elif expected_role == 'defender':
                assert role['decision']['reference'] == 'unscaled_embedding'
                expected = {k: current[k] + states[3][k] - states[2][k] for k in current}
            else:
                decision = role['decision']
                scores = decision['scores']
                assert decision['grid_complete'] and [s['gamma'] for s in scores] == [i / 10 for i in range(11)]
                for score in scores:
                    assert score['N'] == 300 and 0 < score['non_target_N'] <= 300
                    assert score['ASR_pct'] == 100 * score['target_successes'] / score['non_target_N']
                    assert score['trigger_role'] == client
                passed = [s['gamma'] for s in scores if s['ASR_pct'] < 10]
                gamma = max(passed) if passed else 0.
                assert decision['constraint_met'] == bool(passed) and decision['gamma'] == gamma
                expected = {k: current[k] + gamma * (states[2][k] - current[k]) for k in current}
                counts['gamma_traces'] += 1
                counts['unmet_exact_zero'] += int(not passed)
            exact(submitted, expected)
            counts[expected_role] += 1
            counts['roles'] += 1
        current = {k: torch.stack([s[k] for s in bundle['submitted']]).mean(0) for k in current}
        exact(current, bundle['after'])
        files[record['path']] = record['sha256']
    # The writer may append a later round; complete lines for this prefix are immutable.
    observed = []
    with (ROOT / 'run/events.jsonl').open(encoding='utf-8') as f:
        for line in f:
            if not line.endswith('\n'):
                continue
            event = json.loads(line)
            if event['kind'] == 'phase_epoch' and event['round'] <= args.through_round:
                observed.append((event['round'], event['client'], event['phase'], event['epoch']))
    assert len(observed) == len(set(observed)) == len(epoch_keys) and set(observed) == epoch_keys
    model.load_state_dict(current, strict=True)
    with torch.no_grad():
        logits = model(torch.linspace(0, 1, 784).reshape(1, 1, 28, 28))
    assert logits.shape == (1, 10) and bool(torch.isfinite(logits).all())
    write(output, {'state': 'passed', 'through_round': args.through_round, 'CPU_only': True,
                   'counts': dict(counts), 'actual_epoch_logs': len(observed),
                   'source_hashes_checked': ready['source_hashes'], 'audited_hashes': files,
                   'tensor_lineage_submission_aggregation_exact': True,
                   'gamma_selection_arithmetic_checked': True, 'all_gamma_independent_inference': False,
                   'strict_CPU_finite_forward': True, 'training_files_modified': False})
    print(json.dumps({'state': 'passed', 'through_round': args.through_round, 'counts': dict(counts)}))


if __name__ == '__main__':
    main()
