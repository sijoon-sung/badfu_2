"""Small CPU equation/counterexample contracts; no dataset or trained model."""
import json
from pathlib import Path
import torch
from unlearning_kernels import retained_reference, project_l2, pgd_should_stop, inverse_conflict_weights, conflict_samples


def main():
    torch.set_num_threads(1)
    # The deleted contribution must come from this actual aggregation cohort.
    s = {2:{'w':torch.tensor([1.,3.])}, 4:{'w':torch.tensor([7.,9.])}, 9:{'w':torch.tensor([5.,7.])}}
    r = retained_reference(s,4)
    assert torch.equal(r['w'],torch.tensor([3.,5.]))
    try: retained_reference(s,8)
    except ValueError: pass
    else: raise AssertionError('Absent deletion client was silently accepted')
    # A 3-4-5 vector straddles two layers: per-layer clipping gives the wrong answer.
    q={'a':torch.tensor([3.],dtype=torch.float64),'b':torch.tensor([4.],dtype=torch.float64)}
    z={k:torch.zeros_like(v) for k,v in q.items()}
    p=project_l2(q,z,2.5)
    assert torch.equal(p['a'],torch.tensor([1.5],dtype=torch.float64))
    assert torch.equal(p['b'],torch.tensor([2.],dtype=torch.float64))
    assert all(torch.equal(project_l2(q,z,6)[k],q[k]) for k in q)
    assert all(torch.equal(project_l2(q,z,0)[k],z[k]) for k in q)
    assert not pgd_should_stop(q,z,5) and pgd_should_stop(q,z,5.1)
    assert not pgd_should_stop(q,z,4.9)
    w=inverse_conflict_weights({4:2,11:4})
    assert abs(w[4]-2/3)<1e-15 and abs(w[11]-1/3)<1e-15
    assert inverse_conflict_weights({4:0,11:4,15:0})=={4:.5,11:0.,15:.5}
    assert inverse_conflict_weights({4:0,11:0})=={4:.5,11:.5}
    ids,labels,count=conflict_samples(torch.tensor([10,20,30]),torch.tensor([8,0,1]),torch.tensor([8,3,0]))
    assert ids.tolist()==[20,30] and labels.tolist()==[0,1] and count==2
    result={'state':'passed','contracts':7,'device':'CPU','CUDA_initialized':torch.cuda.is_initialized(),
            'datasets':0,'trained_models':0,'full_FU_executed':False}
    path=Path(__file__).with_name('KERNEL_CONTRACTS.json')
    with path.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))


if __name__=='__main__':main()
