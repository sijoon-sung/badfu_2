"""Resolve an explicit audited case and purpose; never guess a checkpoint."""
import argparse
import hashlib
import json
import importlib.util
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent


def main():
    sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    sys.stderr.reconfigure(encoding='utf-8',errors='replace')
    p=argparse.ArgumentParser()
    p.add_argument('case_id')
    p.add_argument('--purpose',required=True,choices=['retrain_activation','global_history','client_history','purification_pilot','approximate_FU','diagnostic'])
    p.add_argument('--location',choices=['dislab','local'],default='dislab',help='Use the registered independent local copy when available')
    a=p.parse_args()
    cat=json.loads((HERE/'catalog.json').read_text(encoding='utf-8'))
    if hashlib.sha256((HERE/'audit/AUDIT.json').read_bytes()).hexdigest()!=cat['audit_sha256']:
        raise SystemExit('감사 파일이 목록의 근거와 다릅니다. 목록을 다시 생성하세요.')
    for entry in cat.get('supplemental_audits',[]):
        path=(HERE/entry['path']).resolve()
        if not path.is_relative_to((HERE/'audit').resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
            raise SystemExit('추가 감사 파일이 목록의 근거와 다릅니다.')
    case=next((c for c in cat['cases'] if c['id']==a.case_id),None)
    if case is None: raise SystemExit('등록되지 않은 궤적 ID입니다. README의 고정 ID를 사용하세요.')
    if a.purpose not in case['allowed_purposes']:
        raise SystemExit('이 궤적은 요청한 용도로 검증되지 않았습니다: '+a.purpose)
    selected=case
    if a.location=='local':
        if 'local_copy' not in case: raise SystemExit('이 사례에는 등록된 로컬 모델 사본이 없습니다.')
        selected=case['local_copy']
    inputs=selected['server_inputs']
    guard=selected.get('checkpoint_guard')
    guard_state=None
    if guard:
        manifest=Path(guard['manifest_path'])
        if manifest.exists():
            if hashlib.sha256(manifest.read_bytes()).hexdigest()!=guard['manifest_sha256']:
                raise SystemExit('확정 모델 목록의 SHA256이 등록 증거와 다릅니다.')
            if hashlib.sha256(Path(guard['seal_path']).read_bytes()).hexdigest()!=guard['seal_sha256']:
                raise SystemExit('확정 모델 봉인의 SHA256이 등록 증거와 다릅니다.')
            # Check the loader itself against the externally anchored manifest
            # before executing it. Then validate every declared file, no torch load.
            loader=Path(guard['loader_path'])
            metadata=json.loads(manifest.read_text(encoding='utf-8'))
            if hashlib.sha256(loader.read_bytes()).hexdigest()!=metadata['files'][loader.name]['sha256']:
                raise SystemExit('확정 모델 로더가 등록 증거와 다릅니다.')
            spec=importlib.util.spec_from_file_location('confirmed_snapshot_guard',loader)
            sys.dont_write_bytecode=True
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            module.verify(manifest.parent,guard['manifest_sha256'])
            guard_state='all_snapshot_files_verified_on_this_host'
        else:
            if a.location=='local': raise SystemExit('등록된 로컬 모델 폴더가 없습니다.')
            guard_state='verify_on_DISLAB_before_consumption'
    if a.purpose in ['global_history','client_history']:
        inputs={k:v for k,v in inputs.items() if k in ['pre','clean_pre']}
    # Oracle metrics/targets are intentionally excluded from this output.
    result={'case_id':case['id'],'purpose':a.purpose,'post_type':case['post_type'],
        'server_inputs':inputs,'source_root':selected.get('root',case['source_root']),
        'consumption_requirement':'Verify checkpoint SHA256 before torch.load and extract the declared payload_key. Do not pass evaluator-only metadata to server methods.'}
    if guard: result.update(checkpoint_guard=guard,guard_state=guard_state)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
