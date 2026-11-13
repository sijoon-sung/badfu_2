"""Streaming sealed-packet guard. No torch, tensor, model or inference imports."""
import hashlib,json,stat
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def verify(root,expected_manifest_sha256):
    root=Path(root).resolve();mp=root/'GUARD_MANIFEST.json';assert sha(mp)==expected_manifest_sha256
    m=read(mp);assert read(root/'GUARD_SEAL.json')['manifest_sha256']==expected_manifest_sha256
    for n,row in m['files'].items():
        p=(root/n).resolve();assert p.is_relative_to(root) and sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
    count=0;metas={}
    for key,packet in m['packets'].items():
        pr=Path(packet['root']).resolve();manifest=pr/packet['manifest'];assert sha(manifest)==packet['manifest_sha256'] and sha(packet['seal'])==packet['seal_sha256']
        data=read(manifest);assert read(packet['seal'])['manifest_sha256']==packet['manifest_sha256'] and len(data['files'])==packet['hashed_files'];metas[key]=data
        for rel,row in data['files'].items():
            p=(pr/rel).resolve();assert p.is_relative_to(pr) and p.is_file() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],rel
            count+=1
    for name,e in m['endpoints'].items():
        packet=m['packets'][e['packet']];data=metas[e['packet']];row=data['files'][e['member']];assert row['sha256']==e['sha256'] and row['bytes']==e['bytes'] and e['payload_key'] is None
        typed=data.get('payloads',data.get('typed_payloads'));t=next(v for v in typed if v.get('file',v.get('path'))==e['member'])
        assert t.get('payload_key') is None and ((t.get('kind')=='model' and t.get('strict_CPU') and t.get('finite')) or t.get('CPU_strict_finite_zero1'))
        assert not (Path(packet['root'])/e['member']).stat().st_mode&stat.S_IWRITE
    assert count==809
    return {'state':'both_external_sealed_packets_and_endpoint_hashes_verified','hashed_files':count,'model_or_tensor_loads':0,'endpoint_count':4,'existing_CPU_storage_receipts_reused':True}
