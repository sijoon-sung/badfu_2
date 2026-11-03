"""One negative-only primary or independent evaluator on fixed existing weights."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import argparse,json,sys,time,traceback
from pathlib import Path
from common import ROOT,read,write,once,sha,checked,source_check,require_run,select_case,load,save,setup,diagnostic_gates
def prepare_model(torch,m):
    import model_reference
    state=load(m);model=model_reference.ResNet18().cuda().eval();model.load_state_dict(state,strict=True)
    for p in model.parameters():p.requires_grad_(False)
    return model,state
def unchanged(torch,model,state):
    assert all(torch.equal(v.detach().cpu(),state[k]) for k,v in model.state_dict().items())
    assert all(not p.requires_grad and p.grad is None for p in model.parameters())
def main(mode):
    p,b,old=require_run()
    selection=select_case(p,b)
    once(mode.upper()+'_ONCE.json',{'pid':os.getpid(),'created':time.time(),'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'mode':mode})
    torch=setup()
    delta=load(b['delta']);assert delta.shape==(1,3,32,32) and delta.dtype==torch.float32 and bool(torch.isfinite(delta).all()) and float(delta.abs().max())<=32/255+1e-7
    test=Path(b['data_root'])/'cifar-10-batches-py/test_batch';assert sha(test)==b['test_file_sha256']
    if mode=='primary':
        (ROOT/'private_run').mkdir(exist_ok=False)
        write('CASE_SELECTION.json',selection)
        input_packets=[]
        for bi,m in enumerate(old['input_packets']):
            item=load(m,b['baseline_input_root']);ids=item['source_ids'];labels=item['labels'];clean=item['clean_input']
            start=bi*128;end=min(start+128,10000)
            assert ids.tolist()==list(range(start,end)) and clean.shape==(end-start,3,32,32) and clean.dtype==torch.float32
            assert bool(torch.isfinite(clean).all()) and clean.is_contiguous()
            negative=torch.clamp(clean-delta*1.5,-1,1).contiguous()
            input_packets.append(save(Path('private_run/inputs')/f'batch{bi+1:02d}.pt',{'source_ids':ids,'labels':labels,'negative_input':negative,'old_clean_packet':m}))
        rows={};logits={};calls=0
        for name in p['model_order']:
            model,state=prepare_model(torch,b['models'][name]);hits=eligible=0;seen=[];metas=[]
            with torch.inference_mode():
                for bi,m in enumerate(input_packets):
                    item=load(m);x=item['negative_input'];y=item['labels'];ids=item['source_ids']
                    out=model(x.to('cuda').contiguous()).cpu();calls+=1
                    assert out.shape==(len(y),10) and out.dtype==torch.float32 and bool(torch.isfinite(out).all())
                    pred=out.argmax(1);mask=y!=2;eligible+=int(mask.sum());hits+=int(((pred==2)&mask).sum());seen.extend(ids.tolist())
                    metas.append(save(Path('private_run/logits')/name/f'batch{bi+1:02d}.pt',{'source_ids':ids,'logits':out,'source_model':b['models'][name],'input_packet':m}))
                    write('PRIMARY_STATE.json',{'state':'running','pid':os.getpid(),'model':name,'batch':bi+1,'forward_calls':calls})
            assert seen==list(range(10000)) and eligible==9000
            c=b['positive_rows'][name]['clean_correct']
            rows[name]={'N':10000,'clean_correct':c,'CA_pct':c/100,'CA_reused_not_reinferred':True,'non_target_N':9000,'triggered_target_hits':hits,'ASR_pct':hits*100/9000}
            logits[name]=metas;unchanged(torch,model,state);del model,state;torch.cuda.empty_cache()
        assert calls==316
        limits=read(b['receipts']['baseline_fu_profile']['path'])['minimum_operational_latent_pair_gate']
        gates={name:diagnostic_gates(rows,name,limits) for name in ['minus_attack','plus_attack']}
        alignment=rows['minus_attack']['triggered_target_hits']>rows['plus_attack']['triggered_target_hits'] and b['positive_rows']['plus_attack']['triggered_target_hits']>b['positive_rows']['minus_attack']['triggered_target_hits']
        source_check()
        result={'state':'completed_primary_negative_sign_diagnosis','models':rows,'positive_models_reused':b['positive_rows'],'source_models':b['models'],'delta':b['delta'],'eval_sign':-1,'multiplier':1.5,'clip':[-1,1],'target':2,'input_packets':input_packets,'logit_packets':logits,'actual_forward_calls':calls,'actual_sample_forwards':40000,'clean_forward_calls':0,'positive_forward_calls':0,'alignment_rule_passed':alignment,'diagnostic_negative_gates':gates,'original_standard_minus_gate':b['original_standard_gate'],'original_standard_plus_gate':b['plus_standard_gate'],'standard_failure_replaced':False,'paper_sign_ambiguity_resolved_as_author_intent':False,'new_checkpoint_selected':False,'overall_goal_complete':False,'case_selection_sha256':sha(ROOT/'CASE_SELECTION.json'),'test_file_sha256':sha(test),'torch_version':str(torch.__version__),'device':torch.cuda.get_device_name(0)}
        write('RESULT.json',result);write('PRIMARY_STATE.json',{'state':'completed','pid':os.getpid(),'forward_calls':calls})
    else:
        from torchvision.datasets import CIFAR10
        result=read(ROOT/'RESULT.json')
        assert read(ROOT/'CASE_SELECTION.json')==selection and sha(ROOT/'CASE_SELECTION.json')==result['case_selection_sha256']
        assert result['source_models']==b['models'] and result['delta']==b['delta'] and result['eval_sign']==-1 and result['multiplier']==1.5
        assert result['device']==torch.cuda.get_device_name(0) and result['torch_version']==str(torch.__version__)
        raw=CIFAR10(b['data_root'],train=False,download=False);labels=list(map(int,raw.targets));assert len(labels)==10000 and sum(y!=2 for y in labels)==9000
        rows={};calls=0;max_error=0.
        for name in p['model_order']:
            model,state=prepare_model(torch,b['models'][name]);hits=eligible=0;seen=[]
            with torch.inference_mode():
                for bi,start in enumerate(range(0,10000,128)):
                    end=min(start+128,10000);y=labels[start:end];ids=list(range(start,end))
                    clean=torch.from_numpy(raw.data[start:end].copy()).permute(0,3,1,2).contiguous().float();clean.div_(255).sub_(.5).div_(.5)
                    negative=clean-delta*1.5;negative[negative>1]=1;negative[negative< -1]=-1
                    item=load(result['input_packets'][bi])
                    assert item['source_ids'].tolist()==ids and item['labels'].tolist()==y and torch.equal(negative,item['negative_input'])
                    packet=load(result['logit_packets'][name][bi]);assert packet['source_model']==b['models'][name] and packet['input_packet']==result['input_packets'][bi] and packet['source_ids'].tolist()==ids
                    out=model(negative.to('cuda').contiguous()).cpu();calls+=1;stored=packet['logits']
                    assert out.shape==stored.shape==(len(y),10) and out.dtype==stored.dtype==torch.float32 and bool(torch.isfinite(out).all()) and bool(torch.isfinite(stored).all())
                    max_error=max(max_error,float((out-stored).abs().max()));assert torch.allclose(out,stored,atol=1e-6,rtol=1e-5)
                    assert torch.equal(out.argmax(1),stored.argmax(1))
                    pred=[max(range(10),key=lambda k:row[k]) for row in out.tolist()]
                    eligible+=sum(label!=2 for label in y);hits+=sum(a==2 and label!=2 for a,label in zip(pred,y));seen.extend(ids)
                    write('INDEPENDENT_STATE.json',{'state':'running','pid':os.getpid(),'model':name,'batch':bi+1,'forward_calls':calls,'max_logit_abs_error':max_error})
            assert seen==list(range(10000)) and eligible==9000
            c=b['positive_rows'][name]['clean_correct']
            rows[name]={'N':10000,'clean_correct':c,'CA_pct':c/100,'CA_reused_not_reinferred':True,'non_target_N':9000,'triggered_target_hits':hits,'ASR_pct':hits*100/9000}
            assert rows[name]==result['models'][name]
            unchanged(torch,model,state);del model,state;torch.cuda.empty_cache()
        assert calls==316 and result['actual_forward_calls']==316 and result['actual_sample_forwards']==40000
        L=read(b['receipts']['baseline_fu_profile']['path'])['minimum_operational_latent_pair_gate'];gates={}
        for a in ['minus_attack','plus_attack']:
            c={k:rows[k]['clean_correct'] for k in ['pre','benign',a]};h={k:rows[k]['triggered_target_hits'] for k in ['pre','benign',a]}
            checks={'pre_ASR':h['pre']*100<=L['pre_ASR_max_pct']*9000,'attack_ASR':h[a]*100>=L['attack_ASR_min_pct']*9000,'attack_minus_pre':(h[a]-h['pre'])*100>=L['attack_minus_pre_ASR_min_pp']*9000,'attack_minus_benign':(h[a]-h['benign'])*100>=L['attack_minus_benign_FU_ASR_min_pp']*9000,'all_three_CA':min(c.values())*100>=L['all_three_CA_min_pct']*10000,'both_post_CA_drop':max(c['pre']-c['benign'],c['pre']-c[a])*100<=L['post_CA_drop_max_pp']*10000}
            gates[a]={'checks':checks,'passed':all(checks.values()),'diagnostic_negative_route_only':True,'standard_positive_failure_replaced':False}
        assert gates==result['diagnostic_negative_gates']
        alignment=rows['minus_attack']['triggered_target_hits']>rows['plus_attack']['triggered_target_hits'] and b['positive_rows']['plus_attack']['triggered_target_hits']>b['positive_rows']['minus_attack']['triggered_target_hits']
        assert alignment==result['alignment_rule_passed']
        source_check();assert sha(test)==b['test_file_sha256']
        verified={'state':'passed_new_negative_sign_independent_evaluation','primary_result_sha256':sha(ROOT/'RESULT.json'),'models':rows,'positive_models_reused':b['positive_rows'],'all10000_negative_inputs_exact':True,'all_negative_argmax_and_counts_exact':True,'max_logit_abs_error':max_error,'atol':1e-6,'rtol':1e-5,'actual_forward_calls':calls,'actual_sample_forwards':40000,'clean_forward_calls':0,'positive_forward_calls':0,'diagnostic_negative_gates':gates,'alignment_rule_passed':alignment,'standard_positive_failure_replaced':False,'author_intent_resolved':False,'overall_goal_complete':False}
        write('VERIFIED.json',verified);write('INDEPENDENT_STATE.json',{'state':'completed','pid':os.getpid(),'forward_calls':calls})
    print(json.dumps({'state':mode+'_completed','models':rows,'calls':calls}))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['primary','independent'],required=True);args=parser.parse_args()
    try:main(args.mode)
    except BaseException:
        write(args.mode.upper()+'_FAILURE.json',{'state':'failed_preserved','pid':os.getpid(),'traceback':traceback.format_exc()});raise
