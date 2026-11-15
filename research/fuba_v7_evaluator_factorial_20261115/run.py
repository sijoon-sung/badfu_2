"""Fixed 2x2 evaluator comparison on an immutable actual-FU pair; no learning."""
import ast
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


def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()


def write(name, value):
    with (ROOT / name).open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)


def frozen():
    for name, digest in read(ROOT / 'FREEZE.json')['files'].items():
        assert sha(ROOT / name) == digest, name


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def prepare():
    frozen()
    write('PREPARE_STARTED.json', {'pid': os.getpid(), 'time': time.time()})
    b = read(ROOT / 'INPUT_BINDING.json')
    assert sha(b['selector_path']) == b['selector_sha256']
    selected = json.loads(subprocess.check_output([sys.executable, '-B', b['selector_path'], b['case_id'],
        '--purpose', 'diagnostic'], text=True, encoding='utf-8'))
    assert selected['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    assert selected['checkpoint_guard']['manifest_sha256'] == b['manifest_sha256']
    for endpoint, name in [('pre', 'before.pt'), ('post', 'after.pt')]:
        assert selected['server_inputs'][endpoint]['payload_key'] is None
        assert selected['server_inputs'][endpoint]['sha256'] == b['files'][name]['sha256']
    (ROOT / 'inputs').mkdir(exist_ok=False)
    for name, item in b['files'].items():
        assert sha(item['path']) == item['sha256'], name
        shutil.copyfile(item['path'], ROOT / 'inputs' / name)
        assert sha(ROOT / 'inputs' / name) == item['sha256']
    write('PREPARED.json', {'state': 'passed', 'selected': selected, 'model_inference': 0,
                          'input_files': b['files']})


def guard():
    util, free, used = [int(v.strip()) for v in subprocess.check_output(['nvidia-smi',
        '--query-gpu=utilization.gpu,memory.free,memory.used', '--format=csv,noheader,nounits'], text=True).split(',')]
    assert util <= 5 and free >= 2500
    ps = "$o=Get-CimInstance Win32_OperatingSystem;@{free_KiB=$o.FreePhysicalMemory;processes=@(Get-CimInstance Win32_Process|Where-Object {$_.Name -match 'python|mpiexec'}|Select-Object ProcessId,ParentProcessId,CommandLine)}|ConvertTo-Json -Depth 4"
    info = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', ps], text=True))
    assert int(info['free_KiB']) >= 3 * 1024 ** 2
    for p in info['processes']:
        if p['ProcessId'] not in (os.getpid(), os.getppid()):
            line = (p.get('CommandLine') or '').lower()
            assert not any(s in line for s in ['runner.py', 'run.py train', 'run.py evaluate',
                'run.py controller', 'run.py attack', 'run.py benign', 'mpiexec.exe']), p
    assert shutil.disk_usage(ROOT).free >= 10 * 1024 ** 3
    return {'util': util, 'free_MiB': free, 'used_MiB': used, **info}


def evaluate():
    frozen()
    assert read(ROOT / 'PREPARED.json')['state'] == 'passed'
    binding = read(ROOT / 'INPUT_BINDING.json')
    for name, item in binding['files'].items():
        assert sha(item['path']) == item['sha256'] == sha(ROOT / 'inputs' / name)
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
    ins = ROOT / 'inputs'
    resnet = module('fixed_resnet', ins / 'resnet.py')
    unet = module('fixed_unet', ins / 'model.py')
    asts = ast.parse((ins / 'comm_utils.py').read_text(encoding='utf-8'))
    functions = [n for n in asts.body if isinstance(n, ast.FunctionDef) and n.name in ['attack', 'test']]
    assert len(functions) == 2
    original = {'torch': torch}
    exec(compile(ast.Module(body=functions, type_ignores=[]), 'public_comm_utils.py', 'exec'), original)
    old_ast = ast.parse((ins / 'old_evaluator.py').read_text(encoding='utf-8'))
    expressions = [n.value for n in ast.walk(old_ast) if isinstance(n, ast.Assign)
                   and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'b']
    assert len(expressions) == 1
    old_expression = compile(ast.Expression(body=expressions[0]), 'original_v7_trigger_expression', 'eval')
    from torchvision.datasets import CIFAR10
    from torchvision.transforms import ToTensor
    ds = CIFAR10(read(ins / 'DATA.json')['root'], train=False, transform=ToTensor(), download=False)
    assert ds._check_integrity()
    x = torch.from_numpy(ds.data).permute(0, 3, 1, 2).contiguous().float().div_(255)
    y = torch.tensor(ds.targets)
    assert len(y) == 10000 and int((y != 8).sum()) == 9000
    labels = y.clone()
    states = {name: torch.load(ins / file, map_location='cpu', weights_only=True)
              for name, file in [('before', 'before.pt'), ('after', 'after.pt'), ('G', 'generator.pt')]}
    for state in states.values(): assert all(bool(torch.isfinite(v).all()) for v in state.values())
    def classifier(name):
        net = resnet.resnet18().cuda().eval()
        net.load_state_dict(states[name], strict=True)
        return net
    def generator(training):
        net = unet.UNet(3).cuda().train(training)
        net.load_state_dict(states['G'], strict=True)
        return net
    def loader():
        return torch.utils.data.DataLoader(torch.utils.data.TensorDataset(x, y), batch_size=32, shuffle=False)
    records, preds, buffers = [], {'labels': y.numpy()}, {}
    for policy in ['legacy', 'public']:
        for mode in ['eval', 'train']:
            nets = {name: classifier(name) for name in ['before', 'after']}
            g = generator(mode == 'train')
            outputs = {name + kind: [] for name in nets for kind in ['_clean', '_trigger']}
            max_change = 0.
            with torch.inference_mode():
                for bx, by in loader():
                    bx = bx.cuda().contiguous()
                    noise = g(bx)
                    tx = (bx + .05 * noise).clamp(0, 1) if policy == 'legacy' else (bx + (.3 * noise).clamp(-.05, .05)).clamp(-1, 1)
                    max_change = max(max_change, float((tx - bx).abs().max()))
                    assert bool(torch.isfinite(tx).all()) and max_change <= .050001
                    for name, net in nets.items():
                        for kind, image in [('_clean', bx), ('_trigger', tx)]:
                            out = net(image)
                            assert bool(torch.isfinite(out).all())
                            outputs[name + kind].append(out.argmax(1).cpu())
            outputs = {name: torch.cat(values) for name, values in outputs.items()}
            final_buffers = {n: b.cpu().clone() for n, b in g.named_buffers()}
            assert all(torch.equal(p.cpu(), states['G'][n]) for n, p in g.named_parameters())
            for n, b in final_buffers.items():
                if mode == 'eval': assert torch.equal(b, states['G'][n])
                elif n.endswith('num_batches_tracked'): assert int(b - states['G'][n]) == 313
            row = {'policy': policy, 'G_mode': mode, 'max_input_change': max_change, 'N': 10000, 'non_target_N': 9000}
            for name, net in nets.items():
                assert all(torch.equal(v.cpu(), states[name][n]) for n, v in net.state_dict().items())
                clean, trigger = outputs[name + '_clean'], outputs[name + '_trigger']
                cc, hits = int((clean == y).sum()), int(((trigger == 8) & (y != 8)).sum())
                if policy == 'legacy' and mode == 'eval':
                    assert cc == 7776 and hits == {'before': 950, 'after': 1507}[name], 'Current legacy control differs from sealed counts'
                other, other_g = classifier(name), generator(mode == 'train')
                ca = original['test'](other, loader(), 'cuda')
                if policy == 'public':
                    asr = original['attack'](other, loader(), other_g, .3, .05, 8, 'cuda')
                    independent_hits = round(asr * 9000 / 100)
                else:
                    independent_hits = 0
                    with torch.inference_mode():
                        for bx, by in loader():
                            bx, by = bx.cuda().contiguous(), by.cuda()
                            out = eval(old_expression, {'c': other, 'x': bx, 'g': other_g})
                            independent_hits += int(((out.argmax(1) == 8) & (by != 8)).sum())
                assert round(ca * 10000 / 100) == cc and independent_hits == hits
                assert all(torch.equal(b.cpu(), final_buffers[n]) for n, b in other_g.named_buffers())
                row[name] = {'clean_correct': cc, 'target_successes': hits, 'CA_pct': cc / 100,
                    'ASR_pct': 100 * hits / 9000, 'independent_integer_exact': True,
                    'clean_target_bias': int(((clean == 8) & (y != 8)).sum())}
                del other, other_g
            row['original_latent_gates_pass'] = (row['before']['CA_pct'] >= 80 and row['after']['CA_pct'] >= 80
                and row['before']['ASR_pct'] < 10 and row['after']['ASR_pct'] >= 60)
            records.append(row)
            for key, val in outputs.items(): preds[f'{policy}_{mode}_{key}'] = val.numpy()
            buffers[f'{policy}_{mode}'] = final_buffers
            write(f'ROW_{policy}_{mode}.json', row)
            print(json.dumps(row), flush=True)
            del nets, g
    assert torch.equal(y, labels)
    for name, item in binding['files'].items():
        assert sha(item['path']) == item['sha256'] == sha(ins / name)
    with (ROOT / 'predictions.npz').open('xb') as f: np.savez_compressed(f, **preds)
    with (ROOT / 'generator_buffers_after.pt').open('xb') as f: torch.save(buffers, f)
    gain = records[-1]['after']['ASR_pct'] - records[0]['after']['ASR_pct']
    write('RESULT.json', {'state': 'complete', 'rows': records, 'post_ASR_gain_pp': gain,
        'hypothesis_supported': gain >= 20, 'all_independent_counts_exact': True,
        'new_FU_steps': 0, 'new_FL_rounds': 0, 'input_files_unchanged': True,
        'evaluator': 'v7-evaluator-factorial-v1-B32-FP32-contiguous-deterministic',
        'predictions_sha256': sha(ROOT / 'predictions.npz'), 'buffers_sha256': sha(ROOT / 'generator_buffers_after.pt'),
        'torch': torch.__version__, 'full_paper_reproduced': False})


if __name__ == '__main__':
    try:
        {'prepare': prepare, 'evaluate': evaluate}[sys.argv[1]]()
    except Exception as exc:
        name = 'FAILURE_' + sys.argv[1] + '.json'
        if not (ROOT / name).exists(): write(name, {'error': str(exc), 'traceback': traceback.format_exc()})
        raise
