"""One-time DISLAB CPU verification of the exact same finite, frozen checks."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    payload = json.loads((HERE/'REMOTE_PAYLOAD.json').read_text(encoding='utf-8'))
    for rel, digest in payload['files'].items():
        assert sha(HERE/rel) == digest, rel
    with (HERE/'REMOTE_STARTED.json').open('x', encoding='utf-8') as f:
        json.dump({'pid': os.getpid(), 'payload_sha256': sha(HERE/'REMOTE_PAYLOAD.json')}, f)
    commands = [
        [sys.executable, str(HERE/'verify_claims.py')],
        [sys.executable, str(HERE/'verify_claims.py'), '--check'],
        [sys.executable, str(HERE/'audit_sources.py'), '--source-dir', str(HERE/'upstream')],
        [sys.executable, str(HERE/'audit_sources.py'), '--source-dir', str(HERE/'upstream'), '--check'],
    ]
    results = []
    for command in commands:
        result = subprocess.run(command, cwd=HERE, text=True, encoding='utf-8',
                                errors='replace', capture_output=True)
        results.append({'script': Path(command[1]).name, 'check': '--check' in command,
                        'returncode': result.returncode, 'stdout': result.stdout,
                        'stderr': result.stderr})
        (HERE/'REMOTE_COMMANDS.json').write_text(json.dumps(results, indent=2)+'\n', encoding='utf-8')
        assert result.returncode == 0, results[-1]
    receipt = {'state': 'passed_DISLAB_independent_CPU_checks',
        'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'location': 'DISLAB', 'python': platform.python_version(),
        'frozen_payload_sha256': sha(HERE/'REMOTE_PAYLOAD.json'),
        'plan_sha256': sha(HERE/'PLAN.json'), 'commands_succeeded': len(results),
        'new_training': False, 'GPU_used': False, 'upstream_imported': False,
        'files': {n: sha(HERE/n) for n in ['MATH_RESULTS.json','SOURCE_AUDIT.json','REMOTE_COMMANDS.json']}}
    (HERE/'REMOTE_RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(receipt))

if __name__ == '__main__':
    main()
