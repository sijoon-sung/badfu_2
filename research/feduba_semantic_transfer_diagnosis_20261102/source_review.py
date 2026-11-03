"""Stdlib-only source and input binding check; no numerical computation."""
import ast
import sys
from io_guard import ROOT, profile, resource_guard, write, sha

p = profile(published=False)
for f in ROOT.glob('*.py'): ast.parse(f.read_text(encoding='utf-8'))
guard = resource_guard()
assert 'torch' not in sys.modules
write('SOURCE_REVIEW_RESULT.json', {'state': 'passed_new_semantic_probe_source_input_metadata',
      'AST_files': len(list(ROOT.glob('*.py'))), 'source_freeze_sha256': sha(ROOT / 'SOURCE_FREEZE.json'),
      'profile_sha256': sha(ROOT / 'PROFILE.json'), 'guard': guard, 'model_loads': 0, 'forward_calls': 0})
