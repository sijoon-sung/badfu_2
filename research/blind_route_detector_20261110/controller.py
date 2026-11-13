"""One controller, one search, one independent verifier. No retries."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from checkpoint_guard import sha

ROOT = Path(__file__).resolve().parent


def write(name, obj):
    (ROOT/name).write_text(json.dumps(obj, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def main():
    (ROOT/'CONTROLLER_ONCE').open('x').write(str(os.getpid()))
    publication = json.loads((ROOT/'PUBLICATION.json').read_text())
    assert publication['all_raw_blob_bytes_verified']
    for name, digest in json.loads((ROOT/'FREEZE.json').read_text())['files'].items(): assert sha(ROOT/name) == digest
    codes = {}
    for script in ('run_search.py', 'verify_results.py'):
        with (ROOT/(script+'.stdout.txt')).open('wb') as out, (ROOT/(script+'.stderr.txt')).open('wb') as err:
            child = subprocess.Popen([sys.executable, '-u', str(ROOT/script)], stdout=out, stderr=err, cwd=ROOT,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            write('CONTROLLER_STATE.json', dict(state='running', controller_pid=os.getpid(), child_pid=child.pid, script=script, time=time.time()))
            codes[script] = child.wait()
        if codes[script]:
            write('CONTROLLER_STATE.json', dict(state='failed', exit_codes=codes, failed_script=script, time=time.time()))
            return codes[script]
    files = {}
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.name not in ('FINAL_FILES.json', 'CONTROLLER_STATE.json'):
            files[str(p.relative_to(ROOT)).replace('\\','/')] = dict(sha256=sha(p), bytes=p.stat().st_size)
    write('FINAL_FILES.json', dict(files=files))
    write('CONTROLLER_STATE.json', dict(state='complete', exit_codes=codes, time=time.time()))
    return 0


if __name__ == '__main__': sys.exit(main())
