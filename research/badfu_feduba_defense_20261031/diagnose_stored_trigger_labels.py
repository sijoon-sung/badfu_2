"""Original-class restoration on already-saved outputs; evaluator-only."""
import hashlib,json
from pathlib import Path
import numpy as np
import torch
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))


def main():
    torch.set_num_threads(2);freeze=read(HERE/'STORED_TRIGGER_LABEL_FREEZE.json')
    for n,h in freeze['files'].items():assert sha(HERE/n)==h,n
    audit=read(HERE/'stage11/INDEPENDENT_VERIFICATION.json');assert audit['state']=='passed' and audit['scope']=='finished_pipeline'
    info=read(HERE/'STAGE03_INPUTS.json')
    assert sha(info['clean_path'])==info['clean_path_sha256'] and sha(info['record_path'])==info['record_path_sha256']
    labels=torch.load(info['clean_path'],map_location='cpu',weights_only=True)['test_y'].numpy()
    record=torch.load(info['record_path'],map_location='cpu',weights_only=False)
    ids=np.array([int(i) for i in record['bd_test']['bd_data_container']['data_dict']])
    assert sorted(ids.tolist())==np.flatnonzero(labels!=0).tolist() and len(ids)==9000
    truth=labels[ids];held=np.isin(ids,read(HERE/'PROXY_SPLIT.json')['heldout_ids']);assert int(held.sum())==8542
    root=HERE/'stage11/attack_cover850';receipt=read(root/'COMPLETED.json')
    result={'state':'completed','fresh_model_inference':False,'labels_evaluator_only':True,'arms':{},'script_sha256':sha(__file__)}
    for arm in ['matched_kl','all_class_disjoint']:
        result['arms'][arm]={}
        for variant in ['raw','selected']:
            p=root/('private_'+arm+'_'+variant+'_attack.pt');assert sha(p)==receipt['files'][p.name]
            z=torch.load(p,map_location='cpu',weights_only=True)['attack_logits'];assert z.shape==(9000,10) and torch.isfinite(z).all()
            pred=z.numpy().argmax(1);rows={}
            for name,mask in [('all9000',np.ones(9000,dtype=bool)),('heldout8542',held)]:
                y=truth[mask];yp=pred[mask]
                rows[name]={'n':len(y),'original_label_correct_n':int((y==yp).sum()),'original_label_CA_pct':100*float((y==yp).mean()),
                    'target_n':int((yp==0).sum()),'predicted_class_counts':np.bincount(yp,minlength=10).tolist(),
                    'class_rows':[{'original_class':c,'n':int((y==c).sum()),'correct_n':int(((y==c)&(yp==c)).sum()),
                        'CA_pct':100*float((yp[y==c]==c).mean()) if (y==c).any() else None} for c in range(10)]}
            result['arms'][arm][variant]=rows
    assert not torch.cuda.is_initialized()
    with (HERE/'STORED_TRIGGER_LABEL_RESULT.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
