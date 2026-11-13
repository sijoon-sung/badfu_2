"""Continue the untouched PCA computation after a pre-inference admission stop."""
import hashlib
import importlib.util
import json
import os
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    source = ROOT.parent / 'evaluate.py'
    freeze = json.loads((ROOT / 'FREEZE.json').read_bytes())
    with source.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == freeze['original_evaluator_sha256']
    spec = importlib.util.spec_from_file_location('frozen_d27', source)
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    original.ROOT = ROOT
    bound = original.bind()
    assert bound.plan['admission']['memory_gib'] == 6
    bound.plan['admission']['memory_gib'] = 4
    from resource_guard import admit

    observations = admit(bound.plan)
    bound.write(ROOT / 'ADMISSION.json', observations)
    original.run(bound)


if __name__ == '__main__':
    try:
        (ROOT / 'ONCE').open('x').write(str(os.getpid()))
        main()
    except Exception:
        (ROOT / 'FAILURE.json').write_text(json.dumps(dict(traceback=traceback.format_exc())), encoding='utf-8')
        raise SystemExit(1)
