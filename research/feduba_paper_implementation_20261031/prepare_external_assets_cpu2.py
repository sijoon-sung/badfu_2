"""Finite CPU provenance/byte-disjointness preparation, never trains a model."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import hashlib
import io
import json
from pathlib import Path
import time
import traceback
import urllib.request
import zipfile
import numpy as np
from PIL import Image
import torch
from torchvision.datasets import CIFAR10
from runtime_common import ROOT, read, write, sha, save, freeze_check

OUT = ROOT / 'private_assets/external'


def download(url, name, expected=None):
    path = OUT / name
    partial = path.with_name(path.name + '.partial')
    assert not path.exists() and not partial.exists(), name
    request = urllib.request.Request(url, headers={'User-Agent': 'FedUBA-reproduction-source-audit/1.0'})
    with urllib.request.urlopen(request, timeout=60) as response, partial.open('xb') as stream:
        header = dict(response.headers.items())
        length = response.headers.get('Content-Length')
        downloaded = 0
        while True:
            block = response.read(1 << 20)
            if not block:
                break
            stream.write(block); downloaded += len(block)
            write(ROOT / 'ASSET_CPU2_STATE.json', {'state': 'downloading', 'pid': os.getpid(),
                  'file': name, 'downloaded_bytes': downloaded, 'updated_unix': time.time()})
        stream.flush(); os.fsync(stream.fileno())
    assert downloaded > 0 and (length is None or downloaded == int(length))
    data = partial.read_bytes() if expected else None
    digest = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() if expected else None
    receipt = {'url': url, 'bytes': downloaded, 'sha256': sha(partial), 'HTTP_headers': header,
               'Git_blob': digest, 'upstream_digest_preknown': bool(expected)}
    write(ROOT / ('ASSET_CPU2_DOWNLOAD_' + name.replace('.', '_') + '.json'), receipt)
    if expected:
        assert downloaded == expected['bytes'] and digest == expected['git_blob'], name
    os.rename(partial, path)
    return path, receipt


def main():
    freeze_check('ASSET_CPU2_FREEZE.json')
    assert 'torch.cuda.is_available' in read(ROOT / 'ASSET_FAILURE.json')['traceback']
    assert not OUT.exists()
    assert read(ROOT / 'CPU_VISIBILITY_DIAGNOSIS.json')['state'] == 'completed'
    with (ROOT / 'ASSET_CPU2_ONCE.json').open('x', encoding='utf-8') as stream:
        json.dump({'pid': os.getpid(), 'created_unix': time.time()}, stream)
    assert not torch.cuda.is_initialized()
    assert torch.zeros(1).device.type == 'cpu'
    torch.set_num_threads(1)
    OUT.mkdir(exist_ok=False)
    p = read(ROOT / 'ASSET_PROFILE.json')
    downloads = {}
    paths = {}
    for name, expected in p['cifar10_1_files'].items():
        url = ('https://raw.githubusercontent.com/modestyachts/CIFAR-10.1/' +
               p['cifar10_1_commit'] + '/datasets/' + name)
        paths[name], downloads[name] = download(url, name, expected)
    images = np.load(paths['cifar10.1_v6_data.npy'], allow_pickle=False)
    labels = np.load(paths['cifar10.1_v6_labels.npy'], allow_pickle=False)
    assert images.shape == (2000, 32, 32, 3) and images.dtype == np.uint8
    assert labels.shape == (2000,) and labels.dtype.kind in 'iu'
    assert np.bincount(labels, minlength=10).tolist() == [200] * 10
    target_ids = np.flatnonzero(labels == p['target_class']).tolist()
    assert len(target_ids) == 200
    data_root = read(ROOT / 'CLEAN_FL_PROFILE.json')['data_root']
    train, test = CIFAR10(data_root, train=True, download=False), CIFAR10(data_root, train=False, download=False)
    victim = {'train': {hashlib.sha256(x.tobytes()).hexdigest() for x in train.data},
              'test': {hashlib.sha256(x.tobytes()).hexdigest() for x in test.data}}
    external_hashes = [hashlib.sha256(x.tobytes()).hexdigest() for x in images]
    overlaps = {'CIFAR10_1_' + split: len(set(external_hashes) & hashes) for split, hashes in victim.items()}
    write(ROOT / 'ASSET_CPU2_OVERLAP_PROGRESS.json', {'overlaps': overlaps})
    assert not any(overlaps.values()), overlaps
    target = save(OUT / 'target_external.pt', {'images_HWC_uint8': torch.from_numpy(images[target_ids].copy()),
                  'labels_original': torch.from_numpy(labels[target_ids].astype(np.int64)),
                  'external_original_IDs': target_ids, 'target_class': p['target_class'],
                  'source_commit': p['cifar10_1_commit'], 'uses_victim_data': False})
    tiny_path, downloads['tiny-imagenet-200.zip'] = download(p['tiny_url'], 'tiny-imagenet-200.zip')
    tiny_images = np.empty((100000, 32, 32, 3), dtype=np.uint8)
    tiny_labels = np.empty(100000, dtype=np.int64)
    image_manifest, transformed_hashes = [], set()
    with zipfile.ZipFile(tiny_path) as archive:
        bad = archive.testzip()
        assert bad is None, bad
        wnids = sorted(archive.read('tiny-imagenet-200/wnids.txt').decode('ascii').splitlines())
        assert len(wnids) == len(set(wnids)) == 200
        names = sorted(name for name in archive.namelist()
                       if name.startswith('tiny-imagenet-200/train/') and '/images/' in name and name.endswith('.JPEG'))
        assert len(names) == 100000 and len(set(names)) == 100000
        mapping = {name: index for index, name in enumerate(wnids)}
        for index, name in enumerate(names):
            raw = archive.read(name)
            label = mapping[name.split('/')[2]]
            with Image.open(io.BytesIO(raw)) as image:
                assert image.size == (64, 64), name
                resized = np.asarray(image.convert('RGB').resize((32, 32), Image.Resampling.BILINEAR))
            tiny_images[index] = resized; tiny_labels[index] = label
            digest = hashlib.sha256(resized.tobytes()).hexdigest()
            transformed_hashes.add(digest)
            image_manifest.append({'member': name, 'class': label, 'original_sha256': hashlib.sha256(raw).hexdigest(),
                                   'resized_HWC_sha256': digest})
            if (index + 1) % 1000 == 0:
                write(ROOT / 'ASSET_CPU2_STATE.json', {'state': 'decoding_Tiny_train', 'pid': os.getpid(),
                      'decoded': index + 1, 'expected': 100000, 'updated_unix': time.time()})
    assert np.bincount(tiny_labels).tolist() == [500] * 200
    overlaps.update({'Tiny_resized_' + split: len(transformed_hashes & hashes) for split, hashes in victim.items()})
    write(ROOT / 'ASSET_CPU2_OVERLAP_PROGRESS.json', {'overlaps': overlaps})
    assert not any(overlaps.values()), overlaps
    manifest_path = OUT / 'Tiny_image_manifest.json'
    write(manifest_path, {'class_order': wnids, 'images': image_manifest})
    tiny = save(OUT / 'surrogate_tiny_train.pt', {'images_HWC_uint8': torch.from_numpy(tiny_images),
                'labels': torch.from_numpy(tiny_labels), 'class_order': wnids,
                'manifest_sha256': sha(manifest_path), 'uses_victim_data': False})
    result = {'state': 'passed', 'CPU_only': True, 'profile': p['id'], 'downloads': downloads,
              'target': target, 'surrogate': tiny, 'target_N': 200, 'target_class': 2,
              'Tiny_train_N': 100000, 'Tiny_classes': 200, 'Tiny_per_class': 500,
              'official_CIFAR_integrity_checked': True, 'exact_overlaps_with_victim': overlaps,
              'Tiny_ZIP_CRC_passed': True, 'Tiny_image_manifest_sha256': sha(manifest_path),
              'near_duplicate_or_semantic_disjointness_certified': False,
              'FedUBA_author_target_collection_identity_certified': False,
              'STG_FL_FU_training_executed': False, 'D08_D15_resolved': False,
              'source_hashes': read(ROOT / 'ASSET_CPU2_FREEZE.json')['files']}
    assert not torch.cuda.is_initialized()
    assert all(t.device.type == 'cpu' for t in [torch.from_numpy(images), torch.from_numpy(tiny_images)])
    write(ROOT / 'ASSET_CPU2_RESULT.json', result)
    write(ROOT / 'ASSET_CPU2_STATE.json', {'state': 'passed', 'pid': os.getpid(), 'updated_unix': time.time()})
    print(json.dumps({k: result[k] for k in ['state', 'CPU_only', 'target_N', 'Tiny_train_N', 'exact_overlaps_with_victim']}))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        write(ROOT / 'ASSET_CPU2_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
