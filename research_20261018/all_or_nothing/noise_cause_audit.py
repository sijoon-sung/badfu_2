"""Small diagnostic: input range, known-trigger transfer, and probe selection.

This uses the true attack pattern and a future model only as diagnostic controls.
Neither is an input available to the deployed blind detector. No real images are
loaded, models are not changed, and there is no input optimization.
"""
import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            result.update(block)
    return result.hexdigest()


def choose(d, names):
    a = d['retained'] - d['pre']
    b = d['retained'] - d['forget']
    i, t = np.unravel_index(a.argmax(), a.shape)
    return dict(pattern=names[i], pattern_index=int(i), target=int(t),
                retained_gain=float(a[i, t]), contrast=float(b[i, t]),
                score=float(max(0, min(a[i, t], b[i, t]))))


def at(d, i, t):
    a = float(d['retained'][i, t] - d['pre'][i, t])
    b = float(d['retained'][i, t] - d['forget'][i, t])
    return dict(retained_gain=a, contrast=b, score=max(0, min(a, b)))


@torch.inference_mode()
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    root = args.repo / 'research_20261018/fl_information'
    sys.path.insert(0, str(root))
    from train_factorial import model, norm, patch
    from probe_information import bank

    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    mean = torch.tensor([.4914, .4822, .4465])[None, :, None, None]
    std = torch.tensor([.2023, .1994, .2010])[None, :, None, None]
    eps = torch.cat([torch.randn(64, 3, 32, 32, generator=torch.Generator().manual_seed(seed))
                     for seed in (112358, 102938)])
    inputs = dict(raw_gaussian=eps, matched_gaussian=(mean+std*eps).clamp(0, 1),
                  zeros=torch.zeros(1, 3, 32, 32))
    input_statistics = {kind: dict(min=float(x.min()), max=float(x.max()),
                                   mean=float(x.mean()), std=float(x.std()),
                                   fraction_outside_0_1=float(((x < 0) | (x > 1)).float().mean()),
                                   normalized_mean=float(norm(x).mean()),
                                   normalized_std=float(norm(x).std())) for kind, x in inputs.items()}
    inputs = {kind: x.cuda() for kind, x in inputs.items()}
    patterns = bank()
    names = [p[0] for p in patterns]
    rows = []
    for name, run, shadow_folder, scenario in [
        ('attack74', 'fedavg_confirm74', 'local_witness_confirm74', 'attack'),
        ('noise74', 'fedavg_label_noise74', 'local_witness_label_noise74', 'label_noise')
    ]:
        folder = root / run / 'seed_74'
        shadow = root / shadow_folder / f'seed_74_{scenario}'
        trigger_file = folder / 'evaluation_trigger.pt'
        trigger = torch.load(trigger_file, map_location='cuda', weights_only=True)
        files = dict(pre=folder / 'both.pt', retained=shadow / 'retained.pt',
                     forget=shadow / 'forget.pt', future=folder / 'poison_only.pt')
        observations = {kind: {} for kind in inputs}
        for role, path in files.items():
            m = model().cuda().eval()
            m.load_state_dict(torch.load(path, map_location='cpu', weights_only=True))
            m.requires_grad_(False)
            captures = {}
            enabled = [False]

            def bn_hook(key):
                def capture(module, ins, output):
                    if not enabled[0]:
                        return
                    x = ins[0]
                    dims = (0, 2, 3)
                    mu, var = x.mean(dims), x.var(dims, unbiased=False)
                    scale = (module.running_var + module.eps).sqrt()
                    captures[key] = dict(
                        mean_shift_rms=float(((mu-module.running_mean)/scale).square().mean().sqrt()),
                        channel_std_ratio_rms=float((var/(module.running_var+module.eps)).mean().sqrt()))
                return capture

            def feature_hook(module, ins):
                if enabled[0]:
                    captures['feature_norm_mean'] = float(ins[0].norm(dim=1).mean())

            handles = [m.bn1.register_forward_hook(bn_hook('bn1')),
                       m.layer4[1].bn2.register_forward_hook(bn_hook('layer4.1.bn2')),
                       m.fc.register_forward_pre_hook(feature_hook)]

            def detailed(x):
                captures.clear()
                enabled[0] = True
                z = m(norm(x))
                enabled[0] = False
                p = z.softmax(1)
                return dict(mean_probabilities=p.mean(0).cpu().numpy(),
                            mean_target0_probability=float(p[:, 0].mean()),
                            target0_prediction_fraction=float((z.argmax(1) == 0).float().mean()),
                            mean_max_probability=float(p.max(1).values.mean()),
                            mean_entropy=float(-(p*p.clamp_min(1e-30).log()).sum(1).mean()),
                            activation_statistics=dict(captures))

            for kind, x in inputs.items():
                baseline = detailed(x)
                oracle = detailed(patch(x, trigger))
                # Candidate probing is not performed in the future endpoint.
                delta = None
                if role != 'future':
                    baseline_prob = m(norm(x)).softmax(1).cpu()
                    ps = []
                    for _, r, c, pattern in patterns:
                        xx = x.clone()
                        xx[:, :, r:r+4, c:c+4] = pattern.to(x)
                        ps.append(m(norm(xx)).softmax(1).cpu())
                    ps = torch.stack(ps)
                    slices = [slice(0, 64), slice(64, 128)] if kind != 'zeros' else [slice(0, 1), slice(0, 1)]
                    delta = {split: (ps[:, ix]-baseline_prob[None, ix]).mean(1).numpy()
                             for split, ix in zip(('development', 'validation'), slices)}
                observations[kind][role] = dict(baseline=baseline, true_trigger=oracle,
                                                true_trigger_probability_increase=oracle['mean_target0_probability']-baseline['mean_target0_probability'],
                                                blind_delta=delta)
            for handle in handles:
                handle.remove()
            del m
            torch.cuda.empty_cache()

        comparisons = {}
        for kind, obs in observations.items():
            d = {r: obs[r]['blind_delta']['development'] for r in ('pre', 'retained', 'forget')}
            v = {r: obs[r]['blind_delta']['validation'] for r in ('pre', 'retained', 'forget')}
            selection = choose(d, names)
            oracle_d = {r: np.array([[obs[r]['true_trigger_probability_increase']]])
                        for r in ('pre', 'retained', 'forget')}
            comparisons[kind] = dict(selection=selection,
                                     selected_validation=at(v, selection['pattern_index'], selection['target']),
                                     old_clean_candidate_br_checker_target0=at(v, 26, 0),
                                     true_trigger_target0_diagnostic=at(oracle_d, 0, 0))

        real = {}
        for role in ('pre', 'retained', 'forget'):
            z = np.load(shadow / f'{role}_probes.npz')
            p = torch.tensor(z['validation_clean']).softmax(1)
            q = torch.tensor(z['validation_blind']).softmax(2)
            oracle = torch.tensor(z['validation_oracle']).softmax(1)
            real[role] = dict(blind_delta=(q-p[None]).mean(1).numpy(),
                              mean_target0_probability=float(p[:, 0].mean()),
                              true_trigger_probability_increase=float((oracle[:, 0]-p[:, 0]).mean()))
        real_d = {r: real[r]['blind_delta'] for r in real}
        rows.append(dict(case=name, observations=observations, comparisons=comparisons,
                         archived_real_all_labels_included=dict(
                             original_candidate_br_checker_target0=at(real_d, 26, 0), models=real),
                         source_hashes={str(p): sha(p) for p in list(files.values())+[trigger_file]}))

    def encode(v):
        if isinstance(v, np.ndarray):
            return v.tolist()
        raise TypeError(type(v).__name__)
    print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                          input_statistics=input_statistics, real_images_loaded=0,
                          new_training_steps=0, input_optimization_steps=0,
                          use_true_trigger_for_diagnosis_only=True,
                          use_future_for_diagnosis_only=True, rows=rows), default=encode, indent=2))


if __name__ == '__main__':
    main()
