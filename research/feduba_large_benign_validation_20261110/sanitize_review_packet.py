"""Byte-only local delivery formatting. Original archive is never modified."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'remote_results'


def sha(value):
    return hashlib.sha256(value).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def strip_commands(value):
    count = 0
    if isinstance(value, dict):
        if 'CommandLine' in value:
            raw = value.pop('CommandLine')
            assert isinstance(raw, str)
            value['command_sha256'] = sha(raw.encode('utf-8'))
            value['raw_command_bytes_removed'] = len(raw.encode('utf-8'))
            count += 1
        for v in value.values():
            count += strip_commands(v)
    elif isinstance(value, list):
        for v in value:
            count += strip_commands(v)
    return count


def main():
    seal = json.loads((OUT / 'REVIEW_SEAL.json').read_bytes())
    original = OUT / seal['file']
    # The original full archive/file-byte verification has already passed.
    passed = json.loads((ROOT / 'LOCAL_DELIVERY_VERIFIED.json').read_bytes())
    assert passed['state'] == 'passed' and passed['sha256'] == seal['sha256']
    old_manifest = json.loads((OUT / 'REVIEW_MANIFEST.json').read_bytes())
    archive = OUT / 'D21_REVIEW_PACKET_SANITIZED.zip'
    changes = []
    files = {}
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=2) as target:
        def add(name, raw):
            assert name not in files
            target.writestr(name, raw)
            files[name] = dict(sha256=sha(raw), bytes=len(raw))

        for name, expected in old_manifest['files'].items():
            raw = source.read(name)
            assert sha(raw) == expected['sha256'] and len(raw) == expected['bytes']
            if name.endswith('.json'):
                value = json.loads(raw)
                count = strip_commands(value)
                if count:
                    clean = encode(value)
                    changes.append(dict(path=name, original_sha256=sha(raw), sanitized_sha256=sha(clean), removed_observations=count))
                    raw = clean
                    dest = ROOT / 'publication/sanitized_observations' / name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(raw)
            add(name, raw)
        for name in ['PACKET_FORMATTING_PROTOCOL.txt', 'sanitize_review_packet.py']:
            add('delivery_formatting/' + name, (ROOT / name).read_bytes())
        typed = [n for n in files if n.endswith('.pt')]
        assert len(typed) == old_manifest['typed_payloads'] == 17
        assert all(files[n] == old_manifest['files'][n] for n in typed)
        receipt = dict(state='passed', original_archive_seal=seal,
                       original_manifest_sha256=sha((OUT / 'REVIEW_MANIFEST.json').read_bytes()),
                       changes=changes, removed_observations=sum(x['removed_observations'] for x in changes),
                       all17_typed_payloads_byte_identical=True,
                       model_loads=0, model_forward_calls=0, original_archive_preserved=True)
        add('delivery_formatting/FORMATTING_RECEIPT.json', encode(receipt))
        scope = dict(old_manifest['scope'])
        scope['unrelated_raw_command_arguments'] = 'removed; original hashes/counts retained'
        manifest = dict(scope=scope, files=files, typed_payloads=17)
        manifest_raw = encode(manifest)
        target.writestr('REVIEW_MANIFEST.json', manifest_raw)
    with archive.open('rb') as f:
        h = hashlib.file_digest(f, 'sha256').hexdigest()
    (OUT / 'REVIEW_SANITIZED_MANIFEST.json').write_bytes(manifest_raw)
    new_seal = dict(file=archive.name, sha256=h, bytes=archive.stat().st_size,
                    files=len(files), typed_payloads=17, model_forward_calls=0,
                    original_archive_sha256=seal['sha256'])
    (OUT / 'REVIEW_SANITIZED_SEAL.json').write_bytes(encode(new_seal))
    (ROOT / 'FORMATTING_RECEIPT.json').write_bytes(encode(receipt))
    print(json.dumps(dict(seal=new_seal, removed_observations=receipt['removed_observations'])))


if __name__ == '__main__':
    main()
