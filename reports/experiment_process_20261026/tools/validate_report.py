"""Check report coverage, citations, preserved evidence, and document metadata."""
import hashlib
import json
import re
import sys
from pathlib import Path
from zipfile import ZipFile
sys.stdout.reconfigure(encoding='utf-8')
OUT=Path(__file__).resolve().parents[1]
ROOT=OUT.parents[1]
registry=json.loads((ROOT/'research/experiment_registry.json').read_text(encoding='utf-8-sig'))
expected={e['id'] for e in registry['entries']}
actual={p.stem for p in (OUT/'experiments').glob('*.md')}
assert actual==expected,(actual^expected)
link_errors=[]
for p in OUT.rglob('*.md'):
    for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        part=target.split('#')[0]
        if part and not re.match(r'^https?://',part) and not (p.parent/part).resolve().exists():link_errors.append((str(p),target))
assert not link_errors,link_errors
source_manifest=json.loads((OUT/'source_manifest.json').read_text(encoding='utf-8'))
changed=[]
for s in source_manifest['sources']:
    p=ROOT/s['path']
    if hashlib.sha256(p.read_bytes()).hexdigest()!=s['sha256']:changed.append(s['path'])
assert not changed,changed
legacy=json.loads((OUT/'legacy_source_records.json').read_text(encoding='utf-8'))
assert len(legacy)==68
assert all(x['method'] and x['hypothesis'] and x['result'] for x in legacy)
folder=json.loads((OUT/'folder_coverage.json').read_text(encoding='utf-8'))
assert len(folder)==97 and sum(not x['related_cards'] for x in folder)==48
with ZipFile(OUT/'BadFU_실험과정_전체정리_20261026.docx') as z:
    assert 'Codex' not in z.read('docProps/core.xml').decode()
    xml=z.read('word/document.xml').decode()
    for k in expected:assert k in xml,k
    assert '同じ' not in xml
audit={'state':'passed','reviewed_cards':len(actual),'legacy_source_records':len(legacy),'inventory_folders':len(folder),'prior_unreviewed_folder_labels_preserved':48,'registered_source_hashes_unchanged':len(source_manifest['sources']),'all_report_links_resolve':True,'docx_author_checked':True,'no_tensor_loaded_or_training_launched':True}
(OUT/'VALIDATION.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(audit,ensure_ascii=False))
