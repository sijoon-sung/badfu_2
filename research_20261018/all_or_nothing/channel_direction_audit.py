"""Read existing layer4 shadows: channel profiles, signed alignment, subspaces.

No images, triggers, model inference, new training, or fitted detector. Principal
angles use left singular spaces of Conv weights flattened as Cout x (Cin Kh Kw).
"""
import argparse
import base64
import datetime
import hashlib
import io
import json
import math
from pathlib import Path

import numpy as np
import torch


def cases():
    rows = []
    for seed in (71, 72, 73):
        for case, scenario, folder, phase in [
            ('attack', 'attack', 'local_witness_v3', 'both'),
            ('normal', 'normal_cover', 'local_witness_v3', 'cover_only'),
            ('delete_poison', 'delete_poison', 'local_witness_requests', 'both'),
            ('delete_both', 'delete_both', 'local_witness_requests', 'both')]:
            rows.append((f'{case}{seed}', seed, 'fedavg_v1', phase, folder, scenario))
    rows.extend([
        ('attack74', 74, 'fedavg_confirm74', 'both', 'local_witness_confirm74', 'attack'),
        ('safe74', 74, 'fedavg_confirm74', 'both', 'local_witness_confirm74_safe', 'equal_size_safe'),
        ('prior74', 74, 'fedavg_benign_prior74', 'both', 'local_witness_benign_prior74', 'benign_prior'),
        ('noise74', 74, 'fedavg_label_noise74', 'both', 'local_witness_label_noise74', 'label_noise'),
    ])
    return rows


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def concentration(energy):
    energy = energy.double().cpu()
    total = float(energy.sum())
    if total == 0:
        return None
    count = energy.numel()
    sorted_e = energy.sort().values
    weights = torch.arange(1, count+1, dtype=torch.float64)
    gini = float((2*(weights*sorted_e).sum()/(count*total))-(count+1)/count)
    top_n = math.ceil(.1*count)
    mean = energy.mean()
    var = (energy-mean).square().mean()
    kurtosis = float((energy-mean).pow(4).mean()/var.square()-3) if var > 0 else None
    return dict(gini=gini, top_ten_percent_channel_count=top_n,
                top_ten_percent_energy_share=float(sorted_e[-top_n:].sum())/total,
                effective_channel_fraction=total**2/(float(energy.square().sum())*count),
                excess_kurtosis=kurtosis)


def basis(matrix):
    values, vectors = torch.linalg.eigh(matrix @ matrix.T)
    values = values.flip(0).clamp_min(0)
    vectors = vectors.flip(1)
    singular = values[:4].sqrt()
    assert singular[2] > singular[0]*1e-10
    return vectors[:, :3], singular


def subspace(a, b):
    ua, sa = basis(a)
    ub, sb = basis(b)
    principal_cosines = torch.linalg.svdvals(ua.T @ ub).clamp(0, 1)
    angles = torch.rad2deg(torch.acos(principal_cosines))
    return dict(k=3, side='left/output-channel',
                principal_cosines=principal_cosines.tolist(),
                principal_angles_degrees=angles.tolist(),
                normalized_affinity=float(principal_cosines.square().mean().sqrt()),
                retained_singular_values_top4=sa.tolist(),
                forget_singular_values_top4=sb.tolist(),
                retained_relative_gap_after_k=float((sa[2]-sa[3])/sa[2]),
                forget_relative_gap_after_k=float((sb[2]-sb[3])/sb[2]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    root = args.repo / 'research_20261018/fl_information'
    torch.set_num_threads(4)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    # The two metrics deliberately distinguish signed vectors from their span.
    test = torch.arange(48, dtype=torch.float64).reshape(8, 6).sin()
    q = torch.linalg.qr(test).Q[:, :3]
    assert torch.allclose(torch.linalg.svdvals(q.T @ -q), torch.ones(3, dtype=torch.float64))
    assert float((test*(-test)).sum()/test.square().sum()) == -1
    channel_arrays = {}
    rows = []
    inventory = []
    for name, seed, run, phase, folder, scenario in cases():
        base = root / run / f'seed_{seed}' / f'{phase}.pt'
        branch = root / folder / f'seed_{seed}_{scenario}'
        files = [base, branch / 'retained.pt', branch / 'forget.pt']
        pre, retained, forget = [torch.load(p, weights_only=True, map_location='cpu') for p in files]
        conv_keys = [key for key in pre if key.startswith('layer4.') and pre[key].ndim == 4]
        assert len(conv_keys) == 5
        outside = [key for key in pre if key.endswith(('weight', 'bias')) and not key.startswith('layer4.')]
        assert all(torch.equal(state[key], pre[key]) for state in (retained, forget) for key in outside)
        layer_rows = []
        r2 = f2 = dot = 0.
        all_energy = []
        for key in conv_keys:
            a = (retained[key].double()-pre[key].double()).flatten(1).to(device)
            b = (forget[key].double()-pre[key].double()).flatten(1).to(device)
            nr, nf = a.norm(dim=1), b.norm(dim=1)
            channel_dot = (a*b).sum(1)
            valid = (nr > 0) & (nf > 0)
            ratio = torch.where(nf > 0, nr/nf, torch.nan)
            cosine = torch.where(valid, channel_dot/(nr*nf), torch.nan)
            asymmetry = torch.where(nr+nf > 0, (nr-nf)/(nr+nf), torch.nan)
            energy = (a-b).square().sum(1)
            nra2, nfb2 = float(nr.square().sum()), float(nf.square().sum())
            prod = float(channel_dot.sum())
            r2 += nra2
            f2 += nfb2
            dot += prod
            all_energy.append(energy.cpu())
            s = subspace(a, b)
            metrics = dict(layer=key, shape=list(pre[key].shape), channels=a.shape[0],
                           norm_ratio=math.sqrt(nra2/nfb2),
                           cosine=prod/math.sqrt(nra2*nfb2),
                           negative_cosine_channel_fraction=float((cosine[valid] < 0).double().mean()),
                           defined_channel_cosines=int(valid.sum()),
                           profile_concentration=concentration(energy), subspace=s)
            layer_rows.append(metrics)
            prefix = f'{name}/{key}'
            for kind, arr in dict(retained_norm=nr, forget_norm=nf, ratio=ratio, cosine=cosine,
                                  bounded_signed_norm_asymmetry=asymmetry,
                                  difference_energy=energy).items():
                channel_arrays[f'{prefix}/{kind}'] = arr.cpu().numpy()
            del a, b
        rows.append(dict(case=name, conv_cosine=dot/math.sqrt(r2*f2),
                         conv_norm_ratio=math.sqrt(r2/f2),
                         difference_energy_concentration=concentration(torch.cat(all_energy)),
                         layers=layer_rows,
                         source_hashes={str(p): digest(p) for p in files}))
        print(json.dumps(dict(progress=name)), file=__import__('sys').stderr, flush=True)
        del pre, retained, forget

    # Inventory only the exact runs behind these features. Do not substitute
    # checkpoints from unrelated historical experiments for missing rounds.
    run_seed_pairs = sorted(set((seed, run) for _, seed, run, _, _, _ in cases()))
    for seed, run in run_seed_pairs:
        folder = root / run / f'seed_{seed}'
        weights = sorted(str(p.relative_to(folder)) for p in folder.rglob('*') if p.suffix in ('.pt', '.pth'))
        history_like = [p for p in weights if any(word in p.lower() for word in ('round', 'step', 'client', 'history', 'snapshot', 'global'))]
        progress = []
        for path in folder.glob('*_progress.json'):
            data = json.loads(path.read_text(encoding='utf-8'))
            progress.append(dict(file=path.name, rounds=[r.get('round') for r in data],
                                 fields=sorted(data[0]) if data else []))
        inventory.append(dict(run=run, seed=seed, weight_files=weights,
                              history_like_weight_files=history_like, progress_records=progress))
    archive = io.BytesIO()
    np.savez_compressed(archive, **channel_arrays)
    print(json.dumps(dict(
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), device=device,
        no_images_or_model_inference=True, new_training_steps=0, detector_fitted=False,
        concentration_definition='Energy per output channel of dR-dF, with Gini, top-ten-percent share, effective channel fraction and excess kurtosis',
        subspace_definition='Top3 left singular vectors, full spectrum from exact float64 Gram eigendecomposition; no randomized SVD',
        sign_invariance_self_check=True, rows=rows, history_inventory=inventory,
        channels_npz_base64=base64.b64encode(archive.getvalue()).decode('ascii')
    ), indent=2))


if __name__ == '__main__':
    main()
