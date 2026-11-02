"""New source/metadata review only; no model or torch import."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
from native_memory import memory_information
from native_processes import processes

ROOT = Path(__file__).resolve().parent


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(65536), b''): h.update(data)
    return h.hexdigest()


def main():
    p = read(ROOT / 'SOURCE_PROFILE.json')
    assert p['launch_enabled'] is False and ROOT == Path(p['execution_root'])
    assert not (ROOT / 'SOURCE_CHECK_RESULT.json').exists()
    for n, digest in read(ROOT / 'SOURCE_FREEZE.json')['files'].items(): assert sha(ROOT / n) == digest, n
    for path in ROOT.glob('*.py'): ast.parse(path.read_text(encoding='utf-8'))
    for n, digest in p['reused_helpers'].items():
        assert sha(ROOT / n) == sha(Path(p['old_pair_root']) / n) == digest, n
    for value in p['inputs'].values(): assert sha(value['path']) == value['sha256'], value['path']
    for n in ['seed', 'rng', 'cpu']:
        trees = [ast.parse(path.read_text(encoding='utf-8')) for path in [ROOT / 'runtime_common.py', Path(p['old_pair_root']) / 'runtime_common.py']]
        bodies = [next(node for node in t.body if isinstance(node, ast.FunctionDef) and node.name == n) for t in trees]
        assert ast.dump(bodies[0], include_attributes=False) == ast.dump(bodies[1], include_attributes=False), n
    # The independent evaluator changes only process metadata, not any numerical loop.
    loops = []
    for path in [ROOT / 'verify_pair_evaluation.py', Path(p['old_pair_root']) / 'verify_pair_evaluation.py']:
        tree = ast.parse(path.read_text(encoding='utf-8'))
        loops.append([ast.dump(n, include_attributes=False) for n in ast.walk(tree) if isinstance(n, ast.For)])
    assert loops[0] == loops[1]
    fu = read(ROOT / 'FU_PROFILE.json')
    old_fu = read(p['inputs']['original_FU_actual_profile']['path'])
    for key in ['history_global_payload_key', 'history_role_payload_key']: assert key in fu and fu[key] == old_fu[key]
    required_fu_keys = {node.slice.value for file in ['fu_runner.py', 'verify_fu.py'] for node in ast.walk(ast.parse((ROOT / file).read_text())) if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == 'p' and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str)}
    assert required_fu_keys.issubset(set(fu) | {'history_manifest_sha256', 'trigger_binding_sha256'}), required_fu_keys - set(fu)
    memory = memory_information()
    assert memory['availableBytes'] >= 8 * 2**30 and memory['commitLimit'] - memory['committedBytes'] >= 16 * 2**30
    raw = subprocess.check_output(['C:/Windows/System32/nvidia-smi.exe', '--query-gpu=utilization.gpu,memory.free,memory.used', '--format=csv,noheader,nounits'], text=True).strip()
    util, free, used = [int(v.strip()) for v in raw.split(',')]
    assert util <= 5 and free >= 4000 and used <= 6000
    peers = [r for r in processes() if r['ProcessId'] not in [os.getpid(), os.getppid()] and any(t in r['CommandLine'].lower() for t in p['known_training_process_tokens'])]
    assert not peers and shutil.disk_usage(ROOT).free >= 80 * 2**30
    assert 'torch' not in sys.modules
    with (ROOT / 'SOURCE_CHECK_RESULT.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump({'state': 'passed_targetclass_pair_source_metadata_review', 'source_freeze_sha256': sha(ROOT / 'SOURCE_FREEZE.json'),
            'AST_files': len(list(ROOT.glob('*.py'))), 'exact_reused_helpers': len(p['reused_helpers']),
            'seed_rng_cpu_AST_exact': True, 'independent_evaluator_all_numerical_For_AST_exact': True,
            'memory': memory, 'GPU': {'util': util, 'free': free, 'used': used}, 'competing_trainers': 0,
            'model_loads': 0, 'model_forwards': 0, 'old_fixture_or_training_rerun': False}, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    try: main()
    except BaseException:
        with (ROOT / 'SOURCE_CHECK_FAILURE.json').open('x', encoding='utf-8') as stream:
            json.dump({'state': 'failed_preserved', 'traceback': traceback.format_exc()}, stream, indent=2)
        raise
