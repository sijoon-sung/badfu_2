"""One finite, read-only evaluation of all six pinned author MNIST/DBA endpoints."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import torch
from prepare import ROOT, sha, write


def model_module():
    spec = importlib.util.spec_from_file_location('author_net', ROOT / 'upstream/model/model.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    torch.set_num_threads(1)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cuda.matmul.allow_tf32 = False
    for name, h in json.loads((ROOT / 'EVALUATION_FREEZE.json').read_text())['files'].items():
        assert sha(ROOT / name) == h, name
    selected = json.loads(subprocess.check_output([sys.executable, '-B', str(ROOT / 'catalog/select_case.py'),
             'fuba.author.bc233610.mnist.dba.post6.20261115', '--purpose', 'diagnostic'], text=True, encoding='utf-8'))
    assert len(selected['server_inputs']) == 6
    raw = subprocess.check_output(['nvidia-smi', '--query-gpu=utilization.gpu,memory.free,memory.used', '--format=csv,noheader,nounits'], text=True)
    util, free, used = [int(v.strip()) for v in raw.split(',')]
    assert util <= 5 and free >= 2500, raw
    ps = "$os=Get-CimInstance Win32_OperatingSystem; $p=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python|mpiexec'} | Select-Object ProcessId,ParentProcessId,CommandLine); @{free_KiB=$os.FreePhysicalMemory;processes=$p}|ConvertTo-Json -Depth 4"
    resources = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', ps], text=True))
    assert int(resources['free_KiB']) >= 2 * 1024 ** 2
    for p in resources['processes']:
        cmd = (p.get('CommandLine') or '').lower()
        if p['ProcessId'] not in (os.getpid(), os.getppid()):
            assert not any(s in cmd for s in ['runner.py', 'run.py controller', 'run.py attack', 'run.py benign', 'mpiexec.exe']), p
    write('EVALUATION_STARTED.json', {'pid': os.getpid(), 'time': time.time(), 'selected': selected,
                                     'GPU': {'util': util, 'free_MiB': free, 'used_MiB': used}, **resources})
    from torchvision.datasets import MNIST
    data_root = 'C:/Users/DISLAB/Documents/antigravity/dazzling-lovelace/FUBA/data'
    ds = MNIST(data_root, train=False, download=False)
    md5 = {}
    for name, digest in MNIST.resources:
        if name.startswith('t10k'):
            path = Path(ds.raw_folder) / name
            actual = hashlib.md5(path.read_bytes()).hexdigest()
            assert actual == digest, name
            md5[name] = actual
    x = ds.data.float().unsqueeze(1).div_(255).contiguous()
    y = ds.targets.clone()
    assert x.shape == (10000, 1, 28, 28) and int((y != 8).sum()) == 9026
    source = ROOT / 'upstream/utils/comm_utils.py'
    parsed = ast.parse(source.read_text(encoding='utf-8'))
    nodes = [n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name in ('attack_dba', 'test')]
    assert len(nodes) == 2
    original = {'torch': torch}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), original)
    trigger_source = ROOT / 'upstream/utils/dba_attack_utils.py'
    triggers = {}
    exec(compile(trigger_source.read_text(encoding='utf-8'), str(trigger_source), 'exec'), triggers)
    results = []
    prediction_rows = {}
    for name, checkpoint in selected['server_inputs'].items():
        path = Path(checkpoint['path'])
        assert checkpoint['payload_key'] is None and sha(path) == checkpoint['sha256']
        net = model_module().Net().cuda().eval()
        state = torch.load(path, weights_only=True, map_location='cpu')
        net.load_state_dict(state, strict=True)
        clean_preds, trigger_preds = [], []
        with torch.inference_mode():
            for start in range(0, len(y), 64):
                batch = x[start:start + 64].cuda()
                attack = batch.clone()
                for a, b, c, d in [(0, 2, 0, 5), (4, 6, 7, 12), (0, 2, 7, 12), (4, 6, 0, 5)]:
                    attack[:, :, a:b, c:d] = 1
                clean = net(batch)
                trig = net(attack)
                assert bool(torch.isfinite(clean).all() & torch.isfinite(trig).all())
                clean_preds.append(clean.argmax(1).cpu())
                trigger_preds.append(trig.argmax(1).cpu())
        c, t = torch.cat(clean_preds), torch.cat(trigger_preds)
        correct = int((c == y).sum())
        hits = int(((t == 8) & (y != 8)).sum())
        ca, asr = 100 * correct / len(y), 100 * hits / 9026
        # Separate original AST path and model instance, fixed identical order/batch.
        other = model_module().Net().cuda().eval()
        other.load_state_dict(state, strict=True)
        loader = torch.utils.data.DataLoader(torch.utils.data.TensorDataset(x, y), batch_size=64, shuffle=False)
        author_ca = original['test'](other, loader, 'cuda')
        author_asr = original['attack_dba'](other, loader, 8, 'cuda', triggers['add_backdoor_all'])
        assert round(author_ca * 10000 / 100) == correct
        assert round(author_asr * 9026 / 100) == hits
        assert all(torch.equal(v.cpu(), state[k]) for k, v in net.state_dict().items())
        assert sha(path) == checkpoint['sha256']
        row = {'method_author_filename': name, 'N': 10000, 'non_target_N': 9026,
               'CA_correct': correct, 'ASR_hits': hits, 'CA_pct': ca, 'ASR_pct': asr,
               'author_CA_pct': author_ca, 'author_ASR_pct': author_asr,
               'independent_integer_agreement': True, 'state_unchanged': True,
               'narrow_public_post_gate': ca >= 97 and asr >= 60,
               'newly_executed_FU': False, 'verified_latent_pair': False,
               'checkpoint_sha256': checkpoint['sha256']}
        write('DBA_' + name + '.json', row)
        results.append(row)
        prediction_rows[name] = {'clean': c, 'trigger': t, 'labels': y}
        print(json.dumps(row), flush=True)
        del net, other
    with (ROOT / 'DBA_predictions.pt').open('xb') as f:
        torch.save(prediction_rows, f)
    write('DBA_RESULT.json', {'state': 'complete', 'results': results, 'dataset_md5': md5,
                             'predictions_sha256': sha(ROOT / 'DBA_predictions.pt'),
                             'torch': torch.__version__, 'device': torch.cuda.get_device_name(),
                             'evaluator': 'author-dba-v1-eval-FP32-contiguous-B64',
                             'new_training_rounds': 0, 'new_FU_steps': 0,
                             'full_paper_reproduced': False, 'time': time.time()})


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        write('DBA_FAILURE.json', {'error': str(exc), 'traceback': traceback.format_exc()})
        raise
