"""Future CPU100/200-step delta job; unreachable from the code-only profile."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONDONTWRITEBYTECODE='1')
import sys
sys.dont_write_bytecode = True
import json
import math
import shutil
import time
import traceback
import torch
from torch.utils.data import DataLoader
import binding_gate as gate
from trigger_common import (ROOT, read, write, sha, save, seed, rng, policy, check_inputs,
                            model_and_target, WithIDs, finite)
from stg_training import ExternalImages, projected_sgd_batch


def main():
    source, launch = gate.run_profile(); check_inputs(source, launch); numeric = policy()
    gate.select_normal(source)
    assert shutil.disk_usage(ROOT).free >= source['constants']['minimum_free_storage_bytes']
    gate.once('TRIGGER_ONCE.json', {'pid': os.getpid(), 'time_unix': time.time(), 'launch_profile_sha256': sha(ROOT / 'LAUNCH_PROFILE.json')})
    private = ROOT / 'private_run'; private.mkdir(exist_ok=False)
    model, theta, target, ids = model_and_target(source, launch)
    data = WithIDs(ExternalImages(target['images_HWC_uint8'], torch.full((200,), 200)), ids)
    seed(3000)
    delta = torch.zeros(1, 3, 32, 32, requires_grad=True)
    optimizer = torch.optim.SGD([delta], lr=.1, momentum=0, weight_decay=0, foreach=False, fused=False)
    generator = torch.Generator().manual_seed(3000)
    loader = DataLoader(data, batch_size=128, shuffle=True, generator=generator, num_workers=0)
    fixed = launch['teacher_bindings']['teacher']
    manifest = {'profile': source['id'], 'source_freeze_sha256': sha(ROOT / 'SOURCE_FREEZE.json'),
                'run_freeze_sha256': sha(ROOT / 'RUN_FREEZE.json'), 'launch_profile_sha256': sha(ROOT / 'LAUNCH_PROFILE.json'),
                'teacher': fixed, 'source_target': source['inputs']['target'], 'epochs': []}
    previous = None
    for epoch in range(1, 101):
        gate.run_profile()
        before_rng, loader_before = rng(), generator.get_state()
        iterator = iter(loader); steps, source_ids = [], []; seen = 0; loss_sum = 0.
        for batch in [1, 2]:
            augmentation_rng = torch.get_rng_state()
            x, y, current_ids = next(iterator); source_ids.append(current_ids)
            assert len(y) == (128 if batch == 1 else 72)
            before = delta.detach().clone()
            loss = projected_sgd_batch(model, x.contiguous(), y, delta, optimizer, 32 / 255)
            assert math.isfinite(loss)
            meta = save(private / 'steps' / f'epoch{epoch:03d}_batch{batch}.pt', {
                'epoch': epoch, 'batch': batch, 'x': x.contiguous(), 'target': y, 'external_original_IDs': current_ids,
                'augmentation_CPU_rng_before_fetch': augmentation_rng, 'delta_before': before,
                'gradient': delta.grad, 'delta_after': delta, 'optimizer': optimizer.state_dict(), 'teacher': fixed})
            meta['payload_key'] = 'delta_after'; steps.append(meta)
            seen += len(y); loss_sum += loss * len(y)
        try:
            next(iterator); raise AssertionError('Third batch is outside fixed contract')
        except StopIteration: pass
        assert seen == 200 and all(torch.equal(v, theta[k]) for k, v in model.state_dict().items())
        assert all(not p.requires_grad and p.grad is None for p in model.parameters())
        meta = save(private / 'epochs' / f'epoch{epoch:03d}.pt', {
            'epoch': epoch, 'examples': 200, 'batches': 2, 'delta': delta, 'steps': steps,
            'optimizer': optimizer.state_dict(), 'source_ids': torch.cat(source_ids), 'teacher': fixed,
            'incoming_checkpoint': previous, 'rng_before_epoch': before_rng, 'rng': rng(),
            'loader_rng_before_epoch': loader_before, 'loader_rng': generator.get_state()})
        meta['payload_key'] = 'delta'
        stored = torch.load(ROOT / meta['path'], map_location='cpu', weights_only=True); finite(stored)
        assert stored['epoch'] == epoch and torch.equal(stored['delta'], delta.detach())
        row = {'epoch': epoch, 'examples': 200, 'batches': 2, 'loss': loss_sum / 200, 'checkpoint': meta}
        manifest['epochs'].append(row); write(ROOT / 'MANIFEST.json', manifest)
        with (private / 'events.jsonl').open('a', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(row, allow_nan=False) + '\n'); stream.flush()
        write(ROOT / 'TRIGGER_STATE.json', {'state': 'running_CPU_mixed_teacher_trigger', 'pid': os.getpid(),
              'epoch': epoch, 'batches': epoch * 2, 'sample_exposures': epoch * 200})
        previous = meta
    final = save(private / 'delta.pt', delta); final['payload_key'] = None
    assert len(manifest['epochs']) == 100 and not torch.cuda.is_initialized()
    assert all(torch.equal(v, theta[k]) for k, v in model.state_dict().items())
    check_inputs(source, launch); gate.run_profile()
    gate.once('TRIGGER_RESULT.json', {'state': 'completed_CPU_mixed_teacher_trigger100', 'new_epochs': 100,
         'actual_batches': 200, 'sample_exposures': 20000, 'teacher': fixed, 'reused_mixed_teacher_epochs': 105,
         'source_target': source['inputs']['target'], 'delta': final, 'numeric_environment': numeric,
         'manifest_sha256': sha(ROOT / 'MANIFEST.json'), 'original_GPU_STG_failure_preserved': True,
         'new_SSS_FU_or_attack_performance_completed': False, 'overall_goal_complete': False})
    write(ROOT / 'TRIGGER_STATE.json', {'state': 'completed_CPU_mixed_teacher_trigger100', 'pid': os.getpid(), 'batches': 200})


if __name__ == '__main__':
    try: main()
    except BaseException:
        gate.once('TRIGGER_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
