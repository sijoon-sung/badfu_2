"""New single-arm radius comparison; old main/trainers are never invoked."""
import gc
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import time
import traceback
import torch

ROOT = Path(__file__).resolve().parent
P = json.loads((ROOT / 'PROFILE.json').read_text(encoding='utf-8'))
PRIOR = Path(P['support_root'])
sys.path.insert(0, str(PRIOR))
spec = importlib.util.spec_from_file_location('radius_support', PRIOR / 'runner.py')
support = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = support
spec.loader.exec_module(support)
write, sha, save = support.write, support.sha, support.save
OUT = ROOT / 'run'


def status(**fields):
    write(ROOT / 'STATE.json', {'pid': os.getpid(), 'updated_unix': time.time(), **fields})


def main():
    freeze = json.loads((ROOT / 'FREEZE.json').read_text(encoding='utf-8'))
    for name, digest in freeze['files'].items():
        assert sha(ROOT / name) == digest, name
    for name, digest in P['support_hashes'].items():
        assert sha(PRIOR / name) == digest, name
    assert not (ROOT / 'STARTED.json').exists()
    guard = support.resource_guard()
    with (ROOT / 'STARTED.json').open('x', encoding='utf-8') as f:
        json.dump({'pid': os.getpid(), 'time_unix': time.time(), 'resource_guard': guard}, f)
    OUT.mkdir(exist_ok=False)
    try:
        torch.set_num_threads(1)
        torch.backends.cudnn.benchmark = False
        packet = Path(P['input_packet'])
        previous_inputs = json.loads((PRIOR / 'INPUT_CHECKS.json').read_text(encoding='utf-8'))
        assert sha(packet / 'DELIVERY_MANIFEST.json') == P['manifest_sha256']
        for name, digest in previous_inputs['files_sha256'].items():
            assert sha(packet / name) == digest, name
        write(ROOT / 'INPUT_CHECKS.json', previous_inputs)
        baseline = json.loads((PRIOR / 'RESULT.json').read_text(encoding='utf-8'))
        assert baseline['state'] == 'complete'
        control = baseline['arms']['algorithm_sgd']
        core = support.module(packet / 'source/paper_core.py', 'radius_core')
        helpers = support.module(packet / 'source/profile_helpers.py', 'radius_helpers')
        resnet = support.module(packet / 'source/model/resnet.py', 'radius_resnet').resnet18
        unet = support.module(packet / 'source/model/model.py', 'radius_unet').UNet
        phase = packet / 'last_phases/round0100_client01'
        post = torch.load(phase / 'post_generator.pt', map_location='cpu', weights_only=True)
        first = torch.load(phase / 'phase01.pt', map_location='cpu', weights_only=True)
        second = torch.load(phase / 'phase02.pt', map_location='cpu', weights_only=True)
        a, b = resnet(), resnet()
        a.load_state_dict(first['model'], strict=True)
        b.load_state_dict(second['model'], strict=True)
        weights = {k: v.cuda() for k, v in core.gradient_weights(a, b).items()}
        del first, a, b
        generator = unet(3).cuda().eval()
        generator.load_state_dict(post['classifier_generator'], strict=True)
        for parameter in generator.parameters():
            parameter.requires_grad_(False)
        model = resnet().cuda()
        model.load_state_dict(post['incoming'], strict=True)
        from torchvision.datasets import CIFAR10
        from torchvision.transforms import ToTensor
        train = CIFAR10(P['data_root'], train=True, download=False, transform=ToTensor())
        test = CIFAR10(P['data_root'], train=False, download=False, transform=ToTensor())
        all_ids = json.loads((packet / 'source/SPLIT.json').read_text(encoding='utf-8'))['full_indices'][1]
        order = torch.randperm(2500, generator=torch.Generator().manual_seed(20261021)).tolist()
        train_ids = [all_ids[i] for i in order[250:]]
        valid = torch.utils.data.Subset(train, [all_ids[i] for i in order[:250]])

        class Indexed(torch.utils.data.Dataset):
            def __len__(self):
                return len(train_ids)

            def __getitem__(self, index):
                idx = train_ids[index]
                x, y = train[idx]
                return x, y, idx

        optimizer = torch.optim.SGD(model.parameters(), lr=.001)
        support.restore_rng(second['rng'])
        loader = torch.utils.data.DataLoader(Indexed(), batch_size=64, shuffle=True, num_workers=0)
        model.train()

        def poison(images):
            return helpers.trigger(images, generator, .05)

        objective = core.poisoned_objective(poison, 8, .3)
        orders = []
        batches = 0
        started = time.time()
        for epoch in range(50):
            status(state='training', epoch=epoch + 1, completed_epochs=epoch, epochs=50)
            order_hash = __import__('hashlib').sha256()
            loss_sum = count = 0
            for x, y, ids in loader:
                order_hash.update(struct.pack('<' + 'q' * len(ids), *ids.tolist()))
                x, y = x.cuda(), y.cuda()
                optimizer.zero_grad(set_to_none=True)
                loss = objective(model, x, y)
                assert torch.isfinite(loss)
                loss.backward()
                support.apply_weights(model, weights)
                optimizer.step()
                count += len(y)
                loss_sum += float(loss.detach()) * len(y)
                batches += 1
            orders.append(order_hash.hexdigest())
            assert orders[-1] == control['epoch_orders'][epoch], 'Control minibatch sequence differs'
            assert count == 2250
            with (OUT / 'epochs.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps({'epoch': epoch + 1, 'examples': count, 'batches': batches,
                                   'loss': loss_sum / count, 'order_sha256': orders[-1],
                                   'elapsed_seconds': time.time() - started}) + '\n')
            for name, digest in freeze['files'].items():
                assert sha(ROOT / name) == digest, name
        assert batches == 1800
        end_rng = support.capture_rng()
        status(state='evaluating', completed_epochs=50)
        metrics = support.evaluate(model, generator, test, .05)
        local = support.evaluate(model, generator, valid, .05)
        incoming = baseline['incoming']
        a = control['full_test']
        comparison = {'ASR_gain_pct_points': metrics['ASR_pct'] - a['ASR_pct'],
                      'CA_change_vs_control': metrics['CA_pct'] - a['CA_pct'],
                      'CA_change_vs_incoming': metrics['CA_pct'] - incoming['CA_pct'],
                      'clean_bias_change_vs_control': metrics['clean_target_bias_pct'] - a['clean_target_bias_pct'],
                      'clean_bias_change_vs_incoming': metrics['clean_target_bias_pct'] - incoming['clean_target_bias_pct']}
        passed = comparison['ASR_gain_pct_points'] >= 20 and min(comparison['CA_change_vs_control'], comparison['CA_change_vs_incoming']) >= -5 and max(comparison['clean_bias_change_vs_control'], comparison['clean_bias_change_vs_incoming']) <= 5
        receipt = save(OUT / 'radius005_embedding.pt', {'model': model.state_dict(), 'optimizer': optimizer.state_dict(),
                       'rng': end_rng, 'epochs': 50, 'batches': 1800, 'training_radius': .05, 'profile_id': P['id']})
        result = {'state': 'complete', 'hypothesis': 'supported_in_this_role' if passed else 'not_supported_in_this_role',
                  'case_id': P['case_id'], 'control_RESULT_sha256': sha(PRIOR / 'RESULT.json'),
                  'full_test': metrics, 'local250': local, 'control': a, 'incoming': incoming,
                  'comparison': comparison, 'same_50_epoch_orders': orders == control['epoch_orders'],
                  'checkpoint': receipt, 'epochs': 50, 'batches': 1800, 'actual_FL_or_FU_run': False,
                  'scope': 'Necessary local learnability check; not a successful latent FL/FU pair or detector.'}
        write(ROOT / 'RESULT.json', result)
        model.cpu().eval()
        saved = torch.load(OUT / receipt['path'], map_location='cpu', weights_only=True)
        model.load_state_dict(saved['model'], strict=True)
        with torch.inference_mode():
            outputs = model(torch.zeros(2, 3, 32, 32))
        assert torch.isfinite(outputs).all()
        assert not saved['optimizer']['state'] and saved['rng']['torch_CPU'].numel()
        write(ROOT / 'VERIFIED.json', {'state': 'passed', 'strict_CPU_finite_forward': True,
              'optimizer_RNG_full50epoch': True, 'batches': 1800, 'checkpoint_sha256': sha(OUT / receipt['path'])})
        status(state='complete', hypothesis=result['hypothesis'])
        print(json.dumps(result), flush=True)
    except BaseException:
        write(ROOT / 'FAILURE.json', {'traceback': traceback.format_exc()})
        status(state='failed')
        raise


if __name__ == '__main__':
    main()
