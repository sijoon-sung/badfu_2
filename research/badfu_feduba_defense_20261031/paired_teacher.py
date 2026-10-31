"""Explicit-head reference construction, not a trusted or deployable defense."""
import torch


def aligned_reference(pre_state,post_state,pre_features,post_features,spec):
    """Public paired features only; no labels, triggers, members or file paths."""
    x=pre_features;y=post_features;wk=spec.head_path+'.weight';bk=spec.head_path+'.bias'
    if set(pre_state)!=set(post_state):raise ValueError('Endpoint state keys differ')
    if wk not in pre_state or bk not in pre_state:raise ValueError('Explicit classifier missing')
    if pre_state[wk].shape!=(spec.classes,spec.features) or pre_state[bk].shape!=(spec.classes,):
        raise ValueError('Pre classifier does not match declared dimensions')
    if post_state[wk].shape!=pre_state[wk].shape or post_state[bk].shape!=pre_state[bk].shape:
        raise ValueError('Post classifier dimensions differ')
    if x.ndim!=2 or x.shape!=y.shape or x.shape[0]<2 or x.shape[1]!=spec.features:
        raise ValueError('Expected paired public feature matrices')
    if x.device.type!='cpu' or y.device.type!='cpu' or not x.is_floating_point() or not y.is_floating_point():
        raise ValueError('Declared alignment is floating CPU arithmetic')
    if not torch.isfinite(x).all() or not torch.isfinite(y).all():raise ValueError('Nonfinite public features')
    for k,v in pre_state.items():
        if v.shape!=post_state[k].shape or not torch.isfinite(v).all() or not torch.isfinite(post_state[k]).all():
            raise ValueError('Incompatible or nonfinite endpoint state: '+k)
    x=x.double();y=y.double();mx=x.mean(0);my=y.mean(0);xc=x-mx;yc=y-my;d=spec.features
    lam=.01*(xc.square().sum()+yc.square().sum())/(2*d)
    u,_,vh=torch.linalg.svd(xc.T@yc+lam*torch.eye(d,dtype=torch.float64));a=u@vh
    error=float((a.T@a-torch.eye(d,dtype=torch.float64)).abs().max())
    if error>=1e-10:raise ValueError('Alignment orthogonality contract failed')
    w=post_state[wk].double();b=post_state[bk].double()
    teacher={k:v.detach().clone() for k,v in pre_state.items()}
    teacher[wk]=(a@w.T).T.to(dtype=pre_state[wk].dtype)
    teacher[bk]=(b+my@w.T-mx@a@w.T).to(dtype=pre_state[bk].dtype)
    return teacher,{'rotation':a,'mean_pre':mx,'mean_post':my,'lambda':float(lam),
        'orthogonality_max_error':error,'head_path':spec.head_path,'trusted_teacher':False}
