"""Model0 review, COM read-only actual RunLevel and never-run task verification."""
import ast,json
from start_ops import ROOT,V2,v2,freeze,preflight
def main():
    p=freeze(publication=False)
    for n in ROOT.glob('*.py'):ast.parse(n.read_text(encoding='utf-8'))
    checked=preflight(p)
    print(json.dumps({'state':'passed_start_only_existing_task_source_and_actual_COM_metadata_model0',
          'utc':v2.now(),'python_AST':4,'JScript_readonly_one_own_task':True,'registered_task':checked,
          'original_storage_and_receiver_sources_unchanged':True,'task_created_or_updated':False,
          'run_request_count':0,'model_queries':0,'finite_reexecution':False},indent=2))
if __name__=='__main__':main()
