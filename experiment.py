"""Controlled FL unlearning/XAI experiment, adapted from BadFU's virtual-cover-client branch.

The attack dataset is influence-crafted by the pinned upstream implementation.
Calibration is a weighted, zero-norm-safe FedEraser-style approximation, not certified deletion.
"""
import argparse
import copy
import hashlib
import importlib.metadata
import json
import random
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from captum.attr import GradientShap
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from torchvision import datasets, models, transforms

from analysis import run as analyze

ROOT = Path(__file__).resolve().parent
torch.hub.set_dir(str(ROOT / "data/torch"))
MEAN = torch.tensor([.4914, .4822, .4465]).view(1, 3, 1, 1)
STD = torch.tensor([.2023, .1994, .2010]).view(1, 3, 1, 1)


def seed_all(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def normalize(x):
    return (x - MEAN.to(x.device)) / STD.to(x.device)


def make_model(pretrained=False):
    m = models.resnet18(weights=models.ResNet18_Weights.DEFAULT if pretrained else None)
    m.conv1 = nn.Conv2d(3, 64, 3, 1, 1, bias=False)
    m.maxpool = nn.Identity()
    m.fc = nn.Linear(m.fc.in_features, 10)
    return m


def state_cpu(model):
    return {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}


def partition(labels, clients, alpha, rng):
    for _ in range(1000):
        out = [[] for _ in range(clients)]
        for c in range(10):
            ids = rng.permutation(np.flatnonzero(labels == c))
            p = rng.dirichlet(np.full(clients, alpha)) if alpha > 0 else np.ones(clients) / clients
            counts = rng.multinomial(len(ids), p)
            for i, chunk in enumerate(np.split(ids, np.cumsum(counts)[:-1])):
                out[i].extend(chunk.tolist())
        if min(map(len, out)) >= 2:
            return [np.array(a, dtype=np.int64) for a in out]
    raise ValueError("Unable to make nonempty partition")


def test_partition(labels, train_labels, parts, rng):
    out = [[] for _ in parts]
    for c in range(10):
        counts = np.array([(train_labels[p] == c).sum() for p in parts], dtype=float)
        probabilities = counts / counts.sum()
        ids = rng.permutation(np.flatnonzero(labels == c))
        n = rng.multinomial(len(ids), probabilities)
        for i, chunk in enumerate(np.split(ids, np.cumsum(n)[:-1])):
            out[i].extend(chunk.tolist())
    return [np.array(a, dtype=np.int64) for a in out]


def resolve_image(path):
    p = Path(path)
    if p.is_absolute() and p.exists():
        return p
    for base in [ROOT / "upstream/data_prepare/uba", ROOT / "upstream/data_prepare/attack",
                 ROOT / "upstream/data_prepare", ROOT]:
        candidate = (base / p).resolve()
        if candidate.exists():
            return candidate
    raise FileNotFoundError(path)


def read_container(container, chosen=None):
    keys = list(container) if chosen is None else list(chosen)
    images, labels = [], []
    for k in keys:
        info = container[k]
        with Image.open(resolve_image(info["path"])) as im:
            images.append(torch.from_numpy(np.array(im.convert("RGB"), copy=True)).permute(2, 0, 1).float() / 255)
        labels.append(int(info["other_info"][0]))
    return normalize(torch.stack(images)), torch.tensor(labels), np.asarray(keys, dtype=int)


def load_data(args):
    artifact = Path(args.artifact)
    if not artifact.exists():
        raise FileNotFoundError("Generate influence-crafted pert_result.pt with legacy_prepare.py first")
    # Trusted local official-code output, never load arbitrary downloaded pickle artifacts.
    saved = torch.load(artifact, map_location="cpu", weights_only=False)
    train = datasets.CIFAR10(args.data, train=True, download=False)
    test = datasets.CIFAR10(args.data, train=False, download=False)
    tx = normalize(torch.from_numpy(train.data.copy()).permute(0, 3, 1, 2).float() / 255)
    ty = torch.tensor(train.targets)
    ex = normalize(torch.from_numpy(test.data.copy()).permute(0, 3, 1, 2).float() / 255)
    ey = torch.tensor(test.targets)
    bd = saved["bd_train"]["bd_data_container"]["data_dict"]
    cv = saved["cv_pert"]["data_dict"]
    bx, by, bi = read_container(bd)
    cx, cy, ci = read_container(cv)
    if len(cx) == 0:
        raise ValueError("Missing influence-crafted cover samples")
    if set(bi) & set(ci):
        raise ValueError("Poison and cover indices overlap")
    if not torch.all(by == args.target):
        raise ValueError("Artifact target mismatch")
    trigger = np.array(Image.open(ROOT / "upstream/data_prepare/resource/badnet/trigger_image_grid.png").convert("RGB").resize((32, 32)))
    patch = torch.from_numpy(trigger.copy()).permute(2, 0, 1).float() / 255
    mask = patch.sum(0) > 0
    triggered_raw = torch.from_numpy(test.data.copy()).permute(0, 3, 1, 2).float() / 255
    # Upstream patch replacement is channel-wise, preserving zero-valued channels.
    triggered_raw = triggered_raw * (patch == 0) + patch * (patch > 0)
    px = normalize(triggered_raw)
    official_test = saved["bd_test"]["bd_data_container"]["data_dict"]
    official_x, _, official_ids = read_container(official_test, list(official_test)[:20])
    torch.testing.assert_close(px[official_ids], official_x, atol=1e-6, rtol=1e-6)
    if not torch.equal(cy, ty[ci]):
        raise ValueError("Cover labels are not original labels; this protocol assumes label-consistent covers")
    return tx, ty, ex, ey, px, bx, by, bi, cx, cy, ci, mask


def loader(x, y, batch, seed):
    return DataLoader(TensorDataset(x, y), batch_size=batch, shuffle=True, num_workers=0,
                      generator=torch.Generator().manual_seed(seed), drop_last=False)


def local_state(model, state, data, args, local_seed, device):
    model.load_state_dict(state)
    model.train()
    seed_all(local_seed)
    opt = torch.optim.SGD(model.parameters(), lr=args.lr, momentum=args.momentum,
                          weight_decay=args.weight_decay)
    for _ in range(args.local_epochs):
        for x, y in loader(*data, args.batch_size, local_seed):
            # BN at 1x1 spatial resolution needs >1 samples in training.
            if len(x) == 1:
                model.eval()
            else:
                model.train()
            x, y = x.to(device), y.to(device)
            opt.zero_grad(set_to_none=True)
            loss = nn.functional.cross_entropy(model(x), y)
            loss.backward()
            opt.step()
    return state_cpu(model)


def aggregate(states, counts):
    total = sum(counts)
    result = {}
    for key in states[0]:
        result[key] = sum(s[key].float() * (n / total) for s, n in zip(states, counts))
        if not states[0][key].is_floating_point():
            result[key] = result[key].round().to(states[0][key].dtype)
    return result


def calibrated_state(current, fresh, norms, params):
    """Calibrate trainable tensors, retaining fresh BN statistics and integer buffers."""
    result = dict(fresh)
    for k in params:
        direction = fresh[k] - current[k]
        norm = torch.linalg.vector_norm(direction)
        result[k] = current[k] + direction * (norms[k] / norm.clamp_min(1e-12))
    if not all(torch.isfinite(v).all() for v in result.values()):
        raise FloatingPointError("Nonfinite calibrated state")
    return result


def fl_train(initial, clients, out, args, seed, device, eval_data):
    path = out / "pre.pt"
    if path.exists():
        return torch.load(path, weights_only=True)
    model = make_model().to(device)
    current = initial
    counts = [len(d[1]) for d in clients]
    start = 0
    resume = out / "resume.pt"
    if resume.exists():
        saved = torch.load(resume, weights_only=True)
        current, start = saved["state"], saved["next_round"]
    for r in range(start, args.rounds):
        before = current
        states = [local_state(model, before, d, args, seed * 100000 + r * 100 + cid, device)
                  for cid, d in enumerate(clients)]
        current = aggregate(states, counts)
        if r % args.calibration_stride == 0:
            norms = {}
            for forget in [len(clients) - 1, 1]:
                ids = [i for i in range(len(clients)) if i != forget]
                retained = aggregate([states[i] for i in ids], [counts[i] for i in ids])
                norms[str(forget)] = {k: float(torch.linalg.vector_norm(retained[k].float() - before[k].float()))
                                     for k in before if k in dict(model.named_parameters())}
            torch.save(norms, out / f"norms_{r:03d}.pt")
        torch.save({"state": current, "next_round": r + 1}, resume)
        model.load_state_dict(current)
        metrics = predict(model, *eval_data, args, device)
        print(json.dumps({"phase": str(out), "round": r + 1,
                          "accuracy": float(metrics["correct"].mean()),
                          "asr": float(metrics["attack_success"][eval_data[1].numpy() != args.target].mean())}), flush=True)
    torch.save(current, path)
    return current


def post_train(initial, pre, clients, forget, history, mode, args, seed, device):
    model = make_model().to(device)
    current = initial if mode == "forget" else pre
    ids = [i for i in range(len(clients)) if i != forget] if mode == "forget" else list(range(len(clients)))
    counts = [len(clients[i][1]) for i in ids]
    params = set(dict(model.named_parameters()))
    for r in range(0, args.rounds, args.calibration_stride):
        states = [local_state(model, current, clients[i], args, seed * 100000 + 50000 + r * 100 + i, device)
                  for i in ids]
        fresh = aggregate(states, counts)
        if mode == "forget":
            norms = torch.load(history / f"norms_{r:03d}.pt", weights_only=True)[str(forget)]
            fresh = calibrated_state(current, fresh, norms, params)
        if not all(torch.isfinite(v).all() for v in fresh.values()):
            raise FloatingPointError("Nonfinite calibrated state")
        current = fresh
        print(f"POST {mode} forget={forget} step={r // args.calibration_stride + 1}", flush=True)
    return current


@torch.no_grad()
def predict(model, x, y, triggered, args, device):
    model.eval()
    logits, poisoned = [], []
    for i in range(0, len(x), args.eval_batch_size):
        logits.append(model(x[i:i + args.eval_batch_size].to(device)).cpu())
        poisoned.append(model(triggered[i:i + args.eval_batch_size].to(device)).cpu())
    logits, poisoned = torch.cat(logits), torch.cat(poisoned)
    probs = logits.softmax(1)
    other = logits.clone()
    other[:, args.target] = -torch.inf
    return {"correct": (logits.argmax(1) == y).float().numpy(),
            "attack_success": (poisoned.argmax(1) == args.target).float().numpy(),
            "target_prob": probs[:, args.target].numpy(), "confidence": probs.max(1).values.numpy(),
            "margin": (logits[:, args.target] - other.max(1).values).numpy()}


def attr_distribution(model, x, target, baselines, rng_seed, args, device):
    seed_all(rng_seed)
    model.eval()
    a = GradientShap(model).attribute(x[None].to(device), baselines=baselines.to(device),
                                       target=int(target), n_samples=args.shap_samples, stdevs=0.0).detach().cpu()
    spatial = a.abs().sum(1).flatten()
    mass = float(spatial.sum())
    q = (spatial + 1e-12) / (spatial.sum() + len(spatial) * 1e-12)
    return q.numpy(), mass


def jsd(p, q):
    m = (p + q) / 2
    return float(.5 * np.sum(p * np.log2(p / m)) + .5 * np.sum(q * np.log2(q / m)))


def attribution_set(model, ex, ey, px, ids, baseline, args, device):
    result = []
    for pos, idx in enumerate(ids):
        record = {}
        for name, x, t in [("clean_target", ex[idx], args.target), ("clean_true", ex[idx], int(ey[idx])),
                            ("trigger_target", px[idx], args.target)]:
            q, mass = attr_distribution(model, x, t, baseline, 700000 + int(idx) * 10 + t, args, device)
            record[name] = q
            record[name + "_mass"] = mass
        result.append(record)
        if (pos + 1) % 20 == 0:
            print(f"XAI {pos + 1}/{len(ids)}", flush=True)
    return result


def one_run(args, seed, alpha, data, device):
    out = Path(args.output) / f"seed_{seed}" / f"alpha_{alpha}"
    out.mkdir(parents=True, exist_ok=True)
    config = vars(args).copy()
    config.pop("seeds")
    config.pop("alphas")
    config.update(seed=seed, alpha=alpha)
    config_file = out / "config.json"
    if config_file.exists() and json.loads(config_file.read_text()) != config:
        raise ValueError("Existing run has a different config; choose another output directory")
    config_file.write_text(json.dumps(config, indent=2))
    if (out / "metrics.csv").exists():
        print(f"Already complete: {out}", flush=True)
        return
    tx, ty, ex, ey, px, bx, by, bi, cx, cy, ci, mask = data
    rng = np.random.default_rng(seed)
    eligible = np.setdiff1d(np.arange(len(tx)), np.union1d(bi, ci))
    if args.train_size:
        selected = []
        clean_n = args.train_size - 2 * int(args.train_size * .017)
        for c in range(10):
            selected.extend(rng.choice(eligible[ty[eligible].numpy() == c], clean_n // 10, replace=False))
        eligible = np.asarray(selected)
        poison_n = int(args.train_size * .017)
        bselect = rng.choice(len(bx), poison_n, replace=False)
        cselect = rng.choice(len(cx), poison_n, replace=False)
        bx, by, bi = bx[bselect], by[bselect], bi[bselect]
        cx, cy, ci = cx[cselect], cy[cselect], ci[cselect]
    parts_relative = partition(ty[eligible].numpy(), args.clients, alpha, rng)
    parts = [eligible[p] for p in parts_relative]
    test_parts = test_partition(ey.numpy(), ty.numpy(), parts, rng)
    clean_clients = [(tx[p], ty[p]) for p in parts]
    attack_clients = list(clean_clients)
    attack_clients[0] = (torch.cat([tx[parts[0]], bx]), torch.cat([ty[parts[0]], by]))
    # Mirrors upstream's auxiliary cover-client branch: duplicate client 0 clean data.
    # The auxiliary client is a training participant, not one of the 20 evaluation distributions.
    attack_clients.append((torch.cat([tx[parts[0]], cx]), torch.cat([ty[parts[0]], cy])))
    clean_clients[0] = (torch.cat([tx[parts[0]], tx[bi]]), torch.cat([ty[parts[0]], ty[bi]]))
    clean_clients.append((torch.cat([tx[parts[0]], tx[ci]]), torch.cat([ty[parts[0]], ty[ci]])))
    clean_dir, attack_dir = out / "clean", out / "attack"
    clean_dir.mkdir(exist_ok=True)
    attack_dir.mkdir(exist_ok=True)
    np.savez(out / "split.npz", **{f"train_{i}": p for i, p in enumerate(parts)},
             **{f"test_{i}": p for i, p in enumerate(test_parts)}, poison_ids=bi, cover_ids=ci)
    seed_all(seed)
    initial = state_cpu(make_model(args.pretrained))
    # Save/evaluate checkpoints before deletion independently of post-treatment outcomes.
    eval_ids = np.concatenate([rng.choice(np.flatnonzero(ey.numpy() == c), args.test_per_class, replace=False)
                               for c in range(10)])
    eval_data = (ex[eval_ids], ey[eval_ids], px[eval_ids])
    clean_pre = fl_train(initial, clean_clients, clean_dir, args, seed, device, eval_data)
    attack_pre = fl_train(initial, attack_clients, attack_dir, args, seed, device, eval_data)
    conditions = [("clean_forget", clean_pre, clean_clients, args.clients, clean_dir, "forget"),
                  ("clean_hold", clean_pre, clean_clients, args.clients, clean_dir, "hold"),
                  ("attack_forget", attack_pre, attack_clients, args.clients, attack_dir, "forget"),
                  ("attack_hold", attack_pre, attack_clients, args.clients, attack_dir, "hold"),
                  ("attack_benign_forget", attack_pre, attack_clients, 1, attack_dir, "forget")]
    # Fixed attribution subset stratified by class. Client metrics use empirical test class proportions.
    # This shares explanations across clients and is explicitly a distribution-weighted estimator.
    xai_ids = np.concatenate([rng.choice(np.flatnonzero(ey.numpy() == c), args.xai_per_class, replace=False)
                              for c in range(10)])
    baseline_ids = np.concatenate([rng.choice(eligible[ty[eligible].numpy() == c], args.baseline_per_class,
                                               replace=False) for c in range(10)])
    baseline = tx[baseline_ids]
    np.savez(out / "evaluation.npz", eval_ids=eval_ids, xai_ids=xai_ids, baseline_ids=baseline_ids)
    model = make_model().to(device)
    before_metrics, before_attrs = {}, {}
    for name, state in [("clean", clean_pre), ("attack", attack_pre)]:
        model.load_state_dict(state)
        before_metrics[name] = predict(model, ex, ey, px, args, device)
        cache = out / f"{name}_pre_attrs.pt"
        if cache.exists():
            before_attrs[name] = torch.load(cache, weights_only=False)
        else:
            before_attrs[name] = attribution_set(model, ex, ey, px, xai_ids, baseline, args, device)
            torch.save(before_attrs[name], cache)
    all_rows, global_rows = [], []
    for name, pre, clients, forget, hist, mode in conditions:
        path = out / f"{name}.pt"
        if path.exists():
            post = torch.load(path, weights_only=True)
        else:
            post = post_train(initial, pre, clients, forget, hist, mode, args, seed, device)
            torch.save(post, path)
        model.load_state_dict(post)
        after = predict(model, ex, ey, px, args, device)
        cache = out / f"{name}_attrs.pt"
        if cache.exists():
            attrs = torch.load(cache, weights_only=False)
        else:
            attrs = attribution_set(model, ex, ey, px, xai_ids, baseline, args, device)
            torch.save(attrs, cache)
        category = "clean" if name.startswith("clean") else "attack"
        before = before_metrics[category]
        per_image = []
        for idx, old, new in zip(xai_ids, before_attrs[category], attrs):
            row = {"image_id": int(idx), "class": int(ey[idx])}
            for kind in ["clean_target", "clean_true", "trigger_target"]:
                row["jsd_" + kind] = jsd(old[kind], new[kind])
            for label, kind in [("target", "clean_target"), ("true", "clean_true")]:
                row["delta_attr_mass_" + label] = new[kind + "_mass"] - old[kind + "_mass"]
            row["delta_trigger_coverage"] = float(new["trigger_target"][mask.flatten()] .sum() -
                                                   old["trigger_target"][mask.flatten()].sum())
            per_image.append(row)
        image_df = pd.DataFrame(per_image)
        image_df.to_csv(out / f"{name}_image_xai.csv", index=False)
        class_xai = image_df.groupby("class").mean(numeric_only=True)
        for cid, ids in enumerate(test_parts):
            if len(ids) == 0:
                continue
            non_target = ids[ey[ids].numpy() != args.target]
            row = {"seed": seed, "alpha": alpha, "condition": name, "client": cid,
                   "test_n": len(ids), "non_target_n": len(non_target),
                   "forgotten_n": len(clients[forget][1]) if mode == "forget" else 0,
                   "accuracy_pre": float(before["correct"][ids].mean()),
                   "delta_accuracy": float(after["correct"][ids].mean() - before["correct"][ids].mean()),
                   "asr_pre": float(before["attack_success"][non_target].mean()) if len(non_target) else None,
                   "asr_post": float(after["attack_success"][non_target].mean()) if len(non_target) else None}
            row["delta_asr"] = row["asr_post"] - row["asr_pre"] if len(non_target) else None
            for k in ["target_prob", "margin", "confidence"]:
                row[k + "_pre"] = float(before[k][ids].mean())
                row["delta_" + k] = float(after[k][ids].mean() - before[k][ids].mean())
            fractions = np.bincount(ey[ids].numpy(), minlength=10) / len(ids)
            row.update({f"class_fraction_{c}": float(fractions[c]) for c in range(10)})
            for k in [*__import__("analysis").XAI, "jsd_trigger_target", "delta_trigger_coverage"]:
                row[k] = float(sum(fractions[c] * class_xai.loc[c, k] for c in range(10)))
            all_rows.append(row)
        nt = ey.numpy() != args.target
        gr = {"condition": name, "accuracy_pre": float(before["correct"].mean()),
              "accuracy_post": float(after["correct"].mean()),
              "asr_pre": float(before["attack_success"][nt].mean()),
              "asr_post": float(after["attack_success"][nt].mean()),
              "forgotten_n": len(clients[forget][1]) if mode == "forget" else 0}
        gr["delta_asr"] = gr["asr_post"] - gr["asr_pre"]
        global_rows.append(gr)
        print(json.dumps(gr), flush=True)
    (out / "global_metrics.json").write_text(json.dumps({"seed": seed, "alpha": alpha,
                                                          "conditions": global_rows}, indent=2))
    pd.DataFrame(all_rows).to_csv(out / "metrics.csv", index=False)


def arguments():
    p = argparse.ArgumentParser()
    p.add_argument("--artifact", default="upstream/data_prepare/record/badnet_seed0/pert_result.pt")
    p.add_argument("--data", default="upstream/data_prepare/data/cifar10")
    p.add_argument("--output", default="results/pilot")
    p.add_argument("--seeds", nargs="+", type=int, default=[11, 22, 33])
    p.add_argument("--alphas", nargs="+", type=float, default=[.5])
    p.add_argument("--clients", type=int, default=20)
    p.add_argument("--rounds", type=int, default=10)
    p.add_argument("--local-epochs", type=int, default=1)
    p.add_argument("--train-size", type=int, default=10000, help="0 means all 50k data")
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--eval-batch-size", type=int, default=128)
    p.add_argument("--lr", type=float, default=.01)
    p.add_argument("--momentum", type=float, default=0.)
    p.add_argument("--weight-decay", type=float, default=0.)
    p.add_argument("--target", type=int, default=0)
    p.add_argument("--calibration-stride", type=int, default=2)
    p.add_argument("--test-per-class", type=int, default=50)
    p.add_argument("--xai-per-class", type=int, default=10)
    p.add_argument("--baseline-per-class", type=int, default=10)
    p.add_argument("--shap-samples", type=int, default=16)
    p.add_argument("--pretrained", action=argparse.BooleanOptionalAction, default=True)
    return p.parse_args()


if __name__ == "__main__":
    args = arguments()
    if args.rounds < 2 or args.calibration_stride < 1 or args.clients < 2:
        raise ValueError("Invalid experimental configuration")
    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    device = "cuda" if torch.cuda.is_available() else "cpu"
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"args": vars(args), "device": device, "torch": torch.__version__,
                "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name() if device == "cuda" else None,
                "artifact_sha256": hashlib.sha256(Path(args.artifact).read_bytes()).hexdigest(),
                "upstream_commit": subprocess.check_output(["git", "-C", "upstream", "rev-parse", "HEAD"], text=True).strip(),
                "attack_artifact_seed": 0, "training_participants": args.clients + 1,
                "packages": {name: importlib.metadata.version(name) for name in
                             ["torchvision", "captum", "numpy", "pandas", "scipy", "scikit-learn"]},
                "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                  for name in ["experiment.py", "analysis.py", "legacy_prepare.py"]},
                "interpretation": "Modified virtual-cover-client BadFU experiment; weighted calibrated unlearning. "
                "One fixed influence-crafted artifact shared across independent FL/partition seeds."}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    started = time.time()
    data = load_data(args)
    for seed in args.seeds:
        for alpha in args.alphas:
            one_run(args, seed, alpha, data, device)
    analyze(output)
    print(f"COMPLETED elapsed_seconds={time.time() - started:.1f}", flush=True)
