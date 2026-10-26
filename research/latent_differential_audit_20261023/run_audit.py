"""Independent reproduction and verification of latent feature differential evaluation.
Evaluates confirmed checkpoints (s20261023_v1) strictly under unknown-target conditions.
"""
import sys
from pathlib import Path
import json
import torch
import torch.nn as nn

ROOT = Path("C:/Users/sijoo/Documents/ChatGPT/badFU")
CONFIRMED_ROOT = ROOT / "CONFIRMED_CHECKPOINTS" / "BadFU_s20261023_v1"
sys.path.insert(0, str(CONFIRMED_ROOT))
import load_confirmed

device = "cuda" if torch.cuda.is_available() else "cpu"

# 1. Load Confirmed Models
models = {
    "attack_pre": load_confirmed.load_model("pre", device=device, root=CONFIRMED_ROOT),
    "attack_post": load_confirmed.load_model("post", device=device, root=CONFIRMED_ROOT),
    "clean_pre": load_confirmed.load_model("clean_pre", device=device, root=CONFIRMED_ROOT),
    "clean_post": load_confirmed.load_model("clean_post", device=device, root=CONFIRMED_ROOT),
    "clean_big_post": load_confirmed.load_model("clean_big_post", device=device, root=CONFIRMED_ROOT),
}

# 2. Load Evaluation Data
data_path = ROOT / "research" / "stage1_20261020" / "assets" / "cifar_raw.pt"
data = torch.load(data_path, map_location="cpu", weights_only=True)
test_x = data["test_x"].permute(0, 3, 1, 2).float() / 255.0
mean = torch.tensor([0.4914, 0.4822, 0.4465]).view(1, 3, 1, 1)
std = torch.tensor([0.2023, 0.1994, 0.2010]).view(1, 3, 1, 1)
test_x = (test_x - mean) / std
test_y = data["test_y"]

N_EVAL = 500
eval_x = test_x[:N_EVAL].to(device)
eval_y = test_y[:N_EVAL].to(device)

def get_features_and_logits(model, x):
    m = model.model
    out = m.relu(m.bn1(m.conv1(x)))
    out = m.maxpool(out)
    out = m.layer1(out)
    out = m.layer2(out)
    out = m.layer3(out)
    out = m.layer4(out)
    out = m.avgpool(out)
    feats = torch.flatten(out, 1)
    logits = m.fc(feats)
    return feats, logits

def evaluate_latent_differential(pre_model, post_model, x_batch, y_batch, steps=100, lr=0.05):
    with torch.no_grad():
        feats_pre, logits_pre = get_features_and_logits(pre_model, x_batch)
        feats_post, logits_post = get_features_and_logits(post_model, x_batch)
        preds_pre = logits_pre.argmax(dim=-1)
        preds_post = logits_post.argmax(dim=-1)
        correct_mask = (preds_pre == y_batch) & (preds_post == y_batch)
        
    feats_pre = feats_pre[correct_mask]
    feats_post = feats_post[correct_mask]
    targets_y = y_batch[correct_mask]
    B = feats_pre.shape[0]
    if B == 0:
        return {}

    fc_pre = pre_model.model.fc
    fc_post = post_model.model.fc
    criterion = nn.CrossEntropyLoss()

    class_results = {}
    for c in range(10):
        delta_h = torch.zeros((1, 512), device=device, requires_grad=True)
        optimizer = torch.optim.Adam([delta_h], lr=lr)
        
        target_labels = torch.full((B,), c, dtype=torch.long, device=device)
        non_target_mask = (targets_y != c)
        if non_target_mask.sum() == 0:
            continue

        for step in range(steps):
            optimizer.zero_grad()
            h_post_perturbed = feats_post + delta_h
            l_post = fc_post(h_post_perturbed)
            loss_target = criterion(l_post[non_target_mask], target_labels[non_target_mask])
            
            h_pre_perturbed = feats_pre + delta_h
            l_pre = fc_pre(h_pre_perturbed)
            loss_pre_preserve = criterion(l_pre[non_target_mask], targets_y[non_target_mask])
            
            norm_loss = torch.norm(delta_h, p=2)
            loss = loss_target + 0.5 * loss_pre_preserve + 0.01 * norm_loss
            loss.backward()
            optimizer.step()

        with torch.no_grad():
            h_post_final = feats_post + delta_h
            h_pre_final = feats_pre + delta_h
            pred_post = fc_post(h_post_final).argmax(dim=-1)
            pred_pre = fc_pre(h_pre_final).argmax(dim=-1)

            differential_success = (pred_pre == targets_y) & (pred_post == c) & non_target_mask
            success_rate = differential_success.float().sum().item() / non_target_mask.float().sum().item() * 100.0
            class_results[c] = float(success_rate)

    return class_results

def analyze_blind_metrics(class_rates):
    rates = list(class_rates.values())
    max_c = max(class_rates, key=class_rates.get)
    max_val = class_rates[max_c]
    other_vals = [v for k, v in class_rates.items() if k != max_c]
    mean_other = sum(other_vals) / len(other_vals) if other_vals else 1e-12
    asymmetry_ratio = max_val / mean_other if mean_other > 0 else 0.0
    return {
        "max_class": max_c,
        "max_rate": max_val,
        "mean_other_classes": mean_other,
        "blind_asymmetry_ratio": asymmetry_ratio
    }

if __name__ == "__main__":
    pairs = [
        ("q10_attack", models["attack_pre"], models["attack_post"]),
        ("q11_clean_same850", models["clean_pre"], models["clean_post"]),
        ("q12_clean_big_client", models["clean_pre"], models["clean_big_post"]),
    ]
    
    out_dir = ROOT / "research" / "latent_differential_audit_20261023"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    summary = {}
    for pair_id, m_pre, m_post in pairs:
        c_rates = evaluate_latent_differential(m_pre, m_post, eval_x, eval_y, steps=100)
        metrics = analyze_blind_metrics(c_rates)
        summary[pair_id] = {
            "class_rates": c_rates,
            "blind_metrics": metrics
        }
        print(f"\n[{pair_id}]")
        print(f"  Blind Max Class: {metrics['max_class']} -> Rate: {metrics['max_rate']:.2f}%")
        print(f"  Mean Other Classes: {metrics['mean_other_classes']:.2f}%")
        print(f"  Blind Asymmetry Ratio: {metrics['blind_asymmetry_ratio']:.4f}")
        
    (out_dir / "AUDIT_RESULTS.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nSaved audit results to {out_dir / 'AUDIT_RESULTS.json'}")
