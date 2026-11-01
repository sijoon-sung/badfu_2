"""Post-only public calibration and deterministic raw-image guards; no private data."""
import torch
import torch.nn.functional as F

ARMS=['switch_median','resize_aa','median_then_resize']
THRESHOLDS=[0.,.05,.10,.20,.35,.50,.75,None]
SIZES=[16,20,24,28,30,32]


def validate(raw):
    if raw.device.type!='cpu' or raw.dtype!=torch.float32 or raw.ndim!=4 or raw.shape[1:]!=(3,32,32):
        raise ValueError('Expected FP32 CPU raw NCHW RGB32 inputs')
    if not torch.isfinite(raw).all() or float(raw.min())<0 or float(raw.max())>1:
        raise ValueError('Expected finite raw[0,1]')


def switch_median(raw,threshold):
    validate(raw)
    if threshold is None:return raw
    if not 0<=threshold<=1:raise ValueError('Invalid fixed threshold')
    padded=F.pad(raw,(1,1,1,1),mode='reflect')
    neighbours=torch.stack([padded[:,:,i:i+32,j:j+32] for i in range(3) for j in range(3) if (i,j)!=(1,1)],dim=-1)
    ordered=neighbours.sort(-1).values;median=(ordered[...,3]+ordered[...,4])*.5
    return torch.where((raw-median).abs()>threshold,median,raw).contiguous()


def resize_aa(raw,size):
    validate(raw)
    if size not in SIZES:raise ValueError('Undeclared resize size')
    if size==32:return raw
    down=F.interpolate(raw,size=(size,size),mode='bilinear',align_corners=False,antialias=True)
    return F.interpolate(down,size=(32,32),mode='bilinear',align_corners=False,antialias=True).clamp(0,1).contiguous()


def apply(raw,config):
    kind=config['operator']
    if kind=='switch_median':return switch_median(raw,config['threshold'])
    if kind=='resize_aa':return resize_aa(raw,config['size'])
    if kind=='median_then_resize':return resize_aa(switch_median(raw,config['threshold']),config['size'])
    raise ValueError('Undeclared operator')


def is_identity(config):
    if config['operator']=='switch_median':return config['threshold'] is None
    if config['operator']=='resize_aa':return config['size']==32
    if config['operator']=='median_then_resize':return config['threshold'] is None and config['size']==32
    raise ValueError('Undeclared operator')


def metrics(native,candidate):
    if native.shape!=candidate.shape or native.dtype!=torch.float64 or candidate.dtype!=torch.float64:
        raise ValueError('Expected matched FP64 cached outputs')
    p=native.softmax(1);label=native.argmax(1);pred=candidate.argmax(1)
    kl=max(0.,float((p*(native.log_softmax(1)-candidate.log_softmax(1))).sum(1).mean()))
    agreement=float((pred==label).double().mean())
    classes=[float((pred[label==c]==c).double().mean()) if (label==c).any() else 1. for c in range(native.shape[1])]
    return {'mean_KL':kl,'agreement':agreement,'class_agreement':classes,
        'eligible':kl<=.010+1e-12 and agreement>=.98-1e-12 and min(classes)>=.95-1e-12}


@torch.inference_mode()
def calibrate(public_raw,predict_raw):
    """The only learned decisions depend on supplied public pixels and Post outputs."""
    validate(public_raw)
    if len(public_raw)!=500:raise ValueError('Declared public500 required')
    native=predict_raw(public_raw);points={};outputs={};selected={}
    for arm in ARMS:
        if arm=='switch_median':configs=[{'operator':arm,'threshold':v} for v in THRESHOLDS]
        elif arm=='resize_aa':configs=[{'operator':arm,'size':v} for v in SIZES]
        else:configs=[{'operator':arm,'threshold':selected['switch_median']['config']['threshold'],'size':v} for v in SIZES]
        rows=[];zs=[]
        for config in configs:
            z=native if is_identity(config) else predict_raw(apply(public_raw,config))
            rows.append({'config':config,**metrics(native,z)});zs.append(z)
        index=next(i for i,row in enumerate(rows) if row['eligible'])
        points[arm]=rows;outputs[arm]=torch.stack(zs);selected[arm]={'selected_index':index,**rows[index],'identity':is_identity(rows[index]['config'])}
    return {'selected':selected,'all_points':points,'Pre_or_H5_received':False,'groundtruth_used':False,
        'actual_trigger_used':False,'target_used':False,'member_used':False}, {'native_logits':native,'candidate_logits':outputs}
