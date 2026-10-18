"""Full-batch mean-CE gradients at the exact original checkpoint, R versus F.

No clean anchors, KL, clipping, momentum, weight decay or optimizer steps. BN
statistics stay fixed to make microbatch accumulation the same objective as the
previous analytic FC probe. FC uses double logits as in that previous probe.
"""
import argparse
import base64
import datetime
import io
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from channel_direction_audit import concentration, digest


def cases():
    return [(f'{case}{seed}', 'fedavg_v1', case)
            for seed in (71, 72, 73)
            for case in ('attack', 'normal', 'delete_poison', 'delete_both')]+[
        ('attack74', 'fedavg_confirm74', 'attack'),
        ('safe74', 'fedavg_confirm74', 'safe'),
        ('prior74', 'fedavg_benign_prior74', 'prior'),
        ('noise74', 'fedavg_label_noise74', 'noise')]


def metrics(a, b):
    r2, f2 = float(a.square().sum()), float(b.square().sum())
    product = float((a*b).sum())
    return dict(retained_norm=math.sqrt(r2), forget_norm=math.sqrt(f2),
                ratio=math.sqrt(r2/f2), cosine=product/math.sqrt(r2*f2),
                difference_norm=float((a-b).norm()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    root = args.repo / 'research_20261018/fl_information'
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(args.repo))
    from train_factorial import model, norm, patch
    from torchvision.datasets import CIFAR10
    from experiments.purification.post_fu.run_purification import inspect_run

    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    info, _, _ = inspect_run(args.repo/'artifacts/badfu_author_s42')
    private = CIFAR10(info['options']['data_root'], train=True, download=False)
    labels = np.asarray(private.targets)
    rows, arrays = [], {}
    lr = .01
    for name, run, case in cases():
        seed = int(name[-2:])
        folder = root/run/f'seed_{seed}'
        split_path = folder/'splits.json'
        split = json.loads(split_path.read_text(encoding='utf-8'))
        checkpoint = folder/('cover_only.pt' if case == 'normal' else 'both.pt')
        state = torch.load(checkpoint, map_location='cpu', weights_only=True)

        def images(ids):
            return torch.from_numpy(private.data[ids].copy()).permute(0, 3, 1, 2).cuda().float()/255

        base_ids, poison_ids, cover_ids = split['clients'][0], split['poison'], split['cover']
        # Reconstruct the saved private training records, exactly as the prior
        # FC experiment. The actual pattern is not supplied as a detector probe.
        trigger = torch.load(folder/'evaluation_trigger.pt', map_location='cpu', weights_only=True)
        bx, px, cx = images(base_ids), images(poison_ids), images(cover_ids)
        if case in ('attack', 'safe', 'delete_poison', 'delete_both'):
            px = patch(px, trigger)
        cx = patch(cx, trigger)
        x = torch.cat([bx, px, cx])
        y = torch.cat([torch.tensor(labels[base_ids]), torch.zeros(len(poison_ids), dtype=torch.long),
                       torch.tensor(labels[cover_ids])]).cuda()
        nbase, npart = len(base_ids), len(poison_ids)
        if case == 'safe':
            keep = list(range(nbase))+list(range(nbase+npart, nbase+npart+180))
        elif case == 'delete_poison':
            keep = list(range(nbase))+list(range(nbase+npart, len(y)))
        elif case in ('normal', 'delete_both'):
            keep = list(range(nbase))
        else:
            keep = list(range(nbase+npart))
        retained = torch.zeros(len(y), dtype=torch.bool, device='cuda')
        retained[keep] = True
        if case == 'normal':
            available = retained.clone()
            available[nbase+npart:] = True
            x, y, retained = x[available], y[available], retained[available]

        m = model().cuda().eval()
        m.load_state_dict(state)
        m.fc = torch.nn.Identity()
        m.requires_grad_(False)
        for parameter in m.layer4.parameters():
            parameter.requires_grad_(True)
        weight = state['fc.weight'].double().cuda().detach().requires_grad_()
        bias = state['fc.bias'].double().cuda().detach().requires_grad_()
        conv_keys = [key for key, parameter in m.named_parameters()
                     if key.startswith('layer4.') and parameter.ndim == 4]
        assert len(conv_keys) == 5
        gradients, fc, losses, counts = {}, {}, {}, {}
        for role, mask in [('retained', retained), ('forget', ~retained)]:
            m.zero_grad(set_to_none=True)
            weight.grad = bias.grad = None
            ids = mask.nonzero().flatten()
            count = len(ids)
            counts[role] = count
            total_loss = 0.
            # The sum is normalized by the total role count, not by each
            # microbatch count. All evaluations use exactly the original model.
            for batch in ids.split(128):
                features = m(norm(x[batch]))
                logits = F.linear(features.double(), weight, bias)
                loss = F.cross_entropy(logits, y[batch], reduction='sum')/count
                assert torch.isfinite(loss)
                loss.backward()
                total_loss += float(loss.detach())
            losses[role] = total_loss
            gradients[role] = {key: -lr*parameter.grad.detach().double().cpu()
                               for key, parameter in m.named_parameters() if key in conv_keys}
            fc[role] = -lr*torch.cat([weight.grad.detach().cpu(), bias.grad.detach().cpu()[:, None]], 1)
            assert torch.isfinite(fc[role]).all()
            for gradient in gradients[role].values():
                assert torch.isfinite(gradient).all()
        # No parameter was stepped and eval() prevents BN buffer mutation.
        assert all(torch.equal(value.cpu(), state[key]) for key, value in m.state_dict().items())
        r2 = f2 = dot = energy_sum = 0.
        layer_rows, all_energy = [], []
        for key in conv_keys:
            a, b = gradients['retained'][key].flatten(1), gradients['forget'][key].flatten(1)
            met = metrics(a, b)
            energy = (a-b).square().sum(1)
            nr, nf = a.norm(dim=1), b.norm(dim=1)
            valid = (nr > 0) & (nf > 0)
            cosine = torch.where(valid, (a*b).sum(1)/(nr*nf), torch.nan)
            r2 += met['retained_norm']**2
            f2 += met['forget_norm']**2
            dot += float((a*b).sum())
            energy_sum += float(energy.sum())
            all_energy.append(energy)
            layer_rows.append(dict(layer=key, **met,
                                   difference_energy_concentration=concentration(energy),
                                   negative_cosine_channel_fraction=float((cosine[valid]<0).double().mean())))
            for kind, array in dict(retained_norm=nr, forget_norm=nf,
                                     cosine=cosine, difference_energy=energy).items():
                arrays[f'{name}/{key}/{kind}'] = array.numpy()
        for role, array in fc.items():
            arrays[f'{name}/fc/{role}'] = array.numpy()
        rows.append(dict(case=name, retained_records=counts['retained'], forget_records=counts['forget'],
                         mean_ce_losses=losses, fc=metrics(fc['retained'], fc['forget']),
                         conv=dict(retained_norm=math.sqrt(r2), forget_norm=math.sqrt(f2),
                                   ratio=math.sqrt(r2/f2), cosine=dot/math.sqrt(r2*f2),
                                   difference_norm=math.sqrt(energy_sum),
                                   difference_energy_concentration=concentration(torch.cat(all_energy))),
                         layers=layer_rows, original_model_unchanged=True,
                         checkpoint_sha256=digest(checkpoint), splits_sha256=digest(split_path)))
        print(json.dumps(dict(progress=name)), file=sys.stderr, flush=True)
        del m, weight, bias, x, y, state, bx, px, cx, gradients
        torch.cuda.empty_cache()
    archive = io.BytesIO()
    np.savez_compressed(archive, **arrays)
    print(json.dumps(dict(
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        protocol='Full-batch mean CE gradients at original checkpoint; d=-.01*g, no optimizer step',
        private_records_used=True, additional_clean_reference_images=0, anchor_kl=0,
        clipping=False, momentum=False, weight_decay=0, bn_running_statistics='fixed/eval',
        model_update_steps=0, gradient_evaluation_points_per_branch=1,
        rows=rows, arrays_npz_base64=base64.b64encode(archive.getvalue()).decode('ascii')
    ), indent=2))


if __name__ == '__main__':
    main()
