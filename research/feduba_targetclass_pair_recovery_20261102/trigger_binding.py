"""Read only the new mixed-trigger binding; never rename an old STG receipt."""
from pair_binding import ROOT, FOUNDATION, read, sha, checked, require_published_run


def verified_cpu_trigger(expected_binding_sha256):
    source, launch = require_published_run()
    assert sha(ROOT / 'TRIGGER_SOURCE_BINDING.json') == expected_binding_sha256
    binding = read(ROOT / 'TRIGGER_SOURCE_BINDING.json')
    assert binding['kind'] == 'new_mixed105_teacher_verified_CPU_trigger100'
    for meta in binding['receipts'].values(): checked(meta)
    result = read(binding['receipts']['TRIGGER_RESULT.json']['path'])
    audit = read(binding['receipts']['TRIGGER_VERIFIED.json']['path'])
    assert result['state'] == 'completed_CPU_mixed_teacher_trigger100'
    assert audit['state'] == 'passed_new_mixed_teacher_CPU_trigger100'
    assert result['teacher'] == audit['teacher'] == binding['teacher']
    assert result['delta'] == audit['delta'] == binding['original_delta_metadata']
    assert binding['teacher']['sha256'] == source['required_mixed_teacher_sha256']
    checked(binding['delta']); checked(binding['old_GPU_failure'])
    assert read(binding['old_GPU_failure']['path'])['state'] == 'failed_preserved'
    assert not (FOUNDATION / 'STG_VERIFIED.json').exists()
    # New output metadata uses an explicit absolute external path; raw receipts stay unchanged.
    result = dict(result, delta=binding['delta'])
    audit = dict(audit, delta=binding['delta'])
    return binding, result, audit
