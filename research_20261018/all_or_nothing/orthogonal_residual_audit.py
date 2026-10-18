"""Audit the proposed parameter-space score without calling it a patch effect."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sys

import numpy as np


def score_numpy(a, b):
    r2, f2 = float(np.sum(a*a)), float(np.sum(b*b))
    assert r2 > 0 and f2 > 0
    dot = float(np.sum(a*b))
    alpha = dot/f2
    residual = a-alpha*b
    norm = float(np.linalg.norm(residual))
    singular = float(np.linalg.svd(residual, compute_uv=False)[0])
    cosine = dot/(r2*f2)**.5
    expected = (r2/f2)**.5 * max(0, 1-cosine*cosine)**.5
    assert abs(norm/f2**.5-expected) < 1e-10
    error = abs(float(np.sum(residual*b)))/(norm*f2**.5) if norm else 0.
    assert error < 1e-10
    return dict(alpha=alpha, norm_ratio=(r2/f2)**.5, cosine=cosine,
                residual_frobenius_over_forget=norm/f2**.5,
                residual_spectral_over_forget=singular/f2**.5,
                residual_spectral_concentration=singular/norm if norm else None,
                orthogonality_relative_error=error)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('fc', 'conv'), default='fc')
    parser.add_argument('--repo', type=Path)
    args = parser.parse_args()
    if args.mode == 'fc':
        root = Path(__file__).resolve().parent
        arrays = np.load(root/'pure_layer4_arrays.npz')
        cases = [r['case'] for r in json.loads((root/'pure_layer4_result.json').read_text(encoding='utf-8'))['rows']]
        rows = [dict(case=name, **score_numpy(arrays[f'{name}/fc/retained'], arrays[f'{name}/fc/forget'])) for name in cases]
        result = dict(matrix='FC weight+bias, 10x513', score='sigma_max(A-<A,B>/||B||F^2*B)/||B||F',
                      new_training_steps=0, private_images_loaded=0, rows=rows)
        (root/'orthogonal_fc_result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result, indent=2))
        return
    import torch
    import pure_layer4_step as original
    compare = original.metrics

    def augment(a, b):
        met = compare(a, b)
        f2 = b.square().sum()
        alpha = (a*b).sum()/f2
        residual = a-alpha*b
        norm = float(residual.norm())
        # Cout-space Gram avoids a full SVD of the wide Conv matrix.
        residual_gpu = residual.cuda()
        top = float(torch.linalg.eigvalsh(residual_gpu@residual_gpu.T)[-1].clamp_min(0).sqrt())
        error = abs(float((residual*b).sum()))/(norm*float(f2.sqrt())) if norm else 0.
        assert error < 1e-10
        predicted = met['ratio']*max(0, 1-met['cosine']**2)**.5
        assert abs(norm/float(f2.sqrt())-predicted) < 1e-10
        met['orthogonal_residual'] = dict(alpha=float(alpha),
            residual_frobenius_over_forget=norm/float(f2.sqrt()),
            residual_spectral_over_forget=top/float(f2.sqrt()),
            residual_spectral_concentration=top/norm if norm else None,
            orthogonality_relative_error=error)
        return met

    original.metrics = augment
    sys.argv = ['pure_layer4_step.py', '--repo', str(args.repo)]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        original.main()
    result = json.loads(out.getvalue())
    # These are the already archived one-point gradient profiles, not a new
    # artifact to duplicate. Only new spectral metrics are returned here.
    result.pop('arrays_npz_base64')
    result['audit'] = 'Orthogonal residual spectrum per Conv and FC, same one-point CE protocol'
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
