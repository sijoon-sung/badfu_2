"""Seed-grouped out-of-fold comparison. No trigger-aware feature enters the detector."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BASE = ["accuracy_pre", "delta_accuracy", "target_prob_pre", "delta_target_prob",
        "margin_pre", "delta_margin", "confidence_pre", "delta_confidence",
        "alpha", *[f"class_fraction_{c}" for c in range(9)]]
XAI = ["jsd_clean_target", "jsd_clean_true", "delta_attr_mass_target",
       "delta_attr_mass_true"]


def compare(df, family="ridge"):
    groups = df.seed.to_numpy()
    if len(np.unique(groups)) < 3:
        return {"status": "insufficient_seeds", "required": 3}, None
    if not np.isfinite(df["delta_asr"]).all():
        raise ValueError("Nonfinite outcome; exclude empty non-target test clients explicitly")
    y = df.delta_asr.to_numpy()
    predictions = df[["seed", "alpha", "condition", "client", "delta_asr"]].copy()
    fold_scores = []
    # Fixed regularization specified before running; no tuning on held-out seeds.
    for train, test in LeaveOneGroupOut().split(df, y, groups):
        fold = {"heldout_seed": int(groups[test][0])}
        for name, columns in [("baseline", BASE), ("with_xai", BASE + XAI)]:
            estimator = (Ridge(alpha=10.0) if family == "ridge" else
                         HistGradientBoostingRegressor(max_iter=100, max_leaf_nodes=7,
                                                        learning_rate=.05, min_samples_leaf=10,
                                                        l2_regularization=10., early_stopping=False,
                                                        random_state=20261009))
            pipe = make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True),
                                 StandardScaler(), estimator)
            pipe.fit(df.iloc[train][columns], y[train])
            pred = pipe.predict(df.iloc[test][columns])
            predictions.loc[df.index[test], name] = pred
            fold[name + "_mae"] = float(mean_absolute_error(y[test], pred))
            fold[name + "_rmse"] = float(np.sqrt(mean_squared_error(y[test], pred)))
        fold["mae_improvement"] = fold["baseline_mae"] - fold["with_xai_mae"]
        fold_scores.append(fold)
    # Cluster bootstrap over held-out seed blocks, never over dependent clients.
    improvement = np.array([f["mae_improvement"] for f in fold_scores])
    rng = np.random.default_rng(20261009)
    boot = rng.choice(improvement, size=(10000, len(improvement)), replace=True).mean(1)
    scores = {}
    for name in ["baseline", "with_xai"]:
        scores[name] = {"mae": float(mean_absolute_error(y, predictions[name])),
                        "rmse": float(np.sqrt(mean_squared_error(y, predictions[name]))),
                        "r2": float(r2_score(y, predictions[name]))}
    return {"status": "completed", "model_family": family, "rows": len(df), "seeds": sorted(map(int, np.unique(groups))),
            "baseline_features": BASE, "added_features": XAI,
            "scores": scores, "folds": fold_scores,
            "mean_seed_mae_improvement": float(improvement.mean()),
            "seed_bootstrap_95_ci": np.quantile(boot, [.025, .975]).tolist(),
            "interpretation": "Exploratory with few seeds; conditional on a shared attack artifact. "
            "Positive improvement means lower held-out MAE. No evidence of deletion validity."}, predictions


def run(root):
    root = Path(root)
    files = sorted(root.glob("seed_*/alpha_*/metrics.csv"))
    if not files:
        raise ValueError("No completed metric files")
    df = pd.concat([pd.read_csv(p) for p in files], ignore_index=True)
    df.to_csv(root / "all_metrics.csv", index=False)
    valid = df.loc[df.non_target_n > 0].reset_index(drop=True)
    report, predictions = compare(valid)
    nonlinear, nonlinear_predictions = compare(valid, "hist_gradient_boosting")
    report["nonlinear_sensitivity"] = nonlinear
    global_files = sorted(root.glob("seed_*/alpha_*/global_metrics.json"))
    global_metrics = [json.loads(p.read_text()) for p in global_files]
    report["global_metrics"] = global_metrics
    report["excluded_empty_clients"] = len(df) - len(valid)
    report["asr_activation_gate"] = {
        "definition": "attack_forget delta ASR >= 0.20 and pre ASR <= 0.30 (preregistered pilot gate)",
        "runs_passing": sum(any(r["condition"] == "attack_forget" and
                                  r["asr_pre"] <= .30 and r["delta_asr"] >= .20
                                  for r in g["conditions"]) for g in global_metrics),
        "runs_total": len(global_metrics)}
    report["controlled_activation_contrasts"] = []
    for g in global_metrics:
        c = {r["condition"]: r for r in g["conditions"]}
        report["controlled_activation_contrasts"].append({
            "seed": g["seed"], "alpha": g["alpha"],
            "attack_forget_minus_attack_hold_delta_asr": c["attack_forget"]["delta_asr"] - c["attack_hold"]["delta_asr"],
            "attack_forget_minus_benign_forget_delta_asr": c["attack_forget"]["delta_asr"] - c["attack_benign_forget"]["delta_asr"],
            "attack_forget_minus_clean_forget_delta_asr": c["attack_forget"]["delta_asr"] - c["clean_forget"]["delta_asr"]})
    report["per_run_spearman"] = []
    for key, part in valid[valid.condition == "attack_forget"].groupby(["seed", "alpha"]):
        if part.delta_asr.nunique() > 1 and part.jsd_clean_target.nunique() > 1:
            rho = spearmanr(part.delta_asr, part.jsd_clean_target).statistic
            report["per_run_spearman"].append({"seed": int(key[0]), "alpha": float(key[1]),
                                               "rho": float(rho)})
    (root / "analysis.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    if predictions is not None:
        predictions.to_csv(root / "out_of_fold_predictions.csv", index=False)
        nonlinear_predictions.to_csv(root / "out_of_fold_predictions_nonlinear.csv", index=False)
    summary = ["# Pilot result", "", "ASR and accuracy are fractions (multiply by 100 for percentage points).",
               "", f"Completed runs: {len(global_metrics)}",
               f"Activation gate passed: {report['asr_activation_gate']['runs_passing']}/{len(global_metrics)}",
               "", "This is a modified BadFU-style virtual-client deletion experiment, not an exact paper reproduction.",
               "Independent FL/data-partition seeds share one fixed influence-crafted cover artifact.", ""]
    if report["status"] == "completed":
        summary.extend([f"Baseline held-out MAE: {report['scores']['baseline']['mae']:.6f}",
                        f"XAI held-out MAE: {report['scores']['with_xai']['mae']:.6f}",
                        f"Mean seed MAE improvement: {report['mean_seed_mae_improvement']:.6f}",
                        f"Seed bootstrap 95% interval: {report['seed_bootstrap_95_ci']}", "",
                        f"Nonlinear baseline held-out MAE: {nonlinear['scores']['baseline']['mae']:.6f}",
                        f"Nonlinear + XAI held-out MAE: {nonlinear['scores']['with_xai']['mae']:.6f}", "",
                        "Three seeds cannot establish robust generalization. A failed activation gate prevents",
                        "interpreting a positive regression improvement as evidence of latent-backdoor detection."])
    summary.extend(["", "| Seed | Alpha | Condition | Accuracy pre | Accuracy post | ASR pre | ASR post | Delta ASR |",
                    "|---|---|---|---|---|---|---|---|"])
    for g in global_metrics:
        for r in g["conditions"]:
            summary.append(f"| {g['seed']} | {g['alpha']} | {r['condition']} | "
                           f"{100*r['accuracy_pre']:.2f}% | {100*r['accuracy_post']:.2f}% | "
                           f"{100*r['asr_pre']:.2f}% | {100*r['asr_post']:.2f}% | {100*r['delta_asr']:+.2f} pp |")
    (root / "REPORT.md").write_text("\n".join(summary), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ["global_metrics", "per_run_spearman"]}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    run(parser.parse_args().root)
