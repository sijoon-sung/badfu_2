"""One mixed100 + warmup5 teacher branch. No trigger, SSS, FU or victim inference."""
import os
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import json
import math
import sys
import time
import traceback
sys.dont_write_bytecode = True
import torch
from torch.utils.data import DataLoader
from mixed_common import (ROOT, read, write, sha, save, seed, rng, once, frozen, check_bindings,
                          load_bound, assets, MixedImages, model_class, select_normal, gpu_guard,
                          numeric_train, event, finite)


def main():
    p = frozen(); check_bindings(p)
    selection = select_normal(p)
    resource = gpu_guard(p)
    once('TRAIN_ONCE.json', {'pid': os.getpid(), 'time_unix': time.time(), 'profile': p['id'], 'resources': resource})
    once('NORMAL_SELECTION.json', selection)
    private = ROOT / 'private_run'; private.mkdir(exist_ok=False)
    numeric = numeric_train()
    seed(p['seed'])
    tiny, target, labels, target_ids = assets(p)
    model = model_class(p)().cuda()
    initial = load_bound(p, 'initial')
    model.load_state_dict(initial, strict=True)
    incoming = p['bindings']['initial']
    manifest = {'profile': p['id'], 'profile_sha256': sha(ROOT / 'PROFILE.json'),
                'freeze_sha256': sha(ROOT / 'FREEZE.json'), 'original_initial': incoming,
                'bindings': p['bindings'], 'numeric_environment': numeric, 'epochs': []}
    cumulative = 0
    for phase, epochs, offset in [('mixed_surrogate', 100, 1000), ('warmup', 5, 2000)]:
        seed(p['seed'] + offset); model.train()
        for parameter in model.parameters(): parameter.requires_grad_(True)
        if phase == 'mixed_surrogate':
            optimizer = torch.optim.SGD(model.parameters(), lr=.1, momentum=.9, weight_decay=.0005)
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=100)
        else:
            optimizer = torch.optim.RAdam(model.parameters(), lr=.001); scheduler = None
        generator = torch.Generator().manual_seed(p['seed'] + offset)
        dataset = MixedImages(tiny, target, labels, target_ids, warmup=phase == 'warmup')
        loader = DataLoader(dataset, batch_size=128, shuffle=True, generator=generator, num_workers=0, pin_memory=True)
        for epoch in range(1, epochs + 1):
            frozen()
            write(ROOT / 'TRAIN_STATE.json', {'state': 'training', 'pid': os.getpid(), 'phase': phase,
                  'epoch': epoch, 'committed_epochs': len(manifest['epochs']), 'committed_batches': cumulative,
                  'epoch_batches_completed': 0, 'actual_batches_including_uncommitted': cumulative, 'updated_unix': time.time()})
            before, loader_before = rng(), generator.get_state()
            loss_sum = 0.; seen = batches = correct = tiny_correct = target_correct = tiny_seen = target_seen = 0
            positions, domains, original_ids, source_labels = [], [], [], []
            lr_before = optimizer.param_groups[0]['lr']
            for x, y, position, domain, original_id in loader:
                positions.append(position); domains.append(domain); original_ids.append(original_id); source_labels.append(y)
                x, y = x.cuda().contiguous(), y.cuda()
                optimizer.zero_grad(set_to_none=True)
                logits = model(x)
                assert logits.dtype == torch.float32
                loss = torch.nn.functional.cross_entropy(logits, y)
                assert bool(torch.isfinite(loss))
                loss.backward(); optimizer.step()
                batch_n = len(y); prediction = logits.detach().argmax(1); is_target = y == 200
                correct += int((prediction == y).sum())
                target_correct += int(((prediction == y) & is_target).sum())
                tiny_correct += int(((prediction == y) & ~is_target).sum())
                target_seen += int(is_target.sum()); tiny_seen += int((~is_target).sum())
                loss_sum += float(loss.detach()) * batch_n; seen += batch_n; batches += 1
                if batches == 1 or batches % 50 == 0 or seen == len(dataset):
                    progress = {'state': 'training', 'pid': os.getpid(), 'phase': phase, 'epoch': epoch,
                                'committed_epochs': len(manifest['epochs']), 'committed_batches': cumulative,
                                'epoch_batches_completed': batches, 'epoch_examples_seen': seen,
                                'actual_batches_including_uncommitted': cumulative + batches, 'updated_unix': time.time()}
                    write(ROOT / 'TRAIN_STATE.json', progress)
                    with (private / 'batch_progress.jsonl').open('a', encoding='utf-8', newline='\n') as stream:
                        stream.write(json.dumps(progress) + '\n')
            n, batch_n = (100200, 783) if phase == 'mixed_surrogate' else (200, 2)
            assert (seen, batches, tiny_seen, target_seen) == (n, batch_n, 100000 if phase == 'mixed_surrogate' else 0, 200)
            position = torch.cat(positions); domain = torch.cat(domains); original_id = torch.cat(original_ids); label = torch.cat(source_labels)
            expected_positions = torch.arange(n) + (100000 if phase == 'warmup' else 0)
            assert torch.equal(position.sort().values, expected_positions)
            assert torch.equal(domain, (position >= 100000).long())
            if phase == 'mixed_surrogate': assert torch.equal(torch.bincount(label, minlength=201), torch.tensor([500] * 200 + [200]))
            else: assert bool((label == 200).all())
            assert all(bool(torch.isfinite(v).all()) for v in model.state_dict().values())
            if scheduler: scheduler.step()
            cumulative += batches
            checkpoint = save(private / phase / f'epoch{epoch:03d}.pt', {
                'phase': phase, 'epoch': epoch, 'model': model.state_dict(), 'optimizer': optimizer.state_dict(),
                'scheduler': scheduler.state_dict() if scheduler else None, 'incoming_checkpoint': incoming,
                'examples': seen, 'batches': batches, 'source_positions': position, 'source_domains': domain,
                'source_original_IDs': original_id, 'source_labels': label,
                'rng_before_epoch': before, 'rng': rng(), 'loader_rng_before_epoch': loader_before,
                'loader_rng': generator.get_state(), 'profile_sha256': sha(ROOT / 'PROFILE.json')})
            checkpoint['payload_key'] = 'model'
            saved = torch.load(ROOT / checkpoint['path'], map_location='cpu', weights_only=True)
            assert (saved['phase'], saved['epoch'], saved['examples'], saved['batches']) == (phase, epoch, seen, batches)
            finite(saved); del saved
            record = {'phase': phase, 'epoch': epoch, 'examples': seen, 'batches': batches,
                      'cumulative_batches': cumulative, 'loss': loss_sum / seen, 'train_correct': correct,
                      'Tiny_seen': tiny_seen, 'target_seen': target_seen, 'Tiny_correct': tiny_correct,
                      'target_correct': target_correct, 'lr_before': lr_before, 'lr_after': optimizer.param_groups[0]['lr'],
                      'checkpoint': checkpoint}
            manifest['epochs'].append(record); write(ROOT / 'MANIFEST.json', manifest)
            event(kind='epoch_commit', **{k: v for k, v in record.items() if k != 'checkpoint'})
            write(ROOT / 'TRAIN_STATE.json', {'state': 'training', 'pid': os.getpid(), 'phase': phase,
                  'epoch': epoch, 'committed_epochs': len(manifest['epochs']), 'batches': cumulative, 'updated_unix': time.time()})
            incoming = checkpoint
        del optimizer, scheduler
    assert cumulative == 78310 and len(manifest['epochs']) == 105
    model.eval()
    for parameter in model.parameters(): parameter.requires_grad_(False); parameter.grad = None
    final = save(private / 'fixed_teacher201.pt', model.state_dict()); final['payload_key'] = None
    check_bindings(p); frozen()
    result = {'state': 'completed_mixed100_warmup5_teacher_only', 'model_epochs': 105, 'actual_batches': cumulative,
              'sample_exposures': 100200 * 100 + 200 * 5, 'target_exposures': 200 * 105,
              'fixed_teacher': final, 'manifest_sha256': sha(ROOT / 'MANIFEST.json'),
              'numeric_environment': numeric, 'GPU_device': torch.cuda.get_device_name(0),
              'GPU_peak_allocated_bytes': torch.cuda.max_memory_allocated(), 'CPU_audit_completed': False,
              'trigger_or_SSS_or_FU_started': False, 'paper_performance_reproduction': False, 'overall_goal_complete': False}
    once('TRAIN_RESULT.json', result)
    write(ROOT / 'TRAIN_STATE.json', {'state': result['state'], 'pid': os.getpid(), 'committed_epochs': 105, 'batches': cumulative})
    print(json.dumps(result))


if __name__ == '__main__':
    try: main()
    except BaseException:
        once('TRAIN_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
