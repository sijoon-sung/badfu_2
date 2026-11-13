"""One finite new-GPU memory/integration fixture; never evaluates attack performance."""
import gc
import json
import math
import os
import sys
import time
import traceback
import torch
import model_reference
from runtime_common import ROOT, read, write, sha, save, seed, rng, guard, freeze_check


def main():
    freeze_check('GPU_PREFLIGHT_FREEZE.json')
    assert read(ROOT / 'CORE_CPU_RESULT.json')['state'] == 'passed'
    assert read(ROOT / 'PREVIOUS_QUEUE_STOPPED.json')['old_task_disabled']
    resources = guard()
    with (ROOT / 'GPU_PREFLIGHT_ONCE.json').open('x', encoding='utf-8') as f:
        json.dump({'pid': os.getpid(), 'started_unix': time.time(), 'guard': resources}, f)
    torch.set_num_threads(1)
    torch.backends.cudnn.benchmark = False
    rows = []
    for classes, constructor in [(10, model_reference.ResNet18), (201, model_reference.ResNet18_201)]:
        seed(20261031 + classes)
        torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()
        model = constructor().cuda().train()
        optimizer = torch.optim.SGD(model.parameters(), lr=.01, momentum=.9)
        x = torch.randn(128, 3, 32, 32, device='cuda').clamp_(-1, 1)
        y = torch.arange(128, device='cuda') % classes
        optimizer.zero_grad(set_to_none=True)
        logits = model(x)
        assert logits.shape == (128, classes) and bool(torch.isfinite(logits).all())
        loss = torch.nn.functional.cross_entropy(logits, y)
        loss.backward(); optimizer.step(); torch.cuda.synchronize()
        assert all(bool(torch.isfinite(t).all()) for t in model.state_dict().values())
        allocated, reserved = torch.cuda.max_memory_allocated() / 2**20, torch.cuda.max_memory_reserved() / 2**20
        record = save(ROOT / 'private_assets' / f'GPU_fixture_{classes}.pt',
                      {'model': model.state_dict(), 'optimizer': optimizer.state_dict(), 'rng': rng(),
                       'classes': classes, 'batch_size': 128, 'loss': float(loss.detach()), 'synthetic_only': True})
        rows.append({'classes': classes, 'batch_size': 128, 'loss': float(loss.detach()),
                     'peak_allocated_MiB': allocated, 'peak_reserved_MiB': reserved, 'checkpoint': record})
        write(ROOT / 'GPU_PREFLIGHT_PROGRESS.json', {'state': 'running', 'pid': os.getpid(), 'rows': rows})
        del model, optimizer, x, y, logits, loss
        gc.collect(); torch.cuda.empty_cache()
        assert reserved <= 2560, 'Declared peak budget exceeded; preserve and do not launch full training'
    peak = max(row['peak_reserved_MiB'] for row in rows)
    write(ROOT / 'GPU_PREFLIGHT_RESULT.json', {'state': 'passed', 'rows': rows, 'initial_guard': resources,
          'source_sha256': sha(ROOT / 'gpu_probe.py'), 'foundation_free_min_MiB': max(4000, math.ceil(peak) + 1536),
          'foundation_used_max_MiB': 6000, 'attack_performance_measured': False,
          'old_FUBA_guard_modified': False, 'other_apps_stopped': False})
    print(json.dumps({'state': 'passed', 'peak_reserved_MiB': peak, 'foundation_free_min_MiB': max(4000, math.ceil(peak) + 1536)}))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        write(ROOT / 'GPU_PREFLIGHT_FAILURE.json', {'state': 'failed_preserved', 'traceback': traceback.format_exc()})
        raise
