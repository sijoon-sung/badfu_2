"""Derive target-direction summaries from exactly the already saved40 SSS query packets."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
import gc,json,math,pickle,traceback
from pathlib import Path
from common import ROOT,read,sha,once,published,guard

def initial():
    return {'N':0,'clean_target_hits':0,'perturbed_target_hits':0,'neither_target':0,'clean_only_target':0,'perturbed_only_target':0,'both_target':0,'margin_decreased':0,'margin_increased':0,'margin_unchanged':0,'margin_shift_sum':0.,'clean_target_CE_sum':0.,'perturbed_target_CE_sum':0.}
def finish(s):
    n=s['N'];assert n>0
    return {**{k:v for k,v in s.items() if not k.endswith('_sum')},'mean_margin_shift':s['margin_shift_sum']/n,'mean_clean_target_CE':s['clean_target_CE_sum']/n,'mean_perturbed_target_CE':s['perturbed_target_CE_sum']/n}
def main():
    p,b=published();resources=guard();once('PRIMARY_ONCE.json',{'pid':os.getpid(),'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'resources':resources})
    import torch
    torch.set_num_threads(p['cpu_threads']);assert not torch.cuda.is_initialized()
    target=p['target'];result=read(b['SSS_result']['path']);audit=read(b['SSS_verified']['path']);parts=read(b['split']['path'])['indices']
    assert result['state']=='completed_SSS_queries' and audit['state']=='passed' and audit['SSS_result_sha256']==b['SSS_result']['sha256']
    assert result['pre_checkpoint']['sha256']==b['pre_checkpoint_sha256'] and result['delta']['sha256']==b['delta_sha256'] and result['case_id']==b['case_id']
    selected={int(k):set(v) for k,v in result['selected_by_owner'].items()}
    assert {str(k):len(v) for k,v in selected.items()}==b['counts']['selected_by_owner']
    labels=[]
    for name,d in b['data_files_sha256'].items():
        path=Path(b['data_root'])/name;assert sha(path)==d,name
        with path.open('rb') as f:value=pickle.load(f,encoding='bytes')
        labels.extend(int(x) for x in value[b'labels']);del value
    assert len(labels)==50000 and set(labels)==set(range(10))
    packets=read(ROOT/'private_inputs/QUERY_INDEX.json');assert packets==result['query_packets'] and len(packets)==40
    groups={g:initial() for g in p['groups']};owners={str(o):{g:initial() for g in p['groups']} for o in [5,7]}
    private=ROOT/'private_result';private.mkdir(exist_ok=False);rows_path=private/'rows.jsonl';seen=set();packet_hashes=[]
    with rows_path.open('x',encoding='utf-8',newline='\n') as rows_out:
        for entry in packets:
            owner,batch,meta=entry['owner'],entry['batch'],entry['packet']
            packet_path=(Path(b['SSS_root'])/meta['path']).resolve();assert packet_path.is_relative_to((Path(b['SSS_root'])/'sss/queries').resolve())
            assert packet_path.stat().st_size==meta['bytes'] and sha(packet_path)==meta['sha256']
            row=torch.load(packet_path,map_location='cpu',weights_only=True)
            assert row['owner']==owner and row['batch']==batch and row['forward_query_calls']==2 and row['gradient_enabled'] is False
            ids=row['source_ids'].tolist();assert ids==parts[owner][(batch-1)*128:batch*128]
            assert row['clean_logits'].dtype==row['perturbed_logits'].dtype==torch.float32
            assert row['clean_logits'].shape==row['perturbed_logits'].shape==(len(ids),10)
            assert bool(torch.isfinite(row['clean_logits']).all()) and bool(torch.isfinite(row['perturbed_logits']).all())
            clean=row['clean_logits'].to(torch.float64);pert=row['perturbed_logits'].to(torch.float64)
            clean_top=clean.argmax(1);pert_top=pert.argmax(1)
            clean_other=clean.clone();pert_other=pert.clone();clean_other[:,target]=-torch.inf;pert_other[:,target]=-torch.inf
            change=(pert[:,target]-pert_other.amax(1))-(clean[:,target]-clean_other.amax(1))
            clean_ce=torch.logsumexp(clean,1)-clean[:,target];pert_ce=torch.logsumexp(pert,1)-pert[:,target]
            row_groups=[]
            for j,source_id in enumerate(ids):
                assert source_id not in seen;seen.add(source_id)
                lab=labels[source_id];is_selected=source_id in selected[owner]
                if is_selected:assert lab==target
                group='selected_target' if is_selected else ('nonselected_target' if lab==target else 'nontarget');row_groups.append(group)
                saved={'source_id':source_id,'owner':owner,'label':lab,'group':group,'clean_logits':row['clean_logits'][j].tolist(),'perturbed_logits':row['perturbed_logits'][j].tolist()}
                rows_out.write(json.dumps(saved,allow_nan=False,separators=(',',':'))+'\n')
            for group in p['groups']:
                mask=torch.tensor([g==group for g in row_groups],dtype=torch.bool)
                if not bool(mask.any()):continue
                ch=clean_top[mask]==target;ph=pert_top[mask]==target;shift=change[mask]
                update={'N':int(mask.sum()),'clean_target_hits':int(ch.sum()),'perturbed_target_hits':int(ph.sum()),'neither_target':int((~ch & ~ph).sum()),'clean_only_target':int((ch & ~ph).sum()),'perturbed_only_target':int((~ch & ph).sum()),'both_target':int((ch & ph).sum()),'margin_decreased':int((shift<0).sum()),'margin_increased':int((shift>0).sum()),'margin_unchanged':int((shift==0).sum()),'margin_shift_sum':float(shift.sum()),'clean_target_CE_sum':float(clean_ce[mask].sum()),'perturbed_target_CE_sum':float(pert_ce[mask].sum())}
                for dst in [groups[group],owners[str(owner)][group]]:
                    for key,value in update.items():dst[key]+=value
            packet_hashes.append(meta['sha256']);del row,clean,pert,clean_other,pert_other;gc.collect()
    assert len(seen)==5000 and seen==set(parts[5]+parts[7])
    assert {g:s['N'] for g,s in groups.items()}=={'selected_target':125,'nonselected_target':343,'nontarget':4532}
    assert not torch.cuda.is_initialized()
    summary={'state':'completed_saved_query_target_direction_primary','profile':p['id'],'input_binding_sha256':sha(ROOT/'INPUT_BINDING.json'),'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'query_condition':p['query_condition'],'groups':{g:finish(s) for g,s in groups.items()},'by_owner':{o:{g:finish(s) for g,s in a.items()} for o,a in owners.items()},'predeclared_majority_margin_decrease':2*groups['selected_target']['margin_decreased']>125,'private_rows':{'path':'private_result/rows.jsonl','sha256':sha(rows_path),'rows':5000},'source_packet_count':40,'source_packet_hashes_checked':packet_hashes,'new_model_loads':0,'new_model_forwards':0,'new_queries':0,'CUDA_initialized':False,'old_finite_job_replayed':False,'new_selection_or_training_allowed':False,'is_standard_CA_or_ASR_evaluation':False,'overall_goal_complete':False}
    once('RESULT.json',summary);print(json.dumps({'state':summary['state'],'selected':summary['groups']['selected_target'],'hypothesis':summary['predeclared_majority_margin_decrease'],'new_model_forwards':0}))
if __name__=='__main__':
    try:main()
    except BaseException:once('PRIMARY_FAILURE.json',{'state':'failed_preserved_no_retry','traceback':traceback.format_exc()});raise
