"""Source and exact input bindings for failed-prefix storage diagnosis; no torch import."""
import hashlib,importlib.metadata,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(65536),b''):h.update(b)
 return h.hexdigest()
def checked(m):
 p=Path(m['path']);assert p.is_absolute() and sha(p)==m['sha256']
 if 'bytes' in m:assert p.stat().st_size==m['bytes']
def profile():
 p=read(ROOT/'PROFILE.json');assert p['launch_enabled'] and ROOT==Path(p['execution_root'])
 pub=read(ROOT/'SOURCE_PUBLICATION.json');assert pub['state']=='published_failed_prefix_review_and_new3model_CPU_archive_before_execution' and pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
 for n,d in read(ROOT/'SOURCE_FREEZE.json')['files'].items():assert sha(ROOT/n)==d,n
 assert list(sys.version_info[:3])==p['python_version']
 for n,v in p['package_versions'].items():assert importlib.metadata.version(n)==v
 for m in p['inputs'].values():checked(m)
 for m in p['new_review_models'].values():checked(m)
 assert sha(ROOT/'FAILED_EVALUATION_TERMINAL_OBSERVATION.json')==p['terminal_observation_sha256']
 return p
