"""Read saved local branches and compare only their genuinely updated weights.

No images, model forward passes, optimizer steps, or checkpoint writes.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

import torch


def sha256(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            result.update(block)
    return result.hexdigest()


def norms(pre, retained, forget, keys):
    r2 = f2 = 0.0
    for key in keys:
        r2 += float((retained[key].double() - pre[key].double()).square().sum())
        f2 += float((forget[key].double() - pre[key].double()).square().sum())
    nr, nf = r2**0.5, f2**0.5
    return dict(retained_norm=nr, forget_norm=nf, ratio=nr / nf if nf else None,
                tensors=len(keys), parameters=sum(pre[key].numel() for key in keys))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(4)
    root = args.repo / "research_20261018/fl_information"
    cases = []
    for seed in (71, 72, 73):
        for case, scenario, folder, phase in [
            ("attack", "attack", "local_witness_v3", "both"),
            ("normal", "normal_cover", "local_witness_v3", "cover_only"),
            ("delete_poison", "delete_poison", "local_witness_requests", "both"),
            ("delete_both", "delete_both", "local_witness_requests", "both"),
        ]:
            cases.append((f"{case}{seed}", seed, "fedavg_v1", phase, folder, scenario))
    cases.extend([
        ("attack74", 74, "fedavg_confirm74", "both", "local_witness_confirm74", "attack"),
        ("safe74", 74, "fedavg_confirm74", "both", "local_witness_confirm74_safe", "equal_size_safe"),
        ("prior74", 74, "fedavg_benign_prior74", "both", "local_witness_benign_prior74", "benign_prior"),
        ("noise74", 74, "fedavg_label_noise74", "both", "local_witness_label_noise74", "label_noise"),
    ])
    rows = []
    for name, seed, run, phase, folder, scenario in cases:
        base = root / run / f"seed_{seed}" / f"{phase}.pt"
        branch = root / folder / f"seed_{seed}_{scenario}"
        files = [base, branch / "retained.pt", branch / "forget.pt"]
        pre, retained, forget = [torch.load(path, weights_only=True, map_location="cpu") for path in files]
        manifest_path = root / folder / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["scope"] == "layer4"
        parameter_keys = [key for key in pre if key.endswith(("weight", "bias"))]
        conv = [key for key in parameter_keys if key.startswith("layer4.") and pre[key].ndim == 4]
        layer4 = [key for key in parameter_keys if key.startswith("layer4.")]
        assert len(conv) == 5
        outside = [key for key in parameter_keys if not key.startswith("layer4.")]
        unchanged = all(torch.equal(state[key], pre[key]) for state in (retained, forget) for key in outside)
        assert unchanged, "A parameter outside the declared scope changed"
        bn_keys = [key for key in pre if key.endswith(("running_mean", "running_var"))]
        bn_unchanged = all(torch.equal(state[key], pre[key]) for state in (retained, forget) for key in bn_keys)
        rows.append(dict(
            case=name, seed=seed, conv_only=norms(pre, retained, forget, conv),
            layer4_all_parameters=norms(pre, retained, forget, layer4),
            per_conv={key: norms(pre, retained, forget, [key]) for key in conv},
            outside_layer4_unchanged=unchanged, bn_running_statistics_unchanged=bn_unchanged,
            original_branch_training={key: manifest.get(key) for key in
                                      ("steps", "lr", "scope", "anchor_size", "anchor_ce", "anchor_kl", "clip_grad")},
            source_hashes={str(path): sha256(path) for path in files + [manifest_path]},
        ))
    print(json.dumps(dict(
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        calculation="Global Frobenius norm over the five layer4 convolution weight tensors, retained/forget",
        images_loaded=0, new_training_steps=0, rows=rows,
        caveat="Original shadow training used 100 steps and 500 clean-reference anchors; this audit only reads weights."
    ), indent=2))


if __name__ == "__main__":
    main()
