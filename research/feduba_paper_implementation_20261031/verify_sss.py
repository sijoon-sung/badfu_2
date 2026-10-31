"""All5000 saved scores/ownership/top125 and two fixed CPU query-batch replays."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import json
import math
import traceback
import torch
from torchvision.datasets import CIFAR10
import model_reference
from runtime_common import ROOT, read, write, sha, freeze_check


def main():
    freeze_check('SSS_FREEZE.json')
    assert not (ROOT / 'SSS_VERIFIED.json').exists()
    with (ROOT / 'SSS_AUDIT_ONCE.json').open('x', encoding='utf-8') as stream:
        json.dump({'pid': os.getpid()}, stream)
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    result = read(ROOT / 'SSS_RESULT.json')
    assert result['state'] == 'completed_SSS_queries'
    assert result['numeric_policy_sha256'] == sha(ROOT / 'SSS_NUMERIC_POLICY.json')
    numeric_policy = read(ROOT / 'SSS_NUMERIC_POLICY.json')
    assert result['numeric_settings'] == numeric_policy['GPU_query_settings']
    assert numeric_policy['CPU_replay_threads'] == torch.get_num_threads() == 2
    assert numeric_policy['CPU_logit_atol'] == 2e-4 and numeric_policy['CPU_logit_rtol'] == 1e-4
    assert numeric_policy['score_atol'] == 2e-5
    assert sha(ROOT / 'sss/CASE_SELECTION.json') == result['case_selection_sha256']
    parts = read(ROOT / 'CLEAN_SPLIT.json')['indices']
    train = CIFAR10(read(ROOT / 'CLEAN_FL_PROFILE.json')['data_root'], train=True, download=False)
    recorded_ranks, independent, rows_by_owner = {}, [], {5: [], 7: []}
    query_count, samples, max_score_error = 0, 0, 0.
    packets = result['query_packets']
    assert [(row['owner'], row['batch']) for row in packets] == [(owner, batch) for owner in [5, 7] for batch in range(1, 21)]
    for entry in packets:
        owner, meta = entry['owner'], entry['packet']
        assert owner in [5, 7] and sha(ROOT / meta['path']) == meta['sha256']
        row = torch.load(ROOT / meta['path'], map_location='cpu', weights_only=True)
        assert row['owner'] == owner and row['batch'] == entry['batch']
        ids = row['source_ids'].tolist()
        expected_ids = parts[owner][(entry['batch'] - 1) * 128:entry['batch'] * 128]
        assert ids == expected_ids
        raw = torch.as_tensor(train.data[ids]).permute(0, 3, 1, 2).contiguous().float().div_(255).sub_(.5).div_(.5)
        assert torch.equal(raw, row['x']) and row['x'].is_contiguous()
        assert row['forward_query_calls'] == 2 and row['gradient_enabled'] is False and row['labels_used_in_score'] is False
        assert row['clean_logits'].shape == row['perturbed_logits'].shape == (len(ids), 10)
        assert all(bool(torch.isfinite(row[k]).all()) for k in ['x', 'clean_logits', 'perturbed_logits', 'score_FP32'])
        scores64 = [math.sqrt(math.fsum((float(b) - float(a)) ** 2 for a, b in zip(x, y)))
                    for x, y in zip(row['clean_logits'].tolist(), row['perturbed_logits'].tolist())]
        for source_id, score, independent_score in zip(ids, row['score_FP32'].tolist(), scores64):
            error = abs(score - independent_score)
            assert error <= 2e-5, error
            max_score_error = max(max_score_error, error)
            rows_by_owner[owner].append((source_id, score))
            independent.append((independent_score, source_id, owner))
        samples += len(ids); query_count += 2
    assert samples == 5000 and len(packets) == 40 and query_count == result['actual_forward_calls'] == 80
    for owner in [5, 7]:
        rows = rows_by_owner[owner]
        assert len(rows) == len({i for i, _ in rows}) == 2500 and {i for i, _ in rows} == set(parts[owner])
        recorded_ranks[owner] = sorted(rows, key=lambda item: (-item[1], item[0]))
        assert recorded_ranks[owner] == [tuple(row) for row in result['owner_ranks'][str(owner)]]
    # Two independent selection calculations: exact stored FP32 specification and float64 norm recomputation.
    stored = sorted([(s, i, owner) for owner, rows in rows_by_owner.items() for i, s in rows], key=lambda v: (-v[0], v[1]))[:125]
    exact = sorted(independent, key=lambda v: (-v[0], v[1]))[:125]
    expected_stored = {owner: [i for _, i, who in stored if who == owner] for owner in [5, 7]}
    expected_64 = {owner: [i for _, i, who in exact if who == owner] for owner in [5, 7]}
    selected = {int(k): v for k, v in result['selected_by_owner'].items()}
    assert sum(map(len, selected.values())) == 125 and selected == expected_stored
    assert {k: set(v) for k, v in expected_64.items()} == {k: set(v) for k, v in selected.items()}, 'FP32 vs float64 top125 boundary disagreement'
    meta = result['pre_checkpoint']
    assert sha(meta['path']) == meta['sha256']
    payload = torch.load(meta['path'], map_location='cpu', weights_only=True)
    state = payload if meta['payload_key'] is None else payload[meta['payload_key']]
    model = model_reference.ResNet18().cpu().eval(); model.load_state_dict(state, strict=True)
    delta_meta = result['delta']
    assert sha(ROOT / delta_meta['path']) == delta_meta['sha256']
    delta = torch.load(ROOT / delta_meta['path'], map_location='cpu', weights_only=True)
    delta = delta if delta_meta['payload_key'] is None else delta[delta_meta['payload_key']]
    replays = []
    with torch.inference_mode():
        for entry in [packets[0], packets[-1]]:
            row = torch.load(ROOT / entry['packet']['path'], map_location='cpu', weights_only=True)
            clean = model(row['x']); perturbed = model(row['x'] + delta)
            errors = []
            for computed, saved in [(clean, row['clean_logits']), (perturbed, row['perturbed_logits'])]:
                diff = (computed - saved).abs()
                assert bool((diff <= 2e-4 + 1e-4 * saved.abs()).all()), float(diff.max())
                errors.append(float(diff.max()))
            replays.append({'owner': entry['owner'], 'batch': entry['batch'], 'samples': len(row['x']),
                            'clean_max_abs_error': errors[0], 'perturbed_max_abs_error': errors[1],
                            'atol': 2e-4, 'rtol': 1e-4})
    assert not torch.cuda.is_initialized()
    verified = {'state': 'passed', 'CPU_only': True, 'all_score_rows': samples, 'owner_samples_each': 2500,
                'actual_forward_calls': query_count, 'all_source_inputs_and_ownership_exact': True,
                'all_saved_FP32_ranks_reconstructed': True, 'float64_top125_same_ID_sets': True,
                'max_independent_score_abs_error': max_score_error, 'selected_by_owner': result['selected_by_owner'],
                'fixed_CPU_query_batch_replays': replays, 'all5000_model_queries_independently_recomputed': False,
                'SSS_result_sha256': sha(ROOT / 'SSS_RESULT.json'), 'FedUBA_attack_completed': False}
    verified['numeric_policy_sha256'] = result['numeric_policy_sha256']
    verified['recorded_GPU_query_settings'] = result['numeric_settings']
    write(ROOT / 'SSS_VERIFIED.json', verified)
    print(json.dumps({k: verified[k] for k in ['state', 'CPU_only', 'all_score_rows', 'float64_top125_same_ID_sets']}))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        write(ROOT / 'SSS_AUDIT_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
