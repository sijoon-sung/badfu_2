"""Finite paper-reference MNIST/DBA FL100 + actual historical subtraction/KD10."""
import copy
import gc
import os
import random
import sys
import time
import traceback
from pathlib import Path
import torch
from common import ROOT, read, sha, write, save, cpu, seed, rng, exact, guard, load_model_class
import reference_core as core

P = read(ROOT / 'PROFILE.json')
OUT = ROOT / 'run'
STATE = {'pid': os.getpid(), 'profile': P['id'], 'state': 'starting', 'rounds': 0}


def status(**fields):
    STATE.update(fields, updated_unix=time.time())
    write(ROOT / 'STATE.json', STATE)


def event(**value):
    with (OUT / 'events.jsonl').open('a', encoding='utf-8') as f:
        import json
        f.write(json.dumps({'time_unix': time.time(), **value}, allow_nan=False) + '\n')
        f.flush()


def evaluate(model, x, y, role=4):
    model.eval()
    correct = torch.zeros((), device=x.device, dtype=torch.long)
    target = correct.clone()
    clean_target = correct.clone()
    non_count = correct.clone()
    with torch.inference_mode():
        for start in range(0, len(y), 512):
            xb, yb = x[start:start + 512], y[start:start + 512]
            clean = model(xb)
            attacked = model(core.stamp(xb, role))
            non = yb != 8
            correct.add_((clean.argmax(1) == yb).sum())
            target.add_(((attacked.argmax(1) == 8) & non).sum())
            clean_target.add_(((clean.argmax(1) == 8) & non).sum())
            non_count.add_(non.sum())
    a, b, c, n = [int(v) for v in [correct, target, clean_target, non_count]]
    assert n > 0
    return {'N': len(y), 'non_target_N': n, 'clean_correct': a, 'target_successes': b,
            'clean_non_target_target_count': c, 'CA_pct': 100 * a / len(y), 'ASR_pct': 100 * b / n,
            'clean_target_bias_pct': 100 * c / n, 'trigger_role': role, 'both_eval': True}


def main():
    freeze = read(ROOT / 'FREEZE.json')
    for name, digest in freeze['files'].items():
        assert sha(ROOT / name) == digest, name
    ready = read(ROOT / 'READY.json')
    assert ready['state'] == 'passed'
    for name, digest in ready['source_hashes'].items():
        assert sha(ROOT / name) == digest, name
    idle = guard()
    with (ROOT / 'STARTED.json').open('x', encoding='utf-8') as f:
        import json
        json.dump({'pid': os.getpid(), 'time_unix': time.time(), 'guard': idle}, f)
    OUT.mkdir(exist_ok=False)
    try:
        torch.set_num_threads(1)
        torch.backends.cudnn.benchmark = False
        seed(P['seed'])
        from torchvision.datasets import MNIST
        train = MNIST(P['data_root'], train=True, download=False)
        test = MNIST(P['data_root'], train=False, download=False)
        x = train.data.cuda().float().unsqueeze(1).div_(255)
        y = train.targets.cuda()
        tx = test.data.cuda().float().unsqueeze(1).div_(255)
        ty = test.targets.cuda()
        assert len(y) == 60000 and len(ty) == 10000
        splits = read(ROOT / 'SPLIT.json')['indices']
        Net = load_model_class()
        m = Net().cuda()
        current = torch.load(ROOT / 'initial.pt', map_location='cpu', weights_only=True)
        m.load_state_dict(current, strict=True)
        settings = core.Settings()
        manifest = {'profile': P['id'], 'initial_sha256': sha(ROOT / 'initial.pt'), 'rounds': []}
        write(ROOT / 'RUNTIME.json', {'python': sys.version, 'torch': torch.__version__,
              'CUDA': torch.version.cuda, 'cuDNN': torch.backends.cudnn.version(),
              'GPU': torch.cuda.get_device_name(0), 'resident_tensors': True,
              'precision': 'float32', 'batch_synchronization': 'finite/loss at epoch boundary',
              'source_sha256': ready['source_hashes']})
        first_role = True
        for r in range(1, 101):
            states, roles = [], []
            clients = sorted(random.Random(P['seed'] + 1000000 + r - 1).sample(range(20), 8))
            for client in clients:
                for name, digest in ready['source_hashes'].items():
                    assert sha(ROOT / name) == digest, name
                role_seed = P['seed'] + r * 10000 + client * 100
                seed(role_seed)
                m.load_state_dict(current, strict=True)
                incoming = copy.deepcopy(m)
                ids = torch.tensor(splits[client], device='cuda')
                data_x, data_y = x[ids], y[ids]
                malicious = r > 5 and client < 5
                role_name = 'defender' if malicious and client == 4 else 'attacker' if malicious else 'benign'
                role = {'round': r, 'client': client, 'role': role_name, 'seed': role_seed,
                        'state': 'running', 'phases': []}
                role_path = OUT / 'roles' / f'round{r:04d}_client{client:02d}.json'
                phase_root = OUT / 'phases' / f'round{r:04d}_client{client:02d}'
                phase_root.mkdir(parents=True)

                def log(**values):
                    event(kind='phase_epoch', round=r, client=client, **values)
                    status(state='training', round=r, client=client, role=role_name, **values)

                def capture(number, model, optimizer, loader_rng, batches):
                    e = save(phase_root / f'phase{number:02d}.pt', {'model': model.state_dict(),
                              'optimizer': optimizer.state_dict(), 'rng': rng(), 'loader_rng': loader_rng,
                              'epochs': 50, 'batches': batches, 'role': role_name, 'phase': number})
                    role['phases'].append(e)
                    write(role_path, role)

                if malicious:
                    order = torch.randperm(3000, generator=torch.Generator().manual_seed(P['partition_seed'] + client))
                    train_pos = order[300:].cuda()
                    valid_pos = order[:300].cuda()
                    vx, vy = data_x[valid_pos], data_y[valid_pos]
                    cx, cy = data_x[train_pos], data_y[train_pos]
                    px, py = cx.clone(), cy.clone()
                    poison_pos = torch.randperm(2700, generator=torch.Generator().manual_seed(P['partition_seed'] + 1000 + client))[:810].cuda()
                    px[poison_pos] = core.stamp(px[poison_pos], client)
                    py[poison_pos] = 8
                    role.update(train_N=2700, validation_N=300, poison_N=810,
                                original_label_target_count=int((cy == 8).sum()))
                    if client == 4:
                        submitted, decision = core.defender(incoming, cx, cy, px, py, settings,
                                                            seed=role_seed, log=log, capture=capture)
                    else:
                        submitted, decision = core.attacker(incoming, cx, cy, px, py, settings,
                                                            seed=role_seed, log=log, capture=capture,
                                                            score=lambda candidate: evaluate(candidate, vx, vy, client))
                    role['decision'] = decision
                    role['local_after'] = evaluate(submitted, vx, vy, client)
                    del cx, cy, px, py, vx, vy
                else:
                    submitted, optimizer, loader_rng, batches = core.learn(copy.deepcopy(incoming), data_x, data_y, settings,
                                                                           phase_seed=role_seed + 1, phase='benign', log=log)
                    capture(1, submitted, optimizer, loader_rng, batches)
                    role.update(train_N=3000, validation_N=0, poison_N=0)
                    del optimizer
                s = cpu(submitted.state_dict())
                assert all(bool(torch.isfinite(v).all()) for v in s.values())
                role['submitted'] = save(phase_root / 'submitted.pt', {'model': s, 'rng': rng()})
                role.update(state='complete')
                write(role_path, role)
                states.append(s)
                roles.append({'path': str(role_path.relative_to(ROOT)), 'sha256': sha(role_path)})
                if first_role:
                    checkpoint = torch.load(ROOT / role['phases'][0]['path'], map_location='cpu', weights_only=True)
                    assert checkpoint['epochs'] == 50 and checkpoint['batches'] == 2350
                    exact(checkpoint['model'], s)
                    write(ROOT / 'FIRST_ROLE_VERIFIED.json', {'round': r, 'client': client, 'actual_epochs': 50,
                          'actual_batches': 2350, 'checkpoint_sha256': role['phases'][0]['sha256'], 'state': 'passed'})
                    first_role = False
                del incoming, submitted, data_x, data_y
                gc.collect()
            after = {k: torch.stack([s[k] for s in states]).mean(0) for k in current}
            record = save(OUT / 'rounds' / f'round{r:04d}.pt', {'round': r, 'clients': clients,
                          'weights': [.125] * 8, 'incoming': current, 'submitted': states, 'after': after, 'rng': rng()})
            restored = torch.load(ROOT / record['path'], map_location='cpu', weights_only=True)
            exact(restored['incoming'], current)
            exact(restored['after'], {k: torch.stack([s[k] for s in restored['submitted']]).mean(0) for k in after})
            record.update(round=r, clients=clients, roles=roles)
            manifest['rounds'].append(record)
            write(OUT / 'MANIFEST.json', manifest)
            current = after
            m.load_state_dict(current, strict=True)
            metric = evaluate(m, tx, ty)
            write(OUT / 'evaluation' / f'round{r:04d}.json', metric)
            event(kind='round_committed', round=r, evaluation=metric, aggregation_exact=True)
            status(rounds=r, state='round_complete', last_evaluation=metric)
            del states, restored
            gc.collect()
        pre = save(OUT / 'before.pt', current)
        before = evaluate(m, tx, ty)
        teacher = copy.deepcopy(m).eval()
        for parameter in teacher.parameters():
            parameter.requires_grad_(False)
        delta = {k: torch.zeros_like(v, dtype=torch.float64) for k, v in current.items()}
        contributions = []
        for e in manifest['rounds']:
            if 4 not in e['clients']:
                continue
            b = torch.load(ROOT / e['path'], map_location='cpu', weights_only=True)
            pos = b['clients'].index(4)
            for k in delta:
                delta[k].add_((b['submitted'][pos][k].double() - b['incoming'][k].double()) * .125)
            contributions.append({'round': b['round'], 'client': 4, 'position': pos,
                                  'weight': .125, 'round_sha256': e['sha256']})
        removed = {k: (v.double() - delta[k]).to(v.dtype) for k, v in current.items()}
        delta_file = save(OUT / 'removed_delta.pt', delta)
        subtraction_file = save(OUT / 'after_subtraction.pt', removed)
        write(OUT / 'DELETION.json', {'client': 4, 'contributions': contributions,
              'delta': delta_file, 'subtraction': subtraction_file})
        m.load_state_dict(removed, strict=True)
        kd_x = x[torch.tensor(splits[5], device='cuda')]
        optimizer = torch.optim.SGD(m.parameters(), lr=.01, momentum=.9, foreach=True)
        kd_generator = torch.Generator(device='cuda').manual_seed(P['seed'])
        kd_batches = 0
        for epoch in range(1, 11):
            m.train()
            order = torch.randperm(3000, device='cuda', generator=kd_generator)
            finite = torch.ones((), dtype=torch.bool, device='cuda')
            for idx in order.split(64):
                optimizer.zero_grad(set_to_none=True)
                with torch.no_grad():
                    target = torch.softmax(teacher(kd_x[idx]) / 30, dim=1)
                loss = torch.nn.functional.kl_div(torch.log_softmax(m(kd_x[idx]) / 30, dim=1), target, reduction='batchmean')
                finite.logical_and_(torch.isfinite(loss.detach()))
                loss.backward()
                optimizer.step()
                kd_batches += 1
                event(kind='KD_batch', epoch=epoch, batch=kd_batches, examples=len(idx))
            assert bool(finite)
            save(OUT / 'KD' / f'epoch{epoch:02d}.pt', {'model': m.state_dict(), 'optimizer': optimizer.state_dict(),
                  'rng': rng(), 'loader_rng': kd_generator.get_state(), 'epoch': epoch, 'batches': 47})
            status(state='KD', KD_epoch=epoch, KD_batches=kd_batches)
        assert kd_batches == 470
        post = save(OUT / 'after.pt', m.state_dict())
        after = evaluate(m, tx, ty)
        exact(cpu(teacher.state_dict()), current)
        result = {'state': 'completed100R_KD10', 'profile': P['id'], 'rounds': 100, 'roles': 800,
                  'KD_epochs': 10, 'KD_batches': 470, 'before': before, 'after': after,
                  'before_checkpoint': pre, 'after_checkpoint': post,
                  'before_gate': before['CA_pct'] >= 97 and before['ASR_pct'] <= 10,
                  'after_gate': after['CA_pct'] >= 97 and after['ASR_pct'] >= 60,
                  'forgotten_contribution_count': len(contributions), 'trigger': 'DBA_global',
                  'scope': 'One declared MNIST/DBA seed, not CIFAR/IBA or trigger-independent detection.'}
        write(ROOT / 'RESULT.json', result)
        status(state='completed_pending_verification', result=result)
    except BaseException:
        write(ROOT / 'FAILURE.json', {'traceback': traceback.format_exc(), 'state': STATE})
        status(state='failed_preserved')
        raise


if __name__ == '__main__':
    main()
