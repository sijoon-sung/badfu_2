"""Concurrent source-only review is permitted while the foundation trains; model0."""
import ast
import json
from pathlib import Path
import sys
import traceback
from clean_delivery_binding import ROOT,read,sha,source_profile
def main():
    p=source_profile();assert not (ROOT/'SOURCE_REVIEW_RESULT.json').exists()
    for file in ROOT.glob('*.py'):ast.parse(file.read_text(encoding='utf-8'))
    for n,d in p['reused_helpers'].items():
        source=Path(p['foundation_root'])/n if n!='review_loader.py' else Path('D:/FEDUBA_PAPER_IMPLEMENTATION_20261031/review_loader.py')
        assert sha(ROOT/n)==sha(source)==d,n
    assert p['normal_case_id']=='feduba.public_fixed10.cifar10.cleanfl20.s42.20261103'
    assert sha(Path(p['foundation_root'])/'SOURCE_FREEZE.json')==p['foundation_source_freeze_sha256']
    assert sha(Path(p['foundation_root'])/'RUN_FREEZE.json')==p['foundation_run_freeze_sha256']
    catalogue=read(Path(p['catalog_root'])/'catalog.json')
    assert not any(c['id']==p['normal_case_id'] for c in catalogue['cases'])
    assert 'torch' not in sys.modules
    with (ROOT/'SOURCE_REVIEW_RESULT.json').open('x',encoding='utf-8') as f:
        json.dump({'state':'passed_fixed10_normal_delivery_source_only','source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),
            'python_AST_files':len(list(ROOT.glob('*.py'))),'unchanged_helpers':list(p['reused_helpers']),
            'foundation_source_and_run_freezes_exact':True,'new_case_not_registered_yet':True,
            'catalogue_sha256':sha(Path(p['catalog_root'])/'catalog.json'),'model_loads':0,'model_forwards':0,
            'actual_export_or_registration_started':False},f,indent=2)
if __name__=='__main__':
    try:main()
    except BaseException:
        with (ROOT/'SOURCE_REVIEW_FAILURE.json').open('x',encoding='utf-8') as f:json.dump({'state':'failed_preserved','traceback':traceback.format_exc()},f,indent=2)
        raise
