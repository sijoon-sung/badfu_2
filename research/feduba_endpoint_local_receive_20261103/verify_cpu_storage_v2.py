"""Exactly four local strictCPU storage checks; no real-data inference or training."""
import gc,importlib.util,json,os,sys,traceback
from receive_common_v2 import ROOT,read,sha,record,event,source_checks,runtime_files,admission,verify_packet,packet_path

def main():
    p=source_checks(actual=True);assert list(sys.version_info[:3])==p['runtime']['python_version'];runtime_files(p)
    assert os.environ.get('CUDA_VISIBLE_DEVICES')=='-1' and read(ROOT/'CPU_RUNTIME_VERIFIED_V2.json')['state']=='usable_declared_CPU_runtime_verified'
    record('CPU_STORAGE_ADMISSION_V2.json',admission(p));guard=verify_packet(p);record('CPU_PRELOAD_PACKET_GUARD_V2.json',guard)
    import torch
    assert torch.__version__==p['runtime']['torch_version'] and not torch.cuda.is_initialized();torch.set_num_threads(1);torch.set_num_interop_threads(1)
    root=packet_path(p);spec=importlib.util.spec_from_file_location('received_endpoint_architecture',root/'model_reference.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rows=[]
    for name in p['model_order']:
        meta=p['models'][name];file=root/meta['file'];assert sha(file)==meta['sha256'] and meta['payload_key'] is None
        event({'stage':'CPU_model_load_begin','name':name,'sha256':meta['sha256']})
        state=torch.load(file,map_location='cpu',weights_only=True);model=module.ResNet18().cpu();template=model.state_dict()
        assert isinstance(state,dict) and state.keys()==template.keys() and all(state[k].shape==v.shape and state[k].dtype==v.dtype for k,v in template.items())
        model.load_state_dict(state,strict=True);model.eval()
        assert isinstance(state,dict) and all(isinstance(v,torch.Tensor) and v.device.type=='cpu' and bool(torch.isfinite(v).all()) for v in state.values())
        with torch.inference_mode():out=model(torch.zeros(tuple(p['CPU_zero_input_shape']),dtype=torch.float32,device='cpu').contiguous())
        assert list(out.shape)==p['CPU_output_shape'] and bool(torch.isfinite(out).all()) and not torch.cuda.is_initialized() and sha(file)==meta['sha256']
        row={'name':name,'sha256':meta['sha256'],'bytes':file.stat().st_size,'payload_key':None,'strict_CPU_load':True,'state_all_finite':True,'state_shapes_and_dtypes_exact':True,'zero1_output_shape':list(out.shape),'zero1_output_finite':True,'CPU_forward_calls':1};rows.append(row);event({'stage':'CPU_model_verified',**row});del state,model,template,out;gc.collect()
    assert len(rows)==4 and not torch.cuda.is_initialized()
    record('CPU_STORAGE_VERIFIED_V2.json',{'state':'passed_four_endpoint_strict_CPU_finite_zero1_storage_checks','rows':rows,'torch_version':torch.__version__,'python_version':list(sys.version_info[:3]),'model_loads':4,'zero1_forward_calls':4,'real_data_sample_forwards':0,'training_or_optimizer':False,'CUDA_initialized':False,'manifest_sha256':p['manifest_sha256'],'seal_sha256':p['seal_sha256'],'run_freeze_sha256':sha(ROOT/'RUN_FREEZE_V2.json'),'performance_success':False,'catalogue_registration_complete':False})
    print(json.dumps({'state':'passed_four_endpoint_strict_CPU_finite_zero1_storage_checks','models':4,'zero1_calls':4}))
if __name__=='__main__':
    try:main()
    except BaseException:record('CPU_STORAGE_FAILURE_V2.json',{'state':'failed_preserved_no_retry','traceback':traceback.format_exc()});raise
