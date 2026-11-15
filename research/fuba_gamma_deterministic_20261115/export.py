"""One-time full packet of the new bounded run, after independent audits."""
import json
import zipfile
from pathlib import Path
from run import ROOT, read, sha, write, frozen


def main():
    frozen()
    assert read(ROOT/'STATE.json')['state']=='complete'
    assert read(ROOT/'CPU_AUDIT.json')['state']=='passed'
    assert read(ROOT/'INDEPENDENT_RESULT.json')['state']=='passed'
    assert read(ROOT/'NUMERICAL_CONTROL.json')['state']=='exact'
    assert read(ROOT/'PREFIX_AUDIT.json')['state']=='passed'
    out=ROOT/'delivery'
    out.mkdir(exist_ok=False)
    files={p.relative_to(ROOT).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size}
           for p in sorted(ROOT.rglob('*')) if p.is_file()
           and not p.is_relative_to(out) and '__pycache__' not in p.parts and p.suffix!='.tmp'}
    manifest={'schema':'fuba-bounded-full-packet-v1','remote_root':str(ROOT),'files':files,
              'scope':'All files of new local/global rounds21-30 and exact incoming20; no original1-19 or FU',
              'performance_supported':read(ROOT/'RESULT.json')['hypothesis_supported'],
              'full_paper_reproduced':False,'unlearning_executed':False}
    write(out/'MANIFEST.json',manifest,True)
    archive=out/'FUBA_GAMMA_DETERMINISTIC_20261115.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for name,item in files.items():
            assert sha(ROOT/name)==item['sha256'],name
            z.write(ROOT/name,name)
        z.write(out/'MANIFEST.json','MANIFEST.json')
    seal={'manifest_sha256':sha(out/'MANIFEST.json'),'archive_sha256':sha(archive),
          'archive_bytes':archive.stat().st_size,'files':len(files),'full_paper_reproduced':False}
    write(out/'SEAL.json',seal,True)
    print(json.dumps(seal),flush=True)


if __name__=='__main__':main()
