"""Pure output composition; public calibration receives no private truth."""
import torch
from stage09 import proxy_metrics


def relabel(post,teacher,threshold):
    assert post.shape==teacher.shape and post.ndim==2 and torch.isfinite(post).all() and torch.isfinite(teacher).all()
    a=post.argmax(1);b=teacher.argmax(1);confidence=post.softmax(1).max(1).values
    mask=(a!=b)&(confidence>=threshold) if threshold is not None else torch.zeros(len(post),dtype=torch.bool,device=post.device)
    z=post.clone();rows=torch.where(mask)[0]
    z[rows,a[rows]]=post[rows,b[rows]];z[rows,b[rows]]=post[rows,a[rows]]
    assert torch.equal(z.sort(1).values,post.sort(1).values)
    return z,mask


def calibrate(post,teacher):
    assert post.dtype==teacher.dtype==torch.float64
    confidence=post.softmax(1).max(1).values;points=[];outputs=[]
    for q in [0.,.5,.75,.9,.95,.99,1.,None]:
        tau=float(torch.quantile(confidence,q,interpolation='linear')) if q is not None else None
        z,mask=relabel(post,teacher,tau);outputs.append(z)
        points.append({'quantile':q,'threshold':tau,'routed_n':int(mask.sum()),**proxy_metrics(post,z)})
    index=next(i for i,row in enumerate(points) if row['eligible'])
    return {'selected_index':index,'selected':points[index],'points':points},torch.stack(outputs)
