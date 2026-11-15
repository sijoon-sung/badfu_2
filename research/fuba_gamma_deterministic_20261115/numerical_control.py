"""Compare already stored first-role states; no new training or inference."""
import json
import torch
from run import ROOT,read,sha,write


def comparisons(a,b,path=''):
    if isinstance(a,torch.Tensor):
        assert isinstance(b,torch.Tensor) and a.shape==b.shape and a.dtype==b.dtype,path
        return [] if torch.equal(a,b) else [{'path':path,'max_abs':float((a.double()-b.double()).abs().max())}]
    if isinstance(a,dict):
        assert a.keys()==b.keys(),path
        return [v for k in a for v in comparisons(a[k],b[k],f'{path}/{k}')]
    if isinstance(a,(list,tuple)):
        assert len(a)==len(b),path
        return [v for i,(x,y) in enumerate(zip(a,b)) for v in comparisons(x,y,f'{path}/{i}')]
    return [] if a==b else [{'path':path,'left':str(a),'right':str(b)}]


def main():
    torch.set_num_threads(1)
    for name,digest in read(ROOT/'NUMERICAL_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest
    assert read(ROOT/'STATE.json')['state']=='complete'
    rows=[]
    for phase in range(1,5):
        p=[ROOT/arm/f'phases/round0021_client00/phase{phase:02d}.pt' for arm in ['local','global']]
        a,b=[torch.load(x,map_location='cpu',weights_only=True) for x in p]
        differences=comparisons(a,b)
        rows.append({'phase':phase,'exact':not differences,'differences':differences,
                     'left_sha256':sha(p[0]),'right_sha256':sha(p[1])})
    write(ROOT/'NUMERICAL_CONTROL.json',{'state':'exact' if all(x['exact'] for x in rows) else 'differences_preserved',
        'rows':rows,'scope':'first21R/client0 four phases only','inference':0,'training':0},True)
    print(json.dumps({'exact':all(x['exact'] for x in rows),'differences':sum(len(x['differences']) for x in rows)}),flush=True)


if __name__=='__main__':main()
