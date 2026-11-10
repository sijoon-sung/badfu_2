"""Blind input inversion. No evaluator role, generator, trigger, or target inputs."""
import gc
import importlib.util
import json
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from probe_reference import Transform, sha, tensor_sha, write, read

ROOT = Path(__file__).resolve().parent
FAMILIES = ('mask', 'additive', 'conditional')
ARMS = ('baseline', 'route')


def settings(cfg):
    torch.set_num_threads(2)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.cuda.set_per_process_memory_fraction(cfg['memory_fraction'])


def seed(value):
    np.random.seed(value)
    torch.manual_seed(value)
    torch.cuda.manual_seed_all(value)


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def load_native(binding, architecture, device):
    assert sha(binding['path']) == binding['sha256'], 'Checkpoint hash mismatch'
    payload = torch.load(binding['path'], map_location='cpu', weights_only=True)
    state = payload if binding['payload_key'] is None else payload[binding['payload_key']]
    assert state and all(isinstance(v, torch.Tensor) and torch.isfinite(v).all() for v in state.values())
    if architecture == 'badfu':
        root = Path('D:/CONFIRMED_CHECKPOINTS/BadFU_s20261023_v1')
        model = module(root/'load_confirmed.py', 'sealed_badfu_loader').model_class(root)()
    elif architecture == 'fuba':
        model = module(ROOT/'fuba_model.py', 'executed_fuba_architecture').resnet18()
    elif architecture == 'feduba':
        model = module(ROOT/'feduba_model.py', 'recovered_feduba_architecture').ResNet18()
    else:
        raise ValueError(architecture)
    model.load_state_dict(state, strict=True)
    model.eval().requires_grad_(False)
    digest = tensor_sha(model.state_dict())
    del payload, state
    return model.to(device), digest


class Endpoint:
    def __init__(self, native, architecture, capture=True):
        self.native = native
        self.architecture = architecture
        self.head = [(name, m) for name, m in native.named_modules() if isinstance(m, nn.Linear)][-1][1]
        self.feature = None
        self.hook = self.head.register_forward_pre_hook(self._capture) if capture else None

    def _capture(self, module, inputs):
        self.feature = inputs[0]

    def normalize(self, x):
        if self.architecture == 'badfu':
            mean = x.new_tensor([.4914, .4822, .4465])[None, :, None, None]
            std = x.new_tensor([.2023, .1994, .2010])[None, :, None, None]
            return (x-mean)/std
        if self.architecture == 'feduba':
            return (x-.5)/.5
        return x

    def __call__(self, x):
        return self.native(self.normalize(x.contiguous()))

    def close(self):
        if self.hook:
            self.hook.remove()
        self.feature = None


def loss_from_logits(z00, z01, z10, z11, y, target, arm):
    if arm == 'baseline':
        return F.cross_entropy(z11, target)+F.cross_entropy(z00, y)
    return .5*(F.cross_entropy(z11, target)+F.cross_entropy(z10, target)
               + F.cross_entropy(z00, y)+F.cross_entropy(z01, y))


def public_data(cfg, device):
    assert sha(cfg['raw_data']) == cfg['raw_sha256']
    raw = torch.load(cfg['raw_data'], map_location='cpu', weights_only=True)
    y = raw['test_y'].long()
    rng = np.random.default_rng(cfg['seed'])
    indices = {k: [] for k in ('fit', 'calibration', 'test')}
    for c in range(10):
        ids = rng.permutation(np.flatnonzero(y.numpy() == c)); offset = 0
        for k in indices:
            n = cfg['public'][k+'_per_class']
            indices[k].extend(ids[offset:offset+n].tolist()); offset += n
    assert all(not set(indices[a]) & set(indices[b]) for a in indices for b in indices if a != b)
    data = {k: (raw['test_x'][ids].permute(0, 3, 1, 2).contiguous().float().to(device)/255,
                y[ids].to(device)) for k, ids in indices.items()}
    return data, indices


@torch.no_grad()
def predict(endpoint, x):
    return torch.cat([endpoint(batch).argmax(1) for batch in x.split(32)])


@torch.no_grad()
def score(pre, post, transform, x, y, targets=range(10)):
    p0, p1 = predict(pre, x), predict(post, x)
    stable = (p0 == y) & (p1 == y)
    rows = []
    for target in targets:
        take = y != target; xx = x[take]; yy = y[take]
        cc = torch.full_like(yy, target)
        changed = torch.cat([transform(b, c) for b, c in zip(xx.split(32), cc.split(32))])
        before, after = predict(pre, changed), predict(post, changed)
        witness = stable[take] & (before == yy) & (after == target)
        rows.append(dict(target=target, n=len(yy), witness=int(witness.sum()),
                         score=int(witness.sum())/len(yy), stable=int(stable[take].sum()),
                         source_counts=[dict(source=c, n=int((yy == c).sum()),
                                             witness=int(witness[yy == c].sum())) for c in range(10) if c != target]))
    return rows


def train(pre, post, transform, cfg, arm, family, x, y, out):
    seed(cfg['seed'])
    rng = np.random.default_rng(cfg['seed'])
    eligible = {c: torch.where(y != c)[0].cpu().numpy() for c in range(10)}
    targets = torch.arange(10, device=x.device).repeat_interleave(2)
    optimizer = torch.optim.Adam(transform.parameters(), lr=.02 if family == 'mask' else .005)
    trace, schedule = [], []
    initial = tensor_sha(transform.state_dict())
    started = time.time()
    for step in range(1, cfg['steps']+1):
        ids = np.concatenate([rng.choice(eligible[c], 2, replace=False) for c in range(10)])
        schedule.append(ids.tolist())
        yy = y[ids]; changed = transform(x[ids], targets)
        z00 = pre(changed); z11 = post(changed)
        z01 = post.head(pre.feature); z10 = pre.head(post.feature)
        loss = loss_from_logits(z00, z01, z10, z11, yy, targets, arm)
        assert torch.isfinite(loss)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in transform.parameters())
        optimizer.step(); transform.project()
        if step % 50 == 0:
            item = dict(step=step, loss=float(loss.detach()), seconds=time.time()-started)
            trace.append(item)
            write(ROOT/'STATE.json', dict(state='search', pid=__import__('os').getpid(),
                                         case=out.parent.name, arm=arm, family=family, **item))
            print(json.dumps(dict(case=out.parent.name, arm=arm, family=family, **item)), flush=True)
    pre.feature = post.feature = None
    torch.save(dict(transform=transform.state_dict(), optimizer=optimizer.state_dict(),
                    torch_rng=torch.get_rng_state(), cuda_rng=torch.cuda.get_rng_state_all(),
                    numpy_rng=rng.bit_generator.state, schedule=schedule), out)
    write(out.with_suffix('.json'), dict(initial_tensor_sha256=initial, trace=trace,
                                       final_payload_sha256=sha(out), schedule=schedule))


def load_transform(family, cfg, path, device):
    t = Transform(family, cfg).to(device)
    t.load_state_dict(torch.load(path, map_location=device, weights_only=True)['transform'], strict=True)
    return t.eval()


def release(pre, post):
    pre.close(); post.close()
    del pre, post
    gc.collect(); torch.cuda.empty_cache()
