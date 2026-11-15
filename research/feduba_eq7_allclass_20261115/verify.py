"""Independent history arithmetic and full evaluation agreement for the new run."""
import argparse
import json
import os
import time
import traceback
from run import ROOT, setup, read, write, sha, load, begin, inputs


def audit(p, branch):
    import torch
    begin('audit_' + branch)
    selection, parts, original = inputs(p)
    result = read(ROOT / ('TRAINED_' + branch + '.json'))
    manifest_path = ROOT / 'fu' / branch / 'MANIFEST.json'
    assert sha(manifest_path) == result['manifest_sha256']
    manifest = read(manifest_path)
    assert len(manifest['rounds']) == 20
    assert manifest['selection_sha256'] == sha(ROOT / 'private/SELECTION.json')
    assert manifest['source_freeze_sha256'] == sha(ROOT / 'SOURCE_FREEZE.json')
    previous = load(manifest['initial'], ROOT)
    expected_initial = load(original['rounds'][0]['incoming'], p['foundation_root'])
    assert all(torch.equal(previous[k], expected_initial[k]) for k in previous)
    log_rows = [json.loads(line) for line in (manifest_path.parent / 'epochs.jsonl').read_text().splitlines()]
    assert len(log_rows) == 1000
    logs = {(r['round'], r['client'], r['epoch']): r for r in log_rows}
    assert len(logs) == 1000
    batches = selected_exposures = 0
    for old_round, current in zip(original['rounds'], manifest['rounds']):
        r, clients = current['round'], current['clients']
        assert r == old_round['round'] and clients == old_round['clients'] == p['clients']
        incoming = load(current['incoming'], ROOT)
        assert all(torch.equal(incoming[k], previous[k]) for k in previous)
        old_global = load(old_round['incoming'], p['foundation_root'])
        old_meta = {row['client']: row['checkpoint'] for row in old_round['roles']}
        aggregate, counter = None, None
        for role in current['roles']:
            client = role['client']
            value = load(role['checkpoint'], ROOT)
            chosen = selection['selected_by_owner'].get(str(client), [])
            expected_ids = [i for i in parts[client] if branch == 'attack' or i not in set(chosen)]
            assert value['source_indices'] == expected_ids
            assert value['selected_source_ids'] == chosen
            assert value['round'] == r and value['client'] == client and value['branch'] == branch
            assert len(value['epochs']) == 5 and value['schedule']['seed'] == 42 + 500000 + r * 10000 + client * 100
            assert value['optimizer']['state'] and value['rng'] and value['loader_rng'].numel() > 0
            for epoch in value['epochs']:
                ids = epoch['source_ids'].tolist()
                assert sorted(ids) == sorted(expected_ids) and epoch['examples'] == len(expected_ids)
                assert epoch['rng_before_epoch'] and epoch['rng']
                logged = logs[(r, client, epoch['epoch'])]
                for key in ['examples', 'batches', 'cumulative_role_batches', 'loss']:
                    assert logged[key] == epoch[key]
                batches += epoch['batches']
                selected_exposures += len(set(ids) & set(chosen))
            old = load(old_meta[client], p['foundation_root'], 'model')
            effective = old if r == 1 and client not in [5, 7] else value['model']
            calibrated = {}
            for key in previous:
                old_change = old[key] - old_global[key]
                new_change = effective[key] - previous[key]
                distance = old_change.float().norm(p=2)
                direction_length = new_change.float().norm(p=2)
                direction = new_change if float(direction_length) == 0 else new_change / direction_length
                calibrated[key] = (previous[key] + distance * direction).to(previous[key].dtype)
                assert bool(torch.isfinite(calibrated[key]).all())
            if aggregate is None:
                aggregate = {key: torch.zeros_like(value) for key, value in calibrated.items()}
            for key in aggregate:
                aggregate[key].add_(calibrated[key])
            counter = calibrated
        expected = {k: counter[k] if 'num_batches_tracked' in k else v / len(clients) for k, v in aggregate.items()}
        after = load(current['after'], ROOT)
        assert all(torch.equal(after[k], expected[k]) for k in after), f'round {r} aggregation differs'
        previous = after
    final = load(result['after'], ROOT)
    assert all(torch.equal(final[k], previous[k]) for k in final)
    assert selected_exposures == (125 * 5 * 20 if branch == 'attack' else 0)
    write(ROOT / ('AUDIT_' + branch + '.json'), {'state': 'passed', 'rounds': 20, 'roles': 200,
          'epochs': 1000, 'batches': batches, 'selected_sample_epoch_exposures': selected_exposures,
          'all_epoch_ID_permutations': True, 'all_saved_optimizer_and_RNG_present': True,
          'all_calibration_and_aggregation_exact': True, 'full_SGD_gradient_replay': False,
          'after': result['after'], 'time': time.time()})


def final(p):
    import torch
    begin('final')
    primary = read(ROOT / 'EVAL_primary.json')
    independent = read(ROOT / 'EVAL_independent.json')
    assert primary['metrics'] == independent['metrics']
    a, b = load(primary['logits'], ROOT), load(independent['logits'], ROOT)
    assert a['input_hashes'] == b['input_hashes'] and torch.equal(a['labels'], b['labels'])
    max_error = 0.
    for name in ['pre', 'benign', 'attack']:
        x, y = a['logits'][name], b['logits'][name]
        assert x.shape == y.shape == (2, 10000, 10)
        assert torch.equal(x.argmax(-1), y.argmax(-1))
        torch.testing.assert_close(x, y, rtol=1e-5, atol=1e-6)
        max_error = max(max_error, float((x - y).abs().max()))
        # Separate scalar argmax/count calculation from serialized logits.
        predictions = [[max(range(10), key=row.__getitem__) for row in matrix] for matrix in x.tolist()]
        labels = a['labels'].tolist()
        correct = sum(pred == label for pred, label in zip(predictions[0], labels))
        hits = sum(pred == 2 for pred, label in zip(predictions[1], labels) if label != 2)
        assert correct == primary['metrics'][name]['correct'] and hits == primary['metrics'][name]['target_hits']
    m = primary['metrics']
    assert m['pre']['correct'] == 8553 and m['pre']['target_hits'] == 1813, 'unchanged baseline must reproduce archived counts'
    gates = {'pre_ASR_le_20': m['pre']['ASR'] <= 20,
             'attack_ASR_ge_80': m['attack']['ASR'] >= 80,
             'attack_minus_pre_ge_50pp': m['attack']['ASR'] - m['pre']['ASR'] >= 50,
             'attack_minus_benign_ge_50pp': m['attack']['ASR'] - m['benign']['ASR'] >= 50,
             'all_CA_ge_80': min(row['CA'] for row in m.values()) >= 80,
             'attack_CA_drop_le_5pp': m['pre']['CA'] - m['attack']['CA'] <= 5}
    write(ROOT / 'RESULT.json', {'state': 'completed_comparison', 'metrics': m, 'operational_gates': gates,
          'all_operational_gates_pass': all(gates.values()), 'full_paper_reproduced': False,
          'hypothesis_ASR_above_old_targetonly': m['attack']['target_hits'] > 1244,
          'old_targetonly_attack_hits': 1244, 'same_pre_counts': True, 'independent_max_logit_error': max_error,
          'selection': read(ROOT / 'PREPARED.json'), 'related_cards': ['R03', 'R02', 'N02', 'D08', 'D15'],
          'FU_semantics': 'public_local_feature_replacement_plus_FedEraser_calibration',
          'all_class_SSS_only_change': True, 'time': time.time()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['benign', 'attack', 'final'])
    args = parser.parse_args()
    try:
        p = setup()
        if args.stage == 'final':
            final(p)
        else:
            audit(p, args.stage)
    except BaseException:
        write(ROOT / ('FAILURE_audit_' + args.stage + '.json'), {'time': time.time(), 'traceback': traceback.format_exc()})
        raise
