"""Explicit CPU-I/O/CPU-export class factory for a separately declared CUDA profile."""
from collections import OrderedDict
import torch


def class_factory(base,device='cuda:0'):
    execution_device=torch.device(device)
    if execution_device.type!='cuda':raise ValueError('This factory requires an explicit CUDA device')

    class CpuIoCudaModel(base):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.execution_device=execution_device
            self.to(execution_device)

        def forward(self,normalized_cpu_input):
            if normalized_cpu_input.device.type!='cpu' or normalized_cpu_input.dtype!=torch.float32:
                raise ValueError('Expected normalized FP32 CPU input')
            return super().forward(normalized_cpu_input.to(self.execution_device)).to('cpu')

        def state_dict(self,*args,**kwargs):
            if args or kwargs:raise ValueError('Only default detached CPU state export is supported')
            original=super().state_dict()
            exported=OrderedDict((k,v.detach().to('cpu').clone()) for k,v in original.items())
            if hasattr(original,'_metadata'):exported._metadata=original._metadata
            return exported

    return CpuIoCudaModel
