"""Explicit raw-image interfaces; no attack truth, checkpoint inference or selection."""
from dataclasses import dataclass
import torch


@dataclass(frozen=True)
class EndpointSpec:
    name:str
    head_path:str
    mean:tuple
    std:tuple
    features:int=512
    classes:int=10


BADFU=EndpointSpec('badfu_torchvision_declared','model.fc',(.4914,.4822,.4465),(.2023,.1994,.2010))
FEDUBA=EndpointSpec('feduba_narcissus_reference_declared','linear',(.5,.5,.5),(.5,.5,.5))


def normalise_raw(raw,spec):
    if raw.ndim!=4 or raw.shape[1]!=3 or not raw.is_floating_point():
        raise ValueError('Expected floating raw[0,1] NCHW RGB inputs')
    if not torch.isfinite(raw).all() or float(raw.detach().min())<0 or float(raw.detach().max())>1:
        raise ValueError('Raw inputs must be finite and lie in[0,1]')
    mean=raw.new_tensor(spec.mean).view(1,3,1,1);std=raw.new_tensor(spec.std).view(1,3,1,1)
    if len(spec.mean)!=3 or len(spec.std)!=3 or not bool((std>0).all()):
        raise ValueError('Expected three declared positive normalization scales')
    return (raw-mean)/std


def forward_raw(model,raw,spec,with_features=False):
    if model.training:raise ValueError('The declared interface requires eval mode/fixed BN buffers')
    head=model.get_submodule(spec.head_path)
    if not isinstance(head,torch.nn.Linear) or (head.in_features,head.out_features)!=(spec.features,spec.classes):
        raise ValueError('Classifier shape does not match the explicitly declared endpoint')
    captured=[]
    def hook(module,args):
        if len(args)!=1 or args[0].ndim!=2 or args[0].shape[1]!=spec.features:
            raise ValueError('Unexpected classifier input')
        captured.append(args[0])
    handle=head.register_forward_pre_hook(hook) if with_features else None
    try:z=model(normalise_raw(raw,spec))
    finally:
        if handle is not None:handle.remove()
    if z.shape!=(len(raw),spec.classes) or not torch.isfinite(z).all():
        raise ValueError('Unexpected/nonfinite endpoint logits')
    if not with_features:return z
    if len(captured)!=1:raise ValueError('Classifier must be called exactly once')
    return z,captured[0]
