"""Single fixed probe then a fresh independent saved-logit/input audit."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', PYTHONDONTWRITEBYTECODE='1')
import ast
import json
import subprocess
import sys
import traceback
from io_guard import ROOT, profile, write, resource_guard, sha


def main():
    p = profile(); resource_guard()
    for f in ROOT.glob('*.py'): ast.parse(f.read_text(encoding='utf-8'))
    write('CONTROLLER_ONCE.json', {'pid': os.getpid(), 'parent': os.getppid()})
    selection = json.loads(subprocess.check_output([sys.executable, '-B', p['catalog_root'] + '/select_case.py',
        p['case_id'], '--purpose', 'diagnostic'], text=True, encoding='utf-8'))
    assert selection['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    assert selection['checkpoint_guard']['manifest_sha256'] == '85b83c04efa29406576232e39080e08adfa0abfb2d4550241517991110fcd99b'
    assert selection['checkpoint_guard']['seal_sha256'] == 'f316861aa56313a821d50d551658d0d8235f0f37970f97e25a58446e11a4ddd6'
    assert selection['server_inputs']['pre']['sha256'] == p['inputs']['victim']['sha256']
    write('CASE_SELECTION.json', selection)
    for phase in ['run', 'verify']:
        child = subprocess.Popen([sys.executable, '-B', '-u', str(ROOT / 'semantic_diagnosis.py'), '--phase', phase], cwd=ROOT)
        write('CONTROLLER_STATE.json', {'state': 'running', 'phase': phase, 'pid': os.getpid(), 'child': child.pid}, exclusive=False)
        code = child.wait(); assert code == 0, 'phase ' + phase + ' exit ' + str(code)
    write('COMPLETION.json', {'state': 'completed_fixed_semantic_transfer_probe_and_audit',
          'result_sha256': sha(ROOT / 'RESULT.json'), 'verified_sha256': sha(ROOT / 'VERIFIED.json'), 'overall_goal_complete': False})
    write('CONTROLLER_STATE.json', {'state': 'completed', 'pid': os.getpid(), 'exit_code': 0}, exclusive=False)


if __name__ == '__main__':
    try: main()
    except BaseException:
        write('CONTROLLER_FAILURE.json', {'state': 'failed_preserved', 'traceback': traceback.format_exc()})
        raise
