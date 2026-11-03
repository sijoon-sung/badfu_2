"""Prepublication source/input metadata checks only; torch/model import forbidden."""
import ast
from pathlib import Path
import sys
from io_guard import ROOT, profile, resource_guard, write, sha
from public_stage import stage_tree

p = profile(published=False)
files = list(ROOT.glob('*.py'))
for file in files: ast.parse(file.read_text(encoding='utf-8'))
stage_tree(Path(p['inputs']['upstream']['path']))
guard = resource_guard()
assert 'torch' not in sys.modules
write('SOURCE_REVIEW_RESULT.json', {'state': 'passed_new_public_AST_and_input_metadata_review',
      'python_AST_files': len(files), 'public_stage_reverse_port_AST_exact': True,
      'source_freeze_sha256': sha(ROOT / 'SOURCE_FREEZE.json'),
      'profile_sha256': sha(ROOT / 'PROFILE.json'), 'guard': guard,
      'torch_imports': 0, 'model_loads': 0, 'forward_calls': 0})
