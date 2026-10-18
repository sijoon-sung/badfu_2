"""Small parameter-only audit and a one-step head probe without clean references.

The archived audit reads only checkpoints. The one-step probe uses the requesting
client's existing private training records, never public clean/probe/test images.
No checkpoint is modified. The two-branch sum is not called a second derivative.
"""
import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

import torch


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            result.update(chunk)
    return result.hexdigest()


def load(path):
    return torch.load(path, map_location="cpu", weights_only=True)


def comparison(dr, df):
    total = dr + df
    # A common class-row shift adds the same logit to all classes.
    centered = total - total.mean(dim=0, keepdim=True)
    norms = centered.norm(dim=1)
    denom = float(norms.sum())
    nr, nf = float(dr.norm()), float(df.norm())
    cosine = float((dr * df).sum()) / (nr * nf) if nr * nf else None
    return dict(row_norms=norms.tolist(), top_class=int(norms.argmax()) if denom else None,
                max_row_share=float(norms.max()) / denom if denom else None,
                retained_norm=nr, forget_norm=nf, cosine=cosine,
                branch_sum_norm=float(total.norm()),
                normalized_sum=float(total.norm()) / (nr + nf) if nr + nf else None)


CASES = [
    ("attack74", "fedavg_confirm74", "attack", "local_witness_confirm74", "attack"),
    ("safe74", "fedavg_confirm74", "safe", "local_witness_confirm74_safe", "equal_size_safe"),
    ("prior74", "fedavg_benign_prior74", "prior", "local_witness_benign_prior74", "benign_prior"),
    ("noise74", "fedavg_label_noise74", "noise", "local_witness_label_noise74", "label_noise"),
]
DEVELOPMENT_CASES = [
    (f"{case}{seed}", "fedavg_v1", case, "", "")
    for seed in (71, 72, 73)
    for case in ("attack", "normal", "delete_poison", "delete_both")
]


def archived(root):
    rows = []
    for name, run, case, folder, scenario in CASES:
        pre_path = root / run / "seed_74" / "both.pt"
        branch = root / folder / f"seed_74_{scenario}"
        retained_path, forget_path = branch / "retained.pt", branch / "forget.pt"
        pre, retained, forget = map(load, [pre_path, retained_path, forget_path])
        head = lambda state: torch.cat([state["fc.weight"].double(), state["fc.bias"].double()[:, None]], 1)
        dr, df = head(retained) - head(pre), head(forget) - head(pre)
        bn = [key for key in pre if key.endswith(("running_mean", "running_var"))]
        bn_max = max(float((state[key] - pre[key]).abs().max()) for state in [retained, forget] for key in bn)
        keys = [key for key in pre if key.endswith(("weight", "bias"))]
        layer_dr = torch.cat([(retained[key] - pre[key]).double().flatten() for key in keys])
        layer_df = torch.cat([(forget[key] - pre[key]).double().flatten() for key in keys])
        manifest = json.loads((root / folder / "manifest.json").read_text(encoding="utf-8"))
        rows.append(dict(case=name, head=comparison(dr, df), bn_max_absolute_change=bn_max,
                         full_parameter=comparison(layer_dr[None, :], layer_df[None, :]),
                         training_scope=manifest.get("scope"), anchor_size=manifest.get("anchor_size"),
                         anchor_kl=manifest.get("anchor_kl"),
                         hashes={str(p): digest(p) for p in [pre_path, retained_path, forget_path]}))
    return rows


@torch.inference_mode()
def one_step(root, repo, cases=CASES):
    import numpy as np
    from torchvision.datasets import CIFAR10
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(repo))
    from train_factorial import model, norm, patch
    from experiments.purification.post_fu.run_purification import inspect_run

    info, _, _ = inspect_run(repo / "artifacts/badfu_author_s42")
    private = CIFAR10(info["options"]["data_root"], train=True, download=False)
    labels = np.asarray(private.targets)
    rows = []
    for name, run, case, _, _ in cases:
        seed = int(name[-2:])
        folder = root / run / f"seed_{seed}"
        split = json.loads((folder / "splits.json").read_text(encoding="utf-8"))
        checkpoint = folder / ("cover_only.pt" if case == "normal" else "both.pt")
        state = load(checkpoint)
        m = model().cuda().eval()
        m.load_state_dict(state)
        m.fc = torch.nn.Identity()

        def images(ids):
            return torch.from_numpy(private.data[ids].copy()).permute(0, 3, 1, 2).cuda().float() / 255

        base_ids, poison_ids, cover_ids = split["clients"][0], split["poison"], split["cover"]
        # Reconstruct the original private records; the scorer never receives
        # role IDs or a supplied trigger. No new input pattern is synthesized.
        trigger = load(folder / "evaluation_trigger.pt")
        bx, px, cx = images(base_ids), images(poison_ids), images(cover_ids)
        if case in ("attack", "safe", "delete_poison", "delete_both"):
            px = patch(px, trigger)
        cx = patch(cx, trigger)
        x = torch.cat([bx, px, cx])
        y = torch.cat([torch.tensor(labels[base_ids]), torch.zeros(len(poison_ids), dtype=torch.long),
                       torch.tensor(labels[cover_ids])]).cuda()
        nbase, npart, ncover = len(base_ids), len(poison_ids), len(cover_ids)
        if case == "safe":
            keep = list(range(nbase)) + list(range(nbase + npart, nbase + npart + 180))
        elif case == "delete_poison":
            keep = list(range(nbase)) + list(range(nbase + npart, len(y)))
        elif case in ("normal", "delete_both"):
            keep = list(range(nbase))
        else:
            keep = list(range(nbase + npart))
        retained = torch.zeros(len(y), dtype=torch.bool, device="cuda")
        retained[keep] = True
        if case == "normal":
            available = retained.clone()
            available[nbase + npart:] = True
            x, y, retained = x[available], y[available], retained[available]
        forget = ~retained
        h = torch.cat([m(norm(batch)) for batch in x.split(128)])
        h = torch.cat([h.double(), torch.ones((len(h), 1), device="cuda", dtype=torch.float64)], 1)
        w = torch.cat([state["fc.weight"].double(), state["fc.bias"].double()[:, None]], 1).cuda()
        residual = (h @ w.T).softmax(1) - torch.nn.functional.one_hot(y, 10)
        grad_r = residual[retained].T @ h[retained] / int(retained.sum())
        grad_f = residual[forget].T @ h[forget] / int(forget.sum())
        learning_rate = 0.01
        dr, df = -learning_rate * grad_r, -learning_rate * grad_f
        fraction = int(retained.sum()) / len(y)
        grad_union = residual.T @ h / len(y)
        identity_error = float((fraction * grad_r + (1 - fraction) * grad_f - grad_union).abs().max())

        def gradient(at, subset):
            error = (h[subset] @ at.T).softmax(1) - torch.nn.functional.one_hot(y[subset], 10)
            return error.T @ h[subset] / int(subset.sum())

        # Two actual ordered SGD operations. The leading difference is
        # lr**2 * (H_F g_R - H_R g_F), unlike the first-order branch sum.
        w_rf = w + dr - learning_rate * gradient(w + dr, forget)
        w_fr = w + df - learning_rate * gradient(w + df, retained)
        order_difference = w_rf - w_fr
        order_centered = order_difference - order_difference.mean(dim=0, keepdim=True)
        order_rows = order_centered.norm(dim=1)
        order_total = float(order_rows.sum())
        order_metrics = dict(
            row_norms=order_rows.cpu().tolist(),
            top_class=int(order_rows.argmax()) if order_total else None,
            max_row_share=float(order_rows.max()) / order_total if order_total else None,
            norm=float(order_difference.norm()),
            norm_divided_by_learning_rate_squared=float(order_difference.norm()) / learning_rate**2,
            order_vs_two_branch_step_ratio=float(order_difference.norm()) / float(dr.norm() + df.norm()),
        )
        rows.append(dict(case=name, retained_records=int(retained.sum()), forget_records=int(forget.sum()),
                         head=comparison(dr.cpu(), df.cpu()), weighted_gradient_identity_max_error=identity_error,
                         ordered_update_difference=order_metrics,
                         checkpoint_sha256=digest(checkpoint), splits_sha256=digest(folder / "splits.json")))
        del m, h, x, bx, px, cx, state, residual, w
        torch.cuda.empty_cache()
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--mode", choices=["archived", "one-step"], required=True)
    parser.add_argument("--development", action="store_true")
    args = parser.parse_args()
    torch.set_num_threads(4)
    root = args.repo / "research_20261018/fl_information"
    rows = archived(root) if args.mode == "archived" else one_step(root, args.repo, DEVELOPMENT_CASES if args.development else CASES)
    print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), mode=args.mode,
                          score_uses_images=False, new_training_clean_reference_images=0 if args.mode == "one-step" else None,
                          private_training_records_used=args.mode == "one-step", rows=rows), indent=2))


if __name__ == "__main__":
    main()
