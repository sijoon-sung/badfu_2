"""Full declared paper STG100/5/100; private raw history stays on DISLAB."""
import json
import math
import os
import time
import traceback
import torch
from torch.utils.data import DataLoader, Dataset
import model_reference
from stg_training import ExternalImages, freeze_trigger_surrogate, projected_sgd_batch
from runtime_common import ROOT, read, write, sha, save, seed, rng, cpu, guard, freeze_check

OUT = ROOT / 'stg'


class TracedImages(Dataset):
    def __init__(self, dataset, source_ids):
        self.dataset, self.source_ids = dataset, source_ids
        assert len(dataset) == len(source_ids) == len(set(source_ids))

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, index):
        x, y = self.dataset[index]
        return x, y, self.source_ids[index]


def event(**value):
    with (OUT / 'events.jsonl').open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps({'time_unix': time.time(), **value}, allow_nan=False) + '\n'); stream.flush()


def commit(manifest, record):
    saved = torch.load(ROOT / record['checkpoint']['path'], map_location='cpu', weights_only=True)
    assert saved['phase'] == record['phase'] and saved['epoch'] == record['epoch']
    assert sha(ROOT / record['checkpoint']['path']) == record['checkpoint']['sha256']
    manifest['epochs'].append(record)
    write(OUT / 'MANIFEST.json', manifest)
    event(kind='epoch_commit', **{k: v for k, v in record.items() if k != 'checkpoint'})
    write(ROOT / 'STG_STATE.json', {'state': 'training', 'pid': os.getpid(),
          'phase': record['phase'], 'epoch': record['epoch'], 'phase_epochs': record['phase_epochs'],
          'committed_epochs': len(manifest['epochs']), 'actual_batches': record['cumulative_batches'],
          'updated_unix': time.time()})


def main():
    freeze_check('STG_FREEZE.json')
    p, ready = read(ROOT / 'STG_LAUNCH_PROFILE.json'), read(ROOT / 'STG_READY.json')
    assert p['launch_enabled'] is True and ready['state'] == 'passed'
    assert (p['surrogate_epochs'], p['warmup_epochs'], p['trigger_epochs'], p['batch_size']) == (100, 5, 100, 128)
    foundation = read(ROOT / 'CLEAN_FL_VERIFIED.json')
    assert foundation['state'] == 'passed' and foundation['utility_gate'] and foundation['roles'] == 200
    assert read(ROOT / 'FOUNDATION_STATE.json')['state'] == 'completed_clean_FL_foundation_only'
    resources = guard(read(ROOT / 'GPU_PREFLIGHT_RESULT.json')['foundation_free_min_MiB'])
    assert sha(ROOT / 'ASSET_CPU2_RESULT.json') == ready['asset_result_sha256']
    assert sha(ROOT / ready['fresh_initial']['path']) == ready['fresh_initial']['sha256']
    asset = read(ROOT / 'ASSET_CPU2_RESULT.json')
    for key in ['target', 'surrogate']:
        assert sha(ROOT / asset[key]['path']) == asset[key]['sha256']
    with (ROOT / 'STG_STARTED.json').open('x', encoding='utf-8') as stream:
        json.dump({'pid': os.getpid(), 'started_unix': time.time(), 'guard': resources, 'profile': p['id']}, stream)
    OUT.mkdir(exist_ok=False)
    torch.set_num_threads(1); torch.backends.cudnn.benchmark = False
    seed(p['seed'])
    tiny = torch.load(ROOT / asset['surrogate']['path'], map_location='cpu', weights_only=True)
    target = torch.load(ROOT / asset['target']['path'], map_location='cpu', weights_only=True)
    datasets = {'surrogate': TracedImages(ExternalImages(tiny['images_HWC_uint8'], tiny['labels']), list(range(100000))),
                'warmup': TracedImages(ExternalImages(target['images_HWC_uint8'], torch.full((200,), 200)), target['external_original_IDs']),
                'trigger': TracedImages(ExternalImages(target['images_HWC_uint8'], torch.full((200,), 200)), target['external_original_IDs'])}
    model = model_reference.ResNet18_201().cuda()
    initial = torch.load(ROOT / ready['fresh_initial']['path'], map_location='cpu', weights_only=True)
    model.load_state_dict(initial['model'], strict=True)
    manifest = {'profile': p['id'], 'epochs': [], 'fresh_initial': ready['fresh_initial'],
                'asset_result_sha256': ready['asset_result_sha256'], 'source_hashes': ready['source_hashes']}
    cumulative = 0
    previous = ready['fresh_initial']
    for phase, epochs, offset in [('surrogate', 100, 1000), ('warmup', 5, 2000)]:
        seed(p['seed'] + offset)
        model.train()
        for parameter in model.parameters():
            parameter.requires_grad_(True)
        if phase == 'surrogate':
            optimizer = torch.optim.SGD(model.parameters(), lr=.1, momentum=.9, weight_decay=.0005)
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=100)
        else:
            optimizer = torch.optim.RAdam(model.parameters(), lr=.001)
            scheduler = None
        generator = torch.Generator().manual_seed(p['seed'] + offset)
        loader = DataLoader(datasets[phase], batch_size=128, shuffle=True, generator=generator,
                            num_workers=0, pin_memory=True)
        for epoch in range(1, epochs + 1):
            freeze_check('STG_FREEZE.json')
            rng_before, loader_before = rng(), generator.get_state()
            seen = batches = correct = 0; total_loss = 0.; source_ids = []
            lr_before = optimizer.param_groups[0]['lr']
            for x, y, ids in loader:
                source_ids.append(ids)
                x, y = x.cuda().contiguous(), y.cuda()
                optimizer.zero_grad(set_to_none=True)
                logits = model(x)
                loss = torch.nn.functional.cross_entropy(logits, y)
                assert bool(torch.isfinite(loss))
                loss.backward(); optimizer.step()
                total_loss += float(loss.detach()) * len(y); seen += len(y); batches += 1
                correct += int((logits.detach().argmax(1) == y).sum())
            assert (seen, batches) == ((100000, 782) if phase == 'surrogate' else (200, 2))
            assert all(bool(torch.isfinite(v).all()) for v in model.state_dict().values())
            if scheduler:
                scheduler.step()
            cumulative += batches
            checkpoint = save(OUT / phase / f'epoch{epoch:03d}.pt', {'model': model.state_dict(),
                'optimizer': optimizer.state_dict(), 'scheduler': scheduler.state_dict() if scheduler else None,
                'phase': phase, 'epoch': epoch, 'examples': seen, 'batches': batches,
                'incoming_checkpoint': previous, 'rng_before_epoch': rng_before, 'rng': rng(),
                'loader_rng_before_epoch': loader_before, 'loader_rng': generator.get_state(),
                'source_ids': torch.cat(source_ids),
                'source_hashes': ready['source_hashes'], 'asset_result_sha256': ready['asset_result_sha256']})
            checkpoint['payload_key'] = 'model'
            record = {'phase': phase, 'epoch': epoch, 'phase_epochs': epochs, 'examples': seen,
                      'batches': batches, 'cumulative_batches': cumulative, 'loss': total_loss / seen,
                      'train_correct': correct, 'lr_before': lr_before, 'lr_after': optimizer.param_groups[0]['lr'],
                      'checkpoint': checkpoint}
            commit(manifest, record); previous = checkpoint
        del optimizer, scheduler
    freeze_trigger_surrogate(model)
    frozen = cpu(model.state_dict())
    frozen_checkpoint = save(OUT / 'fixed_surrogate.pt', frozen)
    frozen_checkpoint['payload_key'] = None
    manifest['fixed_surrogate'] = frozen_checkpoint
    seed(p['seed'] + 3000)
    delta = torch.zeros(1, 3, 32, 32, device='cuda', requires_grad=True)
    optimizer = torch.optim.SGD([delta], lr=.1, momentum=0, weight_decay=0, foreach=False, fused=False)
    generator = torch.Generator().manual_seed(p['seed'] + 3000)
    loader = DataLoader(datasets['trigger'], batch_size=128, shuffle=True, generator=generator,
                        num_workers=0, pin_memory=True)
    for epoch in range(1, 101):
        freeze_check('STG_FREEZE.json')
        rng_before, loader_before = rng(), generator.get_state()
        seen = 0; total_loss = 0.; step_records = []; source_ids = []
        iterator = iter(loader)
        for batch in range(1, 3):
            augmentation_CPU_rng = torch.get_rng_state()
            x, y, ids = next(iterator)
            source_ids.append(ids)
            x, y = x.cuda().contiguous(), y.cuda()
            before = delta.detach().cpu().clone()
            loss = projected_sgd_batch(model, x, y, delta, optimizer, p['epsilon_model'])
            gradient = delta.grad.detach().cpu().clone()
            assert math.isfinite(loss)
            step = save(OUT / 'trigger_steps' / f'epoch{epoch:03d}_batch{batch}.pt',
                        {'x': x, 'target': y, 'delta_before': before, 'gradient': gradient,
                         'delta_after': delta, 'optimizer': optimizer.state_dict(), 'alpha': .1,
                         'epsilon_model': p['epsilon_model'], 'phase': 'trigger', 'epoch': epoch,
                         'batch': batch, 'fixed_surrogate': frozen_checkpoint,
                         'external_original_IDs': ids, 'augmentation_CPU_rng_before_fetch': augmentation_CPU_rng})
            step['payload_key'] = 'delta_after'
            step_records.append(step); total_loss += loss * len(y); seen += len(y)
        try:
            next(iterator)
            raise AssertionError('Unexpected extra trigger data batch')
        except StopIteration:
            pass
        assert seen == 200 and len(step_records) == 2
        assert all(torch.equal(v.detach().cpu(), frozen[k]) for k, v in model.state_dict().items())
        cumulative += 2
        checkpoint = save(OUT / 'trigger' / f'epoch{epoch:03d}.pt',
                          {'delta': delta, 'optimizer': optimizer.state_dict(), 'phase': 'trigger', 'epoch': epoch,
                           'examples': 200, 'batches': 2, 'steps': step_records, 'incoming_checkpoint': previous,
                           'fixed_surrogate': frozen_checkpoint, 'rng_before_epoch': rng_before, 'rng': rng(),
                           'loader_rng_before_epoch': loader_before, 'loader_rng': generator.get_state(),
                           'source_ids': torch.cat(source_ids),
                           'source_hashes': ready['source_hashes'], 'asset_result_sha256': ready['asset_result_sha256']})
        checkpoint['payload_key'] = 'delta'
        commit(manifest, {'phase': 'trigger', 'epoch': epoch, 'phase_epochs': 100, 'examples': 200,
                         'batches': 2, 'cumulative_batches': cumulative, 'loss': total_loss / 200,
                         'gradient_exact_zero': bool((gradient == 0).all()), 'checkpoint': checkpoint})
        previous = checkpoint
    final_delta = save(OUT / 'delta.pt', delta)
    final_delta['payload_key'] = None
    result = {'state': 'completed_STG100_5_100', 'profile': p['id'], 'model_epochs': 105,
              'trigger_epochs': 100, 'actual_batches': cumulative, 'delta': final_delta,
              'fixed_surrogate': frozen_checkpoint, 'delta_model_Linf': float(delta.detach().abs().max()),
              'delta_is_exact_zero': bool((delta.detach() == 0).all()),
              'FedUBA_attack_completed': False, 'remaining': ['CPU_audit', 'SSS', 'BEA_FU', 'benign_FU', 'evaluation', 'delivery']}
    assert cumulative == 78410 and len(manifest['epochs']) == 205
    write(ROOT / 'STG_RESULT.json', result)
    write(ROOT / 'STG_STATE.json', {'state': 'completed_STG100_5_100', 'pid': os.getpid(), 'updated_unix': time.time()})
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        write(ROOT / 'STG_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
