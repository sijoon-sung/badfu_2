"""New declared curriculum only; original source/checkpoints are read-only inputs."""
import importlib.util
import importlib.metadata
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms
from runtime_common import ROOT, read, write, sha, save, cpu, seed, rng
import runtime_common


def once(name, value):
    with (ROOT / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def frozen():
    for name, digest in read(ROOT / 'FREEZE.json')['files'].items():
        assert sha(ROOT / name) == digest, name
    p = read(ROOT / 'PROFILE.json')
    assert ROOT == Path(p['execution_root']) and p['launch_enabled'] is True
    assert (p['seed'], p['batch_size'], p['surrogate_epochs'], p['warmup_epochs']) == (0, 128, 100, 5)
    assert list(sys.version_info[:3]) == p['python_version']
    for name, version in p['package_versions'].items(): assert importlib.metadata.version(name) == version, name
    assert torch.get_default_dtype() == torch.float32
    return p


def check_bindings(p):
    for name, meta in p['bindings'].items():
        path = Path(meta['path'])
        assert sha(path) == meta['sha256'], name
        if 'bytes' in meta: assert path.stat().st_size == meta['bytes'], name


def load_bound(p, name):
    meta = p['bindings'][name]; path = Path(meta['path'])
    assert sha(path) == meta['sha256'] and path.stat().st_size == meta['bytes']
    obj = torch.load(path, map_location='cpu', weights_only=True)
    return obj if meta.get('payload_key') is None else obj[meta['payload_key']]


def load_new(meta):
    path = ROOT / meta['path']
    assert sha(path) == meta['sha256'] and path.stat().st_size == meta['bytes']
    return torch.load(path, map_location='cpu', weights_only=True)


def model_class(p):
    meta = p['bindings']['architecture']; assert sha(meta['path']) == meta['sha256']
    spec = importlib.util.spec_from_file_location('pinned_resnet_201', meta['path'])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.ResNet18_201


def select_normal(p):
    value = json.loads(subprocess.check_output([sys.executable, '-B', p['catalog_root'] + '/select_case.py',
                       p['normal_case_id'], '--purpose', 'diagnostic'], text=True, encoding='utf-8'))
    assert value['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    assert value['checkpoint_guard']['manifest_sha256'] == p['normal_manifest_sha256']
    assert value['checkpoint_guard']['seal_sha256'] == p['normal_seal_sha256']
    assert value['server_inputs']['pre']['sha256'] == p['normal_pre_sha256']
    assert value['server_inputs']['pre']['payload_key'] is None
    return value


def assets(p):
    tiny, target = load_bound(p, 'tiny'), load_bound(p, 'target')
    assert tiny['images_HWC_uint8'].shape == (100000, 32, 32, 3)
    assert target['images_HWC_uint8'].shape == (200, 32, 32, 3)
    assert tiny['images_HWC_uint8'].dtype == target['images_HWC_uint8'].dtype == torch.uint8
    labels = torch.as_tensor(tiny['labels'], dtype=torch.long)
    ids = torch.as_tensor(target['external_original_IDs'], dtype=torch.long)
    assert labels.shape == (100000,) and torch.equal(torch.bincount(labels, minlength=200), torch.full((200,), 500))
    assert ids.shape == (200,) and len(set(ids.tolist())) == 200
    return tiny, target, labels, ids


class MixedImages(Dataset):
    def __init__(self, tiny, target, labels, target_ids, warmup=False, augment=True):
        self.tiny, self.target, self.labels, self.target_ids = tiny, target, labels, target_ids
        self.warmup = warmup
        ops = [transforms.RandomCrop(32, padding=4), transforms.RandomHorizontalFlip()] if augment else []
        self.transform = transforms.Compose(ops + [transforms.ToTensor(), transforms.Normalize((.5,) * 3, (.5,) * 3)])

    def __len__(self): return 200 if self.warmup else 100200

    def __getitem__(self, index):
        position = int(index) + (100000 if self.warmup else 0)
        if position < 100000:
            image, label, domain, original_id = self.tiny['images_HWC_uint8'][position], int(self.labels[position]), 0, position
        else:
            j = position - 100000
            image, label, domain, original_id = self.target['images_HWC_uint8'][j], 200, 1, int(self.target_ids[j])
        return self.transform(Image.fromarray(image.numpy())), label, position, domain, original_id


def finite(value):
    if isinstance(value, torch.Tensor):
        assert value.device.type == 'cpu' and bool(torch.isfinite(value).all())
    elif isinstance(value, dict):
        for item in value.values(): finite(item)
    elif isinstance(value, (tuple, list)):
        for item in value: finite(item)
    elif isinstance(value, float): assert math.isfinite(value)


class ResourceBusy(RuntimeError): pass


def gpu_guard(p):
    # Reuse the already measured B128 resource bounds; no model fixture is repeated.
    try: measured = runtime_common.guard(4000, 6000)
    except AssertionError as exc: raise ResourceBusy(str(exc)) from exc
    except RuntimeError as exc:
        if 'Competing training/evaluation PID' in str(exc): raise ResourceBusy(str(exc)) from exc
        raise
    command = "Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python|mpiexec'} | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
    raw = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', command], text=True, encoding='utf-8').strip()
    rows = json.loads(raw) if raw else []
    if isinstance(rows, dict): rows = [rows]
    for row in rows:
        if row['ProcessId'] in [os.getpid(), os.getppid()]: continue
        text = (row.get('CommandLine') or '').lower()
        if any(token in text for token in ['mixed_teacher_runner.py', 'feduba_paper_implementation_20261031',
                                          'feduba_stage_diagnosis_20261101', 'evaluate_pair.py', 'verify_pair_evaluation.py']):
            raise ResourceBusy('Competing study process ' + str(row['ProcessId']))
    measured['free_storage_bytes'] = shutil.disk_usage(ROOT).free
    assert measured['free_storage_bytes'] >= p['minimum_free_storage_bytes']
    return measured


def event(**value):
    path = ROOT / 'private_run/events.jsonl'; path.parent.mkdir(exist_ok=True)
    with path.open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps({'time_unix': time.time(), **value}, allow_nan=False) + '\n'); stream.flush()


def numeric_train():
    torch.set_num_threads(1); torch.set_float32_matmul_precision('highest')
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = True
    torch.backends.cudnn.benchmark = False; torch.backends.cudnn.deterministic = False
    torch.use_deterministic_algorithms(False)
    result = {'threads': torch.get_num_threads(), 'AMP': torch.is_autocast_enabled(), 'precision': torch.get_float32_matmul_precision(),
              'matmul_TF32': torch.backends.cuda.matmul.allow_tf32, 'cudnn_TF32': torch.backends.cudnn.allow_tf32,
              'cudnn_benchmark': torch.backends.cudnn.benchmark, 'cudnn_deterministic': torch.backends.cudnn.deterministic,
              'deterministic_algorithms': torch.are_deterministic_algorithms_enabled(), 'torch': str(torch.__version__)}
    assert result['threads'] == 1 and result['precision'] == 'highest' and not result['matmul_TF32'] and not result['AMP']
    assert result['cudnn_TF32'] and not any(result[k] for k in ['cudnn_benchmark', 'cudnn_deterministic', 'deterministic_algorithms'])
    return result
