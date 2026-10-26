"""Collect navigation and source hashes without reading or modifying tensors."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1]
registry = json.loads((ROOT / 'research/experiment_registry.json').read_text(encoding='utf-8-sig'))
spec = importlib.util.spec_from_file_location('index_builder', ROOT / 'research/index_tools/rebuild_index.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
inventory = module.collect_inventory(registry['entries'])
sources = sorted({s for e in registry['entries'] for s in e['sources']})
manifest = []
for rel in sources:
    p = ROOT / rel
    manifest.append({'path': rel, 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
(OUT / 'source_manifest.json').write_text(json.dumps({'as_of': '2026-10-26 KST', 'sources': manifest}, ensure_ascii=False, indent=2), encoding='utf-8')
(OUT / 'folder_coverage.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'cards':len(registry['entries']), 'sources':len(sources), 'folders':len(inventory), 'unreviewed':sum(not x['related_cards'] for x in inventory)},ensure_ascii=False))
for x in inventory:
    if not x['related_cards']:
        print(x['path'] + ' | ' + ' ; '.join(x['top_level_documents']))
