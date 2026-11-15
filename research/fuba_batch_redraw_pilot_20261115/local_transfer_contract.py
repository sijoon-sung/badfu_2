"""Light local portability check of input/first/last round; full audit ran on DISLAB."""
import importlib.util
import json
from pathlib import Path
import torch
from receive_packet import verify

ROOT=Path(__file__).resolve().parent


def main():
    torch.set_num_threads(1);payload=ROOT/'delivery/payload'
    seal=json.loads((ROOT/'delivery/SEAL.json').read_text());verify(payload,seal['manifest_sha256'])
    spec=importlib.util.spec_from_file_location('delivered_Net',payload/'inputs/author_model.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);net=module.Net().eval()
    states=0
    for name in ['inputs/round0020.pt','rounds/round0021.pt','rounds/round0030.pt']:
        bundle=torch.load(payload/name,map_location='cpu',weights_only=True)
        models=[bundle['after']] if name.startswith('inputs/') else [bundle['incoming'],bundle['after'],*bundle['submitted']]
        for model in models:
            assert all(v.device.type=='cpu' and bool(torch.isfinite(v).all()) for v in model.values())
            net.load_state_dict(model,strict=True)
            with torch.inference_mode():assert bool(torch.isfinite(net(torch.zeros(1,1,28,28))).all())
            states+=1
    result={'state':'passed','round_bundles':3,'strict_CPU_model_states':states,
            'real_data_inference':0,'CUDA_initialized':torch.cuda.is_initialized(),
            'full_phase_CPU_audit_location':'DISLAB','torch_version':torch.__version__}
    with (ROOT/'LOCAL_MODEL_CONTRACT.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
