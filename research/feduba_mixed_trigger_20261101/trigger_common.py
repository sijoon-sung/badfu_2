"""CPU trigger helpers for a separately bound, completed mixed teacher."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONDONTWRITEBYTECODE='1')
import importlib.util
import math
from pathlib import Path
import torch
from torch.utils.data import Dataset
import binding_gate as gate
from runtime_common import ROOT, read, write, sha, save, seed, rng


def policy():
    torch.set_num_threads(2); torch.backends.mkldnn.enabled = True
    torch.set_float32_matmul_precision('highest')
    assert torch.get_num_threads() == 2 and torch.get_default_dtype() == torch.float32
    assert torch.backends.mkldnn.enabled and os.environ['CUDA_VISIBLE_DEVICES'] == '-1' and not torch.cuda.is_initialized()
    return {'CPU_threads': 2, 'MKLDNN': True, 'FP32': True, 'CUDA_VISIBLE_DEVICES': '-1',
            'CUDA_initialized': False, 'matmul_precision': torch.get_float32_matmul_precision(), 'torch': str(torch.__version__)}


def check_inputs(source, launch):
    assert ROOT == gate.ROOT
    for meta in source['inputs'].values(): gate.verify_meta(meta)
    for meta in launch['teacher_bindings'].values(): gate.verify_meta(meta)
    bindings, terminal = gate.teacher_ready(source)
    assert bindings == launch['teacher_bindings']
    assert terminal['state'] == read(ROOT / 'TEACHER_TERMINAL.json')['state']
    assert sha(ROOT / 'NORMAL_SELECTION.json') == launch['normal_selection_sha256']
    assert sha(ROOT / 'SOURCE_ONLY_REVIEW.json') == launch['source_review_sha256']
    old_root = Path(source['original_root'])
    assert not (old_root / 'STG_VERIFIED.json').exists()
    assert read(old_root / 'STG_CONTROLLER_STATE.json')['state'] == 'failed_preserved'


def model_and_target(source, launch):
    meta = launch['teacher_bindings']['teacher']; gate.verify_meta(meta)
    theta = torch.load(meta['path'], map_location='cpu', weights_only=True)
    architecture = source['inputs']['architecture']
    spec = importlib.util.spec_from_file_location('new_mixed_teacher_architecture', architecture['path'])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    model = module.ResNet18_201().cpu(); model.load_state_dict(theta, strict=True); model.eval()
    for parameter in model.parameters(): parameter.requires_grad_(False); parameter.grad = None
    target_meta = source['inputs']['target']; gate.verify_meta(target_meta)
    target = torch.load(target_meta['path'], map_location='cpu', weights_only=True)
    ids = torch.as_tensor(target['external_original_IDs'], dtype=torch.long)
    assert target['images_HWC_uint8'].shape == (200, 32, 32, 3) and target['images_HWC_uint8'].dtype == torch.uint8
    assert ids.shape == (200,) and len(set(ids.tolist())) == 200
    return model, theta, target, ids


class WithIDs(Dataset):
    def __init__(self, data, ids): self.data, self.ids = data, ids
    def __len__(self): return len(self.ids)
    def __getitem__(self, i):
        x, y = self.data[i]
        return x, y, self.ids[i]


def load(meta):
    path = ROOT / meta['path']; assert sha(path) == meta['sha256'] and path.stat().st_size == meta['bytes']
    return torch.load(path, map_location='cpu', weights_only=True)


def finite(value):
    if isinstance(value, torch.Tensor): assert value.device.type == 'cpu' and bool(torch.isfinite(value).all())
    elif isinstance(value, dict):
        for x in value.values(): finite(x)
    elif isinstance(value, (tuple, list)):
        for x in value: finite(x)
    elif isinstance(value, float): assert math.isfinite(value)
