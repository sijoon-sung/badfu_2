"""
Fed-DMI / Fed-MFS Experiment:
Characterizing the Feasibility Boundary from Broad Space (Additive, Conditional)
to Narrowed Space (Mask) under Attack (q10) vs. Large Benign Non-IID Deletion (q12).
"""

import ast, hashlib, importlib.util, json, time, os, sys
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from torchvision import models

BASE = Path(r"C:\Users\sijoo\Documents\ChatGPT\badFU")
OUT_DIR = BASE / "research/fed_mfs_experiment_20261023"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. Model Definition (ResNet18 for CIFAR-10)
class Model(nn.Module):
    def __init__(self, state):
        super().__init__()
        self.net = models.resnet18(weights=None)
        self.net.conv1 = nn.Conv2d(3, 64, 3, 1, 1, bias=False)
        self.net.maxpool = nn.Identity()
        self.net.fc = nn.Linear(512, 10)
        self.net.load_state_dict({k.removeprefix('model.'): v for k, v in state.items()}, strict=True)
        self.register_buffer('mean', torch.tensor([.4914, .4822, .4465])[None, :, None, None])
        self.register_buffer('std', torch.tensor([.2023, .1994, .2010])[None, :, None, None])

    def forward(self, x):
        return self.net(((x - self.mean) / self.std).contiguous())

def load_model(path):
    payload = torch.load(path, weights_only=True, map_location='cpu')
    state = payload if isinstance(payload, dict) and 'model' not in payload and 'conv1.weight' in payload or 'net' not in payload else payload.get('model', payload)
    return Model(state).cuda().eval().requires_grad_(False)

# 2. Transformation Families (Broad vs Narrowed)
class Conditional(nn.Module):
    def __init__(self):
        super().__init__()
        self.c1 = nn.Conv2d(13, 16, 3, padding=1)
        self.c2 = nn.Conv2d(16, 32, 3, padding=1)
        self.c3 = nn.Conv2d(32, 32, 3, padding=1)
        self.c4 = nn.Conv2d(64, 16, 3, padding=1)
        self.c5 = nn.Conv2d(32, 3, 3, padding=1)
        nn.init.zeros_(self.c5.weight)
        nn.init.zeros_(self.c5.bias)

    def forward(self, x, c):
        cond = F.one_hot(c, 10).to(x.dtype)[:, :, None, None].expand(-1, -1, 32, 32)
        a = F.relu(self.c1(torch.cat([x, cond], 1)))
        b = F.relu(self.c2(F.avg_pool2d(a, 2)))
        d = F.relu(self.c3(F.avg_pool2d(b, 2)))
        e = F.relu(self.c4(torch.cat([F.interpolate(d, size=(16, 16), mode='bilinear', align_corners=False), b], 1)))
        return self.c5(torch.cat([F.interpolate(e, size=(32, 32), mode='bilinear', align_corners=False), a], 1))

class Transform(nn.Module):
    def __init__(self, family, mask_mass=16.0, epsilon=0.04):
        super().__init__()
        self.family = family
        self.mass = mask_mass
        self.eps = epsilon
        if family == 'mask':
            self.mask = nn.Parameter(torch.rand(10, 1, 32, 32) * self.mass / 1024)
            self.pattern = nn.Parameter(torch.rand(10, 3, 32, 32))
        elif family == 'additive':
            self.delta = nn.Parameter(torch.randn(10, 3, 32, 32) * .001)
        elif family == 'conditional':
            self.net = Conditional()
        else:
            raise ValueError(family)

    def forward(self, x, c):
        if self.family == 'mask':
            return (x * (1 - self.mask[c]) + self.pattern[c] * self.mask[c]).clamp(0, 1)
        return (x + (self.delta[c] if self.family == 'additive' else self.eps * self.net(x, c).tanh())).clamp(0, 1)

    @torch.no_grad()
    def project(self):
        if self.family == 'mask':
            self.mask.clamp_(0, 1)
            self.pattern.clamp_(0, 1)
            for m in self.mask:
                f = m.flatten()
                if f.sum() > self.mass:
                    u = f.sort(descending=True).values
                    cs = u.cumsum(0) - self.mass
                    ok = u - cs / torch.arange(1, len(u) + 1, device=u.device) > 0
                    k = int(ok.sum()) - 1
                    f.copy_((f - cs[k] / (k + 1)).clamp_min(0))
        elif self.family == 'additive':
            self.delta.clamp_(-self.eps, self.eps)

@torch.inference_mode()
def predict(m, x):
    return torch.cat([m(b).argmax(1) for b in x.split(64)])

@torch.inference_mode()
def evaluate_differential(pre, post, t, x, y, c, clean_preds=None):
    """
    Computes strict differential witness:
    Samples correctly classified by BOTH pre and post on clean inputs,
    where perturbation keeps pre prediction correct (or stable), but post prediction becomes target c.
    """
    p0, p1 = clean_preds if clean_preds is not None else (predict(pre, x), predict(post, x))
    take = (y != c)
    xx = x[take]
    yy = y[take]
    cc = torch.full((len(xx),), c, device='cuda', dtype=torch.long)
    zz = torch.cat([t(a, b) for a, b in zip(xx.split(64), cc.split(64))])
    
    a = predict(pre, zz)
    b = predict(post, zz)
    stable = (p0[take] == yy) & (p1[take] == yy)
    witness = stable & (a == yy) & (b == c)
    
    rate = float(witness.double().mean()) if len(witness) > 0 else 0.0
    return dict(target=c, total=len(xx), stable_n=int(stable.sum()), witness_n=int(witness.sum()), rate=rate)

# 3. Data Preparation
def load_datasets():
    # Public CIFAR test data
    raw_path = BASE / "research/stage1_20261020/assets/cifar_raw.pt"
    raw = torch.load(raw_path, weights_only=True, map_location='cpu')
    y_test = raw['test_y']
    x_test = (raw['test_x'].permute(0, 3, 1, 2).float() / 255.0).contiguous()
    
    rng = np.random.default_rng(20261023)
    fit_idx, cal_idx, test_idx = [], [], []
    for c in range(10):
        c_pool = rng.permutation(torch.where(y_test == c)[0].numpy())
        fit_idx.extend(c_pool[:32])
        cal_idx.extend(c_pool[32:64])
        test_idx.extend(c_pool[64:164])
        
    public_data = {
        'fit': (x_test[fit_idx].cuda(), y_test[fit_idx].cuda()),
        'cal': (x_test[cal_idx].cuda(), y_test[cal_idx].cuda()),
        'test': (x_test[test_idx].cuda(), y_test[test_idx].cuda()),
    }
    
    # Client training data (Clients 1, 2, 3)
    train_path = BASE / "research/stage1_20261020/assets/cifar_train_raw.pt"
    train_raw = torch.load(train_path, weights_only=True, map_location='cpu')
    split_path = BASE / "research/stage1_20261020/assets/badfu_full6_split.json"
    with open(split_path, 'r', encoding='utf-8') as f:
        parts = json.load(f)['clean_cifar10_indices']
        
    client_rng = np.random.default_rng(20261025)
    client_data = {}
    for cid in [1, 2, 3]:
        pool = parts[cid]
        chosen = client_rng.choice(pool, 512, replace=False)
        cx = (train_raw['train_x'][chosen].permute(0, 3, 1, 2).float() / 255.0).contiguous().cuda()
        cy = train_raw['train_y'][chosen].cuda()
        client_data[cid] = (cx, cy)
        
    return public_data, client_data

# 4. Search Loop
def run_search(post_model, family, public_data, steps=200, seed=20261023):
    x_fit, y_fit = public_data['fit']
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    rng = np.random.default_rng(seed)
    
    t = Transform(family).cuda()
    t.project()
    lr = 0.02 if family == 'mask' else (0.005 if family == 'additive' else 0.001)
    opt = torch.optim.Adam(t.parameters(), lr=lr)
    
    eligible = {c: torch.where(y_fit != c)[0].cpu().numpy() for c in range(10)}
    targets = torch.arange(10, device='cuda').repeat_interleave(2)
    
    for step in range(1, steps + 1):
        ii = np.concatenate([rng.choice(eligible[c], 2, replace=False) for c in range(10)])
        x_batch = x_fit[ii]
        loss = F.cross_entropy(post_model(t(x_batch, targets)), targets)
        opt.zero_grad()
        loss.backward()
        opt.step()
        t.project()
        
    return t

# 5. Main Benchmark Execution
def main():
    print("==========================================================================")
    print("Fed-DMI / Fed-MFS Empirical Verification: Broad vs. Narrowed Feasibility")
    print("==========================================================================")
    
    models_dir = BASE / "CONFIRMED_CHECKPOINTS/BadFU_s20261023_v1/models"
    pairs = {
        'Attack (q10)': {
            'pre_path': models_dir / "01_before_unlearning.pt",
            'post_path': models_dir / "02_after_cover_removal_retrain.pt",
            'desc': "BadFU Attack (Cover removed, Backdoor unleashed, ASR=100%)"
        },
        'Clean Big Deletion (q12)': {
            'pre_path': models_dir / "03_clean_reference.pt",
            'post_path': models_dir / "05_clean_big_client_removed.pt",
            'desc': "Clean Big Client 4 Deletion (19.336% Clean Data Removed)"
        }
    }
    
    print("\n[1/3] Loading Datasets...")
    public_data, client_data = load_datasets()
    print("  Public Fit: 320, Cal: 320, Test: 1000")
    print("  Cooperating Clients 1, 2, 3: 512 samples each (Non-IID)")
    
    families = ['additive', 'conditional', 'mask']
    results = {}
    
    for pair_name, pinfo in pairs.items():
        print(f"\n[2/3] Evaluating Pair: {pair_name}")
        print(f"      {pinfo['desc']}")
        pre_m = load_model(pinfo['pre_path'])
        post_m = load_model(pinfo['post_path'])
        
        # Precompute clean predictions
        clean_cal = (predict(pre_m, public_data['cal'][0]), predict(post_m, public_data['cal'][0]))
        clean_test = (predict(pre_m, public_data['test'][0]), predict(post_m, public_data['test'][0]))
        clean_clients = {cid: (predict(pre_m, client_data[cid][0]), predict(post_m, client_data[cid][0])) for cid in client_data}
        
        results[pair_name] = {}
        
        for fam in families:
            t0 = time.time()
            # Search on post model (200 steps)
            t = run_search(post_m, fam, public_data, steps=200)
            
            # Select target class based on public calibration witness rate (BLIND SELECTION, no true label leaked!)
            cal_rates = [evaluate_differential(pre_m, post_m, t, public_data['cal'][0], public_data['cal'][1], c, clean_cal)['rate'] for c in range(10)]
            best_c = int(np.argmax(cal_rates))
            best_cal_rate = cal_rates[best_c]
            
            # Evaluate on public test
            test_res = evaluate_differential(pre_m, post_m, t, public_data['test'][0], public_data['test'][1], best_c, clean_test)
            s_public = test_res['rate']
            
            # Evaluate on cooperating clients 1, 2, 3
            client_rates = []
            for cid in [1, 2, 3]:
                c_res = evaluate_differential(pre_m, post_m, t, client_data[cid][0], client_data[cid][1], best_c, clean_clients[cid])
                client_rates.append(c_res['rate'])
                
            s1, s2, s3 = client_rates
            arithmetic_mean = (s1 + s2 + s3) / 3.0
            harmonic_consensus = 3.0 / (1.0 / (s1 + 1e-4) + 1.0 / (s2 + 1e-4) + 1.0 / (s3 + 1e-4))
            
            elapsed = time.time() - t0
            results[pair_name][fam] = {
                'selected_target': best_c,
                'cal_rate': best_cal_rate,
                'public_test_rate': s_public,
                'client_rates': {'client_1': s1, 'client_2': s2, 'client_3': s3},
                'arithmetic_mean': arithmetic_mean,
                'harmonic_consensus': harmonic_consensus,
                'search_seconds': elapsed
            }
            print(f"  -> Family: {fam:<11} | Target: {best_c} | Public Test: {s_public*100:5.2f}% | Clients [C1,C2,C3]: [{s1*100:5.2f}%, {s2*100:5.2f}%, {s3*100:5.2f}%] | S_consensus: {harmonic_consensus*100:5.2f}%")

    # Save detailed JSON
    out_json = OUT_DIR / "EXPERIMENT_RESULTS.json"
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f"\n[3/3] Detailed results saved to: {out_json}")
    
    # Print Markdown Summary Table
    print("\n" + "="*80)
    print("FINAL SUMMARY: BROAD VS. NARROWED FEASIBILITY")
    print("="*80)
    print(f"{'Condition':<25} | {'Family':<12} | {'Public Test':<12} | {'Clients Mean':<13} | {'Harmonic S_consensus':<20}")
    print("-" * 90)
    for pair_name in pairs:
        for fam in families:
            r = results[pair_name][fam]
            print(f"{pair_name:<25} | {fam:<12} | {r['public_test_rate']*100:6.2f}%     | {r['arithmetic_mean']*100:6.2f}%      | {r['harmonic_consensus']*100:6.2f}%")
        print("-" * 90)

if __name__ == '__main__':
    main()
