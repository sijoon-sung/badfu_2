"""R02/D08/D15/N02: input provenance, not an attack detector or new training."""
import gzip
import hashlib
import json
from pathlib import Path
import torch
import torchvision
from torchvision.datasets import MNIST
from study_common import ROOT, read, sha, write

assert not (ROOT / 'DATASET_AUDIT.json').exists()
p = read(Path(read(ROOT / 'PREPARED_RECOVERY.json')['seeds'][0]['root']) / 'PROFILE.json')
raw = Path(p['data_root']) / 'MNIST/raw'
rows = []
for name, official_md5 in MNIST.resources:
    compressed, unpacked = raw / name, raw / name.removesuffix('.gz')
    # Stop on missing/mismatched public source rather than downloading/changing data.
    assert compressed.is_file() and unpacked.is_file(), name
    data = compressed.read_bytes()
    assert hashlib.md5(data).hexdigest() == official_md5, name
    assert gzip.decompress(data) == unpacked.read_bytes(), name
    rows.append({'resource': name, 'official_torchvision_MD5': official_md5,
                 'compressed_sha256': sha(compressed), 'uncompressed_sha256': sha(unpacked)})
train, test = [MNIST(p['data_root'], train=v, download=False) for v in [True, False]]
assert (len(train), len(test)) == (60000, 10000)
assert int((test.targets != p['target']).sum()) == 9026
write(ROOT / 'DATASET_AUDIT.json', {'state': 'passed', 'CPU_only': True,
      'resources_match_installed_torchvision_official_MD5': True, 'decompressed_bytes_exact': True,
      'torchvision_version': torchvision.__version__, 'dataset_root': p['data_root'], 'resources': rows,
      'train_N': 60000, 'test_N': 10000, 'non_target_test_N': 9026,
      'source_sha256': sha(Path(__file__)), 'data_modified_or_downloaded': False,
      'historical_baseline_data_byte_identity_proved': False, 'D08_D15_unresolved': True})
print(json.dumps({'state': 'passed', 'official_resource_count': len(rows), 'CPU_only': True}))
