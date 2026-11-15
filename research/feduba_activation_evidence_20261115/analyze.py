"""Inspect sealed evaluation predictions and show paired activation examples."""

import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
import torch


BASE = Path("D:/FEDUBA_FIXED10_PAIR_20261103")
PLUS = Path("D:/FEDUBA_RELATED_HELPER_POSITIVE_EVALUATION_20261103")
RECOVERY = Path("D:/FEDUBA_POSITIVE_INDEPENDENT_RECOVERY_20261103")
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "result"
CLASSES = ("airplane", "automobile", "bird", "cat", "deer",
           "dog", "frog", "horse", "ship", "truck")
PHASES = ("pre", "benign", "minus", "plus")


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def json_receipt(path, expected):
    assert sha(path) == expected, path
    return json.loads(path.read_text(encoding="utf-8-sig"))


def packet(root, meta):
    path = Path(meta["path"])
    path = path if path.is_absolute() else root / path
    assert meta["payload_key"] is None
    assert path.stat().st_size == meta["bytes"] and sha(path) == meta["sha256"], path
    return torch.load(path, map_location="cpu", weights_only=True)


def render(examples, rows):
    fig, axes = plt.subplots(len(examples), 3, figsize=(11, len(examples) * 1.8), squeeze=False,
                             gridspec_kw={"width_ratios": [1, 1, 2.3]})
    for axis_row, example in zip(axes, examples, strict=True):
        for axis, key, title in zip(axis_row[:2], ("clean", "triggered"),
                                    ("Clean image", "Same triggered input"), strict=True):
            image = example[key].permute(1, 2, 0).add(1).div(2).clamp(0, 1).numpy()
            axis.imshow(image, interpolation="nearest")
            axis.set_title(title, fontsize=10)
            axis.axis("off")
        row = rows[example["source_id"]]
        lines = [f"Test ID {row['source_id']} | True class: {CLASSES[row['label']]}"]
        for phase, title in (("pre", "Before unlearning"), ("benign", "Benign unlearning"),
                             ("minus", "Minus-request FU"), ("plus", "Plus-request FU")):
            lines.append(f"{title}: {CLASSES[row[phase + '_triggered']]}")
        lines.append(f"Plus model on clean input: {CLASSES[row['plus_clean']]}")
        axis_row[2].axis("off")
        axis_row[2].text(0, .96, "\n".join(lines), va="top", fontsize=10, linespacing=1.5)
    fig.suptitle("FedUBA saved predictions | target = bird", fontsize=16)
    fig.text(.5, .014, "First qualifying ID per class. Plus-request diagnostic differs from paper Eq. 8.\n"
             "Full-test plus ASR 58.74%; preregistered success gates failed.",
             ha="center", fontsize=10)
    fig.tight_layout(rect=(0, .06, 1, .96))
    fig.savefig(OUT / "examples.png", dpi=160)
    plt.close(fig)


def main():
    torch.set_num_threads(1)
    OUT.mkdir(exist_ok=False)
    baseline = json_receipt(BASE / "PAIR_EVAL_RESULT.json",
        "07e63f6361da94ef4ddfa0f9c4cad2ca7a3ca377da3aa7aa3fdd7d442b1ea7ac")
    positive = json_receipt(PLUS / "PAIR_EVAL_RESULT.json",
        "b6a320a863247f54c8b950057f622361dedea147572a1da71a9640cfc858c24e")
    baseline_audit = json_receipt(BASE / "PAIR_EVAL_VERIFIED.json",
        "b6e95cde8cab64afb645b565a87cb48865d7adf56bd1248a094e8bfb30bdaabe")
    positive_audit = json_receipt(RECOVERY / "RECOVERY_VERIFIED.json",
        "6294fcac2119bfb73d33c7de14fcf9d484798cb1fbf9c988e33b33089b97f93f")
    assert baseline_audit["state"] == positive_audit["state"] == "passed"
    assert positive_audit["primary_result_sha256"] == sha(PLUS / "PAIR_EVAL_RESULT.json")
    assert positive_audit["baseline_evaluation_sha256"] == sha(BASE / "PAIR_EVAL_RESULT.json")
    assert baseline["target"] == positive["target"] == 2
    assert baseline["input_packets"] == positive["input_packets"]
    assert baseline["delta"] == positive["delta"]
    selections = {}
    for branch in ("benign", "minus", "plus"):
        case = f"feduba.public_fixed10.cifar10.s42.sss125.{branch}requestfu20.20261103"
        if branch == "benign":
            case = "feduba.public_fixed10.cifar10.s42.sss125.benignfu20.20261103"
        selection = json.loads(subprocess.check_output([
            sys.executable, "D:/TRAJECTORY_CATALOG_20261023/select_case.py",
            case, "--purpose", "diagnostic"], encoding="utf-8"))
        assert selection["guard_state"] == "all_snapshot_files_verified_on_this_host"
        selections[branch] = selection
    sources = {"pre": (BASE, baseline, "pre"), "benign": (BASE, baseline, "benign"),
               "minus": (BASE, baseline, "attack"), "plus": (PLUS, positive, "attack")}
    for branch in ("benign", "minus", "plus"):
        _, receipt, key = sources[branch]
        assert selections[branch]["server_inputs"]["pre"]["sha256"] == baseline["source_models"]["pre"]["sha256"]
        assert selections[branch]["server_inputs"]["post"]["sha256"] == receipt["source_models"][key]["sha256"]
    rows, exemplars = [], {}
    for batch, meta in enumerate(baseline["input_packets"]):
        images = packet(BASE, meta)
        ids, labels = images["source_ids"], images["labels"]
        assert torch.equal(ids, torch.arange(len(rows), len(rows) + len(labels)))
        assert ids.dtype == labels.dtype == torch.int64
        assert labels.shape == ids.shape and ((labels >= 0) & (labels < 10)).all()
        predictions = {}
        for phase, (root, receipt, key) in sources.items():
            logits = packet(root, receipt["logit_packets"][key][batch])
            assert torch.equal(logits["source_ids"], ids)
            assert logits["input_packet"]["sha256"] == meta["sha256"]
            assert logits["source_model"] == receipt["source_models"][key]
            for kind in ("clean", "triggered"):
                values = logits[kind + "_logits"]
                assert values.shape == (len(ids), 10) and torch.isfinite(values).all()
                predictions[phase + "_" + kind] = values.argmax(1).tolist()
        for i, (source_id, label) in enumerate(zip(ids.tolist(), labels.tolist(), strict=True)):
            row = {"source_id": source_id, "label": label,
                   **{key: value[i] for key, value in predictions.items()}}
            row["strict_activation"] = (
                label != 2 and row["pre_triggered"] == row["benign_triggered"] == label
                and row["plus_triggered"] == 2 and row["plus_clean"] == label)
            rows.append(row)
            if row["strict_activation"] and label not in exemplars:
                exemplars[label] = {"source_id": source_id,
                    "clean": images["clean_input"][i].clone(),
                    "triggered": images["triggered_input"][i].clone()}
    assert len(rows) == 10000
    eligible = [row for row in rows if row["label"] != 2]
    assert len(eligible) == 9000
    metrics = {}
    for phase, (_, receipt, key) in sources.items():
        clean_correct = sum(row[phase + "_clean"] == row["label"] for row in rows)
        hits = sum(row[phase + "_triggered"] == 2 for row in eligible)
        metrics[phase] = {"clean_correct": clean_correct, "N": 10000, "CA_pct": clean_correct / 100,
                         "target_hits": hits, "non_target_N": 9000, "ASR_pct": hits / 90}
        assert clean_correct == receipt["models"][key]["clean_correct"]
        assert hits == receipt["models"][key]["triggered_target_hits"]
    transition = {
        "pre_nontarget_to_plus_target": sum(r["pre_triggered"] != 2 and r["plus_triggered"] == 2 for r in eligible),
        "pre_target_to_plus_nontarget": sum(r["pre_triggered"] == 2 and r["plus_triggered"] != 2 for r in eligible),
        "pre_benign_correct_plus_clean_correct": sum(r["pre_triggered"] == r["benign_triggered"] == r["plus_clean"] == r["label"] for r in eligible),
        "strict_activation": sum(r["strict_activation"] for r in eligible),
    }
    assert transition["pre_nontarget_to_plus_target"] - transition["pre_target_to_plus_nontarget"] == 5287 - 1813
    with (OUT / "predictions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    chosen = [exemplars[label] for label in sorted(exemplars)[:6]]
    if chosen:
        render(chosen, rows)
    summary = {
        "state": "verified_saved_predictions", "metrics": metrics, "transitions": transition,
        "examples": [rows[e["source_id"]] for e in chosen],
        "original_operational_gate": positive["minimum_operational_gate"],
        "case_ids": {key: value["case_id"] for key, value in selections.items()},
        "source_sha256": sha(Path(__file__)), "predictions_sha256": sha(OUT / "predictions.csv"),
        "model_training_steps": 0, "model_forward_calls": 0,
        "request_sign_scope": "plus diagnostic; paper Eq8 minus retained in comparison",
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"metrics": metrics, "transitions": transition, "example_count": len(chosen)}))


if __name__ == "__main__":
    main()
