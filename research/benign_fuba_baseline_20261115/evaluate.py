"""Check archived metric counts or independently verify benign endpoints."""

import argparse
import json
import math
from pathlib import Path


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def percentage(record, numerator, denominator, reported):
    hits, count = record[numerator], record[denominator]
    if (type(hits) is not int or type(count) is not int or count <= 0
            or not 0 <= hits <= count):
        raise ValueError(f"Invalid {numerator}/{denominator}: {hits}/{count}")
    actual = 100 * hits / count
    if not math.isclose(actual, record[reported], rel_tol=0, abs_tol=1e-10):
        raise ValueError(f"{reported}: {record[reported]} disagrees with {actual}")
    return actual


def audit_counts(path):
    receipt = load(path)
    return {
        phase: {
            "CA_pct": percentage(receipt[phase], "clean_correct", "N", "CA_pct"),
            "ASR_pct": percentage(receipt[phase], "target_successes", "non_target_N", "ASR_pct"),
        }
        for phase in ("before", "after")
    }


def verify_run(output, raw):
    import torch
    from benchmark import Net, RAW_FILES, clean_counts, digest, read_split

    torch.set_num_threads(2)
    profile = load(output / "profile.json")
    result = load(output / "result.json")
    if profile["device"] != "cpu" or profile["torch"] != str(torch.__version__):
        raise ValueError("Exact-count verification requires the original CPU runtime")
    if profile["source_sha256"] != digest(Path(__file__).with_name("benchmark.py")):
        raise ValueError("Training source does not match profile")
    if profile["dataset_sha256"] != {name: digest(raw / name) for name in RAW_FILES}:
        raise ValueError("Data provenance does not match profile")
    events = [json.loads(line) for line in (output / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    for stage in ("before_fl", "retained_retrain"):
        rounds = [event for event in events if event["stage"] == stage]
        if [event["round"] for event in rounds] != list(range(1, profile["rounds"] + 1)):
            raise ValueError(f"Incomplete {stage} ledger")
        for row, drawn in zip(rounds, profile["schedule"], strict=True):
            expected = drawn if stage == "before_fl" else [
                client for client in drawn if client != profile["deleted"]
            ]
            if row["participants"] != expected or row["samples_per_epoch"] != 3000 * len(expected):
                raise ValueError(f"Invalid participation in {stage} round {row['round']}")
    kd_rows = [event for event in events if event["stage"] == "benign_kd"]
    if ([row["epoch"] for row in kd_rows] != list(range(1, profile["kd_epochs"] + 1))
            or any(row["samples"] != 3000 or not math.isfinite(row["mean_kl"]) for row in kd_rows)):
        raise ValueError("Incomplete KD ledger")
    if result["deleted_rounds"] != [
        n for n, row in enumerate(profile["schedule"], 1) if profile["deleted"] in row
    ]:
        raise ValueError("Deletion ledger does not match the participation schedule")

    test = read_split(raw, *RAW_FILES[2:], 10000)
    model = Net()
    verified = {}
    for name in ("before", "benign_kd", "retained_retrain"):
        claimed = result[name]
        model_file = output / f"{name}.pt"
        if claimed["file"] != model_file.name or claimed["sha256"] != digest(model_file):
            raise ValueError(f"Checkpoint identity mismatch: {name}")
        weights = torch.load(model_file, map_location="cpu", weights_only=True)
        if not all(torch.isfinite(tensor).all().item() for tensor in weights.values()):
            raise ValueError(f"Nonfinite checkpoint: {name}")
        model.load_state_dict(weights, strict=True)
        actual = clean_counts(model, *test, torch.device("cpu"))
        if any(actual[key] != claimed[key] for key in actual):
            raise ValueError(f"Recorded metrics differ from independent evaluation: {name}")
        verified[name] = {**actual, "sha256": claimed["sha256"]}

    gap = verified["benign_kd"]["CA_pct"] - verified["retained_retrain"]["CA_pct"]
    if result["kd_minus_retrain_CA_pp"] != gap or result["utility_within_2pp"] != (abs(gap) <= 2):
        raise ValueError("The reported utility comparison is inconsistent")
    return {"state": "verified", "result_sha256": digest(output / "result.json"),
            "evaluator_sha256": digest(Path(__file__)), **verified}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    counts = commands.add_parser("counts")
    counts.add_argument("receipt", type=Path)
    run = commands.add_parser("run")
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--mnist-raw", type=Path, required=True)
    args = parser.parse_args()
    report = audit_counts(args.receipt) if args.mode == "counts" else verify_run(args.output, args.mnist_raw)
    print(json.dumps(report, indent=2, allow_nan=False))
