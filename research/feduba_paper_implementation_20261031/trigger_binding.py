"""Explicit provenance of the verified CPU trigger branch; preserves failed original audit."""
from runtime_common import ROOT, read, sha, freeze_check


def verified_cpu_trigger(expected_binding_sha256):
    assert sha(ROOT / 'STG_CPU_SOURCE_BINDING.json') == expected_binding_sha256
    binding = read(ROOT / 'STG_CPU_SOURCE_BINDING.json')
    assert binding['kind'] == 'CPU_trigger100_after_reused_original_105_model_epochs'
    expected_files = {'result': 'STG_CPU_TRIGGER_RESULT.json', 'audit': 'STG_CPU_TRIGGER_VERIFIED.json',
                      'controller': 'STG_CPU_TRIGGER_CONTROLLER_STATE.json', 'profile': 'STG_CPU_TRIGGER_PROFILE.json',
                      'source_freeze': 'STG_CPU_TRIGGER_FREEZE.json', 'original_result': 'STG_RESULT.json',
                      'original_failure': 'STG_AUDIT_FAILURE.json'}
    for key, name in expected_files.items():
        assert binding[key]['path'] == name and sha(ROOT / name) == binding[key]['sha256']
    freeze_check('STG_CPU_TRIGGER_FREEZE.json')
    result = read(ROOT / expected_files['result']); audit = read(ROOT / expected_files['audit'])
    assert result['state'] == 'completed_CPU_trigger100'
    assert audit['state'] == 'passed_CPU_trigger100_with_reused_fixed_surrogate'
    assert read(ROOT / expected_files['controller'])['state'] == 'completed_CPU_trigger100_verified'
    assert result['new_trigger_epochs'] == audit['new_epochs'] == 100
    assert result['new_actual_batches'] == audit['new_batches'] == audit['new_steps'] == 200
    assert result['reused_original_model_epochs'] == 105 and audit['original_105_model_epochs_reused_not_retrained']
    assert [(r['epoch'], r['batch']) for r in audit['independent_gradient_replays']] == [(1, 1), (100, 2)]
    assert result['delta'] == audit['delta'] == binding['delta']
    assert result['fixed_surrogate'] == audit['fixed_surrogate'] == binding['fixed_surrogate']
    assert sha(ROOT / result['delta']['path']) == result['delta']['sha256']
    assert result['original_CPU_GPU_gradient_audit_remains_failed'] and audit['original_CPU_GPU_gradient_audit_remains_failed']
    assert read(ROOT / 'STG_AUDIT_FAILURE.json')['state'] == 'failed_preserved'
    assert not (ROOT / 'STG_VERIFIED.json').exists()
    return binding, result, audit
