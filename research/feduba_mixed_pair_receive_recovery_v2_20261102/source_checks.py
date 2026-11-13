"""Repeatable stdlib source/receipt review; no old finite source_review or models."""
import ast,xml.etree.ElementTree as ET
from pathlib import Path
from receive_ops import ROOT,OLD,BASE,now,read,digest,frozen,own_processes,absence,task_absent
def validate_xml(text,p):
    # Task Scheduler documented schema: no automatic triggers/restarts, own interactive Limited account.
    root=ET.fromstring(text);ns={'t':'http://schemas.microsoft.com/windows/2004/02/mit/task'}
    get=lambda path:root.findtext(path,namespaces=ns)
    assert root.tag=='{'+ns['t']+'}Task'
    assert get('t:Principals/t:Principal/t:UserId')==p['user_sid']
    assert get('t:Principals/t:Principal/t:LogonType')=='InteractiveToken'
    assert get('t:Principals/t:Principal/t:RunLevel')=='LeastPrivilege'
    triggers=root.find('t:Triggers',ns)
    assert triggers is None or len(triggers)==0
    assert root.find('t:Settings/t:RestartOnFailure',ns) is None
    assert get('t:Settings/t:MultipleInstancesPolicy')=='IgnoreNew'
    assert get('t:Settings/t:Hidden')=='true'
    assert get('t:Settings/t:ExecutionTimeLimit')=='PT0S'
    actions=root.find('t:Actions',ns);assert len(actions)==1
    assert Path(get('t:Actions/t:Exec/t:Command')).resolve()==Path(p['python']).resolve()
    assert get('t:Actions/t:Exec/t:Arguments')=='-B "'+str(ROOT/'receive_recovery.py').replace('\\','/')+'"'
    assert Path(get('t:Actions/t:Exec/t:WorkingDirectory')).resolve()==BASE
    return {'direct_python':True,'triggers':0,'automatic_restart':False,'run_level':'LeastPrivilege','hidden':True}
def main():
    p=frozen(publication=False);absence(p);assert not own_processes()
    syntax=[]
    for path in ROOT.glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'));syntax.append(path.name)
    raw=(ROOT/'receive_task.xml').read_bytes()
    assert raw.startswith(b'\xff\xfe')
    xml=raw.decode('utf-16')
    assert xml==(ROOT/'TASK_XML_VIEW.txt').read_text(encoding='utf-8')
    assert 'encoding="UTF-16"' in xml
    scheduler=validate_xml(xml,p)
    scheduler['BOM_and_declaration_match_UTF16']=True
    prior_task_absence=task_absent(p['prior_failed_stage']['task_name'])
    inventory=task_absent(p['task_name'])
    original=read(OLD/'DELIVERY_PROFILE.json')
    assert p['memory_guard']==original['memory_guard']
    assert p['case_ids']==original['case_ids']
    c=__import__('receive_ops').old_module();c.freeze()
    # The safe, verify, cpu_check, finite, digest functions are imported from the original frozen file.
    assert all(getattr(c,k).__code__.co_filename==str(OLD/'pair_review_common.py') for k in ['safe','verify','cpu_check','finite','digest'])
    catalogues={}
    for host,path in p['local_catalogues'].items():
        catalogue=read(path)
        assert all(case not in catalogue['cases'] for case in p['case_ids'].values())
        catalogues[host]={'sha256':digest(path),'case_count':len(catalogue['cases']),'new_cases_absent':True}
    from native_memory import memory_information
    result={'state':'passed_receive_only_source_review_no_model_or_storage_check','utc':now(),
            'python_AST':syntax,'original_frozen_storage_functions_reused':['safe','verify','cpu_check','finite','digest'],
            'original_source_files':len(read(OLD/'SOURCE_FREEZE.json')['files']),
            'original_monitors':len(read(OLD/'MONITOR_FREEZE.json')['files']),
            'memory_guard_identical':True,'memory':memory_information(),'scheduler':scheduler,
            'task_absence':inventory,'prior_failed_task_absence':prior_task_absence,'catalogues':catalogues,'model_loads':0,'model_queries':0,
            'archive_hash_or_extraction':False,'original_receiver_retry':False}
    import json
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    main()
