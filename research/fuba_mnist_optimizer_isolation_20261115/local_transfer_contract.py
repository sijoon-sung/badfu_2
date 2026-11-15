"""Light portability check; all actual-data inference and full audits were remote."""
import importlib.util
import json
from pathlib import Path
import torch
from receive_packet import verify

ROOT=Path(__file__).resolve().parent


def main():
    torch.set_num_threads(1);p=ROOT/'delivery/payload';seal=json.loads((ROOT/'delivery/SEAL.json').read_text())
    verify(p,seal['manifest_sha256'])
    spec=importlib.util.spec_from_file_location('delivered_Net',p/'inputs/author_model.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    net=m.Net().eval();items=[('inputs/round0100.pt','after')]
    for arm in ['algorithm_sgd','experimental_adam']:items.extend([(arm+'/phase03.pt','model'),(arm+'/aggregate.pt','after')])
    for name,key in items:
        state=torch.load(p/name,map_location='cpu',weights_only=True)[key]
        assert all(bool(torch.isfinite(v).all()) for v in state.values());net.load_state_dict(state,strict=True)
        with torch.inference_mode():assert bool(torch.isfinite(net(torch.zeros(1,1,28,28))).all())
    result={'state':'passed','strict_CPU_model_states':len(items),'real_data_inference':0,
        'CUDA_initialized':torch.cuda.is_initialized(),'torch_version':torch.__version__}
    with (ROOT/'LOCAL_MODEL_CONTRACT.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
