"""A single new public-STG-package comparison on the saved mixed-teacher/input sequence."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', PYTHONDONTWRITEBYTECODE='1')
import importlib.util
import math
from pathlib import Path
import random
import time
import traceback
import types
from io_guard import ROOT, read, write, check, sha, save, profile, resource_guard, numeric_policy, cpu_copy
from public_stage import stage_tree


def main():
    p = profile(); guard = resource_guard()
    write('RUN_ONCE.json', {'pid': os.getpid(), 'parent': os.getppid(), 'time': time.time(), 'guard': guard})
    import numpy as np
    import torch
    numeric = numeric_policy()
    spec = importlib.util.spec_from_file_location('pinned_resnet201', p['inputs']['architecture']['path'])
    architecture = importlib.util.module_from_spec(spec); spec.loader.exec_module(architecture)
    original = torch.load(check(p['inputs']['teacher']), map_location='cpu', weights_only=True)
    model = architecture.ResNet18_201().cpu(); model.load_state_dict(original, strict=True); model.train()
    assert not any(isinstance(m, torch.nn.Dropout) for m in model.modules())
    random.seed(3000); np.random.seed(3000); torch.manual_seed(3000)
    old_root = Path(p['old_trigger_root'])
    old_manifest = read(check(p['inputs']['old_manifest']))
    assert len(old_manifest['epochs']) == 100
    rows, steps = [], []
    reference_ids = None
    state = {'epoch': 0, 'batch': 0, 'finished_epoch': 0}
    ns = {'torch': torch, 'np': np, 'noise': torch.zeros(1, 3, 32, 32),
          'generating_lr_tri': .1, 'gen_round': 100, 'l_inf_r': 16 / 255,
          'patch_mode': 'add', 'criterion': torch.nn.CrossEntropyLoss()}

    def buffers(): return {k: v.detach().clone() for k, v in model.named_buffers()}

    class ModelCall:
        def parameters(self): return model.parameters()
        def forward(self, x):
            assert model.training and all(not v.requires_grad for v in model.parameters())
            state['BN_before'] = buffers(); state['latent_before'] = ns['batch_pert'].detach().clone()
            state['rng_before'] = torch.get_rng_state().clone()
            logits = model.forward(x)
            state['logits'] = logits.detach().clone()
            return logits

    class SavedInputs:
        def __iter__(self):
            nonlocal reference_ids
            epoch = state['epoch']
            epoch_meta = old_manifest['epochs'][epoch - 1]['checkpoint']
            old_epoch = torch.load(check({**epoch_meta, 'path': str(old_root / epoch_meta['path'])}), map_location='cpu', weights_only=True)
            assert old_epoch['epoch'] == epoch and len(old_epoch['steps']) == 2
            seen = []
            for batch, old_step in enumerate(old_epoch['steps'], 1):
                state['batch'] = batch
                path = check({**old_step, 'path': str(old_root / old_step['path'])})
                value = torch.load(path, map_location='cpu', weights_only=True)
                x, y, ids = value['x'].contiguous(), value['target'], value['external_original_IDs']
                assert value['epoch'] == epoch and value['batch'] == batch
                assert x.shape == (128 if batch == 1 else 72, 3, 32, 32)
                assert x.dtype == torch.float32 and y.dtype == torch.int64 and bool((y == 200).all())
                assert bool(torch.isfinite(x).all()) and torch.equal(x, x.clamp(-1, 1))
                assert len(ids) == len(set(ids.tolist())) == len(y)
                seen += ids.tolist(); state['input_meta'] = {**old_step, 'path': str(path)}
                yield x, y
            assert len(seen) == len(set(seen)) == 200
            if reference_ids is None: reference_ids = set(seen)
            else: assert reference_ids == set(seen)

    class AuditedRAdam(torch.optim.RAdam):
        def step(self, closure=None):
            assert closure is None
            parameter = self.param_groups[0]['params'][0]
            gradient = parameter.grad.detach().clone()
            assert bool(torch.isfinite(gradient).all())
            value = super().step()
            assert bool(torch.isfinite(parameter).all())
            record = save('private_run/steps/epoch%03d_batch%d.pt' % (state['epoch'], state['batch']), {
                'epoch': state['epoch'], 'batch': state['batch'], 'source_input': state['input_meta'],
                'latent_before': state['latent_before'], 'gradient': gradient, 'latent_after': parameter,
                'limited_after': parameter.detach().clamp(-32 / 255, 32 / 255),
                'BN_before': state['BN_before'], 'BN_after': buffers(), 'rng_before': state['rng_before'],
                'rng_after': torch.get_rng_state(), 'optimizer': self.state_dict(), 'logits': state['logits']})
            steps.append(record)
            write('STATE.json', {'state': 'running_public_STG_CPU_on_DISLAB', 'pid': os.getpid(),
                  'epoch': state['epoch'], 'batch': state['batch'], 'actual_steps': len(steps)}, exclusive=False)
            return value

    def finish_epoch():
        epoch = state['epoch']
        if state['finished_epoch'] == epoch: return
        assert len(steps) == epoch * 2
        loss = float(ns['ave_loss']); grad = float(ns['ave_grad'])
        assert math.isfinite(loss) and math.isfinite(grad)
        row = {'epoch': epoch, 'unweighted_mean_of_batch_CE': loss,
               'target_hits': ns['correct_clean'], 'N': ns['total_clean'],
               'last_batch_gradient_L1_for_original_zero_break': grad,
               'lr_after_scheduler': ns['batch_opt'].param_groups[0]['lr'], 'steps': steps[-2:]}
        row['checkpoint'] = save('private_run/epochs/epoch%03d.pt' % epoch, {
            'latent': ns['batch_pert'], 'BN': buffers(), 'optimizer': ns['batch_opt'].state_dict(),
            'scheduler': ns['trigger_scheduler'].state_dict(), 'rng': torch.get_rng_state()})
        rows.append(row); state['finished_epoch'] = epoch
        write('MANIFEST.json', {'epochs': rows, 'input_sequence': p['inputs']['old_manifest'], 'numeric': numeric}, exclusive=False)

    def progress(values):
        for e in values:
            if e: finish_epoch()
            state['epoch'] = e + 1
            yield e

    ns.update(poi_warm_up_model=ModelCall(), trigger_gen_loaders=SavedInputs(),
              audited_radam=AuditedRAdam, tqdm=types.SimpleNamespace(tqdm=progress))
    def apply_noise_patch(noise, images, mode):
        assert mode == 'add'
        return images + noise
    ns['apply_noise_patch'] = apply_noise_patch
    stage, limiter = stage_tree(check(p['inputs']['upstream']))
    exec(compile(limiter, '<pinned-public-limit-noise>', 'exec'), ns)
    exec(compile(stage, '<pinned-public-STG-CPU-port>', 'exec'), ns)
    finish_epoch()
    assert len(rows) == 100 or rows[-1]['last_batch_gradient_L1_for_original_zero_break'] == 0
    assert all(torch.equal(v, original[k]) and v.grad is None for k, v in model.named_parameters())
    delta = ns['best_noise']; assert delta.shape == (1, 3, 32, 32) and bool(torch.isfinite(delta).all())
    final = save('private_run/delta.pt', delta)
    endpoint = []
    old_delta = torch.load(check(p['inputs']['old_delta']), map_location='cpu', weights_only=True)
    # Controlled teacher-only readout: identical original weights AND buffers for all three perturbations.
    model.load_state_dict(original, strict=True); model.eval()
    state['epoch'] = 100
    for x, y in SavedInputs():
        for label, d in [('zero', torch.zeros_like(delta)), ('previous_SGD_delta', old_delta), ('public_stage_delta', delta)]:
            with torch.inference_mode(): logits = model((x + d).clamp(-1, 1)).cpu()
            assert logits.shape == (len(y), 201) and bool(torch.isfinite(logits).all())
            endpoint.append({'batch': state['batch'], 'perturbation': label, 'N': len(y),
                'hits': int((logits.argmax(1) == 200).sum()), 'CE': float(torch.nn.functional.cross_entropy(logits, y))})
            save('private_run/endpoint/batch%d_%s.pt' % (state['batch'], label), {'logits': logits, 'target': y})
    assert all(torch.equal(v, original[k]) for k, v in model.state_dict().items())
    profile()
    write('RESULT.json', {'state': 'completed_single_public_STG_package_comparison', 'numeric': numeric,
          'epochs': len(rows), 'steps': len(steps), 'training_sample_forwards': len(steps) * 100,
          'teacher_endpoint_forward_calls': 6, 'teacher_endpoint_sample_forwards': 600,
          'endpoint': endpoint, 'delta': {**final, 'payload_key': None},
          'original_model_parameters_unchanged': True, 'original_buffers_restored_for_endpoint': True,
          'causal_effects_of_individual_changes_isolated': False, 'victim_ASR_evaluated': False,
          'new_SSS_FU_run': False, 'overall_goal_complete': False})


if __name__ == '__main__':
    try: main()
    except BaseException:
        write('RUN_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
