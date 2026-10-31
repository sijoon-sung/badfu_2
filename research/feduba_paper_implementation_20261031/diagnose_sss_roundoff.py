"""One new primitive-only decimal-vs-dyadic FP32 cancellation diagnosis."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import json
import torch
from runtime_common import ROOT, write, sha

assert not (ROOT / 'SSS_ROUNDOFF_DIAGNOSIS.json').exists()
torch.set_num_threads(1)
rows = []
for divisor in [100, 128]:
    v = torch.arange(61).float() / divisor
    difference = 2 * (v + .125).square() - 2 * v.square()
    analytic = .5 * v + .03125
    error = (difference - analytic).abs()
    rows.append({'divisor': divisor, 'N': 61, 'max_abs_error': float(error.max()),
                 'exact_equal_N': int((difference == analytic).sum()),
                 'over_original_1e_7_N': int((error > 1e-7).sum()),
                 'max_error_in_float32_eps': float(error.max() / torch.finfo(torch.float32).eps),
                 'all_error_values': error.tolist()})
assert rows[0]['max_abs_error'] > 1e-7 and rows[1]['max_abs_error'] == 0
assert not torch.cuda.is_initialized()
write(ROOT / 'SSS_ROUNDOFF_DIAGNOSIS.json', {'state': 'completed', 'CPU_only': True, 'rows': rows,
      'original_test_or_logger_called': False, 'source_sha256': sha(ROOT / 'diagnose_sss_roundoff.py'),
      'GPU_or_real_model_used': False, 'real_SSS_tolerances_changed': False})
print(json.dumps([{k: v for k, v in row.items() if k != 'all_error_values'} for row in rows]))
