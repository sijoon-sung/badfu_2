"""Independent read-only CPU check of every shared incoming round and phase."""
import json
import os
import torch
from run import ROOT, read, sha, write, frozen
from numerical_control import comparisons


def main():
    torch.set_num_threads(1); frozen()
    assert read(ROOT/'STATE.json')['state']=='complete'
    assert read(ROOT/'CPU_AUDIT.json')['state']=='passed'
    for name,digest in read(ROOT/'PREFIX_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest
    write(ROOT/'PREFIX_AUDIT_STARTED.json',{'pid':os.getpid()},True)
    rows=[];first=None;phases=0
    for r in range(21,31):
        a,b=[torch.load(ROOT/arm/f'rounds/round{r:04d}.pt',map_location='cpu',weights_only=True) for arm in ['local','global']]
        common=not comparisons(a['incoming'],b['incoming'])
        if first is None:assert common,'Unexplained divergence before gamma treatment'
        if not common:continue
        assert a['clients']==b['clients']
        for c,la,lb,sa,sb in zip(a['clients'],a['roles'],b['roles'],a['submitted'],b['submitted']):
            assert len(la['phases'])==len(lb['phases'])
            for pa,pb in zip(la['phases'],lb['phases']):
                assert sha(ROOT/pa['path'])==pa['sha256'] and sha(ROOT/pb['path'])==pb['sha256']
                left,right=[torch.load(ROOT/p['path'],map_location='cpu',weights_only=True) for p in (pa,pb)]
                assert not comparisons(left,right),(r,c,pa['path'])
                phases+=1
            same=c>=4 or la['decision']['gamma']==lb['decision']['gamma']
            if same:assert not comparisons(sa,sb),(r,c,'submission')
            elif first is None:first={'round':r,'client':c,'local_gamma':la['decision']['gamma'],'global_gamma':lb['decision']['gamma']}
            rows.append({'round':r,'client':c,'all_phase_model_optimizer_RNG_exact':True,'same_gamma':same,'submission_exact_when_same_gamma':True})
    claimed=read(ROOT/'PREFIX_PROOF.json')
    assert claimed=={'first_changed_gamma':first,'common_input_roles':rows}
    write(ROOT/'PREFIX_AUDIT.json',{'state':'passed','first_changed_gamma':first,'common_input_roles':len(rows),
         'exact_phase_bundles':phases,'all_inline_claims_independently_verified':True,'CUDA_initialized':torch.cuda.is_initialized(),
         'new_training':0,'new_inference':0},True)
    print(json.dumps({'first':first,'roles':len(rows),'phases':phases}),flush=True)


if __name__=='__main__':main()
