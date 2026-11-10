"""Reuse valid selection metadata and six unaffected baseline arms; no catalogue edit."""
import json
from pathlib import Path
from checkpoint_guard import sha

ROOT = Path(__file__).resolve().parent


def main():
    (ROOT/'PREPARE_ONCE').open('x').write('v2 binding-only\n')
    binding = json.loads((ROOT/'REUSE_BINDING.json').read_text())
    source = Path(binding['source_root'])
    assert sha('D:/TRAJECTORY_CATALOG_20261023/catalog.json') == binding['catalog_sha256']
    original = json.loads((source/'PROFILE.json').read_text())
    current = json.loads((ROOT/'PROFILE.json').read_text())
    for key in original:
        if key not in ('memory_fraction','admission'): assert current[key] == original[key]
    for name, digest in binding['files'].items():
        assert sha(source/name) == digest, name
        if name == 'PROFILE.json': continue
        target = ROOT/name; target.parent.mkdir(parents=True, exist_ok=True)
        assert not target.exists()
        target.write_bytes((source/name).read_bytes())
    inputs = json.loads((ROOT/'INPUTS.json').read_text())
    for pair in inputs['cases']:
        for k in ('pre','post'): assert sha(pair[k]['path']) == pair[k]['sha256']
    print('v2 metadata and 6 unaffected baseline arms bound; catalogue/model writes zero', flush=True)


if __name__ == '__main__': main()
