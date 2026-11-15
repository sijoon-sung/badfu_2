"""Fetch pinned public FUBA artifacts; inspect on CPU without evaluating samples."""
import collections
import hashlib
import importlib.util
import io
import json
import os
import pickle
from pathlib import Path
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(name, value):
    with (ROOT / name).open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)


def load_restricted(path):
    import torch
    def cpu_storage(raw):
        return torch.load(io.BytesIO(raw), map_location='cpu', weights_only=True)
    allowed = {
        ('collections', 'OrderedDict'): collections.OrderedDict,
        ('torch._utils', '_rebuild_tensor_v2'): torch._utils._rebuild_tensor_v2,
        ('torch.storage', '_load_from_bytes'): cpu_storage,
    }
    class StateUnpickler(pickle.Unpickler):
        def find_class(self, module, name):
            if (module, name) not in allowed:
                raise pickle.UnpicklingError(f'Undeclared global {module}.{name}')
            return allowed[module, name]
    with Path(path).open('rb') as f:
        return StateUnpickler(f).load()


def main():
    import torch
    torch.set_num_threads(1)
    write('PREPARE_STARTED.json', {'pid': os.getpid(), 'time': time.time()})
    inventory = json.loads((ROOT / 'UPSTREAM.json').read_text(encoding='utf-8'))
    for name, h in json.loads((ROOT / 'SOURCE_FREEZE.json').read_text())['files'].items():
        assert sha(ROOT / name) == h, name
    (ROOT / 'original').mkdir(exist_ok=False)
    (ROOT / 'states').mkdir(exist_ok=False)
    spec = importlib.util.spec_from_file_location('author_model', ROOT / 'upstream/model/model.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    artifacts = []
    for item in inventory['models']:
        p = ROOT / 'original' / item['name']
        with urllib.request.urlopen(item['download_url'], timeout=60) as response:
            raw = response.read()
        git_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        assert len(raw) == item['size'] and git_blob == item['sha'], item['name']
        with p.open('xb') as f:
            f.write(raw)
        state = load_restricted(p)
        assert isinstance(state, (dict, collections.OrderedDict))
        assert all(isinstance(v, torch.Tensor) and v.device.type == 'cpu' for v in state.values())
        assert all(bool(torch.isfinite(v).all()) for v in state.values())
        model = module.Net() if item['name'].startswith('global_') else module.MNISTAutoencoder()
        model.load_state_dict(state, strict=True)
        output = ROOT / 'states' / (p.stem + '.pt')
        with output.open('xb') as f:
            torch.save(state, f)
        canonical = torch.load(output, weights_only=True, map_location='cpu')
        assert all(torch.equal(state[k], canonical[k]) for k in state)
        artifacts.append({'name': item['name'], 'git_blob': git_blob, 'original_sha256': sha(p),
                          'bytes': len(raw), 'state_path': str(output), 'state_sha256': sha(output),
                          'payload_key': None, 'class': type(model).__name__,
                          'parameter_count': sum(x.numel() for x in model.parameters()),
                          'strict_load': True, 'all_finite': True, 'roundtrip_exact': True})
        print(json.dumps({'prepared': item['name'], 'class': type(model).__name__}), flush=True)
    assert not torch.cuda.is_initialized()
    write('PREPARED.json', {'state': 'passed', 'inference_count': 0, 'GPU_initialized': False,
                           'artifacts': artifacts, 'python': sys.version, 'torch': torch.__version__,
                           'commit': inventory['commit'], 'time': time.time()})


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import traceback
        write('PREPARE_FAILURE.json', {'error': str(exc), 'traceback': traceback.format_exc()})
        raise
