"""Once source/stdlib routing review; no numerical module, model, or fixture runs."""
import ast
import json
import os
from pathlib import Path
import sys
from recovery_io import ROOT, OLD, read, sha, once, input_path, tensor_path, writable, source_check, require_published_run, Unlaunched


def main():
    p = source_check()
    once('SOURCE_REVIEW_ONCE.json', {'pid': os.getpid(), 'torch_imported': False})
    py = sorted(ROOT.glob('*.py'))
    for path in py: ast.parse(path.read_text(encoding='utf-8'))
    for name, digest in p['helper_original_bytes'].items():
        assert sha(ROOT / name) == sha(OLD / name) == digest, name
    assert sha(ROOT / 'native_memory.py') == p['native_memory_original_bytes']
    assert input_path(ROOT / 'FU_benign_RESULT.json') == OLD / 'FU_benign_RESULT.json'
    assert input_path(ROOT / 'FU_attack_RESULT.json') == ROOT / 'FU_attack_RESULT.json'
    assert input_path(ROOT / 'FU_LAUNCH_PROFILE.json') == OLD / 'FU_LAUNCH_PROFILE.json'
    assert input_path(ROOT / 'LAUNCH_PROFILE.json') == ROOT / 'LAUNCH_PROFILE.json'
    assert tensor_path({'path': 'fu/attack/rounds/round04.pt'}) == (OLD / 'fu/attack/rounds/round04.pt').resolve()
    assert tensor_path({'path': str(ROOT / 'fu/attack/rounds/round05.pt')}) == (ROOT / 'fu/attack/rounds/round05.pt').resolve()
    rejected = 0
    for path in [OLD / 'FU_attack_RESULT.json', ROOT / 'FU_benign_RESULT.json']:
        try: writable(path)
        except AssertionError: rejected += 1
        else: raise AssertionError('Read-only input path accepted for writing')
    assert rejected == 2
    try: require_published_run()
    except Unlaunched: pass
    else: raise AssertionError('Source-only gate accepted missing actual profile')
    assert not (ROOT / 'LAUNCH_PROFILE.json').exists()
    assert 'torch' not in sys.modules
    result = {'state': 'passed_source_only_recovery_routing_review', 'Python_AST_files': len(py),
        'copied_original_helper_bytes': 7, 'metadata_path_mapping_checks': 6, 'old_input_write_rejections': 2,
        'closed_actual_run_gate_rejected': True, 'model_loads': 0, 'model_forwards': 0,
        'torch_imported': False, 'new_or_old_numerical_fixture_executed': False,
        'actual_metadata_prepare_executed': False, 'actual_GPU_task_started': False}
    once('SOURCE_REVIEW_RESULT.json', result)
    print(json.dumps(result))


if __name__ == '__main__': main()
