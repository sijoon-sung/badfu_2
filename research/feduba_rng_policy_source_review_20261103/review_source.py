"""One stdlib source-scope review; never executes/imports an upstream module or RNG."""
import ast,hashlib,json,os,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,v):
 with (ROOT/n).open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
class Census(ast.NodeVisitor):
 def __init__(self,name):self.name=name;self.scope=[];self.seeds=[];self.loaders=[]
 def visit_FunctionDef(self,n):
  self.scope.append(n.name);self.generic_visit(n);self.scope.pop()
 def visit_ClassDef(self,n):
  self.scope.append(n.name);self.generic_visit(n);self.scope.pop()
 def visit_Call(self,n):
  q=ast.unparse(n.func)
  if q in ['torch.manual_seed','np.random.seed','random.seed','torch.cuda.manual_seed_all','seed'] or q.endswith('.manual_seed'):
   self.seeds.append({'file':self.name,'line':n.lineno,'scope':'.'.join(self.scope) or '<module>','call':q,'arguments':[ast.unparse(x) for x in n.args]})
  if q.endswith('DataLoader'):
   self.loaders.append({'file':self.name,'line':n.lineno,'scope':'.'.join(self.scope) or '<module>','explicit_generator_keyword':any(k.arg=='generator' for k in n.keywords),'double_star_kwargs_present':any(k.arg is None for k in n.keywords)})
  self.generic_visit(n)
def evaluate_seed(n,env):
 if isinstance(n,ast.Constant) and type(n.value) is int:return n.value
 if isinstance(n,ast.Name):return env[n.id]
 if isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Add,ast.Mult)):
  a,b=evaluate_seed(n.left,env),evaluate_seed(n.right,env);return a+b if isinstance(n.op,ast.Add) else a*b
 raise AssertionError('Unexpected seed expression')
def main():
 p=read(ROOT/'PROFILE.json');pub=read(ROOT/'SOURCE_PUBLICATION.json');binding=read(ROOT/'INPUT_BINDING.json')
 assert p['launch_enabled'] and ROOT==Path(p['execution_root'])
 assert pub['state']=='published_readonly_rng_policy_source_review_before_AST' and pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
 for n,d in read(ROOT/'SOURCE_FREEZE.json')['files'].items():assert sha(ROOT/n)==d,n
 assert p['input_binding_sha256']==sha(ROOT/'INPUT_BINDING.json')
 texts={}
 for n,m in binding['inputs'].items():
  path=Path(m['path']);assert sha(path)==m['sha256'],n;texts[n]=path.read_text(encoding='utf-8')
 write('ONCE.json',{'pid':os.getpid(),'model_imports':0,'RNG_operations':0})
 trees={n:ast.parse(s) for n,s in texts.items() if n.endswith('.py')};rows={}
 for n,tree in trees.items():v=Census(n);v.visit(tree);rows[n]={'seed_calls':v.seeds,'DataLoader_calls':v.loaders}
 public_seeds=[x for n,v in rows.items() if n.startswith('public/') for x in v['seed_calls']]
 public_loaders=[x for n,v in rows.items() if n.startswith('public/') for x in v['DataLoader_calls']]
 assert len(public_seeds)==4 and not any(x['explicit_generator_keyword'] for x in public_loaders)
 module_seeds=[x for x in public_seeds if x['scope']=='<module>']
 assert len(module_seeds)==3 and all(x['file']=='public/trigger_generate_function.py' and x['arguments']==['random_seed'] for x in module_seeds)
 trigger=trees['public/trigger_generate_function.py'];seed_assign=next(n for n in trigger.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='random_seed' for t in n.targets));assert seed_assign.value.value==0
 entry=[x for x in public_seeds if x['file']=='public/Fed_Unlearn_main.py'];assert len(entry)==1 and entry[0]['scope']=='Federated_Unlearning' and entry[0]['arguments']==['FL_params.seed']
 main_tree=trees['public/Fed_Unlearn_main.py'];defaults=[n for n in ast.walk(main_tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Attribute) and isinstance(t.value,ast.Name) and t.value.id=='self' and t.attr=='seed' for t in n.targets)];assert len(defaults)==1 and defaults[0].value.value==42
 fn=next(n for n in trigger.body if isinstance(n,ast.FunctionDef) and n.name=='trigger_generate')
 cache=next(n for n in ast.walk(fn) if isinstance(n,ast.If) and 'noise_path' in ast.unparse(n.test))
 constructors=[n.lineno for n in ast.walk(fn) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='model_init']
 assert len(constructors)==2 and all(n<cache.lineno for n in constructors)
 missing_imports=[n.lineno for n in trigger.body if isinstance(n,ast.ImportFrom) and n.module in ['models','utils']]
 assert len(missing_imports)==2 and max(missing_imports)<min(x['line'] for x in module_seeds)
 common={}
 for n in ['fu_core.py','fu_training.py','runtime_common.py']:
  a,b=binding['inputs']['positive/'+n],binding['inputs']['minus/'+n];assert a['sha256']==b['sha256'];common[n]=a['sha256']
 train=rows['positive/fu_training.py'];assert any(x['call']=='seed' and x['scope']=='train_role' for x in train['seed_calls'])
 assert any(x['scope']=='train_role' and x['explicit_generator_keyword'] for x in train['DataLoader_calls'])
 sched=next(n for n in trees['positive/fu_core.py'].body if isinstance(n,ast.FunctionDef) and n.name=='local_schedule');ret=next(n for n in sched.body if isinstance(n,ast.Return));expr=next(v for k,v in zip(ret.value.keys,ret.value.values) if isinstance(k,ast.Constant) and k.value=='seed')
 schedule=[{'round':r,'client':c,'seed':evaluate_seed(expr,{'round_number':r,'client':c})} for r in range(1,21) for c in p['fixed_clients']]
 assert len(schedule)==len({x['seed'] for x in schedule})==200 and min(x['seed'] for x in schedule)==510242 and max(x['seed'] for x in schedule)==701942
 actual_audit=read(binding['inputs']['positive/FU_attack_VERIFIED.json']['path']);assert actual_audit['state']=='passed' and actual_audit['new_trained_roles']==200
 assert 'torch' not in sys.modules
 result={'state':'completed_readonly_rng_policy_source_review','source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'public_seed_calls':public_seeds,'public_DataLoader_calls':public_loaders,'public_module_seed_literal':0,'public_main_torch_seed_default':42,'missing_imports_precede_module_seed_lines':missing_imports,'module_seed_execution_claim':'conditional source intent only; unresolved imports/helpers prevent untouched execution certification','trigger_model_constructor_lines':constructors,'trigger_noise_cache_if_line':cache.lineno,'trigger_noise_cache_condition':ast.unparse(cache.test),'actual_call_census':{n:v for n,v in rows.items() if not n.startswith('public/')},'common_minus_plus_helper_hashes':common,'source_derived_FU_schedule':schedule,'schedule_is_new_RNG_state_replay':False,'common_policy_cannot_by_itself_explain_minus_plus_difference':True,'new_training_authorized':False,'verdict':'declared RNG boundary is structurally different; causal effect and unique author stream unvalidated/parked','model_loads':0,'tensor_payload_reads':0,'model_forwards':0,'RNG_operations':0,'optimizer_steps':0,'torch_imported':False}
 write('RESULT.json',result);write('COMPLETION.json',{'state':'completed_readonly_rng_policy_source_review','result_sha256':sha(ROOT/'RESULT.json'),'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'model_loads':0,'new_training_authorized':False,'overall_goal_complete':False})
 print(json.dumps({'state':result['state'],'public_seed_calls':len(public_seeds),'public_explicit_generator_keywords':0,'source_derived_roles':len(schedule),'model_forwards':0,'RNG_operations':0,'new_training_authorized':False}))
if __name__=='__main__':
 try:main()
 except BaseException:
  write('FAILURE.json',{'state':'failed_preserved','traceback':traceback.format_exc()});raise
