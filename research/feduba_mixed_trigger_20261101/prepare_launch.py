"""One metadata-only preparation after new teacher completion, never during its training."""
import sys
sys.dont_write_bytecode = True
import os
import traceback
from binding_gate import ROOT, read, sha, once, source_profile, teacher_ready, select_normal


def main():
    source = source_profile()
    assert not (ROOT / 'PREPARE_FAILURE.json').exists() and not (ROOT / 'PREPARE_ONCE.json').exists()
    assert read(ROOT / 'SOURCE_ONLY_REVIEW.json')['state'] == 'passed_source_only_closed_launch_gate'
    publication = read(ROOT / 'SOURCE_PUBLICATION.json')
    assert publication['state'] == 'source_code_published_before_launch_profile_preparation'
    assert publication['source_freeze_sha256'] == sha(ROOT / 'SOURCE_FREEZE.json')
    assert publication['source_review_sha256'] == sha(ROOT / 'SOURCE_ONLY_REVIEW.json')
    assert not (ROOT / 'LAUNCH_PROFILE.json').exists() and not (ROOT / 'RUN_FREEZE.json').exists()
    bindings, terminal = teacher_ready(source)
    selection = select_normal(source)
    once('PREPARE_ONCE.json', {'pid': os.getpid(), 'model_loads': 0, 'model_forwards': 0})
    once('TEACHER_TERMINAL.json', terminal); once('NORMAL_SELECTION.json', selection)
    actual = {'state': 'prepared_single_mixed_teacher_CPU_trigger100', 'launch_enabled': True,
              'execution_root': source['execution_root'], 'source_profile_sha256': sha(ROOT / 'SOURCE_PROFILE.json'),
              'constants': source['constants'], 'teacher_bindings': bindings,
              'normal_selection_sha256': sha(ROOT / 'NORMAL_SELECTION.json'),
              'source_review_sha256': sha(ROOT / 'SOURCE_ONLY_REVIEW.json')}
    once('LAUNCH_PROFILE.json', actual)
    once('RUN_FREEZE.json', {'state': 'actual_teacher_binding_prepared_not_yet_published_for_execution',
          'source_freeze_sha256': sha(ROOT / 'SOURCE_FREEZE.json'), 'launch_profile_sha256': sha(ROOT / 'LAUNCH_PROFILE.json'),
          'teacher_terminal_sha256': sha(ROOT / 'TEACHER_TERMINAL.json')})
    assert 'torch' not in sys.modules
    once('PREPARE_RESULT.json', {'state': 'passed_metadata_only_actual_binding_preparation',
         'launch_profile_sha256': sha(ROOT / 'LAUNCH_PROFILE.json'), 'run_freeze_sha256': sha(ROOT / 'RUN_FREEZE.json'),
         'model_loads': 0, 'model_forwards': 0, 'requires_PR_publication_before_runner': True})


if __name__ == '__main__':
    try: main()
    except BaseException:
        once('PREPARE_FAILURE.json', {'state': 'failed_preserved_no_trigger_started', 'traceback': traceback.format_exc()})
        raise
