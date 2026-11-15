import hashlib
import json
from pathlib import Path
import time
import zipfile
import torch
from models import create_model, PINNED

ROOT=Path(__file__).resolve().parent


def main():
    torch.set_num_threads(1)
    torch.manual_seed(0)
    archive=Path('D:/FEDUBA_ITY92_HISTORY_ARCHIVE_REVIEW_20261103/archive.zip')
    assert hashlib.sha256(archive.read_bytes()).hexdigest()=='ac9408f9bec5ff55f980d179a32d28f5ba33b574cb377ff94145402a91a065f5'
    recovered=ROOT/'recovered'
    recovered.mkdir(exist_ok=False)
    with zipfile.ZipFile(archive) as z:
        for name,digest in PINNED.items():
            raw=z.read('FedUBA-code/models/'+name)
            assert hashlib.sha256(raw).hexdigest()==digest
            (recovered/name).write_bytes(raw)
    rows=[]
    for name,size,classes in [('PATHMNIST',28,9),('PATHMNIST_outter',28,8),('GTSRB',32,43),('GTSRB_outter',32,59)]:
        model=create_model(name,recovered).cpu().eval()
        x=torch.randn(2,3,size,size)
        with torch.inference_mode(): y=model(x)
        assert y.shape==(2,classes) and bool(torch.isfinite(y).all())
        state={k:v.clone() for k,v in model.state_dict().items()}
        model.load_state_dict(state,strict=True)
        with torch.inference_mode(): repeat=model(x)
        assert torch.equal(y,repeat)
        rows.append({'dataset':name,'input':[2,3,size,size],'output':list(y.shape),
                     'parameters':sum(v.numel() for v in model.parameters()),'strict_CPU_roundtrip_exact':True})
        del model,state,x,y,repeat
    assert not torch.cuda.is_initialized()
    with (ROOT/'RESULT.json').open('x',encoding='utf-8') as stream:
        json.dump({'state':'passed','models':rows,'sources':PINNED,'real_dataset_samples':0,
                   'optimizer_steps':0,'CUDA_initialized':False,'author_identity_certified':False,
                   'overall_paper_reproduced':False,'time':time.time()},stream,indent=2)


if __name__=='__main__':main()
