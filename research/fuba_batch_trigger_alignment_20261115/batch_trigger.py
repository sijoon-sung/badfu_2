"""Explicit public-FUBA per-batch Bernoulli mask with a private CPU RNG."""
import torch


PATCHES=((0,2,0,5),(4,6,7,12),(4,6,0,5),(0,2,7,12))


def compose_batch(inputs,labels,role,*,generator):
    if role not in range(5):raise ValueError('Expected one of four attackers or the defender')
    if generator.device.type!='cpu':raise ValueError('Public mask generator is CPU based')
    mask_cpu=torch.rand(len(inputs),generator=generator,device='cpu')<.3
    mask=mask_cpu.to(inputs.device)
    transformed=inputs.clone()
    poisoned=inputs[mask].clone()
    for y0,y1,x0,x1 in PATCHES if role==4 else [PATCHES[role]]:
        poisoned[:,:,y0:y1,x0:x1]=1
    transformed[mask]=poisoned
    targets=torch.where(mask,torch.tensor(8,device=inputs.device),labels)
    return transformed,targets,mask_cpu
