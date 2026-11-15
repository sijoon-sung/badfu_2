"""Bounded current-runtime local/global gamma trajectory comparison; never restarts old FL."""
import copy
import gc
import hashlib
import importlib.util
import json
import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time
import traceback
import numpy as np
import torch
import reference_core as core

ROOT = Path(__file__).resolve().parent


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(p, value, exclusive=False):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        with p.open('x', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, allow_nan=False, indent=2)
        return
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2), encoding='utf-8')
    for attempt in range(20):
        try:
            os.replace(tmp, p)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(.1)


def cpu(value):
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {k: cpu(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return type(value)(cpu(v) for v in value)
    return value


def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as f:
        torch.save(cpu(value), f)
        f.flush()
        os.fsync(f.fileno())
    return {'path': str(p.relative_to(ROOT)), 'sha256': sha(p), 'bytes': p.stat().st_size}


def seed(s):
    random.seed(s)
    np.random.seed(s)
    torch.manual_seed(s)
    torch.cuda.manual_seed_all(s)


def rng():
    n = np.random.get_state()
    return {'python': random.getstate(), 'numpy': (n[0], n[1].tolist(), int(n[2]), int(n[3]), float(n[4])),
            'torch_CPU': torch.get_rng_state(), 'torch_CUDA': torch.cuda.get_rng_state_all()}


def exact(a, b):
    assert a.keys() == b.keys() and all(torch.equal(a[k], b[k]) for k in a)


def exact_tree(a, b):
    if isinstance(a, torch.Tensor):
        assert isinstance(b,torch.Tensor) and torch.equal(a,b), 'Common-input phase tensor mismatch'
    elif isinstance(a,dict):
        assert a.keys()==b.keys()
        for key in a: exact_tree(a[key],b[key])
    elif isinstance(a,(list,tuple)):
        assert len(a)==len(b)
        for left,right in zip(a,b):exact_tree(left,right)
    else:
        assert a==b, 'Common-input phase scalar/RNG mismatch'


def frozen():
    for name, digest in read(ROOT / 'FREEZE.json')['files'].items():
        assert sha(ROOT / name) == digest, name


def prepare():
    frozen()
    write(ROOT / 'PREPARE_STARTED.json', {'pid': os.getpid(), 'time': time.time()}, True)
    binding = read(ROOT / 'INPUT_BINDING.json')
    selection = json.loads(subprocess.check_output([sys.executable, '-B',
        'D:/TRAJECTORY_CATALOG_20261023/select_case.py', binding['case_id'], '--purpose', 'diagnostic'],
        text=True, encoding='utf-8'))
    assert selection['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    packet = Path(selection['source_root'])
    manifest = read(packet / 'FULL_REMOTE_RAW_MANIFEST.json')
    assert sha(packet / 'FULL_REMOTE_RAW_MANIFEST.json') == binding['full_manifest_sha256']
    raw = Path(manifest['remote_root'])
    (ROOT / 'inputs').mkdir(exist_ok=False)
    files = {}
    for name in ['run/rounds/round0020.pt', 'SPLIT.json', 'PROFILE.json', 'author_model.py', 'reference_core.py']:
        record = manifest['files'][name]
        path = raw / name
        assert sha(path) == record['sha256'], name
        assert record['sha256'] == binding['files'][name], name
        target = ROOT / 'inputs' / Path(name).name
        shutil.copyfile(path, target)
        assert sha(target) == record['sha256']
        files[target.relative_to(ROOT).as_posix()] = record['sha256']
    assert sha(ROOT / 'reference_core.py') == files['inputs/reference_core.py']
    bundle = torch.load(ROOT / 'inputs/round0020.pt', map_location='cpu', weights_only=True)
    assert bundle['round'] == 20
    exact(bundle['after'], {k: torch.stack([s[k] for s in bundle['submitted']]).mean(0) for k in bundle['after']})
    assert all(bool(torch.isfinite(v).all()) for v in bundle['after'].values())
    prior = {str(r): read(raw / f'run/evaluation/round{r:04d}.json') for r in range(20, 31)}
    write(ROOT / 'PREPARED.json', {'state': 'passed', 'selection': selection, 'files': files,
                                  'historical_evaluations': prior, 'tensor_inference_count': 0}, True)
    print('prepared explicit round20 input and fixed original core', flush=True)


def guard():
    util, free, used = [int(x.strip()) for x in subprocess.check_output(['nvidia-smi',
        '--query-gpu=utilization.gpu,memory.free,memory.used', '--format=csv,noheader,nounits'], text=True).split(',')]
    assert util <= 5 and free >= 2500
    ps = "$os=Get-CimInstance Win32_OperatingSystem;@{free_KiB=$os.FreePhysicalMemory;processes=@(Get-CimInstance Win32_Process|Where-Object {$_.Name -match 'python|mpiexec'}|Select-Object ProcessId,ParentProcessId,CommandLine)}|ConvertTo-Json -Depth 4"
    current = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', ps], text=True))
    assert int(current['free_KiB']) >= 3 * 1024 ** 2
    for p in current['processes']:
        cmd = (p.get('CommandLine') or '').lower()
        if p['ProcessId'] not in (os.getpid(), os.getppid()):
            assert not any(s in cmd for s in ['runner.py', 'run.py controller', 'run.py attack', 'run.py benign', 'run.py train', 'mpiexec.exe']), p
    assert shutil.disk_usage(ROOT).free >= 10 * 1024 ** 3
    return {'gpu_util_pct': util, 'free_MiB': free, 'used_MiB': used, **current}


def evaluate(net, x, y, trigger):
    net.eval()
    cc = hits = bias = n = 0
    with torch.inference_mode():
        for start in range(0, len(y), 512):
            bx, by = x[start:start+512], y[start:start+512]
            c, t = net(bx), net(core.stamp(bx, trigger))
            assert bool(torch.isfinite(c).all() & torch.isfinite(t).all())
            valid = by != 8
            cc += int((c.argmax(1) == by).sum())
            hits += int(((t.argmax(1) == 8) & valid).sum())
            bias += int(((c.argmax(1) == 8) & valid).sum())
            n += int(valid.sum())
    return {'N': len(y), 'non_target_N': n, 'clean_correct': cc, 'target_successes': hits,
            'clean_target_bias': bias, 'CA_pct': 100*cc/len(y), 'ASR_pct': 100*hits/n, 'trigger_role': trigger}


def train():
    frozen()
    ready = read(ROOT / 'PREPARED.json')
    for name, digest in ready['files'].items():
        assert sha(ROOT / name) == digest, name
    resources = guard()
    write(ROOT / 'STARTED.json', {'pid': os.getpid(), 'time': time.time(), 'resources': resources}, True)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cuda.matmul.allow_tf32 = False
    p = read(ROOT / 'inputs/PROFILE.json')
    spec = importlib.util.spec_from_file_location('fixed_author_net', ROOT / 'inputs/author_model.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    seed(p['seed'])
    from torchvision.datasets import MNIST
    trainset = MNIST(p['data_root'], train=True, download=False)
    testset = MNIST(p['data_root'], train=False, download=False)
    for name, digest in MNIST.resources:
        assert hashlib.md5((Path(trainset.raw_folder)/name).read_bytes()).hexdigest() == digest
    x, y = trainset.data.cuda().float().unsqueeze(1)/255, trainset.targets.cuda()
    tx, ty = testset.data.cuda().float().unsqueeze(1)/255, testset.targets.cuda()
    splits = read(ROOT / 'inputs/SPLIT.json')['indices']
    initial = torch.load(ROOT / 'inputs/round0020.pt', map_location='cpu', weights_only=True)['after']
    settings = core.Settings()
    results = {}
    decisions = {}
    prefix_proof = []
    first_difference = None
    for arm in ['local', 'global']:
        arm_root = ROOT / arm
        arm_root.mkdir(exist_ok=False)
        current = copy.deepcopy(initial)
        net = module.Net().cuda()
        records = []
        decisions[arm] = {}
        for r in range(21, 31):
            clients = sorted(random.Random(p['seed'] + 1000000 + r - 1).sample(range(20), 8))
            submitted_states, role_records = [], []
            common_input = False
            if arm == 'global':
                prior_local = torch.load(ROOT/'local'/f'rounds/round{r:04d}.pt',map_location='cpu',weights_only=True)
                common_input = all(torch.equal(current[k],prior_local['incoming'][k]) for k in current)
                if first_difference is None:
                    assert common_input, 'Incoming diverged before a treatment decision changed'
                local_roles = {role['client']:role for role in prior_local['roles']}
            for client in clients:
                frozen()
                rs = p['seed'] + r * 10000 + client * 100
                seed(rs)
                net.load_state_dict(current, strict=True)
                ids = torch.tensor(splits[client], device='cuda')
                dx, dy = x[ids], y[ids]
                role = {'round': r, 'client': client, 'arm': arm, 'seed': rs,
                        'role': 'defender' if client == 4 else 'attacker' if client < 4 else 'benign', 'phases': []}
                folder = arm_root / 'phases' / f'round{r:04d}_client{client:02d}'
                def log(**values):
                    rec = {'time': time.time(), 'arm': arm, 'round': r, 'client': client, **values}
                    with (arm_root / 'epochs.jsonl').open('a', encoding='utf-8') as f:
                        f.write(json.dumps(rec, allow_nan=False)+'\n')
                        f.flush()
                    write(ROOT / 'STATE.json', {'state': 'training', 'pid': os.getpid(), **rec})
                def capture(number, model, optimizer, loader_rng, batches):
                    item = save(folder / f'phase{number:02d}.pt', {'model': model.state_dict(),
                        'optimizer': optimizer.state_dict(), 'rng': rng(), 'loader_rng': loader_rng,
                        'epochs': 50, 'batches': batches, 'phase': number, 'role': role['role']})
                    role['phases'].append(item)
                    if arm == 'global' and common_input:
                        left = torch.load(ROOT/'local'/f'phases/round{r:04d}_client{client:02d}'/f'phase{number:02d}.pt',map_location='cpu',weights_only=True)
                        right = torch.load(ROOT/item['path'],map_location='cpu',weights_only=True)
                        exact_tree(left,right)
                if client < 5:
                    order = torch.randperm(3000, generator=torch.Generator().manual_seed(p['partition_seed']+client))
                    tr, va = order[300:].cuda(), order[:300].cuda()
                    cx, cy, vx, vy = dx[tr], dy[tr], dx[va], dy[va]
                    px, py = cx.clone(), cy.clone()
                    idx = torch.randperm(2700, generator=torch.Generator().manual_seed(p['partition_seed']+1000+client))[:810].cuda()
                    px[idx] = core.stamp(px[idx], client)
                    py[idx] = 8
                    if client == 4:
                        submitted, decision = core.defender(net, cx, cy, px, py, settings, seed=rs, log=log, capture=capture)
                    else:
                        trigger = client if arm == 'local' else 4
                        submitted, decision = core.attacker(net, cx, cy, px, py, settings, seed=rs, log=log,
                            capture=capture, score=lambda m: evaluate(m, vx, vy, trigger))
                        decisions[arm][f'{r}/{client}'] = decision['gamma']
                    role['decision'] = decision
                    del cx, cy, vx, vy, px, py
                else:
                    submitted, opt, lrng, batches = core.learn(copy.deepcopy(net), dx, dy, settings,
                        phase_seed=rs+1, phase='benign', log=log)
                    capture(1, submitted, opt, lrng, batches)
                    del opt
                state = cpu(submitted.state_dict())
                assert all(bool(torch.isfinite(v).all()) for v in state.values())
                if arm == 'global' and common_input:
                    old_role = local_roles[client]
                    equal_decision = client >=4 or old_role['decision']['gamma'] == role['decision']['gamma']
                    if equal_decision:
                        old_submission = torch.load(ROOT/old_role['submitted']['path'],map_location='cpu',weights_only=True)['model']
                        exact(state,old_submission)
                    elif first_difference is None:
                        first_difference = {'round':r,'client':client,'local_gamma':old_role['decision']['gamma'],'global_gamma':role['decision']['gamma']}
                    prefix_proof.append({'round':r,'client':client,'all_phase_model_optimizer_RNG_exact':True,'same_gamma':equal_decision,'submission_exact_when_same_gamma':True})
                role['submitted'] = save(folder / 'submitted.pt', {'model': state, 'rng': rng()})
                write(arm_root / 'roles' / f'round{r:04d}_client{client:02d}.json', role, True)
                submitted_states.append(state)
                role_records.append(role)
                del submitted, dx, dy
                gc.collect()
            after = {k: torch.stack([s[k] for s in submitted_states]).mean(0) for k in current}
            record = save(arm_root / 'rounds' / f'round{r:04d}.pt', {'round': r, 'clients': clients,
                'incoming': current, 'submitted': submitted_states, 'after': after, 'rng': rng(), 'roles': role_records})
            rb = torch.load(ROOT / record['path'], weights_only=True, map_location='cpu')
            exact(rb['incoming'], current)
            exact(rb['after'], {k: torch.stack([s[k] for s in rb['submitted']]).mean(0) for k in after})
            current = after
            net.load_state_dict(current, strict=True)
            metric = evaluate(net, tx, ty, 4)
            record.update(round=r, clients=clients, evaluation=metric, exact_aggregation=True)
            records.append(record)
            write(arm_root / 'MANIFEST.json', {'arm': arm, 'rounds': records})
            print(json.dumps({'arm': arm, 'round': r, **metric}), flush=True)
            del submitted_states, rb
            gc.collect()
        results[arm] = records
        del net
    a, b = results['local'], results['global']
    violations = {k: sum(e['evaluation']['ASR_pct'] > 10 for e in v) for k, v in results.items()}
    changed = [key for key in decisions['local'] if decisions['local'][key] != decisions['global'][key]]
    checks = {'last3_global_CA97_ASR10': all(e['evaluation']['CA_pct'] >= 97 and e['evaluation']['ASR_pct'] <= 10 for e in b[-3:]),
              'fewer_ASR_violations': violations['global'] < violations['local'], 'changed_decision': len(changed)>0}
    checks['causal_prefix_exact'] = bool(changed) and first_difference is not None and bool(prefix_proof)
    write(ROOT/'PREFIX_PROOF.json',{'first_changed_gamma':first_difference,'common_input_roles':prefix_proof},True)
    write(ROOT / 'RESULT.json', {'state': 'complete', 'results': results, 'violations': violations,
        'changed_gamma_roles': changed, 'checks': checks, 'hypothesis_supported': all(checks.values()),
        'full_paper_reproduced': False, 'unlearning_executed': False, 'time': time.time()}, True)
    write(ROOT / 'STATE.json', {'state': 'complete', 'pid': os.getpid(), 'checks': checks})


if __name__ == '__main__':
    try:
        if sys.argv[1] == 'prepare':
            prepare()
        elif sys.argv[1] == 'train':
            train()
        else:
            raise ValueError('prepare or train required')
    except Exception as exc:
        write(ROOT / ('FAILURE_'+sys.argv[1]+'.json'), {'error': str(exc), 'traceback': traceback.format_exc()}, True)
        raise
