"""New pure CPU synthetic operator contract, independently indexed NumPy reference."""
import hashlib,json,os,sys,time
from pathlib import Path
import numpy as np
import torch
from postonly_inputs import switch_median,resize_aa,apply,is_identity,metrics,THRESHOLDS,SIZES
r=Path(__file__).resolve().parent;OUT=r/'POST_ONLY_INPUT_CONTRACT.json'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert not OUT.exists();torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
    freeze=json.loads((r/'POST_ONLY_INPUT_PREPARATION_FREEZE.json').read_text())
    for n,h in freeze['files'].items():assert sha(r/n)==h,n
    raw=torch.rand((2,3,32,32),generator=torch.Generator().manual_seed(20261101+4100))
    a=raw.numpy();p=np.pad(a,((0,0),(0,0),(1,1),(1,1)),mode='reflect');reference=np.empty_like(a)
    for n in range(2):
        for c in range(3):
            for i in range(32):
                for j in range(32):
                    values=[p[n,c,i+u,j+v] for u in range(3) for v in range(3) if (u,v)!=(1,1)]
                    values.sort();median=np.float32((values[3]+values[4])*np.float32(.5))
                    reference[n,c,i,j]=median if abs(a[n,c,i,j]-median)>np.float32(.2) else a[n,c,i,j]
    calc=switch_median(raw,.2);assert np.array_equal(calc.numpy(),reference)
    constant=torch.full_like(raw,.25)
    for tau in THRESHOLDS:assert torch.equal(switch_median(constant,tau),constant)
    checker=((torch.arange(32)[:,None]+torch.arange(32)[None,:])%2).float()[None,None].expand(1,3,32,32).contiguous()
    assert torch.equal(switch_median(checker,.35),torch.full_like(checker,.5))
    assert torch.equal(switch_median(checker,.75),checker)
    for size in SIZES:
        resized=resize_aa(raw,size);assert resized.shape==raw.shape and resized.is_contiguous()
        assert torch.isfinite(resized).all() and 0<=resized.min()<=resized.max()<=1
    assert torch.equal(apply(raw,{'operator':'median_then_resize','threshold':.2,'size':24}),resize_aa(calc,24))
    for config in [{'operator':'switch_median','threshold':None},{'operator':'resize_aa','size':32},{'operator':'median_then_resize','threshold':None,'size':32}]:
        assert is_identity(config) and torch.equal(apply(raw,config),raw)
    z=torch.tensor([[2.,0.],[0.,2.]],dtype=torch.float64)
    assert metrics(z,z)['eligible'] and not metrics(z,z.flip(1))['eligible']
    rejected=0
    for bad in [raw.double(),raw-1,raw.permute(0,2,3,1),torch.full_like(raw,float('nan'))]:
        try:switch_median(bad,.2)
        except ValueError:rejected+=1
    assert rejected==4 and not torch.cuda.is_initialized()
    result={'state':'passed','pid':os.getpid(),'time':time.time(),'method_sha256':sha(r/'postonly_inputs.py'),
        'checker_sha256':sha(__file__),'preparation_freeze_sha256':sha(r/'POST_ONLY_INPUT_PREPARATION_FREEZE.json'),
        'independent_NumPy_reflect8_neighbour_switch_exact':True,'constant_identity':True,'synthetic_checker_operator_only':True,
        'resize_range_and_cascade_exact':True,'off_identity_exact':True,'invalid_input_rejections':rejected,
        'real_images_models_or_trigger_used':False,'GPU_initialized':False,'defense_efficacy_measured':False}
    with OUT.open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
