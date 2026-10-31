"""Study bookkeeping only. Numerical training code is copied without alteration."""
import hashlib
import json
import os
from pathlib import Path
import time
from storage_retry import replace_with_retry

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 << 20), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    path = Path(path)
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    replace_with_retry(tmp, path)


def once(name):
    with (ROOT / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump({'pid': os.getpid(), 'created_unix': time.time()}, stream)


def verify_freeze():
    for name, digest in read(ROOT / 'STUDY_FREEZE.json')['files'].items():
        assert sha(ROOT / name) == digest, name


def case_id(seed):
    return f'fuba.algorithm_sgd.mnist.dba.s{seed}.pre100.post.kd10.seed_repro20261031'
