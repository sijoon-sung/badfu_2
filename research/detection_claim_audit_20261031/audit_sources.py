"""Audit downloaded upstream bytes and AST imports without executing upstream code."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def audit(source_dir):
    manifest = json.loads((HERE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    rows = []
    for entry in manifest['ity207/FedUBA']['files']:
        data = (source_dir/entry['path']).read_bytes()
        blob = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        assert blob == entry['git_blob_sha'], entry['path']
        imports = []
        if entry['path'].endswith('.py'):
            tree = ast.parse(data.decode('utf-8'), filename=entry['path'])
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    imports.append(dict(module=node.module, line=node.lineno))
        rows.append(dict(path=entry['path'], git_blob_sha=blob, imports=imports))
    project_modules = {Path(e['path']).stem for e in rows}
    required = sorted({i['module'].split('.')[0] for e in rows for i in e['imports']
                       if i['module'] and i['module'].split('.')[0] in {'models','utils'}})
    absent = [name for name in required if name not in project_modules
              and not (source_dir/name).exists()]
    assert absent == ['models','utils']
    return dict(state='static_audit_completed', upstream_files_verified=len(rows),
                repository='ity207/FedUBA', commit=manifest['ity207/FedUBA']['commit'],
                missing_project_modules=absent, parsed_without_import=True,
                upstream_code_executed=False, runtime_reproduction='not_established', files=rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-dir', type=Path, required=True)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    result = audit(args.source_dir)
    path = HERE/'SOURCE_AUDIT.json'
    if args.check:
        assert json.loads(path.read_text(encoding='utf-8')) == result
    else:
        with path.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='files'}))

if __name__ == '__main__':
    main()
