"""Full finite-treatment packet, including every phase and mask; no control rerun."""
import json
import zipfile
from run import ROOT,read,sha,write,frozen


def main():
    frozen();assert read(ROOT/'STATE.json')['state']=='complete'
    for name,digest in read(ROOT/'EXPORT_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest
    for name in ['CPU_AUDIT.json','INDEPENDENT_RESULT.json']:
        assert read(ROOT/name)['state']=='passed'
    out=ROOT/'delivery';out.mkdir(exist_ok=False)
    files={p.relative_to(ROOT).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size}
           for p in sorted(ROOT.rglob('*')) if p.is_file() and not p.is_relative_to(out)
           and '__pycache__' not in p.parts and p.suffix!='.tmp'}
    manifest={'schema':'fuba-mnist-optimizer-diagnostic-packet-v1','remote_root':str(ROOT),'files':files,
              'scope':'Two new embedding phases of MNIST actual-FU round100/client1, original sealed inputs, fixed seven peer submissions, exact aggregation and four independent evaluations. No new100R or actual FU execution.',
              'performance_supported':read(ROOT/'RESULT.json')['hypothesis_supported'],
              'full_paper_reproduced':False,'unlearning_executed':False}
    assert 'REVIEW_MANIFEST.json' not in files
    write('delivery/REVIEW_MANIFEST.json',manifest)
    archive=out/'FUBA_MNIST_OPTIMIZER_ISOLATION_20261115.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for name,item in files.items():
            assert sha(ROOT/name)==item['sha256'];z.write(ROOT/name,name)
        z.write(out/'REVIEW_MANIFEST.json','REVIEW_MANIFEST.json')
    seal={'manifest_sha256':sha(out/'REVIEW_MANIFEST.json'),'archive_sha256':sha(archive),
          'archive_bytes':archive.stat().st_size,'files':len(files),'full_paper_reproduced':False}
    write('delivery/SEAL.json',seal);print(json.dumps(seal),flush=True)


if __name__=='__main__':main()
