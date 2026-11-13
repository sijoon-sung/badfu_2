"""New review-only helpers; no training, gradient replay, or bulk inference."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import hashlib
import importlib.util
import json
import math
from pathlib import Path, PurePosixPath
import stat

ROOT = Path(__file__).resolve().parent
NAME = 'FedUBA_s42_CPUtrigger_SSS125_FU20_pair_20261031'
REMOTE_PACKET = Path('D:/CHECKPOINTS_FOR_REVIEW') / NAME
LOCAL_PACKET = Path('C:/Users/sijoo/Documents/ChatGPT/badFU/CHECKPOINTS_FOR_REVIEW') / NAME
CASES = {b: f'feduba.paper.cifar10.s42.cpu_trigger.sss125.{b}fu20.20261031'
         for b in ['attack', 'benign']}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 << 20), b''): h.update(block)
    return h.hexdigest()


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def freeze():
    for name, sha in read(ROOT / 'PAIR_REVIEW_FREEZE.json')['files'].items():
        assert digest(ROOT / name) == sha, name


def safe(root, name):
    assert isinstance(name, str) and name and '\\' not in name and ':' not in name
    p = PurePosixPath(name)
    assert not p.is_absolute() and str(p) == name and all(x not in ['', '.', '..'] for x in p.parts)
    root = Path(root).resolve(); target = root.joinpath(*p.parts)
    assert target.resolve().is_relative_to(root) and not target.is_symlink()
    return target


def verify(root, expected_manifest_sha256):
    root = Path(root).resolve()
    assert digest(root / 'DELIVERY_MANIFEST.json') == expected_manifest_sha256
    m = read(root / 'DELIVERY_MANIFEST.json')
    expected = set(m['files']) | {'DELIVERY_MANIFEST.json', 'DELIVERY_SEAL.json'}
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    assert expected == actual
    for name in expected:
        path = safe(root, name)
        assert path.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY, name
        if name in m['files']:
            meta = m['files'][name]
            assert path.stat().st_size == meta['bytes'] and digest(path) == meta['sha256'], name
    seal = read(root / 'DELIVERY_SEAL.json')
    assert seal['manifest_sha256'] == expected_manifest_sha256 and seal['case_ids'] == m['case_ids']
    assert seal['hashed_files'] == len(m['files'])
    return {'state': 'passed', 'all_readonly': True, 'hashed_files': len(m['files']), 'total_files': len(expected)}


def finite(value):
    import torch
    if isinstance(value, torch.Tensor):
        assert value.device.type == 'cpu' and bool(torch.isfinite(value).all())
    elif isinstance(value, dict):
        for v in value.values(): finite(v)
    elif isinstance(value, (tuple, list)):
        for v in value: finite(v)
    elif isinstance(value, float):
        assert math.isfinite(value)


def cpu_check(root, payloads, on_check=None):
    import torch
    root = Path(root)
    torch.set_num_threads(1)
    assert os.environ['CUDA_VISIBLE_DEVICES'] == '-1' and not torch.cuda.is_initialized()
    spec = importlib.util.spec_from_file_location('sealed_pair_architecture', root / 'model_reference.py')
    architecture = importlib.util.module_from_spec(spec); spec.loader.exec_module(architecture)
    checks = []
    for row in payloads:
        path = safe(root, row['file'])
        assert digest(path) == row['sha256'] and path.stat().st_size == row['bytes']
        value = torch.load(path, map_location='cpu', weights_only=True); finite(value)
        if row['kind'] == 'model':
            state = value if row['payload_key'] is None else value[row['payload_key']]
            model = (architecture.ResNet18_201() if row['classes'] == 201 else architecture.ResNet18()).cpu().eval()
            model.load_state_dict(state, strict=True)
            with torch.inference_mode():
                output = model(torch.zeros(1, 3, 32, 32))
            assert output.shape == (1, row['classes']) and bool(torch.isfinite(output).all())
            if row.get('role_kind'):
                assert value['optimizer']['state'] and value['rng']['torch_CPU'].numel()
                assert len(value['rng']['torch_CUDA']) == 1
                if row['role_kind'] == 'fu':
                    assert len(value['epochs']) == 5 and value['batches'] == row['batches']
                    assert value['round'] == row['round'] and value['client'] == row['client']
                    assert all(e['source_ids'].numel() == row['source_N'] for e in value['epochs'])
                else:
                    assert value['epochs'] == 10 and value['batches'] == 200
            del model, state
        elif row['kind'] == 'delta':
            assert isinstance(value, torch.Tensor) and tuple(value.shape) == (1, 3, 32, 32)
            assert float(value.abs().max()) <= 32 / 255 + 1e-7
        else:
            assert row['kind'] == 'tensor_evidence'
        checks.append({'file': row['file'], 'sha256': row['sha256'], 'kind': row['kind'],
                       'strict_CPU_finite': True, 'zero_input_model_forward_only': row['kind'] == 'model'})
        if on_check: on_check(checks[-1])
        del value
    assert not torch.cuda.is_initialized()
    return {'state': 'passed', 'CPU_only': True, 'payload_count': len(checks), 'checks': checks,
            'new_performance_inference': False, 'local_SGD_gradients_replayed': False}
