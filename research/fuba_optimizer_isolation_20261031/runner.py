"""New finite two-arm experiment. Never invokes any old trainer/controller."""
import gc
import hashlib
import importlib.util
import json
import os
import platform
import random
import struct
import subprocess
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import torch
from optimizer_policy import apply_weights, make_reweighted_optimizer

ROOT = Path(__file__).resolve().parent
P = json.loads((ROOT / 'PROFILE.json').read_text(encoding='utf-8'))
PACKET = Path(P['input_packet'])
OUT = ROOT / 'run'
STATE = {'profile': P['id'], 'pid': os.getpid(), 'state': 'preparing'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(4 << 20), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def status(**fields):
    STATE.update(fields, updated_unix=time.time())
    write(ROOT / 'STATE.json', STATE)


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def cpu(value):
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {k: cpu(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return type(value)(cpu(v) for v in value)
    return value


def save(path, value):
    path = Path(path)
    assert not path.exists(), path
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('xb') as f:
        torch.save(cpu(value), f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return {'path': path.name, 'sha256': sha(path), 'bytes': path.stat().st_size}


def restore_rng(rng):
    random.setstate(rng['python'])
    state = rng['numpy']
    np.random.set_state((state[0], np.array(state[1], dtype=np.uint32), *state[2:]))
    torch.set_rng_state(rng['torch_CPU'])
    torch.cuda.set_rng_state_all(rng['torch_CUDA'])


def capture_rng():
    n = np.random.get_state()
    return {'python': random.getstate(), 'numpy': (n[0], n[1].tolist(), int(n[2]), int(n[3]), float(n[4])),
            'torch_CPU': torch.get_rng_state(), 'torch_CUDA': torch.cuda.get_rng_state_all()}


def resource_guard():
    rows = subprocess.check_output(['nvidia-smi', '--query-gpu=utilization.gpu,memory.free,memory.used',
                                    '--format=csv,noheader,nounits'], text=True).strip().splitlines()
    assert len(rows) == 1
    util, free, used = [int(x.strip()) for x in rows[0].split(',')]
    assert util <= 5 and free >= 7000 and used <= 2048, (util, free, used)
    command = "Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python|mpiexec'} | Select-Object ProcessId,CommandLine | ConvertTo-Json"
    raw = subprocess.check_output(['powershell', '-NoProfile', '-Command', command], text=True).strip()
    processes = json.loads(raw) if raw else []
    if isinstance(processes, dict):
        processes = [processes]
    for row in processes:
        if row['ProcessId'] in [os.getpid(), os.getppid()]:
            continue
        cmd = (row.get('CommandLine') or '').lower()
        if any(t in cmd for t in ['mpiexec.exe', 'badfu_train.py', 'fuba_queue_worker.py',
                                 'fuba_v2_run.py', 'train_method_iba.py', '/runner.py', '\\runner.py',
                                 'independent_evaluate.py']):
            raise RuntimeError('Competing training process: ' + str(row['ProcessId']))
    return {'utilization_pct': util, 'free_MiB': free, 'used_MiB': used,
            'policy': 'new bounded protocol; no other apps stopped'}


def evaluate(model, generator, dataset, epsilon):
    model.eval()
    generator.eval()
    correct = target = clean_target = non_n = total = 0
    with torch.inference_mode():
        loader = torch.utils.data.DataLoader(dataset, batch_size=32, shuffle=False, num_workers=0)
        for x, y in loader:
            x = x.cuda().contiguous()
            y = y.cuda()
            clean = model(x)
            triggered = model((x + epsilon * generator(x)).clamp(0, 1))
            assert torch.isfinite(clean).all() and torch.isfinite(triggered).all()
            non = y != P['target']
            total += len(y)
            non_n += int(non.sum())
            correct += int((clean.argmax(1) == y).sum())
            clean_target += int(((clean.argmax(1) == P['target']) & non).sum())
            target += int(((triggered.argmax(1) == P['target']) & non).sum())
    assert total and non_n
    return {'N': total, 'non_target_N': non_n, 'clean_correct': correct,
            'triggered_target_count': target, 'clean_non_target_target_count': clean_target,
            'CA_pct': 100 * correct / total, 'ASR_pct': 100 * target / non_n,
            'clean_target_bias_pct': 100 * clean_target / non_n, 'epsilon': epsilon,
            'layout': 'contiguous_NCHW', 'both_eval': True}


def main():
    freeze = json.loads((ROOT / 'FREEZE.json').read_text(encoding='utf-8'))
    for name, digest in freeze['files'].items():
        assert sha(ROOT / name) == digest, name
    contracts = json.loads((ROOT / 'CPU_CONTRACTS.json').read_text(encoding='utf-8'))
    assert contracts['state'] == 'passed'
    assert not (ROOT / 'STARTED.json').exists(), 'one-time experiment already started'
    guard = resource_guard()
    with (ROOT / 'STARTED.json').open('x', encoding='utf-8') as f:
        json.dump({'pid': os.getpid(), 'time_unix': time.time(), 'resource_guard': guard,
                   'freeze_sha256': sha(ROOT / 'FREEZE.json')}, f, indent=2)
    OUT.mkdir(exist_ok=False)
    try:
        torch.set_num_threads(1)
        torch.backends.cudnn.benchmark = False
        assert sha(PACKET / 'DELIVERY_MANIFEST.json') == P['manifest_sha256']
        assert sha(PACKET / 'DELIVERY_SEAL.json') == P['seal_sha256']
        manifest = json.loads((PACKET / 'DELIVERY_MANIFEST.json').read_text(encoding='utf-8'))
        phase = 'last_phases/round0100_client01/'
        sources = ['source/paper_core.py', 'source/profile_helpers.py', 'source/model/resnet.py',
                   'source/model/model.py', 'source/SPLIT.json', 'source/PROFILE.json',
                   'roles/round0100_client01.json'] + [phase + n for n in [
                       'post_generator.pt', 'phase01.pt', 'phase02.pt', 'phase03.pt']]
        checks = {}
        for name in sources:
            digest = sha(PACKET / name)
            assert digest == manifest['files'][name]['sha256'], name
            checks[name] = digest
        write(ROOT / 'INPUT_CHECKS.json', {'case_id': P['case_id'], 'purpose': 'diagnostic',
              'selection_guard_previously_passed': 'all_snapshot_files_verified_on_this_host',
              'files_sha256': checks, 'payloads': {'post_generator.pt': ['incoming', 'classifier_generator'],
                                                 'phase01.pt': ['model'], 'phase02.pt': ['model', 'rng'],
                                                 'phase03.pt': ['model']}})
        core = module(PACKET / 'source/paper_core.py', 'isolation_core')
        helpers = module(PACKET / 'source/profile_helpers.py', 'isolation_helpers')
        resnet = module(PACKET / 'source/model/resnet.py', 'isolation_resnet').resnet18
        unet = module(PACKET / 'source/model/model.py', 'isolation_unet').UNet
        post = torch.load(PACKET / (phase + 'post_generator.pt'), map_location='cpu', weights_only=True)
        first = torch.load(PACKET / (phase + 'phase01.pt'), map_location='cpu', weights_only=True)
        second = torch.load(PACKET / (phase + 'phase02.pt'), map_location='cpu', weights_only=True)
        original = torch.load(PACKET / (phase + 'phase03.pt'), map_location='cpu', weights_only=True)['model']
        anchor = resnet()
        benign = resnet()
        anchor.load_state_dict(first['model'], strict=True)
        benign.load_state_dict(second['model'], strict=True)
        weights = core.gradient_weights(anchor, benign)
        del first, anchor, benign
        generator = unet(3).cuda().eval()
        generator.load_state_dict(post['classifier_generator'], strict=True)
        for parameter in generator.parameters():
            parameter.requires_grad_(False)
        epsilon = helpers.training_epsilon(99)
        from torchvision.datasets import CIFAR10
        from torchvision.transforms import ToTensor
        train = CIFAR10(P['data_root'], train=True, download=False, transform=ToTensor())
        test = CIFAR10(P['data_root'], train=False, download=False, transform=ToTensor())
        splits = json.loads((PACKET / 'source/SPLIT.json').read_text(encoding='utf-8'))['full_indices']
        assert len(train) == 50000 and len(test) == 10000
        all_ids = splits[P['client']]
        assert len(all_ids) == 2500 and len(set(all_ids)) == 2500
        order = torch.randperm(2500, generator=torch.Generator().manual_seed(P['partition_seed'] + P['client'])).tolist()
        valid_ids = [all_ids[i] for i in order[:250]]
        train_ids = [all_ids[i] for i in order[250:]]
        assert set(valid_ids).isdisjoint(train_ids)
        valid = torch.utils.data.Subset(train, valid_ids)

        class Indexed(torch.utils.data.Dataset):
            def __len__(self):
                return len(train_ids)

            def __getitem__(self, index):
                idx = train_ids[index]
                x, y = train[idx]
                return x, y, idx

        write(ROOT / 'RUNTIME.json', {'python': sys.version, 'torch': torch.__version__, 'numpy': np.__version__,
              'CUDA': torch.version.cuda, 'cuDNN': torch.backends.cudnn.version(), 'host': platform.node(),
              'GPU': torch.cuda.get_device_name(0), 'training_epsilon': epsilon, 'test_epsilon': .05,
              'cudnn_benchmark': False, 'TF32_matmul': torch.backends.cuda.matmul.allow_tf32,
              'TF32_cudnn': torch.backends.cudnn.allow_tf32, 'train_count': 2250, 'valid_count': 250})
        model = resnet().cuda()
        model.load_state_dict(post['incoming'], strict=True)
        status(state='evaluating_incoming')
        incoming = evaluate(model, generator, test, .05)
        weights = {k: v.cuda() for k, v in weights.items()}
        result = {'case_id': P['case_id'], 'profile': P['id'], 'incoming': incoming,
                  'training_epsilon': epsilon, 'arms': {}, 'actual_FL_or_FU_run': False}
        for arm in P['arms']:
            model.load_state_dict(post['incoming'], strict=True)
            model.train()
            optimizer = make_reweighted_optimizer(model.parameters(), interpretation=arm, learning_rate=.001)
            restore_rng(second['rng'])
            loader = torch.utils.data.DataLoader(Indexed(), batch_size=64, shuffle=True, num_workers=0)

            def poison(images):
                return helpers.trigger(images, generator, epsilon)

            objective = core.poisoned_objective(poison, P['target'], .3)
            epoch_orders = []
            batches = 0
            torch.cuda.reset_peak_memory_stats()
            started = time.time()
            for epoch in range(P['epochs']):
                status(state='training', arm=arm, epoch=epoch + 1, completed_epochs=epoch, epochs=P['epochs'])
                order_hash = hashlib.sha256()
                loss_sum = count = 0
                for x, y, ids in loader:
                    order_hash.update(struct.pack('<' + 'q' * len(ids), *ids.tolist()))
                    x, y = x.cuda(), y.cuda()
                    optimizer.zero_grad(set_to_none=True)
                    loss = objective(model, x, y)
                    assert torch.isfinite(loss), 'nonfinite loss'
                    loss.backward()
                    apply_weights(model, weights)
                    optimizer.step()
                    loss_sum += float(loss.detach()) * len(y)
                    count += len(y)
                    batches += 1
                assert count == 2250
                epoch_orders.append(order_hash.hexdigest())
                event = {'arm': arm, 'epoch': epoch + 1, 'examples': count, 'batches_cumulative': batches,
                         'mean_loss': loss_sum / count, 'batch_order_sha256': epoch_orders[-1],
                         'elapsed_seconds': time.time() - started}
                with (OUT / 'epochs.jsonl').open('a', encoding='utf-8') as f:
                    f.write(json.dumps(event, allow_nan=False) + '\n')
                    f.flush()
                for name, digest in freeze['files'].items():
                    assert sha(ROOT / name) == digest, ('changed execution source', name)
            assert batches == 50 * 36
            for value in model.state_dict().values():
                assert torch.isfinite(value).all()
            end_rng = capture_rng()
            status(state='evaluating', arm=arm, completed_epochs=50)
            metrics = evaluate(model, generator, test, .05)
            local = evaluate(model, generator, valid, .05)
            assert (metrics['N'], metrics['non_target_N']) == (10000, 9000)
            bit_equal = all(torch.equal(v.detach().cpu(), original[k]) for k, v in model.state_dict().items())
            receipt = save(OUT / (arm + '.pt'), {'model': model.state_dict(), 'optimizer': optimizer.state_dict(),
                           'rng': end_rng, 'profile_id': P['id'], 'interpretation': arm,
                           'epochs': 50, 'batches': batches, 'evaluation': metrics})
            result['arms'][arm] = {'full_test': metrics, 'local250': local, 'epochs': 50, 'batches': batches,
                                  'epoch_orders': epoch_orders, 'checkpoint': receipt,
                                  'same_bits_as_original_v7_phase3': bit_equal,
                                  'optimizer_class': type(optimizer).__name__,
                                  'peak_GPU_allocated_bytes': torch.cuda.max_memory_allocated()}
            write(ROOT / 'PARTIAL_RESULT.json', result)
            del optimizer
            gc.collect()
        a, b = [result['arms'][arm]['full_test'] for arm in P['arms']]
        assert result['arms'][P['arms'][0]]['epoch_orders'] == result['arms'][P['arms'][1]]['epoch_orders']
        gains = {'ASR_gain_pct_points': b['ASR_pct'] - a['ASR_pct'],
                 'B_CA_change_vs_A_pct_points': b['CA_pct'] - a['CA_pct'],
                 'B_CA_change_vs_incoming_pct_points': b['CA_pct'] - incoming['CA_pct'],
                 'B_clean_bias_change_vs_A_pct_points': b['clean_target_bias_pct'] - a['clean_target_bias_pct'],
                 'B_clean_bias_change_vs_incoming_pct_points': b['clean_target_bias_pct'] - incoming['clean_target_bias_pct']}
        passed = gains['ASR_gain_pct_points'] >= 20 and min(gains['B_CA_change_vs_A_pct_points'], gains['B_CA_change_vs_incoming_pct_points']) >= -5 and max(gains['B_clean_bias_change_vs_A_pct_points'], gains['B_clean_bias_change_vs_incoming_pct_points']) <= 5
        result.update(state='complete', same_epoch_orders=True, comparisons=gains,
                      hypothesis='supported_in_this_role' if passed else 'not_supported_in_this_role',
                      full_FL_launch_authorized_by_this_result=False,
                      limitations=['One fixed phase and one seed, no latent pair or detection claim.',
                                   'Existing FUBA results preserved; no old trainer/evaluator invoked.'])
        result['fixed_generator'] = save(OUT / 'fixed_generator.pt', post['classifier_generator'])
        result['incoming_classifier'] = save(OUT / 'incoming_classifier.pt', post['incoming'])
        write(ROOT / 'RESULT.json', result)
        status(state='complete', hypothesis=result['hypothesis'])
        print(json.dumps({'state': result['state'], 'hypothesis': result['hypothesis'], 'comparisons': gains}), flush=True)
    except BaseException:
        write(ROOT / 'FAILURE.json', {'traceback': traceback.format_exc(), 'state': STATE,
                                     'time_unix': time.time()})
        status(state='failed')
        raise


if __name__ == '__main__':
    main()
