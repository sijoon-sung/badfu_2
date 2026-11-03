import hashlib,json,subprocess
from pathlib import Path
b=Path(r'C:/Users/sijoo/Documents/ChatGPT/badFU');p=Path(r'C:/Users/sijoo/Documents/ChatGPT/badFU-pr-detection-20261031');rel='research/feduba_historical_selector_pin_review_20261103'
names=json.loads((b/'tmp/historical_selector_pin_public_files.json').read_text(encoding='utf-8'))
subprocess.run(['git','add','--',*[rel+'/'+n for n in names]],cwd=p,check=True,capture_output=True)
for root in [b,p]:subprocess.run(['C:/ProgramData/miniconda3/python.exe','-B','research/index_tools/rebuild_index.py'],cwd=root,check=True)
subprocess.run(['C:/ProgramData/miniconda3/python.exe','-B','research/index_tools/rebuild_github.py'],cwd=p,check=True)
generated=['research/experiment_registry.json','research/INDEX.md','research/EXPERIMENT_CARDS.md','research/EXPERIMENT_FOLDERS.md','research/INDEX_AUDIT.json','experiments/01-reproduction/R03-feduba-reproduction/SOURCES.md','experiments/01-reproduction/R03-feduba-reproduction/README.md','experiments/01-reproduction/README.md','experiments/README.md']
subprocess.run(['git','add','--',*generated],cwd=p,check=True,capture_output=True)
allowed=set(generated+[rel+'/'+n for n in names]);staged=set(subprocess.check_output(['git','diff','--cached','--name-only'],cwd=p,text=True).splitlines());assert staged<=allowed,(staged-allowed)
for n in names:assert (b/rel/n).read_bytes()==(p/rel/n).read_bytes()==subprocess.check_output(['git','show',':'+rel+'/'+n],cwd=p),n
import hashlib
assert hashlib.sha256((b/'research/00_trajectories/catalog.json').read_bytes()).hexdigest()=='557425237090c464173f332e1ef0da01eb6eb9b0dec287023278044526590f2b'
assert hashlib.sha256((p/'research/00_trajectories/catalog.json').read_bytes()).hexdigest()=='8f923189073d9ed56e6246ee51c921e4b7fc0c2dff9830868139ac645fe91c76'
for root in [b,p]:subprocess.run(['C:/ProgramData/miniconda3/python.exe','-B','research/index_tools/rebuild_index.py','--check'],cwd=root,check=True)
subprocess.run(['C:/ProgramData/miniconda3/python.exe','-B','research/index_tools/rebuild_github.py','--check'],cwd=p,check=True)
subprocess.run(['git','commit','-F',str(b/'tmp/historical_selector_pin_message.txt')],cwd=p,check=True,capture_output=True)
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=p,text=True).strip();subprocess.run(['git','push','origin','HEAD:codex/detection-claim-audit-20261031'],cwd=p,check=True,capture_output=True)
(b/'tmp/historical_selector_pin_commit.json').write_text(json.dumps({'commit':commit}),encoding='utf-8');print(json.dumps({'actual_profile_commit':commit,'new_public_files_exact':len(names)}))
