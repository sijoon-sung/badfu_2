"""Evaluate the P07 immediate correction against stored, read-only test fixtures."""

import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
CASES = ('attack23', 'attack20', 'infected_normal')
PATHS = ('balanced', 'client1_weighted')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def summarize(result, name):
    clean = result['clean']
    archive = result['fixed_archive']
    first = {arm: paths['balanced']['anchor'] for arm, paths in archive.items()}
    assert all(paths['client1_weighted']['anchor'] == first[arm] for arm, paths in archive.items())
    for paths in archive.values():
        for values in paths.values():
            for phase in ('anchor', 'final'):
                row = values[phase]
                assert row['n'] == 1440 == sum(row[k] for k in ('target', 'original_correct', 'other_wrong'))
    keys = ('none', 'anchor')
    comparisons = {'immediate': {arm: first[arm] for arm in keys if arm in first}}
    comparisons.update({path: {arm: archive[arm][path]['final'] for arm in keys if arm in archive} for path in PATHS})
    clean_counts = {
        'immediate': {arm: clean[arm]['balanced'][0]['public']['correct'] for arm in keys if arm in clean},
        **{path: {arm: clean[arm][path][-1]['public']['correct'] for arm in keys if arm in clean} for path in PATHS},
    }
    coverage = result['fit']['eligible_by_class']
    passed = False
    if 'anchor' in archive:
        for stage, rows in comparisons.items():
            a, b = rows['anchor'], rows['none']
            rows['asr_drop_pp'] = 100 * (b['target'] - a['target']) / 1440
            rows['original_gain_pp'] = 100 * (a['original_correct'] - b['original_correct']) / 1440
        checks = [comparisons[stage]['asr_drop_pp'] >= 5 and comparisons[stage]['original_gain_pp'] >= 5 for stage in comparisons]
        passed = all(checks) and all(v['passed'] for v in result['utility_deltas']['anchor'].values())
    return {'input_sha256': result['fit']['input_sha256'], 'comparison': comparisons,
            'clean_correct_of_1600': clean_counts, 'utility': result['utility_deltas'].get('anchor'),
            'eligible_by_class': coverage, 'passed': passed,
            'available_arms': sorted(archive), 'case': name, 'seconds': result['seconds']}


def main():
    for name, digest in read(ROOT / 'FREEZE.json').items():
        assert sha(ROOT / name) == digest, name
    with (ROOT / 'STARTED.json').open('x', encoding='utf-8') as f:
        json.dump({'pid': os.getpid(), 'runner_sha256': sha(__file__)}, f)
    import run_real as p07
    import numpy as np
    import scipy
    import torch
    import torchvision

    assert (torch.__version__, torchvision.__version__, np.__version__, scipy.__version__) == ('2.7.1+cu118', '0.22.1+cu118', '1.26.4', '1.15.3')
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(61116)
    cfg = read(ROOT / 'INPUTS.json')
    snap = cfg['snapshot']
    snapshot = p07.old.check(snap['manifest']).parent
    p07.old.check(snap['seal'])
    p07.old.check(snap['loader'])
    sys.path.insert(0, str(snapshot))
    import load_confirmed as sealed
    sealed.verify(snapshot, snap['manifest']['sha256'])
    constructor = sealed.model_class(snapshot)
    data, plans, extras, test_ids = p07.select_data(cfg)
    summaries = {}
    for case in CASES:
        p07.run_case(case, cfg, constructor, data, plans, extras, test_ids, True)
        summaries[case] = summarize(read(ROOT / f'{case}_RESULT.json'), case)
        p07.write(f'{case}_DIAGNOSTIC.json', summaries[case])
        print(f'{case} direct comparison {summaries[case]["comparison"]}', flush=True)
    p07.write('SUMMARY.json', {'state': 'complete', 'attack_effect_gate': all(summaries[k]['passed'] for k in CASES[:2]),
                               'cases': summaries, 'scope': 'stored BadFU test fixtures only'})


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        with (ROOT / 'FAILURE.json').open('x', encoding='utf-8') as f:
            json.dump({'error': type(exc).__name__, 'message': str(exc)}, f)
        raise
