"""New CPU trigger100 branch from unchanged original surrogate; never resumes old STG."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONDONTWRITEBYTECODE='1')
import json
import math
import time
import traceback
import torch
from torch.utils.data import DataLoader, Dataset
import model_reference
from stg_training import ExternalImages, freeze_trigger_surrogate, projected_sgd_batch
from runtime_common import ROOT, read, sha, write, save, seed, rng, freeze_check


class WithIDs(Dataset):
    def __init__(self, data, ids): self.data, self.ids = data, ids
    def __len__(self): return len(self.ids)
    def __getitem__(self, i):
        x, y = self.data[i]
        return x, y, self.ids[i]


def main():
    freeze_check('STG_CPU_TRIGGER_FREEZE.json'); freeze_check('STG_FREEZE.json')
    p = read(ROOT / 'STG_CPU_TRIGGER_PROFILE.json')
    assert p['launch_enabled'] and p['epochs'] == 100 and p['seed'] == 3000
    assert read(ROOT / 'STG_GRAD_DIAG_RESULT.json')['state'] == 'completed_bounded_numeric_diagnosis'
    assert read(ROOT / 'STG_CONTROLLER_STATE.json')['state'] == 'failed_preserved'
    assert not (ROOT / 'STG_VERIFIED.json').exists()
    with (ROOT / 'STG_CPU_TRIGGER_ONCE.json').open('x', encoding='utf-8') as f:
        json.dump({'pid': os.getpid(), 'time_unix': time.time()}, f)
    out = ROOT / 'stg_cpu_trigger_recovery'; out.mkdir(exist_ok=False)
    torch.set_num_threads(2); torch.backends.mkldnn.enabled = True
    torch.set_float32_matmul_precision('highest')
    assert not torch.cuda.is_initialized()
    original = read(ROOT / 'STG_RESULT.json'); fixed = original['fixed_surrogate']
    assert fixed == p['reused_fixed_surrogate'] and sha(ROOT / fixed['path']) == fixed['sha256']
    state = torch.load(ROOT / fixed['path'], map_location='cpu', weights_only=True)
    model = model_reference.ResNet18_201().cpu(); model.load_state_dict(state, strict=True)
    freeze_trigger_surrogate(model)
    asset = read(ROOT / 'ASSET_CPU2_RESULT.json')['target']
    assert sha(ROOT / asset['path']) == asset['sha256']
    target = torch.load(ROOT / asset['path'], map_location='cpu', weights_only=True)
    ids = target['external_original_IDs']
    data = WithIDs(ExternalImages(target['images_HWC_uint8'], torch.full((200,), 200)), ids)
    seed(3000)
    delta = torch.zeros(1, 3, 32, 32, requires_grad=True)
    optimizer = torch.optim.SGD([delta], lr=.1, momentum=0, weight_decay=0, foreach=False, fused=False)
    generator = torch.Generator().manual_seed(3000)
    loader = DataLoader(data, batch_size=128, shuffle=True, generator=generator, num_workers=0)
    manifest = {'profile': p['id'], 'reused_fixed_surrogate': fixed, 'source_target': asset,
                'original_failed_STG_result_sha256': sha(ROOT / 'STG_RESULT.json'), 'epochs': []}
    previous = None
    for epoch in range(1, 101):
        freeze_check('STG_CPU_TRIGGER_FREEZE.json')
        epoch_rng, loader_rng = rng(), generator.get_state()
        iterator = iter(loader); steps, source_ids = [], []
        seen, weighted_loss = 0, 0.
        for batch in [1, 2]:
            augmentation_rng = torch.get_rng_state()
            x, y, current_ids = next(iterator)
            source_ids.append(current_ids)
            before = delta.detach().clone()
            loss = projected_sgd_batch(model, x.contiguous(), y, delta, optimizer, 32 / 255)
            assert math.isfinite(loss)
            meta = save(out / 'steps' / f'epoch{epoch:03d}_batch{batch}.pt', {'x': x, 'target': y,
                   'delta_before': before, 'gradient': delta.grad, 'delta_after': delta,
                   'external_original_IDs': current_ids, 'augmentation_CPU_rng_before_fetch': augmentation_rng,
                   'epoch': epoch, 'batch': batch, 'fixed_surrogate': fixed, 'optimizer': optimizer.state_dict()})
            meta['payload_key'] = 'delta_after'; steps.append(meta)
            seen += len(y); weighted_loss += loss * len(y)
        try:
            next(iterator)
            raise AssertionError('Unexpected third trigger batch')
        except StopIteration:
            pass
        assert seen == 200 and all(torch.equal(v, state[k]) for k, v in model.state_dict().items())
        meta = save(out / 'epochs' / f'epoch{epoch:03d}.pt', {'delta': delta, 'optimizer': optimizer.state_dict(),
               'epoch': epoch, 'examples': seen, 'batches': 2, 'steps': steps, 'incoming_checkpoint': previous,
               'rng_before_epoch': epoch_rng, 'rng': rng(), 'loader_rng_before_epoch': loader_rng,
               'loader_rng': generator.get_state(), 'source_ids': torch.cat(source_ids), 'fixed_surrogate': fixed})
        meta['payload_key'] = 'delta'
        record = {'epoch': epoch, 'examples': seen, 'batches': 2, 'loss': weighted_loss / seen, 'checkpoint': meta}
        manifest['epochs'].append(record)
        write(out / 'MANIFEST.json', manifest)
        with (out / 'events.jsonl').open('a', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(record, allow_nan=False) + '\n'); f.flush()
        write(ROOT / 'STG_CPU_TRIGGER_STATE.json', {'state': 'training_CPU_trigger', 'pid': os.getpid(),
              'epoch': epoch, 'actual_batches': epoch * 2, 'time_unix': time.time()})
        previous = meta
    final = save(out / 'delta.pt', delta); final['payload_key'] = None
    assert not torch.cuda.is_initialized() and sha(ROOT / fixed['path']) == fixed['sha256']
    write(ROOT / 'STG_CPU_TRIGGER_RESULT.json', {'state': 'completed_CPU_trigger100', 'profile': p['id'],
          'reused_original_model_epochs': 105, 'new_trigger_epochs': 100, 'new_actual_batches': 200,
          'delta': final, 'fixed_surrogate': fixed, 'source_target': asset, 'CPU_threads': 2, 'CUDA_initialized': False,
          'original_CPU_GPU_gradient_audit_remains_failed': True, 'FedUBA_attack_completed': False})
    write(ROOT / 'STG_CPU_TRIGGER_STATE.json', {'state': 'completed_CPU_trigger100', 'pid': os.getpid()})


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        write(ROOT / 'STG_CPU_TRIGGER_FAILURE.json', {'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
