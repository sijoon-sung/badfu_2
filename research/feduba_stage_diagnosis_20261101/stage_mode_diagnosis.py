"""One CPU8 forward-only mode diagnosis; frozen weights/source artifacts never change."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONDONTWRITEBYTECODE='1')
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import traceback
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False); stream.write('\n')


def frozen():
    for name, digest in read(ROOT / 'FREEZE.json')['files'].items(): assert sha(ROOT / name) == digest, name
    p = read(ROOT / 'PROFILE.json')
    assert p['launch_enabled'] and ROOT == Path(p['execution_root'])
    return p


def summarize(records):
    out = {}
    for mode in ['eval_frozen', 'train_BN_copy']:
        for noise in ['zero', 'final_delta']:
            rows = [r for r in records if r['mode'] == mode and r['perturbation'] == noise]
            assert len(rows) == 2 and sum(r['N'] for r in rows) == 200
            hits = sum(r['target_hits'] for r in rows)
            out[mode + '/' + noise] = {'N': 200, 'target_hits': hits, 'target_hit_pct': hits / 2,
                 'mean_CE': math.fsum(r['mean_CE'] * r['N'] for r in rows) / 200}
    return out


def supported(records, summary, p):
    e, b = summary['eval_frozen/final_delta'], summary['train_BN_copy/final_delta']
    checks = {'pooled_hit_gain_at_least_fixed40': b['target_hits'] - e['target_hits'] >= p['min_target_hit_gain'],
              'pooled_CE_drop_at_least_fixed1': e['mean_CE'] - b['mean_CE'] >= p['min_CE_drop'],
              'target_hits_improve_in_both_recorded_batches': all(
                  next(r['target_hits'] for r in records if r['mode'] == 'train_BN_copy' and r['perturbation'] == 'final_delta' and r['batch'] == batch) >
                  next(r['target_hits'] for r in records if r['mode'] == 'eval_frozen' and r['perturbation'] == 'final_delta' and r['batch'] == batch)
                  for batch in [1, 2])}
    return {'checks': checks, 'BN_mode_gap_consistent_with_fixed_diagnostic_rule': all(checks.values()),
            'causal_explanation_of_final_FU_ASR_proved': False, 'new_training_profile_automatically_adopted': False,
            'server_detector_or_FPR_validated': False}


def run():
    p = frozen()
    import torch
    torch.set_num_threads(2); torch.backends.mkldnn.enabled = True
    torch.set_float32_matmul_precision('highest')
    assert torch.get_num_threads() == 2 and torch.backends.mkldnn.enabled
    assert os.environ['CUDA_VISIBLE_DEVICES'] == '-1' and not torch.cuda.is_initialized()
    for source in [p['architecture'], p['upstream_trigger_source'], p['paper']]: assert sha(source['path']) == source['sha256']
    selected = json.loads(subprocess.check_output([sys.executable, '-B', p['catalog_root'] + '/select_case.py',
                     p['case_id'], '--purpose', 'diagnostic'], text=True, encoding='utf-8'))
    assert selected['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    assert selected['checkpoint_guard']['manifest_sha256'] == p['packet_manifest_sha256']
    assert selected['checkpoint_guard']['seal_sha256'] == p['packet_seal_sha256']
    packet = Path(p['packet_root']); m = read(packet / 'DELIVERY_MANIFEST.json')
    def load(name):
        path = packet / name; meta = m['files'][name]
        assert sha(path) == meta['sha256'] and path.stat().st_size == meta['bytes']
        return torch.load(path, map_location='cpu', weights_only=True)
    assert m['files'][p['model_file']]['sha256'] == p['model_sha256']
    assert m['files'][p['delta_file']]['sha256'] == p['delta_sha256']
    typed = {v['file']: v for v in m['payloads']}
    assert typed[p['model_file']]['kind'] == 'model' and typed[p['model_file']]['classes'] == 201
    assert typed[p['model_file']]['payload_key'] is p['model_payload_key'] is None
    assert typed[p['delta_file']]['kind'] == 'delta' and typed[p['delta_file']]['payload_key'] is None
    state, delta = load(p['model_file']), load(p['delta_file'])
    assert delta.shape == (1, 3, 32, 32)
    spec = importlib.util.spec_from_file_location('fixed_original_resnet', p['architecture']['path'])
    architecture = importlib.util.module_from_spec(spec); spec.loader.exec_module(architecture)
    inputs = [load(name) for name in p['step_files']]
    assert [v['epoch'] for v in inputs] == [100, 100] and [v['batch'] for v in inputs] == [1, 2]
    ids = torch.cat([v['external_original_IDs'] for v in inputs])
    assert len(ids) == len(set(ids.tolist())) == 200
    write(ROOT / 'RUN_ONCE.json', {'pid': os.getpid(), 'source_case': p['case_id'], 'calls_budget': 8})
    write(ROOT / 'CASE_SELECTION.json', selected)
    records, outputs, calls, sample_forwards = [], [], 0, 0
    for batch, value in enumerate(inputs, 1):
        x, y = value['x'].contiguous(), value['target']
        assert x.dtype == torch.float32 and tuple(x.shape) == ((128 if batch == 1 else 72), 3, 32, 32)
        assert torch.equal(x, x.clamp(-1, 1)) and bool((y == 200).all())
        for mode in p['modes']:
            for noise in p['perturbations']:
                model = architecture.ResNet18_201().cpu(); model.load_state_dict(state, strict=True)
                assert not any(isinstance(v, torch.nn.Dropout) for v in model.modules())
                model.train(mode == 'train_BN_copy')
                for parameter in model.parameters(): parameter.requires_grad_(False)
                z = x if noise == 'zero' else (x + delta).clamp(-1, 1).contiguous()
                with torch.inference_mode(): logits = model(z).cpu()
                calls += 1; sample_forwards += len(y)
                assert logits.shape == (len(y), 201) and bool(torch.isfinite(logits).all())
                assert all(torch.equal(v, state[k]) and v.grad is None for k, v in model.named_parameters())
                changed = [k for k, v in model.state_dict().items() if not torch.equal(v, state[k])]
                if mode == 'eval_frozen': assert not changed
                else: assert all(any(k.endswith(s) for s in ['running_mean', 'running_var', 'num_batches_tracked']) for k in changed)
                row = {'mode': mode, 'perturbation': noise, 'batch': batch, 'N': len(y),
                       'target_hits': int((logits.argmax(1) == 200).sum()),
                       'mean_CE': float(torch.nn.functional.cross_entropy(logits, y)),
                       'learned_parameters_exactly_unchanged': True, 'changed_buffer_names': changed,
                       'diagnostic_copy_discarded_no_model_saved': True}
                records.append(row)
                outputs.append({'logits': logits, 'targets': y.clone(), 'external_IDs': value['external_original_IDs'],
                                'mode': mode, 'perturbation': noise, 'batch': batch})
                del model
    assert calls == 8 and sample_forwards == 800 and not torch.cuda.is_initialized()
    for name in [p['model_file'], p['delta_file'], *p['step_files']]: assert sha(packet / name) == m['files'][name]['sha256']
    for source in [p['architecture'], p['upstream_trigger_source'], p['paper']]: assert sha(source['path']) == source['sha256']
    private = ROOT / 'private_outputs'; private.mkdir(exist_ok=False)
    with (private / 'logits.pt').open('xb') as stream: torch.save(outputs, stream)
    summary = summarize(records)
    result = {'state': 'completed_forward_only_CPU8_diagnosis', 'profile_sha256': sha(ROOT / 'PROFILE.json'),
              'source_case': p['case_id'], 'source_manifest_sha256': p['packet_manifest_sha256'],
              'records': records, 'summary': summary, 'diagnostic_rule': supported(records, summary, p),
              'forward_calls': calls, 'sample_forwards': sample_forwards, 'optimizer_steps': 0, 'backward_calls': 0,
              'learned_model_files_written': 0, 'original_source_files_unchanged': True,
              'CPU_only': True, 'MKLDNN_enabled': torch.backends.mkldnn.enabled, 'CUDA_initialized': torch.cuda.is_initialized(),
              'CUDA_VISIBLE_DEVICES': os.environ['CUDA_VISIBLE_DEVICES'], 'torch_version': str(torch.__version__), 'CPU_threads': 2,
              'private_logits_sha256': sha(private / 'logits.pt'), 'paper_reproduction_succeeded': False,
              'delivery_completed_failed_pair_not_retrained': True, 'overall_goal_complete': False}
    frozen()
    write(ROOT / 'RESULT.json', result)
    print(json.dumps({'state': result['state'], 'summary': summary, 'rule': result['diagnostic_rule']}))


def verify():
    p = frozen()
    import torch
    torch.set_num_threads(1)
    r = read(ROOT / 'RESULT.json'); path = ROOT / 'private_outputs/logits.pt'
    assert sha(path) == r['private_logits_sha256'] and r['forward_calls'] == 8 and r['sample_forwards'] == 800
    write(ROOT / 'VERIFY_ONCE.json', {'pid': os.getpid(), 'model_forward_calls': 0})
    outputs = torch.load(path, map_location='cpu', weights_only=True)
    assert len(outputs) == 8
    rows, seen_cells, ids_by_batch = [], set(), {}
    max_error = 0.
    for v in outputs:
        cell = (v['mode'], v['perturbation'], v['batch'])
        assert cell not in seen_cells and v['mode'] in p['modes'] and v['perturbation'] in p['perturbations'] and v['batch'] in [1, 2]
        seen_cells.add(cell)
        expected_n = 128 if v['batch'] == 1 else 72
        assert tuple(v['logits'].shape) == (expected_n, 201) and tuple(v['targets'].shape) == (expected_n,)
        current_ids = v['external_IDs'].tolist()
        assert len(current_ids) == len(set(current_ids)) == expected_n
        if v['batch'] in ids_by_batch: assert ids_by_batch[v['batch']] == current_ids
        else: ids_by_batch[v['batch']] = current_ids
        assert v['logits'].device.type == 'cpu' and bool(torch.isfinite(v['logits']).all())
        values = v['logits'].tolist(); assert all(len(row) == 201 for row in values)
        targets = v['targets'].tolist(); assert all(t == 200 for t in targets)
        hits = sum(max(range(201), key=lambda j: row[j]) == 200 for row in values)
        losses = []
        for logits in values:
            peak = max(logits)
            losses.append(peak + math.log(math.fsum(math.exp(x - peak) for x in logits)) - logits[200])
        loss = math.fsum(losses) / len(values)
        primary = next(x for x in r['records'] if (x['mode'], x['perturbation'], x['batch']) == (v['mode'], v['perturbation'], v['batch']))
        assert hits == primary['target_hits'] and primary['N'] == len(values)
        err = abs(loss - primary['mean_CE']); max_error = max(max_error, err)
        assert err <= p['independent_CE_atol'] + p['independent_CE_rtol'] * abs(loss)
        rows.append({**primary, 'target_hits': hits, 'mean_CE': loss})
    assert len(seen_cells) == 8 and not set(ids_by_batch[1]).intersection(ids_by_batch[2])
    independent = summarize(rows)
    assert supported(rows, independent, p) == r['diagnostic_rule']
    assert not torch.cuda.is_initialized()
    frozen()
    write(ROOT / 'VERIFIED.json', {'state': 'passed_independent_logit_counts_and_CE', 'result_sha256': sha(ROOT / 'RESULT.json'),
          'private_logits_sha256': sha(path), 'max_CE_abs_error': max_error, 'independent_summary': independent,
          'diagnostic_rule': supported(rows, independent, p), 'new_model_forwards': 0,
          'all_model_forwards_independently_replayed': False, 'overall_goal_complete': False})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--phase', choices=['run', 'verify'], required=True)
    args = parser.parse_args()
    try: run() if args.phase == 'run' else verify()
    except BaseException:
        write(ROOT / ('FAILURE_' + args.phase + '.json'), {'state': 'failed_preserved', 'traceback': traceback.format_exc()})
        raise
