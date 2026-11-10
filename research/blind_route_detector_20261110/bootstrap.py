"""Scheduled one-shot lifecycle; preserve interrupted SSH metadata preparation."""
import json
import os
import subprocess
import sys
from pathlib import Path
from checkpoint_guard import sha

ROOT = Path(__file__).resolve().parent


def main():
    (ROOT/'BOOTSTRAP_ONCE').open('x').write(str(os.getpid()))
    assert json.loads((ROOT/'PUBLICATION.json').read_text())['all_raw_blob_bytes_verified']
    for name, digest in json.loads((ROOT/'FREEZE.json').read_text())['files'].items(): assert sha(ROOT/name) == digest, name
    assert sha('D:/TRAJECTORY_CATALOG_20261023/catalog.json') == '8cbb86b98bf44cfa344daca6df1326f1b2fafe946c3eceb3cf75dd961a21ec38'
    assert not (ROOT/'GUARD_MANIFEST.json').exists() and not (ROOT/'INPUTS.json').exists()
    for name in ('PREPARE_ONCE','prepare.stdout.txt','prepare.stderr.txt'):
        path = ROOT/name
        if path.exists(): path.rename(ROOT/('interrupted_'+name))
    for script in ('prepare.py','controller.py'):
        with (ROOT/(script+'.lifecycle.stdout.txt')).open('wb') as out, (ROOT/(script+'.lifecycle.stderr.txt')).open('wb') as err:
            result = subprocess.run([sys.executable,'-u',str(ROOT/script)], cwd=ROOT, stdout=out, stderr=err,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
        (ROOT/'BOOTSTRAP_STATE.json').write_text(json.dumps(dict(script=script, exit_code=result.returncode, pid=os.getpid())),encoding='utf-8')
        if result.returncode: return result.returncode
    return 0


if __name__ == '__main__': sys.exit(main())
