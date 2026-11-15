"""New bounded all-class SSS comparison. Never calls an old finite runner."""
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(temp, path)


def check(meta, base=None):
    path = Path(meta['path'])
    if not path.is_absolute():
        if base is None:
            raise ValueError('relative input requires its declared base')
        path = Path(base) / path
        assert path.resolve().is_relative_to(Path(base).resolve())
    assert sha(path) == meta['sha256'], str(path)
    return path


def setup():
    p = read(ROOT / 'PROFILE.json')
    assert ROOT == Path(p['root'])
    for name, digest in read(ROOT / 'SOURCE_FREEZE.json').items():
        assert sha(ROOT / name) == digest, name
    for name, version in p['versions'].items():
        assert importlib.metadata.version(name) == version, name
    for name, digest in p['external_sources'].items():
        assert sha(Path(p['kernel_root']) / name) == digest, name
    for meta in p['inputs'].values():
        check(meta)
    sys.path.insert(0, p['kernel_root'])
    import torch
    torch.set_num_threads(1)
    torch.backends.cudnn.benchmark = False
    return p


def load(meta, base=None, key=None):
    import torch
    value = torch.load(check(meta, base), map_location='cpu', weights_only=True)
    return value if key is None else value[key]


def save(path, value):
    import torch
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        torch.save(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}


def begin(stage):
    with (ROOT / (stage + '_ONCE.json')).open('x', encoding='utf-8') as stream:
        json.dump({'pid': os.getpid(), 'time': time.time(), 'stage': stage}, stream)


def resource_guard(p):
    from native_memory import memory_information
    from native_processes import processes
    memory = memory_information()
    assert memory['availableBytes'] >= 4 * 2**30, memory
    assert memory['commitLimit'] - memory['committedBytes'] >= 12 * 2**30, memory
    assert shutil.disk_usage(ROOT).free >= 60 * 2**30
    gpu = subprocess.check_output(['nvidia-smi', '--query-gpu=utilization.gpu,memory.free,memory.used',
                                   '--format=csv,noheader,nounits'], text=True).strip()
    util, free, used = map(int, gpu.split(','))
    assert util <= 5 and free >= 4000, gpu
    tokens = ['fu_runner.py', 'clean_fl_runner.py', 'trigger_runner.py', 'train_method_iba.py', 'mpiexec.exe', 'badfu_train.py']
    others = [row for row in processes() if row['ProcessId'] not in (os.getpid(), os.getppid())
              and any(token in row['CommandLine'].lower() for token in tokens)]
    assert not others, others
    return {'memory': memory, 'GPU': {'util': util, 'free_MiB': free, 'used_MiB': used}, 'other_research_trainers': others}


def prepare(p):
    import torch
    from torchvision.datasets import CIFAR10
    from selection import select_all_classes
    begin('prepare')
    case = json.loads(subprocess.check_output([sys.executable, str(Path(p['catalog']) / 'select_case.py'),
                     p['case_id'], '--purpose', 'diagnostic'], text=True, encoding='utf-8'))
    assert case['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    assert case['server_inputs']['pre']['sha256'] == p['pre_sha256']
    write(ROOT / 'private/CASE_SELECTION.json', case)
    old = read(p['inputs']['selection']['path'])
    receipt = read(p['inputs']['selection_verified']['path'])
    assert receipt['state'] == 'passed' and receipt['SSS_result_sha256'] == sha(p['inputs']['selection']['path'])
    parts = read(p['inputs']['split']['path'])['indices']
    assert sorted(sum(parts, [])) == list(range(50000))
    ownership = {str(owner): parts[owner] for owner in [5, 7]}
    selected = select_all_classes(old['owner_ranks'], ownership, 125)
    # The previously verified FP32 scores are reused. The NEW all-class boundary
    # is independently checked in FP64; no repeat query or old audit is launched.
    rows64 = {key: [] for key in ownership}
    for entry in old['query_packets']:
        row = load(entry['packet'], p['query_root'])
        ids = row['source_ids'].tolist()
        owner = entry['owner']
        assert ids == parts[owner][(entry['batch'] - 1) * 128:entry['batch'] * 128]
        for source_id, a, b in zip(ids, row['clean_logits'].tolist(), row['perturbed_logits'].tolist()):
            score = math.sqrt(math.fsum((x - y)**2 for x, y in zip(a, b)))
            rows64[str(owner)].append((source_id, score))
    independent = select_all_classes(rows64, ownership, 125)
    assert {k: set(v) for k, v in selected.items()} == {k: set(v) for k, v in independent.items()}
    assert selected != old['selected_by_owner'], 'no new comparison'
    train = CIFAR10(p['data_root'], train=True, download=False)
    class_counts = [sum(train.targets[i] == label for ids in selected.values() for i in ids) for label in range(10)]
    assert sum(class_counts) == 125
    write(ROOT / 'private/SELECTION.json', {'selected_by_owner': selected, 'delta': old['delta'],
          'pre_checkpoint': old['pre_checkpoint'], 'class_counts': class_counts})
    assert not torch.cuda.is_initialized()
    write(ROOT / 'PREPARED.json', {'state': 'passed', 'case_id': p['case_id'], 'class_counts': class_counts,
          'owner_counts': {k: len(v) for k, v in selected.items()}, 'selection_sha256': sha(ROOT / 'private/SELECTION.json'),
          'FP64_same_top125': True, 'new_forward_calls': 0, 'new_training': 0,
          'overlap_with_old_target125': len(set(sum(selected.values(), [])) & set(sum(old['selected_by_owner'].values(), [])))})


def inputs(p):
    prepared = read(ROOT / 'PREPARED.json')
    assert prepared['state'] == 'passed' and sha(ROOT / 'private/SELECTION.json') == prepared['selection_sha256']
    selection = read(ROOT / 'private/SELECTION.json')
    parts = read(p['inputs']['split']['path'])['indices']
    original = read(p['inputs']['history']['path'])
    assert len(original['rounds']) == 20
    return selection, parts, original


def train(p, branch):
    import torch
    from torchvision import transforms
    from torchvision.datasets import CIFAR10
    import model_reference
    from fu_core import branch_dataset, calibration_round, local_schedule
    from fu_training import train_role
    selection, parts, history = inputs(p)
    guard = resource_guard(p)
    begin('train_' + branch)
    write(ROOT / ('ADMISSION_' + branch + '.json'), guard)
    if branch == 'attack':
        assert read(ROOT / 'AUDIT_benign.json')['state'] == 'passed'
    out = ROOT / 'fu' / branch
    out.mkdir(parents=True, exist_ok=False)
    delta = load(selection['delta'])
    selected = {c: selection['selected_by_owner'].get(str(c), []) for c in range(20)}
    data = CIFAR10(p['data_root'], train=True, download=False, transform=transforms.Compose([
        transforms.RandomCrop(32, padding=4), transforms.RandomHorizontalFlip(), transforms.ToTensor(),
        transforms.Normalize((.5,) * 3, (.5,) * 3)]))
    old_base = p['foundation_root']
    new_global = load(history['rounds'][0]['incoming'], old_base)
    incoming = save(out / 'initial.pt', new_global)
    manifest = {'branch': branch, 'selection_sha256': sha(ROOT / 'private/SELECTION.json'),
                'source_freeze_sha256': sha(ROOT / 'SOURCE_FREEZE.json'), 'initial': incoming, 'rounds': []}
    model = model_reference.ResNet18().cuda()
    for record in history['rounds']:
        r, clients = record['round'], record['clients']
        assert clients == p['clients']
        old_global = load(record['incoming'], old_base)
        old_meta = {row['client']: row['checkpoint'] for row in record['roles']}
        old_states = {c: load(old_meta[c], old_base, 'model') for c in clients}
        trained, roles = {}, []
        for client in clients:
            model.load_state_dict(new_global, strict=True)
            dataset = branch_dataset(data, parts[client], selected[client], delta, branch)
            ids = [i for i in parts[client] if branch == 'attack' or i not in set(selected[client])]
            schedule = local_schedule(r, client, len(dataset))
            def event(values):
                row = {'branch': branch, 'round': r, 'client': client, **values, 'time': time.time()}
                with (out / 'epochs.jsonl').open('a', encoding='utf-8') as stream:
                    stream.write(json.dumps(row, allow_nan=False) + '\n')
                write(ROOT / 'STATE.json', {'stage': 'training', 'pid': os.getpid(), **row})
            value = train_role(model, dataset, ids, schedule, 'cuda', event)
            value.update(round=r, client=client, branch=branch, selected_source_ids=selected[client])
            meta = save(out / 'trained' / f'round{r:02d}_client{client:02d}.pt', value)
            roles.append({'client': client, 'checkpoint': meta, 'source_N': len(dataset), 'batches': value['batches']})
            trained[client] = value['model']
            del value
        after, effective, calibrated, reused = calibration_round(r, clients, [5, 7], old_states, trained, old_global, new_global)
        model.load_state_dict(after, strict=True)
        assert all(bool(torch.isfinite(value).all()) for value in after.values())
        saved = save(out / 'rounds' / f'round{r:02d}.pt', after)
        reloaded = load(saved, ROOT)
        assert all(torch.equal(after[key], reloaded[key]) for key in after)
        manifest['rounds'].append({'round': r, 'clients': clients, 'roles': roles, 'incoming': incoming,
                                   'after': saved, 'reused_original_nonowners': reused})
        write(out / 'MANIFEST.json', manifest)
        new_global, incoming = after, saved
        del trained, old_states, effective, calibrated, reloaded
        write(ROOT / 'STATE.json', {'stage': 'round_committed', 'branch': branch, 'round': r, 'pid': os.getpid(), 'time': time.time()})
    endpoint = save(out / 'after.pt', new_global)
    write(ROOT / ('TRAINED_' + branch + '.json'), {'state': 'completed', 'rounds': 20, 'roles': 200,
          'epochs': 1000, 'after': endpoint, 'manifest_sha256': sha(out / 'MANIFEST.json')})


def evaluate(p, route):
    import torch
    from torchvision.datasets import CIFAR10
    import model_reference
    selection, _, _ = inputs(p)
    guard = resource_guard(p)
    begin('eval_' + route)
    assert read(ROOT / 'AUDIT_attack.json')['state'] == 'passed'
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision('highest')
    torch.use_deterministic_algorithms(True)
    delta = load(selection['delta']).cuda()
    if delta.ndim == 4:
        delta = delta[0]
    data = CIFAR10(p['data_root'], train=False, download=False)
    names = ['pre', 'benign', 'attack']
    endpoints = {'pre': selection['pre_checkpoint'], **{b: read(ROOT / ('TRAINED_' + b + '.json'))['after'] for b in names[1:]}}
    if route == 'independent':
        names.reverse()
    model = model_reference.ResNet18().cuda().eval()
    result, saved_logits = {}, {}
    with torch.inference_mode():
        for name in names:
            model.load_state_dict(load(endpoints[name], ROOT), strict=True)
            outputs, hashes = [], []
            for start in range(0, 10000, 128):
                if route == 'primary':
                    x = torch.as_tensor(data.data[start:start+128]).permute(0, 3, 1, 2).contiguous().float().div_(255).sub_(.5).div_(.5)
                else:
                    import numpy as np
                    array = np.ascontiguousarray(data.data[start:start+128].transpose(0, 3, 1, 2), dtype=np.float32)
                    array = ((array / np.float32(255)) - np.float32(.5)) / np.float32(.5)
                    x = torch.from_numpy(array)
                hashes.append(hashlib.sha256(x.numpy().tobytes()).hexdigest())
                x = x.cuda()
                clean = model(x)
                triggered = model((x + 1.5 * delta).clamp(-1, 1))
                assert bool(torch.isfinite(clean).all()) and bool(torch.isfinite(triggered).all())
                outputs.append(torch.stack([clean.cpu(), triggered.cpu()]))
            all_logits = torch.cat(outputs, dim=1)
            labels = torch.tensor(data.targets)
            hits = int((all_logits[1].argmax(1)[labels != 2] == 2).sum())
            correct = int((all_logits[0].argmax(1) == labels).sum())
            result[name] = {'correct': correct, 'clean_N': 10000, 'target_hits': hits, 'ASR_N': 9000,
                            'CA': 100 * correct / 10000, 'ASR': 100 * hits / 9000, 'checkpoint': endpoints[name]}
            saved_logits[name] = all_logits
    meta = save(ROOT / 'private' / (route + '_logits.pt'), {'logits': saved_logits, 'input_hashes': hashes, 'labels': labels})
    write(ROOT / ('EVAL_' + route + '.json'), {'state': 'completed', 'route': route, 'metrics': result, 'logits': meta,
          'sample_forwards': 60000, 'calls': 474, 'guard': guard, 'layout': 'contiguous_NCHW_FP32'})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['prepare', 'benign', 'attack', 'primary', 'independent', 'controller'])
    args = parser.parse_args()
    p = setup()
    if args.stage == 'prepare':
        prepare(p)
    elif args.stage in ['benign', 'attack']:
        train(p, args.stage)
    elif args.stage in ['primary', 'independent']:
        evaluate(p, args.stage)
    else:
        begin('controller')
        stages = [('run.py', 'benign'), ('verify.py', 'benign'), ('run.py', 'attack'), ('verify.py', 'attack'),
                  ('run.py', 'primary'), ('run.py', 'independent'), ('verify.py', 'final')]
        for script, stage in stages:
            write(ROOT / 'CONTROLLER.json', {'state': 'running', 'stage': stage, 'script': script, 'pid': os.getpid(), 'time': time.time()})
            with (ROOT / (script + '_' + stage + '.log')).open('x', encoding='utf-8') as log:
                subprocess.run([sys.executable, '-u', str(ROOT / script), stage], stdout=log, stderr=subprocess.STDOUT, check=True)
        write(ROOT / 'CONTROLLER.json', {'state': 'completed', 'pid': os.getpid(), 'time': time.time()})


if __name__ == '__main__':
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
    os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
    try:
        main()
    except BaseException:
        write(ROOT / ('FAILURE_' + '_'.join(sys.argv[1:]) + '.json'), {'time': time.time(), 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
