"""New CPU-only stage wiring + fresh external surrogate initial, not a rerun."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import torch
import model_reference
from stg_training import ExternalImages
from runtime_common import ROOT, read, write, sha, save, freeze_check

freeze_check('STG_FREEZE.json')
assert not (ROOT / 'STG_READY.json').exists()
assert not torch.cuda.is_initialized()
torch.set_num_threads(1)
p = read(ROOT / 'STG_LAUNCH_PROFILE.json')
asset = read(ROOT / 'ASSET_CPU2_RESULT.json')
assert asset['state'] == 'passed' and read(ROOT / 'STG_SGD_CPU_RESULT.json')['state'] == 'passed'
for name, digest in asset['source_hashes'].items():
    assert sha(ROOT / name) == digest, name
for key in ['target', 'surrogate']:
    meta = asset[key]
    assert sha(ROOT / meta['path']) == meta['sha256']
    assert (ROOT / meta['path']).stat().st_size == meta['bytes']
tiny = torch.load(ROOT / asset['surrogate']['path'], map_location='cpu', weights_only=True)
target = torch.load(ROOT / asset['target']['path'], map_location='cpu', weights_only=True)
assert tiny['images_HWC_uint8'].shape == (100000, 32, 32, 3)
assert torch.bincount(tiny['labels'], minlength=200).tolist() == [500] * 200
assert target['images_HWC_uint8'].shape == (200, 32, 32, 3)
assert torch.equal(target['labels_original'], torch.full((200,), 2))
assert len(target['external_original_IDs']) == len(set(target['external_original_IDs'])) == 200
torch.manual_seed(p['seed'])
model = model_reference.ResNet18_201().cpu().eval()
fresh = save(ROOT / 'private_assets/stg_initial.pt', {'model': model.state_dict(), 'torch_CPU_rng': torch.get_rng_state(), 'seed': p['seed']})
fresh['payload_key'] = 'model'
with torch.inference_mode():
    x = torch.stack([ExternalImages(tiny['images_HWC_uint8'][:2], tiny['labels'][:2], augment=False)[i][0] for i in range(2)])
    logits = model(x)
    assert logits.shape == (2, 201) and bool(torch.isfinite(logits).all())
assert not torch.cuda.is_initialized()
write(ROOT / 'STG_READY.json', {'state': 'passed', 'profile': p['id'], 'fresh_initial': fresh,
      'CPU_only': True, 'Tiny_N': 100000, 'target_N': 200, 'asset_result_sha256': sha(ROOT / 'ASSET_CPU2_RESULT.json'),
      'target_external_original_IDs': target['external_original_IDs'],
      'source_hashes': read(ROOT / 'STG_FREEZE.json')['files'], 'victim_model_used': False})
print('New STG stage wiring / source assets / fresh seed0 surrogate initial verified on CPU')
