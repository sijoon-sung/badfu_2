"""Once source/native metadata probe; no model, torch import, GPU, or scientific fixture."""
import ast
import json
import os
import sys
import time
import traceback
from evaluation_io import ROOT, OLD, RECOVERY, read, sha, once, source_check, input_path, tensor_path, writable
from native_processes import processes


def main():
    p=source_check();pub=read(ROOT/'SOURCE_PUBLICATION.json')
    assert pub['state']=='published_closed_evaluation_recovery_source_before_probe_prepare'
    assert pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    once('METADATA_PROBE_ONCE.json',{'pid':os.getpid(),'model_forwards':0})
    for f in ROOT.glob('*.py'):ast.parse(f.read_text(encoding='utf-8'))
    for name,digest in p['helper_original_bytes'].items():assert sha(ROOT/name)==sha(RECOVERY/name)==digest,name
    assert input_path(ROOT/'FU_attack_VERIFIED.json')==RECOVERY/'FU_attack_VERIFIED.json'
    assert input_path(ROOT/'FU_benign_RESULT.json')==OLD/'FU_benign_RESULT.json'
    assert input_path(ROOT/'PAIR_EVAL_RESULT.json')==ROOT/'PAIR_EVAL_RESULT.json'
    assert input_path(ROOT/'RECOVERY_INPUT_BINDING.json')==RECOVERY/'RECOVERY_INPUT_BINDING.json'
    rejected=0
    for f in [RECOVERY/'PAIR_EVAL_RESULT.json',ROOT/'FU_attack_RESULT.json',ROOT/'SSS_RESULT.json']:
        try:writable(f)
        except AssertionError:rejected+=1
    assert rejected==3 and not (ROOT/'LAUNCH_PROFILE.json').exists()
    values=processes();own=next(v for v in values if v['ProcessId']==os.getpid())
    assert own['ParentProcessId']==os.getppid() and 'source_probe.py' in own['CommandLine']
    assert 'torch' not in sys.modules
    once('METADATA_PROBE_RESULT.json',{'state':'passed_new_native_metadata_source_probe',
        'Python_AST_files':len(list(ROOT.glob('*.py'))),'unchanged_helpers':5,'read_only_write_rejections':3,
        'native_process_rows':values,'own_native_row':own,'model_loads':0,'model_forwards':0,
        'torch_imported':False,'scientific_fixture_reexecuted':False,'probe_hold_seconds_for_external_CIM':25})
    time.sleep(25)
    once('METADATA_PROBE_DONE.json',{'state':'native_metadata_probe_completed_no_model','pid':os.getpid()})
    print(json.dumps({'state':'native_metadata_probe_completed_no_model','pid':os.getpid()}))


if __name__=='__main__':
    try:main()
    except BaseException:
        once('METADATA_PROBE_FAILURE.json',{'state':'failed_preserved','traceback':traceback.format_exc()});raise
