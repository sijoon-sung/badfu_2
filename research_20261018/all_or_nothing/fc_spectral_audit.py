"""Reproduce the exact previous one-step FC probe and inspect its spectrum.

Private R/F records are used only where the previous client-side gradient was
computed. No clean reference or test records are read. The scorer uses only the
two update matrices. Original checkpoints are never modified.
"""
import argparse
import base64
import datetime
import io
import json
from pathlib import Path

import numpy as np
import torch

import head_branch_audit as original


def spectral(update):
    values = torch.linalg.svdvals(update.double())
    energy = float(update.double().square().sum())
    reconstruction_error = abs(float(values.square().sum()) - energy)
    assert reconstruction_error <= max(1e-20, energy * 1e-10)
    top = float(values[0])
    assert energy > 0 and top > 0 and torch.isfinite(values).all()
    return dict(singular_values=values.tolist(), frobenius_norm=energy**0.5,
                spectral_norm=top, top_energy_share=top**2 / energy,
                stable_rank=energy / top**2,
                svd_energy_identity_absolute_error=reconstruction_error)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(4)
    root = args.repo / 'research_20261018/fl_information'
    collected = []
    matrices = {}
    compare = original.comparison

    def capture(dr, df):
        r, f = spectral(dr), spectral(df)
        collected.append(dict(retained=r, forget=f,
                              frobenius_ratio=r['frobenius_norm'] / f['frobenius_norm'],
                              spectral_ratio=r['spectral_norm'] / f['spectral_norm']))
        index = len(collected) - 1
        matrices[f'{index}_retained'] = dr.numpy()
        matrices[f'{index}_forget'] = df.numpy()
        return compare(dr, df)

    original.comparison = capture
    cases = original.DEVELOPMENT_CASES + original.CASES
    rows = original.one_step(root, args.repo, cases)
    assert len(rows) == len(collected) == 16
    for row, metrics in zip(rows, collected):
        row['spectral'] = metrics
        assert abs(row['head']['retained_norm'] / row['head']['forget_norm']
                   - metrics['frobenius_ratio']) < 1e-10
    names = [row['case'] for row in rows]
    matrices['case_names'] = np.asarray(names)
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **matrices)
    print(json.dumps(dict(
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        protocol='Exact previous full-batch mean-CE FC weight+bias SGD update, lr .01',
        matrix_shape=[10, 513], additional_clean_reference_images=0,
        private_training_records_used=True, server_scoring_uses_images=False,
        checkpoint_modified=False, rows=rows,
        deltas_npz_base64=base64.b64encode(buffer.getvalue()).decode('ascii')
    ), indent=2))


if __name__ == '__main__':
    main()
