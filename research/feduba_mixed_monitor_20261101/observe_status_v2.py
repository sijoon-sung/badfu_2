"""Bounded read-only status; JSON event rows never carry PowerShell ETS providers."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
QUERY = (HERE / 'QUERY_V2.ps1').read_text(encoding='utf-8')


def observe():
    frozen = json.loads((HERE / 'FREEZE_V2.json').read_text(encoding='utf-8'))
    for name, digest in frozen['files'].items():
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest, name
    sys.path.insert(0, str(HERE.parent / '00_trajectories'))
    import dislab_audit
    raw = dislab_audit.remote(QUERY)
    if len(raw) > 50000:
        raise RuntimeError('Observer output exceeded the fixed character bound; raw output withheld')
    value = json.loads(raw)
    assert value['root'] == 'D:/FEDUBA_MIXED_PAIR_20261101'
    assert set(value) == {'utc', 'root', 'states', 'processes', 'committed_rounds', 'last_events', 'completed'}
    # Explicit schemas also reject accidental ETS expansion within a short output.
    for event in value['last_events'].values():
        assert set(event) == {'kind', 'branch', 'round', 'client', 'epoch', 'examples', 'batches', 'cumulative_role_batches'}
    assert 'torch' not in sys.modules
    return {'state': 'passed_bounded_readonly_metadata_observation', 'output_characters': len(raw),
            'source_freeze_sha256': hashlib.sha256((HERE / 'FREEZE_V2.json').read_bytes()).hexdigest(),
            'query_sha256': hashlib.sha256(QUERY.encode()).hexdigest(),
            'new_model_queries': 0, 'training_or_audit_reexecuted': False, 'observation': value}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--save', type=Path)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    result = observe()
    output = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.save:
        with args.save.open('x', encoding='utf-8', newline='\n') as stream: stream.write(output)
    print(output)
