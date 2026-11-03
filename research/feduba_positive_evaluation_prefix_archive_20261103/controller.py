"""One CPU-only prefix review and new3model storage archive, no inference retry."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
import json,shutil,subprocess,sys,time,traceback
from binding import ROOT,profile,read,sha
from native_memory import memory_information
from native_processes import processes

def once(n,v):
 with (ROOT/n).open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def guard(p):
 m=memory_information();g=p['guard']
 busy=m['availableBytes']<g['native_available_GiB']*2**30 or m['commitLimit']-m['committedBytes']<g['commit_free_GiB']*2**30 or shutil.disk_usage(ROOT).free<g['disk_free_GiB']*2**30
 peers=[r for r in processes() if r['ProcessId'] not in [os.getpid(),os.getppid()] and any(t in r['CommandLine'].lower() for t in p['known_training_process_tokens'])]
 gpu=subprocess.check_output(['C:/Windows/System32/nvidia-smi.exe','--query-gpu=utilization.gpu,memory.free,memory.used','--format=csv,noheader,nounits'],text=True).strip();util,free,used=[int(v.strip()) for v in gpu.split(',')]
 busy=busy or bool(peers) or util>g['GPU_util_max'] or free<g['GPU_free_MiB_min'] or used>g['GPU_used_MiB_max']
 return not busy,{'native_memory':m,'GPU_util':util,'GPU_free_MiB':free,'GPU_used_MiB':used,'competing_trainers':len(peers)}
def main():
 p=profile();once('CONTROLLER_ONCE.json',{'pid':os.getpid(),'source_publication_sha256':sha(ROOT/'SOURCE_PUBLICATION.json')})
 for script in ['review_prefix.py','export_review.py']:
  started=time.monotonic()
  while True:
   ready,resources=guard(p)
   if ready:break
   assert time.monotonic()-started<p['guard']['wait_seconds'],'Fixed resource wait exhausted'
   time.sleep(p['guard']['poll_seconds'])
  with (ROOT/('console_'+script+'.log')).open('x',encoding='utf-8') as f:
   child=subprocess.Popen([sys.executable,'-B','-u',str(ROOT/script)],cwd=ROOT,env=dict(os.environ),stdout=f,stderr=subprocess.STDOUT)
   once(script+'.STARTED.json',{'parent':os.getpid(),'child':child.pid,'resources':resources})
   code=child.wait()
  assert code==0,script+' exit='+str(code)
 once('COMPLETION.json',{'state':'completed_failed_eval_prefix_review_and_new_CPU_archive','prefix_review_sha256':sha(ROOT/'PREFIX_REVIEW_RESULT.json'),'remote_review_sha256':sha(ROOT/'REMOTE_CHECKPOINT_REVIEW.json'),'original_evaluation_task_exit':1,'original_independent_VERIFIED_absent':True,'original_verifier_completed_successfully':False,'new_bulk_model_inference_calls':0,'new_CPU_zero1_calls':3,'local_delivery_complete':False,'overall_goal_complete':False})
 print(json.dumps(read(ROOT/'COMPLETION.json')))
if __name__=='__main__':
 try:main()
 except BaseException:
  once('CONTROLLER_FAILURE.json',{'state':'failed_preserved','pid':os.getpid(),'traceback':traceback.format_exc()});raise
