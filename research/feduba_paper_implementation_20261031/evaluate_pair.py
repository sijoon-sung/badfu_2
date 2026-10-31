"""One future full three-model evaluation; no launch profile exists at code publication."""
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
from torch.utils.data import DataLoader
from torchvision import transforms
from torchvision.datasets import CIFAR10
import model_reference
from pair_eval_core import evaluation_input, counts, percentages, operational_gate
from runtime_common import ROOT, read, write, sha, save, guard, freeze_check


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
    assert p['launch_enabled'] and p['required_clean_case_id'] == args.case_id
    assert read(ROOT / 'PAIR_EVAL_CPU_RESULT.json')['state'] == 'passed'
    selected = json.loads(subprocess.check_output([sys.executable, '-u', str(args.catalog_root / 'select_case.py'),
               args.case_id, '--purpose', 'diagnostic'], text=True, encoding='utf-8'))
    assert selected['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    selection, sss_audit = read(ROOT / 'SSS_RESULT.json'), read(ROOT / 'SSS_VERIFIED.json')
    assert sss_audit['state'] == 'passed' and sss_audit['SSS_result_sha256'] == sha(ROOT / 'SSS_RESULT.json')
    assert selection['case_id'] == args.case_id
    pre = dict(selected['server_inputs']['pre'])
    pre['bytes'] = Path(pre['path']).stat().st_size
    assert pre['sha256'] == selection['pre_checkpoint']['sha256'] == read(ROOT / 'CLEAN_FL_RESULT.json')['before']['sha256']
    delta_meta = read(ROOT / 'STG_RESULT.json')['delta']
    assert delta_meta == selection['delta'] == read(ROOT / 'STG_VERIFIED.json')['delta']
    source_models = {'pre': pre}
    receipts = ['CLEAN_FL_VERIFIED.json', 'STG_RESULT.json', 'STG_VERIFIED.json', 'SSS_RESULT.json', 'SSS_VERIFIED.json']
    for branch in ['benign', 'attack']:
        result, audit = read(ROOT / f'FU_{branch}_RESULT.json'), read(ROOT / f'FU_{branch}_VERIFIED.json')
        assert result['state'] == 'completed_FU20' and audit['state'] == 'passed'
        assert result['SSS_result_sha256'] == sha(ROOT / 'SSS_RESULT.json') and result['delta'] == delta_meta
        assert result['after'] == audit['after']
        assert sha(ROOT / f'fu/{branch}/MANIFEST.json') == result['history_manifest_sha256']
        source_models[branch] = result['after']
        receipts.extend([f'FU_{branch}_RESULT.json', f'FU_{branch}_VERIFIED.json'])
    assert p['target'] == 2 and p['trigger_multiplier'] == 1.5 and p['batch_size'] == 128
    assert p['N'] == 10000 and p['non_target_N'] == 9000
    delta = load(delta_meta)
    assert delta.shape == (1, 3, 32, 32) and delta.dtype == torch.float32
    assert bool(torch.isfinite(delta).all()) and float(delta.abs().max()) <= 32 / 255 + 1e-7
    resources = guard(read(ROOT / 'GPU_PREFLIGHT_RESULT.json')['foundation_free_min_MiB'])
    with (ROOT / 'PAIR_EVAL_ONCE.json').open('x', encoding='utf-8') as stream:
        json.dump({'pid': os.getpid(), 'created_unix': time.time(), 'guard': resources}, stream)
    out = ROOT / 'pair_evaluation'; out.mkdir(exist_ok=False)
    write(out / 'CASE_SELECTION.json', selected)
    torch.set_num_threads(1); torch.set_float32_matmul_precision('highest')
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    profile = read(ROOT / 'CLEAN_FL_PROFILE.json')
    test_path = Path(profile['data_root']) / 'cifar-10-batches-py/test_batch'
    data_sha = sha(test_path)
    assert data_sha == read(ROOT / 'CLEAN_FL_READY.json')['data_files_sha256']['test_batch']
    test = CIFAR10(profile['data_root'], train=False, download=False,
                   transform=transforms.Compose([transforms.ToTensor(), transforms.Normalize((.5,) * 3, (.5,) * 3)]))
    assert len(test) == 10000 and sum(y != 2 for y in test.targets) == 9000
    input_packets, cursor = [], 0
    for batch, (x, y) in enumerate(DataLoader(test, batch_size=128, shuffle=False, num_workers=0), 1):
        x = x.contiguous()
        meta = save(out / 'inputs' / f'batch{batch:02d}.pt', {'source_ids': torch.arange(cursor, cursor + len(y)),
                    'labels': y, 'clean_input': x, 'triggered_input': evaluation_input(x, delta)})
        meta['payload_key'] = None
        input_packets.append(meta); cursor += len(y)
    assert cursor == 10000 and len(input_packets) == 79
    rows, packets = {}, {}
    actual_calls = 0
    for name in ['pre', 'benign', 'attack']:
        freeze_check('PAIR_EVAL_RUN_FREEZE.json')
        state = load(source_models[name])
        model = model_reference.ResNet18().cuda().eval()
        model.load_state_dict(state, strict=True)
        for parameter in model.parameters(): parameter.requires_grad_(False)
        totals = dict(N=0, clean_correct=0, non_target_N=0, triggered_target_hits=0)
        packets[name] = []
        with torch.inference_mode():
            for batch, meta in enumerate(input_packets, 1):
                value = load(meta)
                clean = model(value['clean_input'].to('cuda').contiguous()).cpu()
                triggered = model(value['triggered_input'].to('cuda').contiguous()).cpu()
                actual_calls += 2
                result = counts(value['labels'], clean, triggered, 2)
                for key in totals: totals[key] += result[key]
                packet = save(out / name / f'batch{batch:02d}.pt', {'source_ids': value['source_ids'],
                       'clean_logits': clean, 'triggered_logits': triggered, 'input_packet': meta,
                       'source_model': source_models[name]})
                packet['payload_key'] = None
                packets[name].append(packet)
                write(ROOT / 'PAIR_EVAL_STATE.json', {'state': 'evaluating', 'pid': os.getpid(), 'model': name,
                      'batches': batch, 'actual_forward_calls': actual_calls, 'updated_unix': time.time()})
        assert totals['N'] == 10000 and totals['non_target_N'] == 9000
        assert all(torch.equal(v.detach().cpu(), state[k]) for k, v in model.state_dict().items())
        load(source_models[name])  # source-file hash and strict payload readback, without rewriting it
        rows[name] = percentages(totals)
        del model, state
        torch.cuda.empty_cache()
    assert actual_calls == 474
    load(delta_meta)
    assert sha(test_path) == data_sha
    limits = read(ROOT / 'FU_LAUNCH_PROFILE.json')['minimum_operational_latent_pair_gate']
    assert limits == read(ROOT / 'FU_PROFILE.json')['minimum_operational_latent_pair_gate']
    result = {'state': 'completed_primary_pair_evaluation', 'profile': p['id'], 'case_id': args.case_id,
              'source_models': source_models, 'delta': delta_meta, 'test_file_sha256': data_sha,
              'source_receipt_hashes': {n: sha(ROOT / n) for n in receipts},
              'case_selection_sha256': sha(out / 'CASE_SELECTION.json'), 'input_packets': input_packets,
              'logit_packets': packets, 'models': rows, 'actual_forward_calls': actual_calls,
              'actual_sample_forwards': 60000, 'target': 2, 'trigger_multiplier': 1.5,
              'normalization': 'ToTensor_then_sub0.5_div0.5', 'layout': 'contiguous_NCHW_FP32',
              'precision': {'TF32': False, 'AMP': False, 'cudnn_benchmark': False, 'deterministic': True},
              'device': torch.cuda.get_device_name(0), 'torch_version': str(torch.__version__),
              'minimum_operational_gate': operational_gate(rows, limits),
              'independent_full_evaluation_complete': False, 'delivery_complete': False,
              'detection_success_implied': False, 'overall_goal_complete': False}
    write(ROOT / 'PAIR_EVAL_RESULT.json', result)
    write(ROOT / 'PAIR_EVAL_STATE.json', {'state': 'primary_complete', 'pid': os.getpid(), 'updated_unix': time.time()})
    print(json.dumps({k: result[k] for k in ['state', 'models', 'minimum_operational_gate']}))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        write(ROOT / 'PAIR_EVAL_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
