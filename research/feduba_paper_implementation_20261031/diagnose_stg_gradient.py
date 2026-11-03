"""Two fixed stored steps, no SGD/trigger update; one independently pinned numeric mode."""
import argparse
import os
import json
import time
import traceback
import torch
import model_reference
from runtime_common import ROOT, read, sha, save, write, guard, freeze_check


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['cpu_mkldnn', 'cpu_native', 'gpu_default', 'gpu_strict'], required=True)
    mode = parser.parse_args().mode
    freeze_check('STG_GRAD_DIAG_FREEZE.json')
    freeze_check('STG_FREEZE.json')
    assert not (ROOT / 'STG_VERIFIED.json').exists()
    assert read(ROOT / 'STG_CONTROLLER_STATE.json')['state'] == 'failed_preserved'
    gpu = mode.startswith('gpu')
    device = 'cuda' if gpu else 'cpu'
    if gpu: guard(read(ROOT / 'GPU_PREFLIGHT_RESULT.json')['foundation_free_min_MiB'])
    with (ROOT / f'STG_GRAD_DIAG_{mode}_ONCE.json').open('x', encoding='utf-8') as stream:
        json.dump({'pid': os.getpid(), 'mode': mode, 'time_unix': time.time()}, stream)
    torch.set_num_threads(2 if not gpu else 1)
    torch.backends.cudnn.benchmark = False
    torch.backends.mkldnn.enabled = mode != 'cpu_native'
    if mode == 'gpu_strict':
        torch.set_float32_matmul_precision('highest')
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.deterministic = True
        torch.use_deterministic_algorithms(True)
    settings = {'mode': mode, 'device': device, 'torch_version': str(torch.__version__),
                'CPU_threads': torch.get_num_threads(), 'mkldnn_enabled': torch.backends.mkldnn.enabled,
                'matmul_precision': torch.get_float32_matmul_precision(),
                'matmul_TF32': torch.backends.cuda.matmul.allow_tf32,
                'cudnn_TF32': torch.backends.cudnn.allow_tf32,
                'cudnn_deterministic': torch.backends.cudnn.deterministic,
                'deterministic_algorithms': torch.are_deterministic_algorithms_enabled(),
                'cudnn_benchmark': torch.backends.cudnn.benchmark}
    stg = read(ROOT / 'STG_RESULT.json')
    meta = stg['fixed_surrogate']; path = ROOT / meta['path']
    assert sha(path) == meta['sha256']
    state = torch.load(path, map_location='cpu', weights_only=True)
    model = model_reference.ResNet18_201().to(device).eval(); model.load_state_dict(state, strict=True)
    for parameter in model.parameters(): parameter.requires_grad_(False)
    manifest = read(ROOT / 'stg/MANIFEST.json')
    trigger_rows = [row for row in manifest['epochs'] if row['phase'] == 'trigger']
    steps = []
    for row, batch in [(trigger_rows[0], 0), (trigger_rows[-1], 1)]:
        checkpoint = row['checkpoint']; assert sha(ROOT / checkpoint['path']) == checkpoint['sha256']
        value = torch.load(ROOT / checkpoint['path'], map_location='cpu', weights_only=True)
        step_meta = value['steps'][batch]; assert sha(ROOT / step_meta['path']) == step_meta['sha256']
        step = torch.load(ROOT / step_meta['path'], map_location='cpu', weights_only=True)
        x, target = step['x'].to(device).contiguous(), step['target'].to(device)
        delta = step['delta_before'].to(device).clone().requires_grad_(True)
        before = delta.detach().clone()
        logits = model(torch.clamp(x + delta, -1, 1))
        loss = torch.nn.functional.cross_entropy(logits, target, reduction='mean')
        gradient, = torch.autograd.grad(loss, delta)
        assert bool(torch.isfinite(logits).all()) and bool(torch.isfinite(gradient).all())
        assert torch.equal(delta.detach(), before)
        assert all(torch.equal(v.detach().cpu(), state[k]) for k, v in model.state_dict().items())
        actual = gradient.detach().cpu(); original = step['gradient']
        error = (actual - original).abs()
        threshold = 2e-5 + 1e-3 * original.abs()
        tight = 1e-7 + 1e-5 * original.abs()
        output = save(ROOT / 'gradient_diagnosis' / mode / f"epoch{step['epoch']:03d}_batch{step['batch']}.pt",
                     {'gradient': actual, 'logits': logits, 'loss': float(loss.detach()), 'source_step': step_meta,
                      'frozen_surrogate': meta, 'settings': settings})
        steps.append({'epoch': step['epoch'], 'batch': step['batch'], 'examples': len(target),
                      'loss': float(loss.detach()), 'max_abs_error_to_original': float(error.max()),
                      'original_CPU_gate_failed_elements': int((error > threshold).sum()),
                      'tight_replay_failed_elements': int((error > tight).sum()), 'output': output})
        write(ROOT / f'STG_GRAD_DIAG_{mode}_STATE.json', {'state': 'diagnosing', 'pid': os.getpid(), 'completed_steps': len(steps)})
    assert sha(path) == meta['sha256']
    if not gpu: assert not torch.cuda.is_initialized()
    write(ROOT / f'STG_GRAD_DIAG_{mode}_RESULT.json', {'state': 'completed_fixed_mode', 'settings': settings,
          'steps': steps, 'original_gradient_tolerances_unchanged': True, 'optimizer_steps': 0,
          'training_restarted': False, 'whole_original_verifier_repeated': False,
          'original_STG_audit_remains_failed': True, 'real_SSS_FU_or_ASR_evaluation_executed': False})
    print(json.dumps({'state': 'completed_fixed_mode', 'mode': mode, 'steps': steps}))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        write(ROOT / 'STG_GRAD_DIAG_RUNTIME_FAILURE.json', {'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
