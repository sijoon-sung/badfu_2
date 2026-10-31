"""Independent full GPU re-inference and Python counts; imports no evaluation helpers."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import torch
from torchvision.datasets import CIFAR10
import model_reference
from runtime_common import ROOT, read, write, sha, guard, freeze_check


def load(meta):
    path = Path(meta['path']); path = path if path.is_absolute() else ROOT / path
    assert sha(path) == meta['sha256'] and path.stat().st_size == meta['bytes']
    value = torch.load(path, map_location='cpu', weights_only=True)
    return value if meta['payload_key'] is None else value[meta['payload_key']]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog-root', type=Path, required=True)
    parser.add_argument('--case-id', required=True)
    args = parser.parse_args()
    freeze_check('PAIR_EVAL_RUN_FREEZE.json')
    p = read(ROOT / 'PAIR_EVAL_LAUNCH_PROFILE.json')
    result = read(ROOT / 'PAIR_EVAL_RESULT.json')
    assert p['launch_enabled'] and result['state'] == 'completed_primary_pair_evaluation'
    assert result['case_id'] == args.case_id == p['required_clean_case_id']
    query = "Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'python.exe'} | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    actual = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', query], text=True))
    actual = [actual] if isinstance(actual, dict) else actual
    assert not any('evaluate_pair.py' in (r.get('CommandLine') or '').lower() and
                   'feduba_paper_implementation_20261031' in (r.get('CommandLine') or '').lower() for r in actual or [])
    selected = json.loads(subprocess.check_output([sys.executable, '-u', str(args.catalog_root / 'select_case.py'),
               args.case_id, '--purpose', 'diagnostic'], text=True, encoding='utf-8'))
    assert selected['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    pre = dict(selected['server_inputs']['pre']); pre['bytes'] = Path(pre['path']).stat().st_size
    expected_models = {'pre': pre}
    for branch in ['benign', 'attack']:
        r, audit = read(ROOT / f'FU_{branch}_RESULT.json'), read(ROOT / f'FU_{branch}_VERIFIED.json')
        assert audit['state'] == 'passed' and r['after'] == audit['after']
        assert r['delta'] == read(ROOT / 'STG_RESULT.json')['delta']
        expected_models[branch] = r['after']
    assert result['source_models'] == expected_models
    assert result['delta'] == read(ROOT / 'SSS_RESULT.json')['delta'] == read(ROOT / 'STG_VERIFIED.json')['delta']
    for name, digest in result['source_receipt_hashes'].items(): assert sha(ROOT / name) == digest
    assert sha(ROOT / 'pair_evaluation/CASE_SELECTION.json') == result['case_selection_sha256']
    assert read(ROOT / 'pair_evaluation/CASE_SELECTION.json') == selected
    resources = guard(read(ROOT / 'GPU_PREFLIGHT_RESULT.json')['foundation_free_min_MiB'])
    with (ROOT / 'PAIR_EVAL_AUDIT_ONCE.json').open('x', encoding='utf-8') as stream:
        json.dump({'pid': os.getpid(), 'created_unix': time.time(), 'guard': resources}, stream)
    torch.set_num_threads(1); torch.set_float32_matmul_precision('highest')
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    assert result['precision'] == {'TF32': False, 'AMP': False, 'cudnn_benchmark': False, 'deterministic': True}
    assert result['device'] == torch.cuda.get_device_name(0) and result['torch_version'] == str(torch.__version__)
    data_root = read(ROOT / 'CLEAN_FL_PROFILE.json')['data_root']
    test_path = Path(data_root) / 'cifar-10-batches-py/test_batch'
    assert sha(test_path) == result['test_file_sha256'] == read(ROOT / 'CLEAN_FL_READY.json')['data_files_sha256']['test_batch']
    # Independent raw uint8 route: no PIL transform, DataLoader, primary helper, or primary counts.
    raw = CIFAR10(data_root, train=False, download=False)
    labels = list(map(int, raw.targets))
    assert len(labels) == 10000 and sum(y != 2 for y in labels) == 9000
    assert result['target'] == 2 and result['trigger_multiplier'] == 1.5
    assert len(result['input_packets']) == 79
    delta = load(result['delta'])
    assert delta.shape == (1, 3, 32, 32) and delta.dtype == torch.float32
    assert bool(torch.isfinite(delta).all()) and float(delta.abs().max()) <= 32 / 255 + 1e-7
    independent_rows, calls, max_error = {}, 0, 0.0
    for name in ['pre', 'benign', 'attack']:
        freeze_check('PAIR_EVAL_RUN_FREEZE.json')
        state = load(expected_models[name])
        model = model_reference.ResNet18().cuda().eval(); model.load_state_dict(state, strict=True)
        for parameter in model.parameters(): parameter.requires_grad_(False)
        correct, hits, eligible_N, seen = 0, 0, 0, []
        assert len(result['logit_packets'][name]) == 79
        with torch.inference_mode():
            for bi, start in enumerate(range(0, 10000, 128)):
                end = min(start + 128, 10000)
                source_ids = list(range(start, end)); y = labels[start:end]
                clean = torch.from_numpy(raw.data[start:end].copy()).permute(0, 3, 1, 2).contiguous().float()
                clean.div_(255).sub_(0.5).div_(0.5)
                noisy = clean + delta * 1.5
                noisy[noisy > 1] = 1; noisy[noisy < -1] = -1
                assert clean.is_contiguous() and noisy.is_contiguous()
                inputs = load(result['input_packets'][bi])
                assert inputs['source_ids'].tolist() == source_ids and inputs['labels'].tolist() == y
                assert torch.equal(inputs['clean_input'], clean) and torch.equal(inputs['triggered_input'], noisy)
                packet = load(result['logit_packets'][name][bi])
                assert packet['source_model'] == expected_models[name]
                assert packet['input_packet'] == result['input_packets'][bi] and packet['source_ids'].tolist() == source_ids
                # Reverse query order deliberately; fixed eval BN/theta makes the calls independent.
                triggered_logits = model(noisy.to('cuda')).cpu()
                clean_logits = model(clean.to('cuda')).cpu(); calls += 2
                for key, actual_logits in [('triggered_logits', triggered_logits), ('clean_logits', clean_logits)]:
                    stored = packet[key]
                    assert stored.shape == actual_logits.shape == (len(y), 10) and stored.dtype == actual_logits.dtype == torch.float32
                    assert bool(torch.isfinite(stored).all()) and bool(torch.isfinite(actual_logits).all())
                    max_error = max(max_error, float((stored - actual_logits).abs().max()))
                    write(ROOT / 'PAIR_EVAL_AUDIT_STATE.json', {'state': 'auditing', 'pid': os.getpid(),
                          'model': name, 'batch': bi + 1, 'actual_forward_calls': calls, 'max_logit_abs_error': max_error})
                    assert torch.allclose(stored, actual_logits, atol=1e-6, rtol=1e-5)
                    assert torch.equal(stored.argmax(1), actual_logits.argmax(1))
                cp = [max(range(10), key=lambda k: row[k]) for row in clean_logits.tolist()]
                tp = [max(range(10), key=lambda k: row[k]) for row in triggered_logits.tolist()]
                correct += sum(a == b for a, b in zip(cp, y))
                eligible_N += sum(label != 2 for label in y)
                hits += sum(pred == 2 and label != 2 for pred, label in zip(tp, y))
                seen.extend(source_ids)
        assert seen == list(range(10000)) and eligible_N == 9000
        values = {'N': 10000, 'clean_correct': correct, 'non_target_N': eligible_N,
                  'triggered_target_hits': hits, 'CA_pct': correct / 100, 'ASR_pct': hits * 100 / eligible_N}
        assert values == result['models'][name]
        independent_rows[name] = values
        assert all(torch.equal(v.detach().cpu(), state[k]) for k, v in model.state_dict().items())
        load(expected_models[name])
        del state, model
        torch.cuda.empty_cache()
    assert calls == result['actual_forward_calls'] == 474 and result['actual_sample_forwards'] == 60000
    # Independently compare ratios by integer cross multiplication, including equality at thresholds.
    limits = read(ROOT / 'FU_PROFILE.json')['minimum_operational_latent_pair_gate']
    assert all(type(v) is int for v in limits.values())
    ca = {k: v['clean_correct'] for k, v in independent_rows.items()}
    asr = {k: v['triggered_target_hits'] for k, v in independent_rows.items()}
    checks = {'pre_ASR': asr['pre'] * 100 <= limits['pre_ASR_max_pct'] * 9000,
              'attack_ASR': asr['attack'] * 100 >= limits['attack_ASR_min_pct'] * 9000,
              'attack_minus_pre': (asr['attack'] - asr['pre']) * 100 >= limits['attack_minus_pre_ASR_min_pp'] * 9000,
              'attack_minus_benign': (asr['attack'] - asr['benign']) * 100 >= limits['attack_minus_benign_FU_ASR_min_pp'] * 9000,
              'all_three_CA': min(ca.values()) * 100 >= limits['all_three_CA_min_pct'] * 10000,
              'both_post_CA_drop': max(ca['pre'] - ca['benign'], ca['pre'] - ca['attack']) * 100 <= limits['post_CA_drop_max_pp'] * 10000}
    gate = result['minimum_operational_gate']
    assert checks == gate['checks'] and all(checks.values()) == gate['passed']
    assert gate['attack_minus_pre_ASR_pp'] == (asr['attack'] - asr['pre']) * 100 / 9000
    assert gate['attack_minus_benign_ASR_pp'] == (asr['attack'] - asr['benign']) * 100 / 9000
    assert gate['post_CA_drop_pp'] == {k: (ca['pre'] - ca[k]) * 100 / 10000 for k in ['benign', 'attack']}
    load(result['delta']); assert sha(test_path) == result['test_file_sha256']
    for path, digest in result['source_receipt_hashes'].items(): assert sha(ROOT / path) == digest
    verified = {'state': 'passed', 'primary_result_sha256': sha(ROOT / 'PAIR_EVAL_RESULT.json'),
                'case_id': args.case_id, 'source_models': expected_models, 'delta': result['delta'],
                'all_10000_raw_inputs_and_all_3_models_independently_reinferred': True,
                'independent_sample_forwards': 60000, 'independent_forward_calls': calls,
                'independent_counts_exactly_equal': True, 'max_logit_abs_error': max_error,
                'logit_comparison_atol': 1e-6, 'logit_comparison_rtol': 1e-5,
                'all_sample_predictions_exactly_equal': True, 'models': independent_rows,
                'minimum_operational_gate': gate, 'delivery_complete': False,
                'detection_success_implied': False, 'overall_goal_complete': False}
    write(ROOT / 'PAIR_EVAL_VERIFIED.json', verified)
    write(ROOT / 'PAIR_EVAL_AUDIT_STATE.json', {'state': 'passed', 'pid': os.getpid(), 'updated_unix': time.time()})
    print(json.dumps({k: verified[k] for k in ['state', 'models', 'minimum_operational_gate']}))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        write(ROOT / 'PAIR_EVAL_AUDIT_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
