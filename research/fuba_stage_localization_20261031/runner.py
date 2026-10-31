"""New bounded inference on immutable stage states; reuses old endpoint counts."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

sys.dont_write_bytecode = True
import torch
from torchvision.datasets import MNIST

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def main():
    p = read(ROOT / 'PROFILE.json')
    for name, digest in read(ROOT / 'FREEZE.json')['files'].items():
        assert sha(ROOT / name) == digest, name
    selection = json.loads(subprocess.check_output([sys.executable, p['catalog_selector'], p['case_id'], '--purpose', 'diagnostic']).decode('utf-8'))
    assert selection['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    assert selection['checkpoint_guard']['manifest_sha256'] == p['manifest_sha256']
    review = Path(p['review_root'])
    m = read(review / 'DELIVERY_MANIFEST.json')
    helper = module('stage_common', review / 'common.py')
    core = module('stage_core', review / 'reference_core.py')
    idle = helper.guard()
    write_new(ROOT / 'STARTED.json', {'pid': os.getpid(), 'time_unix': time.time(), 'resource_guard': idle,
                                     'selection': selection, 'source_freeze': read(ROOT / 'FREEZE.json')})
    try:
        torch.set_num_threads(1)
        torch.backends.cudnn.benchmark = False
        profile = read(review / 'PROFILE.json')
        verified = read(review / 'VERIFIED.json')
        endpoints = read(review / 'RESULT.json')
        for label in ['before', 'after']:
            assert all(verified['independent_counts'][label][key] == endpoints[label][key] for key in ['clean_correct', 'target_successes', 'non_target_N'])
        test = MNIST(profile['data_root'], train=False, download=False)
        train = MNIST(profile['data_root'], train=True, download=False)
        tx = test.data.cuda().float().unsqueeze(1).div_(255)
        ty = test.targets.cuda()
        assert len(ty) == 10000 and tx.is_contiguous()
        splits = read(review / 'SPLIT.json')['indices']
        model = helper.load_model_class()().cuda().eval()
        cache, records = {}, []

        def load(path, key):
            rel = path.replace('\\', '/')
            source = (review / rel).resolve()
            assert source.is_relative_to(review.resolve()) and sha(source) == m['files'][rel]['sha256']
            data = torch.load(source, map_location='cpu', weights_only=True)
            if key != '$':
                for part in key.split('/'):
                    data = data[int(part)] if isinstance(data, list) else data[part]
            model.load_state_dict(data, strict=True)
            model.eval()
            return rel

        def evaluate(x, y, role):
            clean_correct = target_successes = clean_bias = non_count = 0
            with torch.inference_mode():
                for start in range(0, len(y), 512):
                    xb, yb = x[start:start + 512], y[start:start + 512]
                    logits = model(xb)
                    triggered = model(core.stamp(xb, role))
                    assert bool(torch.isfinite(logits).all() & torch.isfinite(triggered).all())
                    clean, attack, non = logits.argmax(1), triggered.argmax(1), yb != 8
                    clean_correct += int((clean == yb).sum())
                    target_successes += int(((attack == 8) & non).sum())
                    clean_bias += int(((clean == 8) & non).sum())
                    non_count += int(non.sum())
            return {'N': len(y), 'non_target_N': non_count, 'clean_correct': clean_correct,
                    'target_successes': target_successes, 'clean_target_count': clean_bias,
                    'CA_pct': 100 * clean_correct / len(y), 'ASR_pct': 100 * target_successes / non_count,
                    'clean_target_bias_pct': 100 * clean_bias / non_count, 'trigger_role': role}

        def point(path, key, label, role=None):
            rel = load(path, key)
            cache_key = rel + ':' + key
            if cache_key not in cache:
                cache[cache_key] = evaluate(tx, ty, 4)
            item = {'label': label, 'path': rel, 'payload_key': key, 'global_test': cache[cache_key]}
            if role is not None:
                client = role['client']
                ids = torch.tensor(splits[client])
                order = torch.randperm(3000, generator=torch.Generator().manual_seed(profile['partition_seed'] + client))[:300]
                vx = train.data[ids[order]].cuda().float().unsqueeze(1).div_(255)
                vy = train.targets[ids[order]].cuda()
                item['local_validation'] = evaluate(vx, vy, client)
                item.update(round=role['round'], client=client, role=role['role'])
            records.append(item)
            print(json.dumps({'point': label, 'CA': item['global_test']['CA_pct'], 'ASR': item['global_test']['ASR_pct']}), flush=True)
            return item

        subtraction = point('run/after_subtraction.pt', '$', 'after_subtraction_before_KD')
        all_roles = [read(path) for path in sorted((review / 'run/roles').glob('*.json'))]
        chosen = [next(r for r in all_roles if r['role'] == label) for label in ['attacker', 'defender']]
        chosen += [r for r in all_roles if r['round'] == 100 and r['role'] != 'benign']
        assert len(chosen) <= 7
        for role in chosen:
            prefix = f"r{role['round']}_c{role['client']}"
            point(f"run/rounds/round{role['round']:04d}.pt", 'incoming', prefix + '_incoming', role)
            for i, phase in enumerate(role['phases'], 1):
                point(phase['path'], 'model', prefix + '_phase' + str(i), role)
            point(role['submitted']['path'], 'model', prefix + '_submitted', role)
        s, post = subtraction['global_test'], endpoints['after']
        supported = s['CA_pct'] >= 97 and s['ASR_pct'] >= 60 and post['CA_pct'] >= 97 and post['ASR_pct'] < 60
        write_new(ROOT / 'RESULT.json', {'state': 'complete', 'profile': p['id'],
                  'hypothesis_KD_destroyed_strong_activation': 'supported_in_this_run' if supported else 'not_supported_in_this_run',
                  'after_subtraction': s, 'reused_verified_endpoints': {'before': endpoints['before'], 'after': post},
                  'roles': [{'round': r['round'], 'client': r['client'], 'role': r['role']} for r in chosen],
                  'points': records, 'unique_full_test_states': len(cache), 'training_performed': False,
                  'checkpoint_edits': False, 'case_id': p['case_id'], 'manifest_sha256': p['manifest_sha256'],
                  'evaluator_sha256': sha(ROOT / 'runner.py'), 'resource_guard': idle,
                  'scope': 'New stage inference only. Old endpoint evaluation reused. No reproduction/detection success asserted.'})
    except BaseException:
        write_new(ROOT / 'FAILURE.json', {'traceback': traceback.format_exc()})
        raise


if __name__ == '__main__':
    main()
