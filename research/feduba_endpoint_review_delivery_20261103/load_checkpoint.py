"""Hash guard and explicit CPU state reader for a bounded diagnostic packet."""
import hashlib,json
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def verify(root,expected_manifest_sha256):
    root=Path(root).resolve();manifest=root/'ENDPOINT_MANIFEST.json'
    assert sha(manifest)==expected_manifest_sha256
    m=read(manifest);assert m['state']=='sealed_four_diagnostic_endpoints_and_scalar_FU_epoch_logs'
    assert read(root.with_name(root.name+'_SEAL.json'))['manifest_sha256']==expected_manifest_sha256
    for rel,row in m['files'].items():
        p=(root/rel).resolve();assert p.is_relative_to(root) and p.is_file() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],rel
    assert set(m['models'])=={'pre','benign','minus','plus'}
    assert {rel for rel in m['files'] if rel.endswith('.pt')}=={v['file'] for v in m['models'].values()}
    for v in m['models'].values():
        row=m['files'][v['file']];assert row['sha256']==v['sha256'] and row['bytes']==44770315 and v['payload_key'] is None
    assert m['new_tensor_loads']==0 and m['new_CPU_model_checks']==0
    return {'state':'endpoint_packet_hashes_verified_only','files':len(m['files']),'model_files':4,'new_model_loads':0,'origin_CPU_receipts_reused':True,'local_CPU_or_delivery_success_implied':False}
def load_checkpoint(root,name,expected_manifest_sha256):
    verify(root,expected_manifest_sha256)
    m=read(Path(root)/'ENDPOINT_MANIFEST.json');assert name in m['models'];meta=m['models'][name]
    import torch
    return torch.load(Path(root)/meta['file'],map_location='cpu',weights_only=True)
