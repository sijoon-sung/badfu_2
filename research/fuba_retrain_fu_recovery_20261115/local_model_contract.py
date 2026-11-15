"""Small transfer-portability check: strict CPU loads and synthetic finite forwards only."""
import importlib.util
import json
import math
from pathlib import Path
import torch
from verify_payload import verify


def finite(v):
    if isinstance(v,torch.Tensor):assert v.device.type=='cpu' and bool(torch.isfinite(v).all())
    elif isinstance(v,dict):
        for x in v.values():finite(x)
    elif isinstance(v,(tuple,list)):
        for x in v:finite(x)
    elif isinstance(v,float):assert math.isfinite(v)


def main():
    torch.set_num_threads(1);root=Path(__file__).resolve().parent;payload=root/'delivery/payload'
    seal=json.loads((root/'delivery/SEAL.json').read_text());verify(payload,seal['manifest_sha256'])
    spec=importlib.util.spec_from_file_location('delivered_author_net',payload/'inputs/author_model.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);net=module.Net().eval()
    manifest=json.loads((payload/'REVIEW_MANIFEST.json').read_text());files=states=0
    for name in manifest['files']:
        if not name.endswith('.pt'):continue
        value=torch.load(payload/name,map_location='cpu',weights_only=True);finite(value)
        if name in ['inputs/initial.pt','inputs/before.pt','after.pt']:models=[value]
        elif name.startswith('rounds/'):models=[value['incoming'],value['after'],*value['submitted']]
        elif name.startswith('phases/'):models=[value['model']]
        else:raise ValueError('Undeclared payload format: '+name)
        for model in models:
            net.load_state_dict(model,strict=True)
            with torch.inference_mode():assert bool(torch.isfinite(net(torch.zeros(1,1,28,28))).all())
            states+=1
        files+=1
    result={'state':'passed','model_files':files,'strict_model_states':states,'torch_version':torch.__version__,
            'CUDA_initialized':torch.cuda.is_initialized(),'real_data_inference':0,
            'only_synthetic_finite_forwards':True,'full_paper_reproduced':False}
    with (root/'LOCAL_MODEL_CONTRACT.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
