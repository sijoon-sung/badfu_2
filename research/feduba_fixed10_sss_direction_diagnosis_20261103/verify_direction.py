"""Independent scalar Python arithmetic from serialized saved logits; torch/model-free."""
import json,math,os,sys,traceback
from common import ROOT,read,sha,once,published

def main():
    p,b=published();assert 'torch' not in sys.modules
    once('VERIFY_ONCE.json',{'pid':os.getpid(),'input_binding_sha256':sha(ROOT/'INPUT_BINDING.json')})
    result=read(ROOT/'RESULT.json');meta=result['private_rows'];assert sha(ROOT/meta['path'])==meta['sha256']
    source=read(b['SSS_result']['path']);selected={int(o):set(ids) for o,ids in source['selected_by_owner'].items()};target=p['target']
    sets={g:[] for g in p['groups']};owner_sets={str(o):{g:[] for g in p['groups']} for o in [5,7]};ids=set()
    with (ROOT/meta['path']).open(encoding='utf-8') as stream:
        for line in stream:
            row=json.loads(line);assert row['source_id'] not in ids;ids.add(row['source_id'])
            group='selected_target' if row['source_id'] in selected[row['owner']] else ('nonselected_target' if row['label']==target else 'nontarget')
            assert group==row['group'] and (group!='selected_target' or row['label']==target)
            a,z=row['clean_logits'],row['perturbed_logits'];assert len(a)==len(z)==10 and all(math.isfinite(v) for v in a+z)
            ca=max(range(10),key=a.__getitem__);pa=max(range(10),key=z.__getitem__)
            am=a[target]-max(v for j,v in enumerate(a) if j!=target);pm=z[target]-max(v for j,v in enumerate(z) if j!=target)
            ace=max(a)+math.log(math.fsum(math.exp(v-max(a)) for v in a))-a[target]
            pce=max(z)+math.log(math.fsum(math.exp(v-max(z)) for v in z))-z[target]
            item=(ca==target,pa==target,pm-am,ace,pce);sets[group].append(item);owner_sets[str(row['owner'])][group].append(item)
    assert len(ids)==5000
    def summarize(rows):
        n=len(rows);assert n
        return {'N':n,'clean_target_hits':sum(x[0] for x in rows),'perturbed_target_hits':sum(x[1] for x in rows),'neither_target':sum(not x[0] and not x[1] for x in rows),'clean_only_target':sum(x[0] and not x[1] for x in rows),'perturbed_only_target':sum(not x[0] and x[1] for x in rows),'both_target':sum(x[0] and x[1] for x in rows),'margin_decreased':sum(x[2]<0 for x in rows),'margin_increased':sum(x[2]>0 for x in rows),'margin_unchanged':sum(x[2]==0 for x in rows),'mean_margin_shift':math.fsum(x[2] for x in rows)/n,'mean_clean_target_CE':math.fsum(x[3] for x in rows)/n,'mean_perturbed_target_CE':math.fsum(x[4] for x in rows)/n}
    computed={'groups':{g:summarize(x) for g,x in sets.items()},'by_owner':{o:{g:summarize(x) for g,x in groups.items()} for o,groups in owner_sets.items()}}
    max_error=0.
    for scope in ['groups','by_owner']:
        subpairs=[(computed[scope],result[scope])] if scope=='groups' else [(computed[scope][o],result[scope][o]) for o in ['5','7']]
        for left,right in subpairs:
            assert left.keys()==right.keys()
            for g in left:
                assert left[g].keys()==right[g].keys()
                for k,v in left[g].items():
                    expected=right[g][k]
                    if isinstance(v,int):assert v==expected,(scope,g,k,v,expected)
                    else:
                        err=abs(v-expected);assert err<=p['ce_and_mean_check_atol']+p['ce_and_mean_check_rtol']*abs(expected),(scope,g,k,err)
                        max_error=max(max_error,err)
    verdict=2*computed['groups']['selected_target']['margin_decreased']>125
    assert verdict==result['predeclared_majority_margin_decrease'] and 'torch' not in sys.modules
    verified={'state':'passed_independent_scalar_saved_logit_arithmetic','primary_result_sha256':sha(ROOT/'RESULT.json'),'private_rows_sha256':meta['sha256'],'checked_rows':5000,'all_integer_counts_and_signs_exact':True,'max_FP64_summary_abs_error':max_error,'predeclared_majority_margin_decrease':verdict,'model_loads':0,'forward_calls':0,'torch_imported':False,'original_PT_packets_independently_reloaded':False,'new_selection_or_training_allowed':False,'overall_goal_complete':False}
    once('VERIFIED.json',verified);print(json.dumps(verified))
if __name__=='__main__':
    try:main()
    except BaseException:once('VERIFY_FAILURE.json',{'state':'failed_preserved_no_retry','traceback':traceback.format_exc()});raise
