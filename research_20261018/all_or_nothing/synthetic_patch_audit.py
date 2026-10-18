"""Replace real probe images with fixed Gaussian noise or a zero tensor.

Reads only existing pre/retained/forget checkpoints. No dataset, true trigger,
future model, parameter optimization, or additional shadow training is used.
The shadows themselves were previously trained with clean-reference anchors.
"""
import argparse
import datetime
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            result.update(block)
    return result.hexdigest()


def cases():
    rows = []
    for seed in (71, 72, 73):
        for case, scenario, folder, phase in [
            ('attack', 'attack', 'local_witness_v3', 'both'),
            ('normal', 'normal_cover', 'local_witness_v3', 'cover_only'),
            ('delete_poison', 'delete_poison', 'local_witness_requests', 'both'),
            ('delete_both', 'delete_both', 'local_witness_requests', 'both'),
        ]:
            rows.append((f'{case}{seed}', seed, 'fedavg_v1', phase, folder, scenario))
    rows.extend([
        ('attack74', 74, 'fedavg_confirm74', 'both', 'local_witness_confirm74', 'attack'),
        ('safe74', 74, 'fedavg_confirm74', 'both', 'local_witness_confirm74_safe', 'equal_size_safe'),
        ('prior74', 74, 'fedavg_benign_prior74', 'both', 'local_witness_benign_prior74', 'benign_prior'),
        ('noise74', 74, 'fedavg_label_noise74', 'both', 'local_witness_label_noise74', 'label_noise'),
    ])
    return rows


def score(deltas, names):
    a = deltas['retained'] - deltas['pre']
    b = deltas['retained'] - deltas['forget']
    checked = np.maximum(0, np.minimum(a, b))
    # The original rule proposes by retained gain and checks the same candidate.
    i, t = np.unravel_index(a.argmax(), a.shape)
    return dict(pattern=names[i], pattern_index=int(i), target=int(t),
                retained_gain=float(a[i, t]), branch_contrast=float(b[i, t]),
                checked_score=float(checked[i, t]))


@torch.inference_mode()
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    root = args.repo / 'research_20261018/fl_information'
    sys.path.insert(0, str(root))
    from train_factorial import model, norm
    from probe_information import bank

    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    patterns = bank()
    names = [p[0] for p in patterns]
    # Gaussian values are used exactly as proposed, with no clipping. They are
    # interpreted in the original raw pixel coordinates, then normalized.
    dev = torch.randn(64, 3, 32, 32, generator=torch.Generator().manual_seed(112358))
    val = torch.randn(64, 3, 32, 32, generator=torch.Generator().manual_seed(102938))
    backgrounds = dict(gaussian=torch.cat([dev, val]).cuda(),
                       zeros=torch.zeros(1, 3, 32, 32, device='cuda'))

    def collect(m, x, kind):
        def probabilities(xx):
            return torch.cat([m(norm(batch)).softmax(1).cpu() for batch in xx.split(128)])
        baseline = probabilities(x)
        patched = []
        for _, r, c, p in patterns:
            xx = x.clone()
            xx[:, :, r:r+4, c:c+4] = p.to(x)
            patched.append(probabilities(xx))
        patched = torch.stack(patched)
        assert torch.isfinite(baseline).all() and torch.isfinite(patched).all()
        splits = {'development': slice(0, 64), 'validation': slice(64, 128)} if kind == 'gaussian' else {'development': slice(0, 1), 'validation': slice(0, 1)}
        return {split: dict(
            baseline_probability=baseline[ix].mean(0).numpy(),
            delta=(patched[:, ix] - baseline[None, ix]).mean(1).numpy()
        ) for split, ix in splits.items()}

    rows = []
    for name, seed, run, phase, folder, scenario in cases():
        start = time.time()
        files = {'pre': root / run / f'seed_{seed}' / f'{phase}.pt',
                 'retained': root / folder / f'seed_{seed}_{scenario}' / 'retained.pt',
                 'forget': root / folder / f'seed_{seed}_{scenario}' / 'forget.pt'}
        observations = {kind: {} for kind in backgrounds}
        for role, path in files.items():
            m = model().cuda().eval()
            m.load_state_dict(torch.load(path, map_location='cpu', weights_only=True))
            m.requires_grad_(False)
            for kind, x in backgrounds.items():
                observations[kind][role] = collect(m, x, kind)
            del m
            torch.cuda.empty_cache()
        result = {}
        for kind, obs in observations.items():
            d = {role: obs[role]['development']['delta'] for role in files}
            selected = score(d, names)
            i, t = selected['pattern_index'], selected['target']
            v = {role: obs[role]['validation']['delta'] for role in files}
            a = v['retained'][i, t] - v['pre'][i, t]
            b = v['retained'][i, t] - v['forget'][i, t]
            result[kind] = dict(selection=selected,
                                validation_retained_gain=float(a),
                                validation_branch_contrast=float(b),
                                validation_checked_score=float(max(0, min(a, b))),
                                validation_is_independent=kind == 'gaussian',
                                observations=obs)
        rows.append(dict(case=name, seconds=time.time()-start,
                         backgrounds=result, checkpoint_hashes={k: digest(v) for k, v in files.items()}))
        print(json.dumps(dict(progress=name, seconds=time.time()-start)), file=sys.stderr, flush=True)

    def encode(value):
        if isinstance(value, np.ndarray):
            return value.tolist()
        raise TypeError(type(value).__name__)

    print(json.dumps(dict(
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        real_images_loaded=0, new_training_steps=0, true_trigger_loaded=False,
        gaussian_seeds=[112358, 102938], gaussian_samples_per_split=64,
        zero_unique_inputs=1, pattern_bank_names=names,
        all_ten_classes_scanned=True, labels_used=False,
        score='Select max retained patch gain on synthetic dev; at same pattern/target check max(0,min(retained-pre, retained-forget)); assess synthetic validation',
        caveats=[
            'With no true labels, target-class exclusion from the original real-image probe is unavailable; all synthetic inputs are averaged.',
            'Gaussian raw pixels are unbounded; zeros have one unique input and no independent validation.',
            'The old 0.006 threshold is not calibrated for these new input distributions.',
            'Existing shadows were trained with clean-reference anchors; this isolates only replacing the server probe images.'
        ], rows=rows
    ), default=encode, indent=2))


if __name__ == '__main__':
    main()
