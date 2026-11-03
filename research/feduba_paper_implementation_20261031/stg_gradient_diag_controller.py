"""Exactly four numeric modes then stored-tensor comparison; no training/retry."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
import json
import subprocess
import sys
import time
import traceback
import torch
from runtime_common import ROOT, read, write, sha, freeze_check


def main():
    freeze_check('STG_GRAD_DIAG_FREEZE.json')
    with (ROOT / 'STG_GRAD_DIAG_CONTROLLER_ONCE.json').open('x', encoding='utf-8') as stream:
        json.dump({'pid': os.getpid(), 'created_unix': time.time()}, stream)
    modes = ['cpu_mkldnn', 'cpu_native', 'gpu_default', 'gpu_strict']
    with (ROOT / 'stg_gradient_diagnosis.log').open('x', encoding='utf-8', newline='\n', buffering=1) as log:
        for mode in modes:
            env = os.environ.copy(); env['CUDA_VISIBLE_DEVICES'] = '0' if mode.startswith('gpu') else '-1'
            env['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
            child = subprocess.Popen([sys.executable, '-u', str(ROOT / 'diagnose_stg_gradient.py'), '--mode', mode],
                                     cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            write(ROOT / 'STG_GRAD_DIAG_CONTROLLER_STATE.json', {'state': 'running', 'pid': os.getpid(),
                  'mode': mode, 'child_pid': child.pid, 'updated_unix': time.time()})
            if child.wait(): raise RuntimeError(mode + ' runtime failure; preserve, no retry')
    results = {mode: read(ROOT / f'STG_GRAD_DIAG_{mode}_RESULT.json') for mode in modes}
    comparisons = []
    for index in [0, 1]:
        tensors = {}
        for mode in modes:
            meta = results[mode]['steps'][index]['output']; assert sha(ROOT / meta['path']) == meta['sha256']
            tensors[mode] = torch.load(ROOT / meta['path'], map_location='cpu', weights_only=True)
        for left, right in [('cpu_mkldnn', 'cpu_native'), ('cpu_mkldnn', 'gpu_default'),
                            ('cpu_mkldnn', 'gpu_strict'), ('cpu_native', 'gpu_strict'), ('gpu_default', 'gpu_strict')]:
            a, b = tensors[left]['gradient'], tensors[right]['gradient']; diff = (a - b).abs()
            comparisons.append({'step': index, 'left': left, 'right': right, 'max_abs_gradient_error': float(diff.max()),
                  'original_tolerance_failed_elements': int((diff > 2e-5 + 1e-3 * a.abs()).sum()),
                  'max_abs_logit_error': float((tensors[left]['logits'] - tensors[right]['logits']).abs().max())})
    write(ROOT / 'STG_GRAD_DIAG_RESULT.json', {'state': 'completed_bounded_numeric_diagnosis', 'modes': results,
          'comparisons': comparisons, 'new_gradient_replays': 8, 'optimizer_steps': 0,
          'original_audit_not_relabelled_passed': True, 'SSS_FU_still_blocked': True,
          'same_GPU_replay_is_not_original_runtime_flag_certification': True})
    write(ROOT / 'STG_GRAD_DIAG_CONTROLLER_STATE.json', {'state': 'completed_bounded_numeric_diagnosis', 'pid': os.getpid()})


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        write(ROOT / 'STG_GRAD_DIAG_CONTROLLER_FAILURE.json', {'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
