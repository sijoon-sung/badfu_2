"""Seal a new review copy around an untouched completed export. No training."""
import json
from pathlib import Path
import shutil
import zipfile
from common import ROOT, read, sha, write
from review_guard import CASE, verify

EXPECTED_EXPORT = '372db7351f7a0cb68182a68d75c3f85a4ba6d96341fb4a75a82078fadd459562'
DEST = Path('D:/CHECKPOINTS_FOR_REVIEW/FUBA_reference_MNIST_DBA_s20261023_pre100_post_KD10')


def main():
    assert not DEST.exists(), 'Existing review copy must be preserved'
    assert DEST.resolve().parent == Path('D:/CHECKPOINTS_FOR_REVIEW').resolve()
    assert sha(ROOT / 'DELIVERY_MANIFEST.json') == EXPECTED_EXPORT
    assert read(ROOT / 'DELIVERY_SEAL.json')['manifest_sha256'] == EXPECTED_EXPORT
    export = read(ROOT / 'DELIVERY_MANIFEST.json')
    packet = ROOT / 'delivery_packet'
    for name, entry in export['files'].items():
        p = (packet / name).resolve()
        assert p.is_relative_to(packet.resolve()) and sha(p) == entry['sha256'] and p.stat().st_size == entry['bytes']
    shutil.copytree(packet, DEST)
    shutil.copy2(ROOT / 'DELIVERY_MANIFEST.json', DEST / 'SOURCE_EXPORT_MANIFEST.json')
    shutil.copy2(ROOT / 'DELIVERY_SEAL.json', DEST / 'SOURCE_EXPORT_SEAL.json')
    shutil.copy2(ROOT / 'review_guard.py', DEST / 'load_checkpoint.py')
    (DEST / 'README.md').write_text(
        '# FUBA MNIST/DBA diagnostic pair\n\n'
        f'Case: `{CASE}`; related cards R02/D08/D15/N02.\n\n'
        'Actual100R/800roles/67900 phase epochs and actual client4 history subtraction/KD10/470batches completed. '
        'Before CA99.11/ASR30.600487480611566; after CA99.08/ASR32.35098604032794. '
        'Both registered performance gates failed. Diagnostic use only; no detection/purification/history default approval.\n\n'
        'Bare model states: run/before.pt and run/after.pt (payload_key=null). '
        'Other selected payload keys and exact scope are in SCOPE.json and the manifests. '
        'Full100R/all intermediate phase tensors stay in D:/FUBA_REFERENCE_MNIST_DBA_20261031. '
        'This copy includes endpoints, KD10/optimizer/RNG, declared selected phase/round tensors and all logs/role JSON.\n\n'
        'The original export manifest/seal are preserved as SOURCE_EXPORT_MANIFEST.json/SOURCE_EXPORT_SEAL.json. '
        'DELIVERY_MANIFEST.json plus its external seal cover this additional review wrapper and loader. '
        'Verify the externally registered manifest SHA before any checkpoint load. Do not train into or automatically resume this copy.\n\n'
        'This is a declared interpretation of stcebra/FUBA, not ity207/FedUBA, not a successful paper reproduction. '
        'CIFAR/IBA failures and D08/D15 large benign non-IID counterexamples remain unresolved.\n',
        encoding='utf-8', newline='\n')
    files = {p.relative_to(DEST).as_posix(): {'sha256': sha(p), 'bytes': p.stat().st_size}
             for p in sorted(DEST.rglob('*')) if p.is_file()}
    manifest = {'schema': 'fuba-mnist-dba-review-v1', 'case_id': CASE, 'actual_pre_post_pair': True,
                'rounds': 100, 'KD_epochs': 10, 'KD_batches': 470, 'allowed_purposes': ['diagnostic'],
                'files': files, 'model_payloads': export['model_payloads'],
                'original_export': {'manifest_sha256': EXPECTED_EXPORT,
                                    'seal_sha256': sha(ROOT / 'DELIVERY_SEAL.json')},
                'full_raw_scope': 'All original100R phase tensors on DISLAB; selected tensors and all logs in this review copy.'}
    write(DEST / 'DELIVERY_MANIFEST.json', manifest)
    digest = sha(DEST / 'DELIVERY_MANIFEST.json')
    write(DEST / 'DELIVERY_SEAL.json', {'schema': 'external-manifest-sha256-v1', 'manifest_sha256': digest})
    verify(DEST, digest)
    archive = ROOT / 'REVIEW_DELIVERY.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        for p in sorted(DEST.rglob('*')):
            if p.is_file():
                z.write(p, p.relative_to(DEST).as_posix())
    receipt = {'state': 'remote_review_sealed', 'case_id': CASE, 'remote_root': str(DEST),
               'files': len(files) + 2, 'manifest_sha256': digest,
               'seal_sha256': sha(DEST / 'DELIVERY_SEAL.json'), 'archive_sha256': sha(archive),
               'archive_bytes': archive.stat().st_size, 'local_transfer_complete': False}
    write(ROOT / 'REMOTE_REVIEW_RECEIPT.json', receipt)
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
