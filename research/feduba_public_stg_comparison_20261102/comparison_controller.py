"""One-shot direct Python controller. Never resumes, retries, or starts SSS/FU."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', PYTHONDONTWRITEBYTECODE='1')
import ast
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
from io_guard import ROOT, profile, write, sha, resource_guard
from public_stage import stage_tree


def main():
    p = profile(); resource_guard()
    for file in ROOT.glob('*.py'): ast.parse(file.read_text(encoding='utf-8'))
    stage_tree(Path(p['inputs']['upstream']['path']))
    assert not any((ROOT / n).exists() for n in ['RUN_ONCE.json', 'RESULT.json', 'VERIFIED.json', 'RUN_FAILURE.json', 'AUDIT_FAILURE.json'])
    write('CONTROLLER_ONCE.json', {'pid': os.getpid(), 'parent': os.getppid(), 'utc_unix': time.time(),
          'publication_sha256': sha(ROOT / 'PUBLICATION.json')})
    selected = json.loads(subprocess.check_output([sys.executable, '-B', p['catalog_root'] + '/select_case.py',
                          p['normal_case_id'], '--purpose', 'diagnostic'], text=True, encoding='utf-8'))
    assert selected['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    assert selected['checkpoint_guard']['manifest_sha256'] == '85b83c04efa29406576232e39080e08adfa0abfb2d4550241517991110fcd99b'
    assert selected['checkpoint_guard']['seal_sha256'] == 'f316861aa56313a821d50d551658d0d8235f0f37970f97e25a58446e11a4ddd6'
    write('NORMAL_CASE_SELECTION.json', selected)
    for name in ['run_comparison.py', 'verify_comparison.py']:
        process = subprocess.Popen([sys.executable, '-B', '-u', str(ROOT / name)], cwd=ROOT)
        write('CONTROLLER_STATE.json', {'state': 'running', 'pid': os.getpid(), 'child': process.pid, 'step': name}, exclusive=False)
        code = process.wait()
        assert code == 0, name + ' exit=' + str(code)
    write('COMPLETION.json', {'state': 'completed_new_public_STG_comparison_and_audit',
          'result_sha256': sha(ROOT / 'RESULT.json'), 'verified_sha256': sha(ROOT / 'VERIFIED.json'),
          'no_SSS_FU_or_victim_evaluation_started': True, 'overall_goal_complete': False})
    write('CONTROLLER_STATE.json', {'state': 'completed', 'pid': os.getpid(), 'exit_code': 0}, exclusive=False)


if __name__ == '__main__':
    try: main()
    except BaseException:
        write('CONTROLLER_FAILURE.json', {'state': 'failed_preserved', 'traceback': traceback.format_exc()})
        raise
