"""Actual receiver CPU runtime probe. Called only after actual publication/admission."""
import json,os,sys,traceback
from receive_common import ROOT,sha,record,source_checks,runtime_files,admission

def main():
    p=source_checks(actual=True);assert list(sys.version_info[:3])==p['runtime']['python_version'];runtime_files(p)
    assert os.environ.get('CUDA_VISIBLE_DEVICES')=='-1';record('RUNTIME_PROBE_ADMISSION.json',admission(p))
    import torch
    assert torch.__version__==p['runtime']['torch_version'] and not torch.cuda.is_initialized()
    value=torch.zeros(1,device='cpu');assert value.device.type=='cpu' and bool(torch.isfinite(value).all()) and not torch.cuda.is_initialized()
    record('CPU_RUNTIME_VERIFIED.json',{'state':'usable_declared_CPU_runtime_verified','python_version':list(sys.version_info[:3]),'torch_version':torch.__version__,'torch_imported':True,'CPU_scalar_probe':True,'model_loads':0,'model_forward_calls':0,'CUDA_initialized':False,'run_freeze_sha256':sha(ROOT/'RUN_FREEZE.json')});print(json.dumps({'state':'usable_declared_CPU_runtime_verified'}))
if __name__=='__main__':
    try:main()
    except BaseException:record('CPU_RUNTIME_FAILURE.json',{'state':'failed_preserved_no_retry','traceback':traceback.format_exc()});raise
