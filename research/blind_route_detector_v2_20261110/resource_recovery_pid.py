"""Recover failed pre-CNN admission under the published shared-resource profile."""
import json
import os
from pathlib import Path
import subprocess
import sys
from checkpoint_guard import sha

ROOT = Path(__file__).resolve().parent


def main():
    (ROOT/'RESOURCE_RECOVERY_ONCE').open('x').write(str(os.getpid()))
    assert json.loads((ROOT/'PUBLICATION.json').read_text())['all_raw_blob_bytes_verified']
    for n,d in json.loads((ROOT/'FREEZE.json').read_text())['files'].items(): assert sha(ROOT/n) == d
    assert not any((ROOT/n).exists() for n in ('STATE.json','RESULT.json','SELECTIONS.json','ALGEBRA_CONTRACT.json','FIXTURES.json','VERIFY_ONCE'))
    assert json.loads((ROOT/'CONTROLLER_STATE.json').read_text())['state'] == 'failed'
    original = json.loads((ROOT/'PROFILE_INITIAL.json').read_text())
    current = json.loads((ROOT/'PROFILE.json').read_text())
    for key in original:
        if key not in ('memory_fraction','admission'): assert current[key] == original[key]
    for key in original['admission']:
        if key != 'gpu_free_mib': assert current['admission'][key] == original['admission'][key]
    archive = ROOT/'admission_blocked'; archive.mkdir(exist_ok=False)
    for name in ('CONTROLLER_ONCE','CONTROLLER_STATE.json','SEARCH_ONCE','SEARCH_FAILURE.txt','BOOTSTRAP_STATE.json',
                 'run_search.py.stdout.txt','run_search.py.stderr.txt','controller.py.lifecycle.stdout.txt','controller.py.lifecycle.stderr.txt'):
        p = ROOT/name
        if p.exists(): p.rename(archive/name)
    with (ROOT/'recovery_controller.stdout.txt').open('wb') as out, (ROOT/'recovery_controller.stderr.txt').open('wb') as err:
        result = subprocess.run([sys.executable,'-u',str(ROOT/'controller.py')], cwd=ROOT, stdout=out, stderr=err,
                                creationflags=subprocess.CREATE_NO_WINDOW)
    (ROOT/'RESOURCE_RECOVERY_STATE.json').write_text(json.dumps(dict(exit_code=result.returncode,pid=os.getpid())),encoding='utf-8')
    return result.returncode


if __name__ == '__main__': sys.exit(main())
