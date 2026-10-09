"""Export scientific summary plots after a completed analysis."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plot(root):
    root = Path(root)
    report = json.loads((root / "analysis.json").read_text())
    if report["status"] != "completed":
        return
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2), layout="constrained")
    for ax, model, title in [(axes[0], report, "Linear baseline"),
                             (axes[1], report["nonlinear_sensitivity"], "Nonlinear baseline")]:
        folds = model["folds"]
        x = np.arange(len(folds))
        ax.bar(x - .18, [100 * f["baseline_mae"] for f in folds], .36, label="Outputs / accuracy", color="#63788a")
        ax.bar(x + .18, [100 * f["with_xai_mae"] for f in folds], .36, label="+ Clean XAI", color="#158f88")
        ax.set_xticks(x, [str(f["heldout_seed"]) for f in folds])
        ax.set_xlabel("Held-out seed")
        ax.set_ylabel("MAE of ASR change (percentage points)")
        ax.set_title(title)
        ax.legend(frameon=False, fontsize=8)
        ax.spines[["top", "right"]].set_visible(False)
    ax = axes[2]
    runs = report["global_metrics"]
    for g in runs:
        c = {r["condition"]: r for r in g["conditions"]}
        ax.plot([0, 1], [100 * c["attack_forget"]["asr_pre"], 100 * c["attack_forget"]["asr_post"]],
                "o-", label=f"Seed {g['seed']}, alpha={g['alpha']}")
    ax.set_xticks([0, 1], ["Before", "After cover deletion"])
    ax.set_ylabel("Global ASR (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Attack activation check")
    ax.legend(frameon=False, fontsize=7)
    ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Pilot: seed-held-out incremental XAI value; fixed cover-generation artifact", fontsize=12)
    fig.savefig(root / "summary.png", dpi=180)
    fig.savefig(root / "summary.pdf")
    plt.close(fig)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("root")
    plot(p.parse_args().root)
