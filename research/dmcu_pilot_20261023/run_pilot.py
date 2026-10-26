"""Differential Margin-Constrained Unlearning (DMCU) Pilot Experiment.
Evaluates both:
1. Security: Attack Post (Model 02) -> does ASR drop from 100% to low (<10%)?
2. Utility & Unlearning Fidelity: Clean Big Client Post (Model 05, 19.336% deletion) -> does CA stay >= 89.5% and unlearning preserved?
Strictly preserves confirmed snapshot checkpoints (read-only).
"""
import copy
import json
from pathlib import Path
import sys
from PIL import Image
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, TensorDataset, DataLoader
import torchvision.transforms as transforms

ROOT = Path("c:/Users/sijoo/Documents/ChatGPT/badFU")
CONFIRMED_DIR = ROOT / "CONFIRMED_CHECKPOINTS" / "BadFU_s20261023_v1"
OUT_DIR = ROOT / "research" / "dmcu_pilot_20261023"
OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "models").mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(CONFIRMED_DIR))
import load_confirmed

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# 1. Load Evaluation Data (10,000 Clean Test, 9,000 Triggered Test)
record_root = ROOT / "upstream/data_prepare/record/badnet_original"
record = torch.load(record_root / "pert_result.pt", map_location="cpu", weights_only=False)
data = record["bd_test"]["bd_data_container"]["data_dict"]
for info in data.values():
    parts = str(info["path"]).replace("\\", "/").split("/")
    start = parts.index("bd_test_dataset")
    info["path"] = str(record_root.joinpath(*parts[start:]))

transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010))
])

test_raw = torch.load(ROOT / "research/stage1_20261020/assets/cifar_raw.pt", map_location="cpu", weights_only=True)
clean_test_x = torch.stack([transform(Image.fromarray(v.numpy())) for v in test_raw["test_x"]])
clean_test_y = test_raw["test_y"]
clean_test_ds = TensorDataset(clean_test_x, clean_test_y)

class BackdoorDataset(Dataset):
    def __init__(self, data_dict, transform=None):
        self.paths = [v["path"] for v in data_dict.values()]
        self.labels = [int(v["other_info"][0]) for v in data_dict.values()]
        self.transform = transform
    def __len__(self):
        return len(self.paths)
    def __getitem__(self, idx):
        img = Image.open(self.paths[idx]).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, self.labels[idx]

poison_test_ds = BackdoorDataset(data, transform)
clean_test_loader = DataLoader(clean_test_ds, batch_size=128, shuffle=False)
poison_test_loader = DataLoader(poison_test_ds, batch_size=128, shuffle=False)
print(f"Loaded evaluation sets: Clean {len(clean_test_ds)}, Triggered {len(poison_test_ds)}")

# 2. Load Server Small Clean Dataset (e.g. 1000 images from cifar_train_raw.pt)
train_raw = torch.load(ROOT / "research/stage1_20261020/assets/cifar_train_raw.pt", map_location="cpu", weights_only=True)
N_SERVER = 1000
torch.manual_seed(20261023)
server_indices = torch.randperm(len(train_raw["train_y"]))[:N_SERVER]
server_x = torch.stack([transform(Image.fromarray(train_raw["train_x"][i].numpy())) for i in server_indices])
server_y = train_raw["train_y"][server_indices]
server_ds = TensorDataset(server_x, server_y)
server_loader = DataLoader(server_ds, batch_size=64, shuffle=True)
print(f"Loaded server clean dataset: {len(server_ds)} samples")

def evaluate_ca_asr(model):
    model.eval()
    correct_clean = 0
    with torch.no_grad():
        for bx, by in clean_test_loader:
            pred = model(bx.to(device)).argmax(dim=1)
            correct_clean += (pred == by.to(device)).sum().item()
    ca = correct_clean / len(clean_test_ds) * 100.0

    correct_poison = 0
    with torch.no_grad():
        for bx, by in poison_test_loader:
            pred = model(bx.to(device)).argmax(dim=1)
            correct_poison += (pred == 0).sum().item() # target is 0
    asr = correct_poison / len(poison_test_ds) * 100.0
    return ca, asr

def compute_margin(logits):
    # margin = logit_max - logit_second_max
    top2 = torch.topk(logits, k=2, dim=-1).values
    return top2[:, 0] - top2[:, 1]

def run_dmcu(m_pre, m_post, epochs=8, lr=1e-4, alpha=1.0, beta=2.0, epsilon=0.25):
    """Differential Margin-Constrained Unlearning."""
    m_target = copy.deepcopy(m_post)
    m_target.train()
    m_pre.eval()
    m_post.eval()
    
    optimizer = torch.optim.Adam(m_target.parameters(), lr=lr)
    
    for epoch in range(epochs):
        total_loss = 0.0
        total_margin_loss = 0.0
        
        for bx, by in server_loader:
            bx = bx.to(device)
            by = by.to(device)
            B = bx.size(0)
            
            # --- Inner Loop: Adversarial Differential Margin Perturbation ---
            delta = torch.zeros_like(bx, requires_grad=True)
            # 2 steps of PGD to find the direction where m_target margin explodes over m_pre
            for _ in range(2):
                bx_adv = bx + delta
                l_target_adv = m_target(bx_adv)
                with torch.no_grad():
                    l_pre_adv = m_pre(bx_adv)
                
                margin_target = compute_margin(l_target_adv)
                margin_pre = compute_margin(l_pre_adv)
                diff_margin = (margin_target - margin_pre).mean()
                
                grad = torch.autograd.grad(diff_margin, delta)[0]
                delta.data = torch.clamp(delta.data + (epsilon / 2.0) * torch.sign(grad), -epsilon, epsilon)
            
            # --- Outer Loop: Model Parameter Update ---
            optimizer.zero_grad()
            
            # 1. Clean Task Loss + Alignment to m_post on clean data
            l_target_clean = m_target(bx)
            loss_task = F.cross_entropy(l_target_clean, by)
            
            with torch.no_grad():
                l_post_clean = m_post(bx)
            loss_kl = F.kl_div(
                F.log_softmax(l_target_clean, dim=-1),
                F.softmax(l_post_clean, dim=-1),
                reduction="batchmean"
            )
            
            # 2. Differential Margin Penalty
            l_target_adv = m_target(bx + delta.detach())
            with torch.no_grad():
                l_pre_adv = m_pre(bx + delta.detach())
            
            margin_target_adv = compute_margin(l_target_adv)
            margin_pre_adv = compute_margin(l_pre_adv)
            
            # Hinge penalty: penalize only if margin on perturbed input exceeds m_pre margin
            margin_explosion = F.relu(margin_target_adv - margin_pre_adv).mean()
            
            loss = loss_task + alpha * loss_kl + beta * margin_explosion
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item() * B
            total_margin_loss += margin_explosion.item() * B
            
        print(f"  Epoch {epoch+1}/{epochs}: Loss = {total_loss/N_SERVER:.4f}, Margin Explosion = {total_margin_loss/N_SERVER:.4f}")
        
    return m_target

print("\n" + "="*70)
print("EXPERIMENT 1: Security Evaluation on BadFU Attack Pair (01_before -> 02_after)")
print("="*70)
m01 = load_confirmed.load_model("pre", device=device, root=CONFIRMED_DIR)
m02 = load_confirmed.load_model("post", device=device, root=CONFIRMED_DIR)

ca_base_02, asr_base_02 = evaluate_ca_asr(m02)
print(f"Base Unpurified Model 02: CA = {ca_base_02:.2f}%, ASR = {asr_base_02:.2f}%")

print("Running DMCU on Model 02...")
m02_purified = run_dmcu(m01, m02, epochs=8, lr=2e-4, alpha=1.0, beta=3.0, epsilon=0.25)
ca_purified_02, asr_purified_02 = evaluate_ca_asr(m02_purified)
print(f"Purified Model 02 (Attack): CA = {ca_purified_02:.2f}%, ASR = {asr_purified_02:.2f}%")
print(f"  ASR Reduction: {asr_base_02:.2f}% -> {asr_purified_02:.2f}% (Delta: {asr_purified_02 - asr_base_02:.2f}%p)")
print(f"  CA Change:     {ca_base_02:.2f}% -> {ca_purified_02:.2f}% (Delta: {ca_purified_02 - ca_base_02:.2f}%p)")

print("\n" + "="*70)
print("EXPERIMENT 2: Utility & Non-IID Safety on Clean Big Deletion (03_clean -> 05_clean_big)")
print("="*70)
m03 = load_confirmed.load_model("clean_pre", device=device, root=CONFIRMED_DIR)
m05 = load_confirmed.load_model("clean_big_post", device=device, root=CONFIRMED_DIR)

ca_base_05, asr_base_05 = evaluate_ca_asr(m05)
print(f"Base Unpurified Model 05 (19.336% deletion): CA = {ca_base_05:.2f}%, ASR = {asr_base_05:.2f}%")

print("Running EXACT IDENTICAL DMCU on Model 05...")
m05_purified = run_dmcu(m03, m05, epochs=8, lr=2e-4, alpha=1.0, beta=3.0, epsilon=0.25)
ca_purified_05, asr_purified_05 = evaluate_ca_asr(m05_purified)
print(f"Purified Model 05 (Clean Big): CA = {ca_purified_05:.2f}%, ASR = {asr_purified_05:.2f}%")
print(f"  CA Change:     {ca_base_05:.2f}% -> {ca_purified_05:.2f}% (Delta: {ca_purified_05 - ca_base_05:.2f}%p)")
print(f"  ASR Change:    {asr_base_05:.2f}% -> {asr_purified_05:.2f}% (Delta: {asr_purified_05 - asr_base_05:.2f}%p)")

# Save Results Summary
results = {
    "protocol": "DMCU_pilot_v1",
    "attack_case": {
        "base_CA": ca_base_02,
        "base_ASR": asr_base_02,
        "purified_CA": ca_purified_02,
        "purified_ASR": asr_purified_02,
        "ASR_drop_pp": asr_base_02 - asr_purified_02,
        "CA_drop_pp": ca_base_02 - ca_purified_02
    },
    "clean_big_case": {
        "base_CA": ca_base_05,
        "base_ASR": asr_base_05,
        "purified_CA": ca_purified_05,
        "purified_ASR": asr_purified_05,
        "CA_drop_pp": ca_base_05 - ca_purified_05
    }
}

torch.save(m02_purified.state_dict(), OUT_DIR / "models/02_purified.pt")
torch.save(m05_purified.state_dict(), OUT_DIR / "models/05_purified.pt")
(OUT_DIR / "PILOT_RESULTS.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"\nPilot experiment complete! Saved results to {OUT_DIR / 'PILOT_RESULTS.json'}")
