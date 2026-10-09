"""Execute upstream badfu.py without changing its training or unlearning functions.

Compatibility adaptations: absolute data paths, trusted local legacy pickle,
Windows workers=0, disk/CPU historical-model storage, logging/checkpoint hooks.
The destructive, broken final shell postprocess is not applied to generated images.
"""
import argparse
import ast
import copy
import hashlib
import json
import os
import random
import subprocess
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "upstream/badfu.py"
HISTORIES = {"old_CMs", "old_GMs", "old_CMs_b", "old_GMs_b"}
PHASES = ["global_model_clean", "global_model_bd", "global_model_cv",
          "global_model_for_ul", "global_model_ul", "global_model_ul_b"]


class TrainingPaused(Exception):
    pass


def pause_at_checkpoint(output, metrics):
    output = Path(output)
    if (output / "PAUSE").exists():
        (output / "paused.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        raise TrainingPaused("Pause requested; model and all RNG states are saved")


def cpu_state(model):
    return {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}


def atomic_save(obj, path):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    torch.save(obj, temp)
    os.replace(temp, path)


def rng_state():
    return {"torch": torch.get_rng_state(), "cuda": torch.cuda.get_rng_state_all(),
            "numpy": np.random.get_state(), "python": random.getstate()}


def restore_rng(saved):
    torch.set_rng_state(saved["torch"])
    torch.cuda.set_rng_state_all(saved["cuda"])
    np.random.set_state(saved["numpy"])
    random.setstate(saved["python"])


class DiskHistory:
    """Preserve state tensors exactly, reload models without consuming training RNG."""
    def __init__(self, name, output, namespace):
        self.path = Path(output) / "history" / name
        self.path.mkdir(parents=True, exist_ok=True)
        self.namespace = namespace
        self.count = len(list(self.path.glob("*.pt")))

    def append(self, obj):
        is_list = isinstance(obj, list)
        models = obj if is_list else [obj]
        payload = {"is_list": is_list,
                   "models": [{"class": type(m).__name__, "state": cpu_state(m)} for m in models]}
        # A crash can occur between saving history and the round checkpoint.
        # Index by the source loop's round so resume overwrites that uncommitted round.
        index = int(self.namespace.get("r", self.count))
        atomic_save(payload, self.path / f"{index:03d}.pt")
        self.count = max(self.count, index + 1)

    def __getitem__(self, idx):
        saved = torch.load(self.path / f"{idx:03d}.pt", map_location="cpu", weights_only=True)
        rng = rng_state()
        try:
            models = []
            for item in saved["models"]:
                m = self.namespace[item["class"]]().to(self.namespace["device"])
                m.load_state_dict(item["state"])
                models.append(m)
        finally:
            restore_rng(rng)
        return models if saved["is_list"] else models[0]

    def __len__(self):
        return self.count


def resolve_original(path):
    p = Path(path)
    if p.is_absolute() and p.exists():
        return p
    for base in [ROOT / "upstream/data_prepare/uba", ROOT / "upstream/data_prepare/attack", ROOT]:
        q = (base / p).resolve()
        if q.exists():
            return q
    raise FileNotFoundError(f"Upstream artifact references missing image: {path}")


def canonical_artifact(path, output):
    obj = torch.load(path, map_location="cpu", weights_only=False)
    count = 0

    def rewrite(value):
        nonlocal count
        if isinstance(value, dict):
            for k, v in value.items():
                if k == "path" and isinstance(v, str):
                    value[k] = str(resolve_original(v))
                    count += 1
                else:
                    rewrite(v)
        elif isinstance(value, (list, tuple)):
            for v in value:
                rewrite(v)
    rewrite(obj)
    target = Path(output) / "input.pt"
    atomic_save(obj, target)
    return target, count


class Compatibility(ast.NodeTransformer):
    def __init__(self, artifact, output, smoke):
        self.artifact, self.output, self.smoke = artifact, output, smoke
        self.changes = []

    def visit_Assign(self, node):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name == "data_path":
                node.value = ast.Constant(str(self.artifact))
                self.changes.append("data_path -> same generated artifact, absolute image references")
            elif name in HISTORIES and isinstance(node.value, ast.List):
                node.value = ast.parse(f"_DiskHistory('{name}', _output, globals())").body[0].value
                self.changes.append(f"{name}: GPU list -> exact state storage on disk")
            elif self.smoke and name in ["num_rounds", "local_epochs"]:
                node.value = ast.Constant(2 if name == "num_rounds" else 1)
                self.changes.append(f"SMOKE ONLY {name} override")
        return self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "CIFAR10":
            for k in node.keywords:
                if k.arg == "root":
                    k.value = ast.Constant(str(ROOT / "upstream/data_prepare/data/cifar10"))
                    self.changes.append("CIFAR10 root -> existing unmodified CIFAR files")
        if isinstance(node.func, ast.Name) and node.func.id == "DataLoader":
            for k in node.keywords:
                if k.arg == "num_workers":
                    k.value = ast.Constant(0)
                    self.changes.append("Windows DataLoader num_workers=0")
        return self.generic_visit(node)

    def visit_For(self, node):
        phase = None
        if isinstance(node.target, ast.Name) and node.target.id == "r":
            for statement in node.body:
                if isinstance(statement, ast.Assign):
                    for target in statement.targets:
                        if isinstance(target, ast.Name) and target.id in PHASES:
                            phase = target.id
        node = self.generic_visit(node)
        if phase:
            prefix = ast.parse(f"if _resume_skip('{phase}', r, globals()):\n    continue").body
            suffix = ast.parse(f"_checkpoint('{phase}', r, globals())").body
            node.body = [*prefix, *node.body, *suffix]
        return node


def build_tree(artifact, output, smoke=False):
    original = ast.parse(SOURCE.read_text(encoding="utf-8"))
    original_defs = {n.name: ast.dump(n, include_attributes=False) for n in original.body
                     if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    modifier = Compatibility(artifact, output, smoke)
    changed = modifier.visit(copy.deepcopy(original))
    ast.fix_missing_locations(changed)
    changed_defs = {n.name: ast.dump(n, include_attributes=False) for n in changed.body
                    if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    if original_defs != changed_defs:
        raise RuntimeError("Compatibility layer changed an upstream function/class definition")
    return changed, modifier.changes, sorted(original_defs)


def main(args):
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    torch.hub.set_dir(str(ROOT / "data/torch"))
    if not torch.__version__.startswith("2.4.1") or torch.version.cuda != "11.8":
        raise RuntimeError("Use the dedicated original Conda environment: PyTorch 2.4.1 + cu118")
    source_sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    artifact_sha = hashlib.sha256(Path(args.artifact).read_bytes()).hexdigest()
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        if (old["source_sha256"], old["artifact_sha256"], old["smoke_only"]) != (source_sha, artifact_sha, args.smoke):
            raise RuntimeError("Source/artifact/mode changed; choose a fresh output folder")
    artifact, image_refs = canonical_artifact(args.artifact, output)
    tree, changes, untouched_defs = build_tree(artifact, output, args.smoke)
    manifest = {"upstream_commit": subprocess.check_output(["git", "-C", "upstream", "rev-parse", "HEAD"], text=True).strip(),
                "source_sha256": source_sha, "artifact_sha256": artifact_sha,
                "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "torch": torch.__version__, "cuda": torch.version.cuda, "numpy": np.__version__,
                "smoke_only": args.smoke, "compatibility_changes": changes,
                "unchanged_function_and_class_definitions": untouched_defs,
                "verified_existing_image_references": image_refs,
                "original_parameters": {"clients": 5, "dominant_ratio": .7, "rounds": 40, "local_epochs": 5, "seed": 42},
                "preparation_exception": "The final rm/mv commands of upstream prepare_data.sh invalidate image metadata paths. "
                "Generated cover images are retained without changing their values, labels, indices or ratios.",
                "interpretation": "Original training/unlearning execution with documented preparation-path exception; "
                "not a claim of exact end-to-end shell-script reproduction."}
    manifest_path.write_text(json.dumps(manifest, indent=2))
    progress_cache = {}
    for phase in PHASES:
        p = output / f"{phase}_latest.pt"
        if p.exists():
            progress_cache[phase] = torch.load(p, map_location="cpu", weights_only=False)

    def resume_skip(phase, r, namespace):
        saved = progress_cache.get(phase)
        if saved and r <= saved["round"]:
            if r == saved["round"]:
                namespace[phase].load_state_dict(saved["state"])
                restore_rng(saved["rng"])
                print(f"RESUMED {phase} after round {r + 1}", flush=True)
            return True
        return False

    def checkpoint(phase, r, namespace):
        state = cpu_state(namespace[phase])
        finite = all(torch.isfinite(v).all().item() for v in state.values())
        metrics = {"phase": phase, "round": r + 1,
                   "accuracy_percent": namespace["global_clean_acc"],
                   "asr_percent": namespace["global_clean_asr"], "finite_state": finite}
        with (output / "round_metrics.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(metrics) + "\n")
        atomic_save({"state": state, "round": r, "rng": rng_state(), "metrics": metrics},
                    output / f"{phase}_latest.pt")
        print("REFERENCE_CHECKPOINT " + json.dumps(metrics), flush=True)
        if not finite:
            raise FloatingPointError("Unchanged upstream algorithm produced a nonfinite state; no silent correction applied")
        pause_at_checkpoint(output, metrics)

    original_load = torch.load

    def trusted_load(*positional, **kwargs):
        kwargs.setdefault("weights_only", False)
        return original_load(*positional, **kwargs)

    torch.load = trusted_load
    namespace = {"__name__": "__main__", "__file__": str(SOURCE), "_DiskHistory": DiskHistory,
                 "_output": str(output), "_checkpoint": checkpoint, "_resume_skip": resume_skip}
    try:
        exec(compile(tree, str(SOURCE), "exec"), namespace)
        summary = {}
        for phase in PHASES:
            accuracy, class_accuracy, asr = namespace["evaluate_model"](
                namespace[phase], namespace["device"], namespace["test_loader"],
                namespace["bd_test_loader"], backdoor_target=0)
            summary[phase] = {"accuracy_percent": accuracy, "class_accuracy_percent": class_accuracy,
                              "asr_percent": asr}
        summary["cover_client_deletion_delta_asr_pp"] = summary["global_model_ul"]["asr_percent"] - summary["global_model_for_ul"]["asr_percent"]
        (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False))
        labels = {"global_model_clean": "Clean FL", "global_model_bd": "Backdoor-only FL",
                  "global_model_cv": "Backdoor + cover FL",
                  "global_model_for_ul": "Before auxiliary cover-client deletion",
                  "global_model_ul": "After auxiliary cover-client deletion",
                  "global_model_ul_b": "After client 1 deletion (other original branch)"}
        report = ["# Original training/unlearning execution", "",
                  "Original defaults: 5 clients, dominant ratio 0.7, 40 rounds, 5 local epochs, seed 42.",
                  "The auxiliary-client branch has six actual participants before deletion.",
                  f"Smoke-only QA run: {args.smoke}", "",
                  "| Original phase | Accuracy | ASR |", "|---|---|---|"]
        for phase in PHASES:
            report.append(f"| {labels[phase]} | {summary[phase]['accuracy_percent']:.2f}% | "
                          f"{summary[phase]['asr_percent']:.2f}% |")
        delta = summary["cover_client_deletion_delta_asr_pp"]
        report.extend(["", f"Auxiliary cover-client deletion ASR change: {delta:+.2f} percentage points.", "",
                       "Training, aggregation, evaluation and unlearning function definitions are unchanged.",
                       "Compatibility adaptations and exact upstream source hash are in manifest.json.",
                       "Preparation exception: generated images are preserved before the public shell script's",
                       "broken final delete/move operations; only metadata path strings are made absolute.",
                       "This is not a claim that the published preparation shell script runs unchanged end to end.",
                       "A smoke run cannot establish attack reproduction; a single full seed cannot establish robustness."])
        (output / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
        print("REFERENCE_COMPLETED " + json.dumps(summary), flush=True)
    except TrainingPaused as e:
        print("REFERENCE_PAUSED " + str(e), flush=True)
    except Exception as e:
        (output / "failure.json").write_text(json.dumps({"type": type(e).__name__, "message": str(e)}, indent=2))
        raise
    finally:
        torch.load = original_load


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", default="upstream/data_prepare/record/badnet_original/pert_result.pt")
    parser.add_argument("--output", default="results/reference")
    parser.add_argument("--smoke", action="store_true", help="Only execution QA (2 rounds / 1 epoch); never attack reproduction evidence")
    main(parser.parse_args())
