"""Independent arithmetic/log audit of the new bounded trajectories; read-only CPU."""
import collections
import json
import os
from pathlib import Path
import torch
from run import ROOT, read, sha, exact, write, frozen


def main():
    torch.set_num_threads(1)
    frozen()
    for name,digest in read(ROOT/'AUDIT_FREEZE.json')['files'].items():
        assert sha(ROOT/name)==digest
    assert read(ROOT / 'STATE.json')['state'] == 'complete'
    write(ROOT/'CPU_AUDIT_STARTED.json',{'pid':os.getpid()},True)
    result = read(ROOT / 'RESULT.json')
    initial = torch.load(ROOT / 'inputs/round0020.pt', weights_only=True, map_location='cpu')['after']
    totals = collections.Counter()
    branch_decisions = {}
    for arm in ['local', 'global']:
        events = [json.loads(line) for line in (ROOT / arm / 'epochs.jsonl').read_text().splitlines()]
        grouped = collections.defaultdict(list)
        for e in events:
            grouped[e['round'], e['client'], e['phase']].append(e)
        entries = read(ROOT / arm / 'MANIFEST.json')['rounds']
        assert len(entries) == 10 and [e['round'] for e in entries] == list(range(21,31))
        previous = initial
        branch_decisions[arm] = {}
        for entry in entries:
            path = ROOT / entry['path']
            assert sha(path) == entry['sha256']
            bundle = torch.load(path, weights_only=True, map_location='cpu')
            exact(previous, bundle['incoming'])
            assert len(bundle['clients']) == len(bundle['submitted']) == len(bundle['roles']) == 8
            exact(bundle['after'], {k: torch.stack([s[k] for s in bundle['submitted']]).mean(0) for k in previous})
            for client, submission, role in zip(bundle['clients'], bundle['submitted'], bundle['roles']):
                assert client == role['client'] and role['round'] == entry['round'] and role['arm'] == arm
                file = ROOT / role['submitted']['path']
                assert sha(file) == role['submitted']['sha256']
                exact(submission, torch.load(file, weights_only=True, map_location='cpu')['model'])
                phases = []
                names = ['benign'] if client >= 5 else ['backdoor_anchor','benign_anchor','embedding','recovery' if client==4 else 'representative']
                assert len(role['phases']) == len(names)
                for item, name in zip(role['phases'], names):
                    p = ROOT / item['path']
                    assert sha(p) == item['sha256']
                    payload = torch.load(p, weights_only=True, map_location='cpu')
                    assert payload['epochs'] == 50 and payload['batches'] == (2350 if client >=5 else 2150)
                    assert {'model','optimizer','loader_rng','rng'} <= payload.keys()
                    assert {'torch_CPU','torch_CUDA','python','numpy'} <= payload['rng'].keys()
                    assert all(bool(torch.isfinite(v).all()) for v in payload['model'].values())
                    ev = grouped[entry['round'],client,name]
                    assert [x['epoch'] for x in ev] == list(range(1,51))
                    expected_optimizer = 'SGD' if name in ['embedding','recovery'] else 'Adam'
                    assert all(x['optimizer']==expected_optimizer for x in ev)
                    assert [x['batches'] for x in ev] == [(i+1)*(47 if client>=5 else 43) for i in range(50)]
                    assert (not payload['optimizer']['state']) == (expected_optimizer=='SGD')
                    phases.append(payload['model'])
                    totals['phases']+=1;totals['epochs']+=50;totals['batches']+=payload['batches']
                if client <4:
                    dec=role['decision'];scores=dec['scores']
                    assert [s['gamma'] for s in scores]==[i/10 for i in range(11)]
                    expected_trigger=client if arm=='local' else 4
                    for s in scores:
                        assert s['N']==300 and s['trigger_role']==expected_trigger
                        assert s['ASR_pct']==100*s['target_successes']/s['non_target_N']
                    passed=[s['gamma'] for s in scores if s['ASR_pct']<10]
                    gamma=max(passed) if passed else 0.
                    assert dec['gamma']==gamma and dec['constraint_met']==bool(passed)
                    calculated={k:previous[k]+gamma*(phases[2][k]-previous[k]) for k in previous}
                    exact(submission,calculated)
                    branch_decisions[arm][f"{entry['round']}/{client}"]=gamma
                    totals['gamma_traces']+=1
                elif client==4:
                    exact(submission,{k:previous[k]+phases[3][k]-phases[2][k] for k in previous})
                    totals['defender_roles']+=1
                else:
                    exact(submission,phases[0])
                totals['roles']+=1
            previous=bundle['after']
            metric=entry['evaluation']
            assert metric['N']==10000 and metric['non_target_N']==9026 and metric['trigger_role']==4
            assert metric['ASR_pct']==100*metric['target_successes']/9026
            assert metric['CA_pct']==100*metric['clean_correct']/10000
            totals['rounds']+=1
    assert totals['epochs']==len([json.loads(s) for arm in ['local','global'] for s in (ROOT/arm/'epochs.jsonl').read_text().splitlines()])
    changed=[k for k in branch_decisions['local'] if branch_decisions['local'][k]!=branch_decisions['global'][k]]
    assert changed==result['changed_gamma_roles']
    write(ROOT/'CPU_AUDIT.json',{'state':'passed','counts':dict(totals),'exact_submission_and_aggregation':True,
        'complete_epoch_logs':True,'optimizer_and_RNG_present':True,'gamma_arithmetic':True,
        'all_gamma_independent_inference':False,'gradient_training_replay':False,
        'CUDA_initialized':torch.cuda.is_initialized()},True)
    print(json.dumps(dict(totals)),flush=True)


if __name__=='__main__':
    main()
