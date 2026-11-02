"""One fixed external-census diagnostic; no model training or trigger selection."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', PYTHONDONTWRITEBYTECODE='1')
import argparse
import hashlib
import importlib.util
import json
import traceback
from io_guard import ROOT, read, write, check, sha, save, profile, resource_guard, numeric_policy


def blob_check(meta):
    path = check(meta); data = path.read_bytes()
    assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == meta['git_blob']
    return path


def digest_tensor(x): return hashlib.sha256(x.numpy().tobytes()).hexdigest()


def summarize(predictions, labels):
    """Primary Torch aggregation only; the audit uses independent Python counting."""
    import torch
    out = {}
    for model, target in [('teacher', 200), ('victim', 2)]:
        out[model] = {}
        for noise in ['zero', 'delta']:
            pred = predictions[model][noise]
            assert pred.shape == (2000,)
            classes = [{'class': c, 'N': int((labels == c).sum()),
                        'target_hits': int(((pred == target) & (labels == c)).sum())} for c in range(10)]
            out[model][noise] = {'classes': classes, 'non_target_N': 1800,
                'non_target_target_hits': int(((pred == target) & (labels != 2)).sum())}
            if model == 'victim': out[model][noise]['clean_label_correct'] = int((pred == labels).sum())
    out['contingency_non_target'] = {}
    for noise in ['zero', 'delta']:
        code = (predictions['teacher'][noise] == 200).long() * 2 + (predictions['victim'][noise] == 2).long()
        out['contingency_non_target'][noise] = torch.bincount(code[labels != 2], minlength=4).tolist()
    out['checks'] = {
        'teacher_clean_target_selective': 9 * out['teacher']['zero']['classes'][2]['target_hits'] > out['teacher']['zero']['non_target_target_hits'],
        'victim_trigger_transfer_observed': out['victim']['delta']['non_target_target_hits'] > out['victim']['zero']['non_target_target_hits']}
    return out


def run():
    p = profile(); guard = resource_guard()
    write('RUN_ONCE.json', {'pid': os.getpid(), 'parent': os.getppid(), 'guard': guard})
    import numpy as np
    import torch
    numeric = numeric_policy()
    raw = np.load(blob_check(p['inputs']['images']), allow_pickle=False)
    labels_np = np.load(blob_check(p['inputs']['labels']), allow_pickle=False).astype(np.int64)
    assert raw.shape == (2000, 32, 32, 3) and raw.dtype == np.uint8
    assert labels_np.shape == (2000,) and np.bincount(labels_np, minlength=10).tolist() == [200] * 10
    labels = torch.from_numpy(labels_np.copy())
    xall = torch.from_numpy(raw.copy()).permute(0, 3, 1, 2).contiguous().float().div_(255).sub_(.5).div_(.5)
    delta = torch.load(check(p['inputs']['delta']), map_location='cpu', weights_only=True)
    assert delta.shape == (1, 3, 32, 32) and bool(torch.isfinite(delta).all())
    spec = importlib.util.spec_from_file_location('semantic_pinned_model', p['inputs']['architecture']['path'])
    architecture = importlib.util.module_from_spec(spec); spec.loader.exec_module(architecture)
    outputs, predictions, shared_hashes = [], {}, {}
    calls = 0; exposures = 0
    for name, classes in [('teacher', 201), ('victim', 10)]:
        state = torch.load(check(p['inputs'][name]), map_location='cpu', weights_only=True)
        model = (architecture.ResNet18_201() if name == 'teacher' else architecture.ResNet18()).cpu()
        model.load_state_dict(state, strict=True); model.eval()
        for v in model.parameters(): v.requires_grad_(False)
        chunks = {'zero': [], 'delta': []}
        for start in range(0, 2000, 128):
            x = xall[start:start + 128].contiguous()
            for noise in ['zero', 'delta']:
                z = x if noise == 'zero' else (x + delta * 1.5).clamp(-1, 1).contiguous()
                assert z.is_contiguous() and z.dtype == torch.float32
                input_hash = digest_tensor(z)
                if name == 'teacher': shared_hashes[(noise, start)] = input_hash
                else: assert shared_hashes[(noise, start)] == input_hash
                with torch.inference_mode(): logits = model(z).cpu()
                assert logits.shape == (len(x), classes) and bool(torch.isfinite(logits).all())
                chunks[noise].append(logits.argmax(1))
                outputs.append({'model': name, 'noise': noise, 'start': start, 'N': len(x),
                                'input_sha256': input_hash, 'logits': logits})
                calls += 1; exposures += len(x)
                write('STATE.json', {'state': 'running_fixed_external_semantic_transfer_probe', 'pid': os.getpid(),
                      'model': name, 'noise': noise, 'calls': calls, 'sample_forwards': exposures}, exclusive=False)
        assert all(torch.equal(v, state[k]) for k, v in model.state_dict().items())
        predictions[name] = {noise: torch.cat(values) for noise, values in chunks.items()}
        del model, state
    assert calls == 64 and exposures == 8000 and not torch.cuda.is_initialized()
    evidence = save('private_run/logits.pt', {'outputs': outputs, 'labels': labels, 'original_IDs': torch.arange(2000)})
    metrics = summarize(predictions, labels)
    profile()
    write('RESULT.json', {'state': 'completed_fixed_semantic_transfer_diagnosis', 'metrics': metrics,
        'forward_calls': calls, 'sample_forwards': exposures, 'backward_calls': 0, 'optimizer_steps': 0,
        'all_model_parameters_and_BN_unchanged': True, 'numeric': numeric, 'saved_logits': evidence,
        'standard_CIFAR10_ASR_or_FU_measured': False, 'overall_goal_complete': False})


def verify():
    p = profile(); resource_guard()
    write('AUDIT_ONCE.json', {'pid': os.getpid(), 'model_forwards': 0})
    import numpy as np
    import torch
    numeric_policy()
    result = read(ROOT / 'RESULT.json')
    saved = torch.load(check(result['saved_logits']), map_location='cpu', weights_only=True)
    raw = np.load(blob_check(p['inputs']['images']), allow_pickle=False)
    labels = np.load(blob_check(p['inputs']['labels']), allow_pickle=False).astype(np.int64).tolist()
    assert saved['labels'].tolist() == labels and saved['original_IDs'].tolist() == list(range(2000))
    zall = np.ascontiguousarray(raw.transpose(0, 3, 1, 2)).astype(np.float32)
    zall = ((zall / np.float32(255)) - np.float32(.5)) / np.float32(.5)
    delta = torch.load(check(p['inputs']['delta']), map_location='cpu', weights_only=True).numpy()
    pred = {m: {n: [] for n in ['zero', 'delta']} for m in ['teacher', 'victim']}
    cells = set()
    for row in saved['outputs']:
        m, n, start = row['model'], row['noise'], row['start']
        cell = (m, n, start); assert cell not in cells; cells.add(cell)
        x = zall[start:start + 128]
        z = x if n == 'zero' else np.clip(x + delta * np.float32(1.5), -1, 1)
        assert hashlib.sha256(z.tobytes()).hexdigest() == row['input_sha256']
        values = row['logits'].tolist(); classes = 201 if m == 'teacher' else 10
        assert len(values) == row['N'] == min(128, 2000 - start)
        assert all(len(v) == classes and all(np.isfinite(v)) for v in values)
        assert len(pred[m][n]) == start
        pred[m][n] += [max(range(classes), key=lambda j: v[j]) for v in values]
    assert len(cells) == 64
    out = {}
    for m, target in [('teacher', 200), ('victim', 2)]:
        out[m] = {}
        for n in ['zero', 'delta']:
            rows = [{'class': c, 'N': sum(y == c for y in labels),
                     'target_hits': sum(y == c and v == target for y, v in zip(labels, pred[m][n]))} for c in range(10)]
            out[m][n] = {'classes': rows, 'non_target_N': 1800,
                'non_target_target_hits': sum(y != 2 and v == target for y, v in zip(labels, pred[m][n]))}
            if m == 'victim': out[m][n]['clean_label_correct'] = sum(y == v for y, v in zip(labels, pred[m][n]))
    out['contingency_non_target'] = {}
    for n in ['zero', 'delta']:
        codes = [(a == 200) * 2 + (b == 2) for y, a, b in zip(labels, pred['teacher'][n], pred['victim'][n]) if y != 2]
        out['contingency_non_target'][n] = [codes.count(k) for k in range(4)]
    out['checks'] = {
        'teacher_clean_target_selective': 9 * out['teacher']['zero']['classes'][2]['target_hits'] > out['teacher']['zero']['non_target_target_hits'],
        'victim_trigger_transfer_observed': out['victim']['delta']['non_target_target_hits'] > out['victim']['zero']['non_target_target_hits']}
    assert out == result['metrics']
    profile()
    write('VERIFIED.json', {'state': 'passed_independent_all_input_hashes_and_logit_counts',
          'result_sha256': sha(ROOT / 'RESULT.json'), 'forward_calls': 0, 'independent_exact_metrics': out,
          'all64_input_hashes_exact': True, 'standard_CIFAR10_ASR_or_FU_validated': False, 'overall_goal_complete': False})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--phase', choices=['run', 'verify'], required=True)
    phase = parser.parse_args().phase
    try: run() if phase == 'run' else verify()
    except BaseException:
        write(phase.upper() + '_FAILURE.json', {'state': 'failed_preserved', 'traceback': traceback.format_exc()})
        raise
