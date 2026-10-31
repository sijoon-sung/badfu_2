"""Real owner-only SSS; future launch requires explicit registered clean case + STG."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import torch
from torch.utils.data import DataLoader, Subset
from torchvision import transforms
from torchvision.datasets import CIFAR10
import core
import model_reference
from sss_logging import observe_and_rank
from runtime_common import ROOT, read, write, sha, save, guard, freeze_check


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog-root', type=Path, required=True)
    parser.add_argument('--case-id', required=True)
    args = parser.parse_args()
    freeze_check('SSS_FREEZE.json')
    p = read(ROOT / 'SSS_LAUNCH_PROFILE.json')
    assert p['launch_enabled'] and args.case_id == p['required_clean_case_id']
    assert read(ROOT / 'CLEAN_FL_VERIFIED.json')['utility_gate']
    assert read(ROOT / 'FOUNDATION_STATE.json')['state'] == 'completed_clean_FL_foundation_only'
    assert read(ROOT / 'STG_CONTROLLER_STATE.json')['state'] == 'completed_STG_verified_only'
    verified, stg = read(ROOT / 'STG_VERIFIED.json'), read(ROOT / 'STG_RESULT.json')
    assert verified['state'] == 'passed' and verified['delta'] == stg['delta']
    assert read(ROOT / p['logger_CPU_result'])['state'] == 'passed'
    selected = json.loads(subprocess.check_output([sys.executable, '-u', str(args.catalog_root / 'select_case.py'),
                          args.case_id, '--purpose', 'diagnostic'], text=True, encoding='utf-8'))
    assert selected['case_id'] == args.case_id and selected['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    meta = selected['server_inputs']['pre']
    assert meta['sha256'] == read(ROOT / 'CLEAN_FL_RESULT.json')['before']['sha256']
    assert sha(meta['path']) == meta['sha256'] and sha(ROOT / stg['delta']['path']) == stg['delta']['sha256']
    resources = guard(read(ROOT / 'GPU_PREFLIGHT_RESULT.json')['foundation_free_min_MiB'])
    with (ROOT / 'SSS_ONCE.json').open('x', encoding='utf-8') as stream:
        json.dump({'pid': os.getpid(), 'created_unix': time.time(), 'case_id': args.case_id, 'guard': resources}, stream)
    out = ROOT / 'sss'; out.mkdir(exist_ok=False)
    write(out / 'CASE_SELECTION.json', selected)
    state = torch.load(meta['path'], map_location='cpu', weights_only=True)
    state = state if meta['payload_key'] is None else state[meta['payload_key']]
    delta = torch.load(ROOT / stg['delta']['path'], map_location='cpu', weights_only=True)
    delta = delta if stg['delta']['payload_key'] is None else delta[stg['delta']['payload_key']]
    assert delta.shape == (1, 3, 32, 32) and float(delta.abs().max()) <= 32 / 255 + 1e-7
    torch.set_num_threads(1); torch.backends.cudnn.benchmark = False
    model = model_reference.ResNet18().cuda().eval()
    model.load_state_dict(state, strict=True)
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    profile = read(ROOT / 'CLEAN_FL_PROFILE.json')
    train = CIFAR10(profile['data_root'], train=True, download=False,
                    transform=transforms.Compose([transforms.ToTensor(), transforms.Normalize((.5,) * 3, (.5,) * 3)]))
    parts = read(ROOT / 'CLEAN_SPLIT.json')['indices']
    assert sha(ROOT / 'CLEAN_SPLIT.json') == read(ROOT / 'CLEAN_FL_READY.json')['split_sha256']
    owners = p['malicious_owner_ids']
    assert owners == [5, 7] and p['request_budget'] == 125
    ranked, ownership, packets = {}, {}, []
    actual_calls = 0
    def query_backend(x):
        nonlocal actual_calls
        actual_calls += 1
        assert not torch.is_grad_enabled() and not model.training
        return model(x)
    for owner in owners:
        ids = parts[owner]; ownership[owner] = ids
        assert len(ids) == 2500
        dataset = core.IndexedDataset(Subset(train, ids), ids)
        loader = DataLoader(dataset, batch_size=128, shuffle=False, num_workers=0, pin_memory=True)
        ranked[owner], observations = observe_and_rank(query_backend, loader, delta, 'cuda')
        assert {i for i, _ in ranked[owner]} == set(ids)
        for batch, observation in enumerate(observations, 1):
            observation.update(owner=owner, batch=batch)
            packet = save(out / 'queries' / f'owner{owner}_batch{batch:02d}.pt', observation)
            packets.append({'owner': owner, 'batch': batch, 'packet': packet})
        write(ROOT / 'SSS_STATE.json', {'state': 'querying', 'pid': os.getpid(), 'completed_owner': owner,
              'observed_samples': sum(len(v) for v in ranked.values()), 'actual_forward_calls': actual_calls,
              'updated_unix': time.time()})
    selected_ids = core.select_requests(ranked, ownership, 125)
    assert len(packets) == 40 and actual_calls == 80 and sum(len(v) for v in ranked.values()) == 5000
    assert sha(meta['path']) == meta['sha256'] and sha(ROOT / stg['delta']['path']) == stg['delta']['sha256']
    assert all(torch.equal(v.detach().cpu(), state[k]) for k, v in model.state_dict().items())
    result = {'state': 'completed_SSS_queries', 'profile': p['id'], 'case_id': args.case_id,
              'pre_checkpoint': meta, 'delta': stg['delta'], 'observed_samples': 5000,
              'query_batches': 40, 'actual_forward_calls': actual_calls, 'forward_sample_evaluations': 10000,
              'owner_ranks': {str(k): v for k, v in ranked.items()},
              'selected_by_owner': {str(k): v for k, v in selected_ids.items()}, 'request_budget': 125,
              'query_packets': packets, 'case_selection_sha256': sha(out / 'CASE_SELECTION.json'),
              'pre_and_delta_source_hashes_unchanged': True, 'model_state_unchanged': True,
              'real_FU_executed': False, 'FedUBA_attack_completed': False}
    write(ROOT / 'SSS_RESULT.json', result)
    write(ROOT / 'SSS_STATE.json', {'state': 'completed_SSS_queries', 'pid': os.getpid(), 'updated_unix': time.time()})
    print(json.dumps({k: result[k] for k in ['state', 'observed_samples', 'actual_forward_calls', 'request_budget']}))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        write(ROOT / 'SSS_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
