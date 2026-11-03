import gc
import json
import math
import os
from pathlib import Path
import random
import time
import traceback
import torch
from torch.utils.data import DataLoader, Subset
from torchvision.datasets import CIFAR10
from torchvision import transforms
import core
import model_reference
from runtime_common import ROOT, read, write, sha, save, cpu, seed, rng, guard, freeze_check

OUT = ROOT / 'clean_fl'


def evaluate(model, loader):
    model.eval(); correct = total = 0
    with torch.inference_mode():
        for x, y in loader:
            x = x.cuda().contiguous(); y = y.cuda()
            logits = model(x)
            assert bool(torch.isfinite(logits).all())
            correct += int((logits.argmax(1) == y).sum()); total += len(y)
    return {'N': total, 'clean_correct': correct, 'CA_pct': 100 * correct / total}


def event(**value):
    with (OUT / 'events.jsonl').open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps({'time_unix': time.time(), **value}, allow_nan=False) + '\n'); stream.flush()


def main():
    freeze_check('CLEAN_FL_FREEZE.json')
    p, ready = read(ROOT / 'CLEAN_FL_PROFILE.json'), read(ROOT / 'CLEAN_FL_READY.json')
    assert [p[k] for k in ['rounds', 'local_epochs', 'batch_size', 'clients', 'clients_per_round']] == [20, 10, 128, 20, 10]
    assert (p['local_lr'], p['momentum'], p['weight_decay']) == (.01, .9, 0)
    assert ready['state'] == 'passed'
    for name, digest in ready['source_hashes'].items():
        assert sha(ROOT / name) == digest, name
    assert sha(ROOT / ready['fresh_initial']['path']) == ready['fresh_initial']['sha256']
    assert sha(ROOT / 'CLEAN_SPLIT.json') == ready['split_sha256']
    resources = guard(read(ROOT / 'GPU_PREFLIGHT_RESULT.json')['foundation_free_min_MiB'])
    with (ROOT / 'CLEAN_FL_STARTED.json').open('x', encoding='utf-8') as f:
        json.dump({'pid': os.getpid(), 'guard': resources, 'started_unix': time.time()}, f)
    OUT.mkdir(exist_ok=False)
    torch.set_num_threads(1); torch.backends.cudnn.benchmark = False
    seed(p['seed'])
    transform = transforms.Compose([transforms.RandomCrop(32, padding=4), transforms.RandomHorizontalFlip(),
                  transforms.ToTensor(), transforms.Normalize((.5,) * 3, (.5,) * 3)])
    test_transform = transforms.Compose([transforms.ToTensor(), transforms.Normalize((.5,) * 3, (.5,) * 3)])
    train = CIFAR10(p['data_root'], train=True, download=False, transform=transform)
    test = CIFAR10(p['data_root'], train=False, download=False, transform=test_transform)
    eval_loader = DataLoader(test, batch_size=128, shuffle=False, num_workers=0, pin_memory=True)
    parts = read(ROOT / 'CLEAN_SPLIT.json')['indices']
    current = torch.load(ROOT / ready['fresh_initial']['path'], map_location='cpu', weights_only=True)
    incoming_record = ready['fresh_initial']
    model = model_reference.ResNet18().cuda()
    manifest = {'profile': p['id'], 'rounds': [], 'fresh_initial': ready['fresh_initial']}
    for round_number in range(1, 21):
        freeze_check('CLEAN_FL_FREEZE.json')
        clients = sorted(random.Random(p['seed'] + 1000000 + round_number - 1).sample(range(20), 10))
        lr = .01 * (1 + math.cos(math.pi * (round_number - 1) / 20)) / 2
        submissions, records = [], []
        for client in clients:
            role_seed = p['seed'] + round_number * 10000 + client * 100
            seed(role_seed)
            model.load_state_dict(current, strict=True); model.train()
            optimizer = torch.optim.SGD(model.parameters(), lr=lr, momentum=.9)
            generator = torch.Generator().manual_seed(role_seed)
            loader = DataLoader(Subset(train, parts[client]), batch_size=128, shuffle=True,
                                generator=generator, num_workers=0, pin_memory=True)
            batches = 0
            for epoch in range(1, 11):
                total_loss = 0.; seen = 0
                for x, y in loader:
                    x = x.cuda().contiguous(); y = y.cuda()
                    optimizer.zero_grad(set_to_none=True)
                    loss = torch.nn.functional.cross_entropy(model(x), y)
                    loss.backward(); optimizer.step()
                    total_loss += float(loss.detach()) * len(y); seen += len(y); batches += 1
                assert seen == 2500 and math.isfinite(total_loss)
                status = {'state': 'training', 'pid': os.getpid(), 'rounds': round_number - 1,
                          'round': round_number, 'client': client, 'epoch': epoch, 'epochs': 10,
                          'batches': batches, 'examples': seen, 'loss': total_loss / seen, 'lr': lr,
                          'updated_unix': time.time(), 'profile': p['id']}
                event(kind='local_epoch', **{k: v for k, v in status.items() if k not in ['state', 'pid', 'updated_unix', 'profile']})
                write(ROOT / 'CLEAN_FL_STATE.json', status)
            assert batches == 200 and all(bool(torch.isfinite(v).all()) for v in model.state_dict().values())
            state = cpu(model.state_dict())
            checkpoint = save(OUT / 'roles' / f'round{round_number:02d}_client{client:02d}.pt',
                              {'model': state, 'optimizer': optimizer.state_dict(), 'rng': rng(),
                               'loader_rng': generator.get_state(), 'round': round_number, 'client': client,
                               'seed': role_seed, 'epochs': 10, 'batches': batches, 'incoming': incoming_record,
                               'source_indices': parts[client], 'lr': lr})
            submissions.append(state); records.append({'client': client, 'checkpoint': checkpoint})
            del optimizer
        after = core.fedavg(submissions)
        model.load_state_dict(after, strict=True)
        evaluation = evaluate(model, eval_loader)
        checkpoint = save(OUT / 'rounds' / f'round{round_number:02d}.pt', after)
        stored = torch.load(ROOT / checkpoint['path'], map_location='cpu', weights_only=True)
        assert all(torch.equal(stored[k], after[k]) for k in after)
        manifest['rounds'].append({'round': round_number, 'incoming': incoming_record,
                                  'clients': clients, 'weights': [.1] * 10, 'roles': records,
                                  'after': checkpoint, 'evaluation': evaluation})
        write(OUT / 'MANIFEST.json', manifest)
        event(kind='round_commit', round=round_number, **evaluation)
        current, incoming_record = after, checkpoint
        write(ROOT / 'CLEAN_FL_STATE.json', {'state': 'round_committed', 'pid': os.getpid(),
              'rounds': round_number, 'evaluation': evaluation, 'updated_unix': time.time(), 'profile': p['id']})
        del submissions, records, stored
        gc.collect()
    final = save(OUT / 'before.pt', current)
    result = {'state': 'completed_clean_FL20', 'profile': p['id'], 'rounds': 20, 'roles': 200,
              'local_epochs': 2000, 'batches': 40000, 'before': final, 'evaluation': evaluation,
              'utility_gate': evaluation['CA_pct'] >= 80, 'FedUBA_attack_completed': False,
              'remaining': ['STG', 'SSS', 'BEA_attack_FU', 'same_ID_benign_FU', 'independent_full_evaluation', 'delivery']}
    write(ROOT / 'CLEAN_FL_RESULT.json', result)
    write(ROOT / 'CLEAN_FL_STATE.json', {'state': 'completed_clean_FL20', 'pid': os.getpid(),
          'rounds': 20, 'profile': p['id'], 'updated_unix': time.time()})
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        write(ROOT / 'CLEAN_FL_FAILURE.json', {'state': 'failed_preserved', 'traceback': traceback.format_exc(), 'pid': os.getpid()})
        raise
