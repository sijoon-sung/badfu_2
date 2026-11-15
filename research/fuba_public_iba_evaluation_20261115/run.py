"""Finite public IBA endpoint/benign-transfer evaluation; no FL or FU training."""
import ast
import copy
import hashlib
import importlib.util
import json
import os
os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent
METHODS = ['distillation', 'federaser', 'pgd', 'retrain', 'robustfu', 'sga']
PUBLIC_ID = 'fuba.author.bc233610.mnist.iba.post6.20261115'
BENIGN_ID = 'benign.fuba.mnist.iid.s20261023.round20.20261115'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write(name, value):
    with (ROOT / name).open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, allow_nan=False, indent=2)


def frozen():
    for name, digest in read(ROOT / 'FREEZE.json')['files'].items():
        assert sha(ROOT / name) == digest, name


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def select(case):
    chosen = json.loads(subprocess.check_output([sys.executable, '-B', str(ROOT / 'catalog/select_case.py'),
                        case, '--purpose', 'diagnostic'], text=True, encoding='utf-8'))
    assert chosen['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    return chosen


def prepare():
    frozen()
    write('PREPARE_STARTED.json', {'pid': os.getpid(), 'time': time.time()})
    binding = read(ROOT / 'INPUT_BINDING.json')
    inputs = ROOT / 'inputs'
    inputs.mkdir(exist_ok=False)
    for name, item in binding['files'].items():
        src = Path(item['path'])
        assert sha(src) == item['sha256'], name
        shutil.copyfile(src, inputs / name)
        assert sha(inputs / name) == item['sha256']
    shutil.copyfile(ROOT / 'check_inputs.py', inputs / 'check_inputs.py')
    manifest = {'files': {p.name: {'sha256': sha(p), 'bytes': p.stat().st_size}
                         for p in sorted(inputs.iterdir())}}
    write('inputs/REVIEW_MANIFEST.json', manifest)
    write('inputs/SEAL.json', {'manifest_sha256': sha(inputs / 'REVIEW_MANIFEST.json')})
    catalogue = ROOT / 'catalog'
    shutil.copytree('D:/FUBA_AUTHOR_MODELS_20261115/catalog', catalogue)
    cat = read(catalogue / 'catalog.json')
    original_ids = [c['id'] for c in cat['cases']]
    guard = {'manifest_path': str(inputs / 'REVIEW_MANIFEST.json'),
             'manifest_sha256': sha(inputs / 'REVIEW_MANIFEST.json'),
             'seal_path': str(inputs / 'SEAL.json'), 'seal_sha256': sha(inputs / 'SEAL.json'),
             'loader_path': str(inputs / 'check_inputs.py')}
    for case, names in [(PUBLIC_ID, binding['public_states']), (BENIGN_ID, ['benign_before.pt'])]:
        assert case not in original_ids
        cat['cases'].append({'id': case, 'title': case, 'source_root': str(inputs),
            'allowed_purposes': ['diagnostic'], 'post_type': 'public_post_only' if case == PUBLIC_ID else 'benign_endpoint',
            'checkpoint_guard': guard, 'server_inputs': {
                name: {'path': str(inputs / name), 'sha256': manifest['files'][name]['sha256'], 'payload_key': None}
                for name in names}})
    (catalogue / 'catalog.json').write_text(json.dumps(cat, ensure_ascii=False, indent=2), encoding='utf-8')
    selected = [select(PUBLIC_ID), select(BENIGN_ID)]
    import torch
    torch.set_num_threads(1)
    author = module('source_author', inputs / 'author_model.py')
    baseline = module('source_baseline', inputs / 'benchmark.py')
    checked = []
    for name in binding['public_states'] + ['benign_before.pt']:
        state = torch.load(inputs / name, map_location='cpu', weights_only=True)
        model = (baseline.Net() if name == 'benign_before.pt' else author.MNISTAutoencoder()
                 if name.startswith('backdoor_') else author.Net())
        model.load_state_dict(state, strict=True)
        assert all(bool(torch.isfinite(v).all()) for v in state.values())
        checked.append({'name': name, 'class': type(model).__name__,
                        'parameters': sum(p.numel() for p in model.parameters())})
    assert not torch.cuda.is_initialized()
    write('PREPARED.json', {'state': 'passed', 'selected': selected, 'models': checked,
                           'model_inference': 0, 'CUDA_initialized': False})


def guard():
    util, free, used = [int(x.strip()) for x in subprocess.check_output(['nvidia-smi',
        '--query-gpu=utilization.gpu,memory.free,memory.used', '--format=csv,noheader,nounits'], text=True).split(',')]
    assert util <= 5 and free >= 2500
    ps = "$o=Get-CimInstance Win32_OperatingSystem;@{free_KiB=$o.FreePhysicalMemory;processes=@(Get-CimInstance Win32_Process|Where-Object {$_.Name -match 'python|mpiexec'}|Select-Object ProcessId,ParentProcessId,CommandLine)}|ConvertTo-Json -Depth 4"
    info = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', ps], text=True))
    assert int(info['free_KiB']) >= 3 * 1024 ** 2
    for p in info['processes']:
        cmd = (p.get('CommandLine') or '').lower()
        if p['ProcessId'] not in (os.getpid(), os.getppid()):
            assert not any(s in cmd for s in ['runner.py', 'run.py train', 'run.py controller',
                'run.py attack', 'run.py benign', 'run.py evaluate', 'mpiexec.exe']), p
    assert shutil.disk_usage(ROOT).free >= 10 * 1024 ** 3
    return {'GPU_util': util, 'free_MiB': free, 'used_MiB': used, **info}


def evaluate():
    frozen()
    assert read(ROOT / 'PREPARED.json')['state'] == 'passed'
    selected = [select(PUBLIC_ID), select(BENIGN_ID)]
    resources = guard()
    write('EVALUATION_STARTED.json', {'pid': os.getpid(), 'time': time.time(), 'resources': resources})
    import numpy as np
    import torch
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cuda.matmul.allow_tf32 = False
    from torchvision.datasets import MNIST
    ds = MNIST('C:/Users/DISLAB/Documents/antigravity/dazzling-lovelace/FUBA/data', train=False, download=False)
    for name, digest in MNIST.resources:
        if name.startswith('t10k'):
            assert hashlib.md5((Path(ds.raw_folder) / name).read_bytes()).hexdigest() == digest
    x, y = ds.data.float().unsqueeze(1).div_(255).contiguous(), ds.targets.clone()
    original_labels = y.clone()
    assert len(y) == 10000 and int((y != 8).sum()) == 9026
    inputs = ROOT / 'inputs'
    author = module('source_author', inputs / 'author_model.py')
    baseline = module('source_baseline', inputs / 'benchmark.py')
    parsed = ast.parse((inputs / 'comm_utils.py').read_text(encoding='utf-8'))
    nodes = [n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name in ('attack', 'test')]
    assert len(nodes) == 2
    original = {'torch': torch}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'original_comm_utils.py', 'exec'), original)
    records, predictions, buffers = [], {'labels': y.numpy()}, {}
    normal_state = torch.load(inputs / 'benign_before.pt', map_location='cpu', weights_only=True)

    def create(cls, state, training=False):
        model = cls().cuda()
        model.load_state_dict(state, strict=True)
        return model.train(training)

    def unchanged_parameters(model, state):
        assert all(torch.equal(p.detach().cpu(), state[n]) for n, p in model.named_parameters())

    for method in METHODS:
        clf_state = torch.load(inputs / f'global_{method}_iba_mnist.pt', map_location='cpu', weights_only=True)
        gen_state = torch.load(inputs / f'backdoor_{method}_iba_mnist.pt', map_location='cpu', weights_only=True)
        for mode in ['eval', 'train']:
            training = mode == 'train'
            post, normal = create(author.Net, clf_state), create(baseline.Net, normal_state)
            generator = create(author.MNISTAutoencoder, gen_state, training)
            outputs = {k: [] for k in ['post_clean', 'post_trigger', 'normal_clean', 'normal_trigger']}
            max_noise = max_change = 0.
            with torch.inference_mode():
                for start in range(0, len(y), 64):
                    bx = x[start:start + 64].cuda()
                    noise = (.3 * generator(bx)).clamp(-.05, .05)
                    changed = (bx + noise).clamp(-1., 1.)
                    max_noise = max(max_noise, float(noise.abs().max()))
                    max_change = max(max_change, float((changed - bx).abs().max()))
                    assert bool(torch.isfinite(noise).all()) and max_change <= .050001
                    for key, model, images in [('post_clean', post, bx), ('post_trigger', post, changed),
                        ('normal_clean', normal, bx), ('normal_trigger', normal, changed)]:
                        value = model(images)
                        assert bool(torch.isfinite(value).all())
                        outputs[key].append(value.argmax(1).cpu())
            outputs = {k: torch.cat(v) for k, v in outputs.items()}
            unchanged_parameters(post, clf_state)
            unchanged_parameters(normal, normal_state)
            unchanged_parameters(generator, gen_state)
            final_buffers = {n: b.cpu().clone() for n, b in generator.named_buffers()}
            if not training:
                assert all(torch.equal(b, gen_state[n]) for n, b in final_buffers.items())
            else:
                assert all(int(b - gen_state[n]) == 157 for n, b in final_buffers.items() if n.endswith('num_batches_tracked'))
            row = {'method': method, 'generator_mode': mode, 'max_noise': max_noise,
                   'max_input_change': max_change, 'N': 10000, 'non_target_N': 9026}
            for label, cls, state in [('post', author.Net, clf_state), ('normal', baseline.Net, normal_state)]:
                clean, trigger = outputs[label + '_clean'], outputs[label + '_trigger']
                correct = int((clean == y).sum())
                hits = int(((trigger == 8) & (y != 8)).sum())
                bias = int(((clean == 8) & (y != 8)).sum())
                other, other_gen = create(cls, state), create(author.MNISTAutoencoder, gen_state, training)
                loader = torch.utils.data.DataLoader(torch.utils.data.TensorDataset(x, y), batch_size=64, shuffle=False)
                ca = original['test'](other, loader, 'cuda')
                asr = original['attack'](other, loader, other_gen, .3, .05, 8, 'cuda')
                assert round(ca * 10000 / 100) == correct and round(asr * 9026 / 100) == hits
                assert all(torch.equal(b.cpu(), final_buffers[n]) for n, b in other_gen.named_buffers())
                unchanged_parameters(other, state)
                unchanged_parameters(other_gen, gen_state)
                row[label] = {'clean_correct': correct, 'target_successes': hits, 'clean_target_bias': bias,
                              'CA_pct': 100 * correct / 10000, 'ASR_pct': 100 * hits / 9026,
                              'author_integer_exact': True}
                del other, other_gen
            row['narrow_conjunction'] = row['post']['ASR_pct'] >= 60 and row['normal']['ASR_pct'] < 10
            records.append(row)
            for key, value in outputs.items():
                predictions[f'{method}_{mode}_{key}'] = value.numpy()
            buffers[f'{method}_{mode}'] = final_buffers
            write(f'ROW_{method}_{mode}.json', row)
            print(json.dumps(row), flush=True)
            del post, normal, generator
    assert torch.equal(y, original_labels)
    for chosen in selected:
        for item in chosen['server_inputs'].values():
            assert sha(item['path']) == item['sha256']
    with (ROOT / 'predictions.npz').open('xb') as f:
        np.savez_compressed(f, **predictions)
    with (ROOT / 'generator_buffers_after.pt').open('xb') as f:
        torch.save(buffers, f)
    write('RESULT.json', {'state': 'complete', 'rows': records,
        'hypothesis_supported': all(r['narrow_conjunction'] for r in records if r['generator_mode'] == 'eval'),
        'evaluator': 'public-IBA-v1-deterministic-FP32-contiguous-B64-fixed-eval-and-reset-train',
        'predictions_sha256': sha(ROOT / 'predictions.npz'), 'buffers_sha256': sha(ROOT / 'generator_buffers_after.pt'),
        'torch': torch.__version__, 'CUDA': torch.cuda.get_device_name(), 'all_independent_counts_exact': True,
        'input_files_unchanged': True, 'new_FL_rounds': 0, 'new_FU_steps': 0,
        'verified_latent_pair': False, 'full_paper_reproduced': False})


if __name__ == '__main__':
    try:
        {'prepare': prepare, 'evaluate': evaluate}[sys.argv[1]]()
    except Exception as exc:
        name = 'FAILURE_' + sys.argv[1] + '.json'
        if not (ROOT / name).exists():
            write(name, {'error': str(exc), 'traceback': traceback.format_exc()})
        raise
