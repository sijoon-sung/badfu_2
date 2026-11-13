"""New derived endpoint clean utility only, no attack trigger or old evaluator."""
import argparse
import json
import os
from bindings import ROOT,read,write,sha


def main(branch):
    (ROOT/('CLEAN_EVAL_'+branch+'_ONCE')).open('x').write(str(os.getpid()))
    cfg=read(ROOT/'PROFILE.json')
    from resource_guard import admit
    write(ROOT/('ADMISSION_CLEAN_'+branch+'.json'),admit(cfg))
    import torch
    import model_reference
    torch.set_num_threads(2);torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False
    torch.cuda.set_per_process_memory_fraction(cfg['memory_fraction'])
    data_cfg=read(ROOT/'DETECTOR_PROFILE.json');assert sha(data_cfg['raw_data'])==data_cfg['raw_sha256']
    raw=torch.load(data_cfg['raw_data'],map_location='cpu',weights_only=True)
    meta=read(ROOT/('FU_'+branch+'_RESULT.json'))['after'];assert sha(meta['path'])==meta['sha256']
    model=model_reference.ResNet18().cuda().eval();model.load_state_dict(torch.load(meta['path'],map_location='cpu',weights_only=True),strict=True)
    counts=[0]*10;totals=[0]*10
    with torch.inference_mode():
        for ids in torch.arange(10000).split(128):
            x=raw['test_x'][ids].permute(0,3,1,2).contiguous().float().cuda()/255
            y=raw['test_y'][ids].long().cuda();prediction=model(((x-.5)/.5).contiguous()).argmax(1)
            for c in range(10):counts[c]+=int(((prediction==y)&(y==c)).sum());totals[c]+=int((y==c).sum())
    assert totals==[1000]*10
    write(ROOT/('CLEAN_'+branch+'.json'),dict(version='D21.clean_utility.contiguous_FP32.v1',N=10000,
          correct=sum(counts),CA_pct=sum(counts)/100,correct_by_class=counts,N_by_class=totals,model_sha256=meta['sha256'],
          role_truth_or_trigger_inputs=0,independent_second_clean_inference=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('branch');main(p.parse_args().branch)
