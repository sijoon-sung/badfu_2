"""Read stored evaluation and execution records for two approved diagnostic runs."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parent
N = 10000
M = 9026


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def counts(row):
    assert row.get('N', N) == N and row['non_target_N'] == M
    ca = row['clean_correct']
    hits = row['target_successes']
    bias = row.get('clean_non_target_target_count', row.get('clean_target_count'))
    assert 0 <= ca <= N and 0 <= hits <= M and 0 <= bias <= M
    for name, expect in [('CA_pct', ca*100/N), ('ASR_pct', hits*100/M),
                         ('clean_target_bias_pct', bias*100/M)]:
        if name in row:
            assert math.isclose(row[name], expect, rel_tol=0, abs_tol=1e-10)
    return dict(clean_correct=ca, triggered_target=hits, clean_target=bias)


def qualifies(v):
    return v['clean_correct'] >= 9700 and v['triggered_target']*10 <= M


def stages(packet, files, spec):
    result = read(packet/'RESULT.json')
    verified = read(packet/'VERIFIED.json')
    endpoints = {}
    for stage in ('before','after'):
        independent = verified['independent_counts'][stage]
        endpoints[stage] = v = counts(result[stage])
        assert (v['clean_correct'], v['triggered_target'], M) == (
            independent['clean_correct'], independent['target_successes'], independent['non_target_N'])
    ledger = read(packet/'run/DELETION.json')
    intermediate = ledger['subtraction']
    sealed = files['run/after_subtraction.pt']
    assert intermediate['sha256'] == sealed['sha256'] and intermediate['bytes'] == sealed['bytes']
    assert verified['historical_subtraction_exact'] is True
    assert len(ledger['contributions']) == result['forgotten_contribution_count']
    events = [json.loads(s) for s in (packet/'run/events.jsonl').read_text(encoding='utf-8').splitlines()]
    kd = Counter(row['epoch'] for row in events if row['kind']=='KD_batch')
    assert kd == {i:47 for i in range(1,11)}
    assert verified['KD_batches'] == result['KD_batches'] == sum(kd.values())
    assert sum(row['kind']=='round_committed' for row in events) == 100
    evidence = spec.get('stage_result')
    cut = None
    if evidence:
        phase = read(evidence)
        assert phase['case_id'] == spec['id']
        assert phase['manifest_sha256'] == sha(packet/'DELIVERY_MANIFEST.json')
        cut = counts(phase['after_subtraction'])
    raw = Path(spec['raw_root'])
    assert raw.is_dir(), raw
    raw_eval = raw/'evaluation'
    assert raw_eval.is_dir(), raw_eval
    alternate_stage_paths = sorted(p.name for p in raw_eval.glob('*.json') if not p.name.startswith('round'))
    raw_events = raw/'events.jsonl'
    assert sha(raw_events) == sha(packet/'run/events.jsonl')
    return dict(before=endpoints['before'],after_subtraction=cut,after_kd10=endpoints['after'],
        deletion_verified=True,kd_batches_by_epoch=dict(sorted(kd.items())),
        non_round_raw_evaluation_files=alternate_stage_paths,raw_event_log_matches_seal=True)


def audit(spec, catalog):
    case = catalog[spec['id']]
    assert case['allowed_purposes']==['diagnostic'] and case['seed']==spec['seed']
    packet = Path(spec['packet'])
    assert packet == Path(case['source_root'])
    files = read(packet/'DELIVERY_MANIFEST.json')['files']
    for n in ('RESULT.json','VERIFIED.json','run/events.jsonl','run/DELETION.json'):
        assert sha(packet/n)==files[n]['sha256'] and (packet/n).stat().st_size==files[n]['bytes'], n
    points = []
    for i in range(1,101):
        n=f'run/evaluation/round{i:04}.json'
        assert sha(packet/n)==files[n]['sha256'] and (packet/n).stat().st_size==files[n]['bytes'], n
        row=read(packet/n)
        assert row['both_eval'] and row['trigger_role']==4
        points.append(dict(round=i,**counts(row)))
    post = stages(packet,files,spec)
    assert all(points[-1][k]==v for k,v in post['before'].items())
    last = max(v['round'] for v in points if qualifies(v))
    assert last == spec['last_pass']
    late = points[last:]
    assert all(not qualifies(v) for v in late)
    summary = dict(seed=spec['seed'],case_id=spec['id'],rounds_checked=100,last_pass=points[last-1],
        first_after_last_pass=late[0],round99=points[98],round100=points[99],late_rounds=len(late),
        late_bounds={k:[min(v[k] for v in late),max(v[k] for v in late)]
                    for k in ('clean_correct','triggered_target','clean_target')},
        stages=post,qualified=qualifies(post['before']) and post['after_kd10']['clean_correct']>=9700
                  and post['after_kd10']['triggered_target']*5>=3*M,
        trajectory=points)
    return summary


def main():
    freeze = read(ROOT/'FREEZE.json')
    receipt = read(ROOT/'PUBLICATION.json')
    assert receipt['all_raw_blob_bytes_verified'] and receipt['freeze_sha256']==sha(ROOT/'FREEZE.json')
    assert all(sha(ROOT/n)==v for n,v in freeze['files'].items())
    plan=read(ROOT/'PLAN.json')
    assert all(sha(n)==v for n,v in plan['references'].items())
    catalog={x['id']:x for x in read(plan['catalog'])['cases']}
    rows=[audit(s,catalog) for s in plan['cases']]
    output=dict(state='metadata_verified',N=N,non_target=M,rows=rows,new_model_loads=0,new_inference=0,new_training=0)
    with (ROOT/'RESULT.json').open('x',encoding='utf-8',newline='\n') as f:
        f.write(json.dumps(output,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in x.items() if k!='trajectory'} for x in rows],indent=2))


if __name__=='__main__':
    main()
