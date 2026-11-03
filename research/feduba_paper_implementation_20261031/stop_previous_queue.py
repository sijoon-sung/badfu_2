"""Stop only the identified idle FUBA queue after the user's target correction."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
OLD = Path('D:/FUBA_SEED_REPRO_20261031')
TASK = 'Codex-FUBA-ten-seed-repro-recovery-20261031'


def ps(script):
    return subprocess.check_output(['powershell', '-NoProfile', '-NonInteractive', '-Command',
                                   "$ErrorActionPreference='Stop';" + script], text=True)


def main():
    assert not (ROOT / 'PREVIOUS_QUEUE_STOPPED.json').exists()
    state = json.loads((OLD / 'STUDY_STATE.json').read_text(encoding='utf-8'))
    assert state['state'] == 'waiting_for_resources' and state['seed'] == 4059094 and state['pid'] == 48688
    assert [r['seed'] for r in state['completed_rows']] == [20261023, 5129832]
    query = "Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python' -and $_.CommandLine -like '*FUBA_SEED_REPRO_20261031*'} | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    rows = json.loads(ps(query))
    rows = [rows] if isinstance(rows, dict) else rows
    assert len(rows) == 1 and rows[0]['ProcessId'] == 48688
    assert 'background_recovery.py' in rows[0]['CommandLine']
    task = json.loads(ps("Get-ScheduledTask -TaskName '" + TASK + "' | Select-Object TaskName,@{Name='Arguments';Expression={$_.Actions.Arguments}} | ConvertTo-Json -Compress"))
    assert task['TaskName'] == TASK and 'D:/FUBA_SEED_REPRO_20261031/background_recovery.py' in task['Arguments']
    with (ROOT / 'BEFORE_QUEUE_STOP.json').open('x', encoding='utf-8', newline='\n') as f:
        json.dump({'state': state, 'processes': rows, 'task': task}, f, indent=2); f.write('\n')
    ps("Stop-ScheduledTask -TaskName '" + TASK + "'; Disable-ScheduledTask -TaskName '" + TASK + "' | Out-Null")
    for _ in range(50):
        remaining = ps(query).strip()
        if not remaining:
            break
        time.sleep(.1)
    assert not remaining, 'Preserve state and diagnose remaining own process; do not launch another queue'
    result = {'state': 'stopped_by_user_target_change', 'previous_target': 'stcebra/FUBA',
              'active_target': 'ity207/FedUBA_STG_SSS_BEA', 'task': TASK, 'own_parent_pid_stopped': 48688,
              'previous_state': state, 'completed_rows_preserved': 2, 'unstarted_rows_preserved': 8,
              'other_apps_stopped': False, 'models_profiles_sources_modified': False,
              'old_task_disabled': True, 'created_unix': time.time(),
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    for target in [ROOT / 'PREVIOUS_QUEUE_STOPPED.json', OLD / 'STOPPED_BY_USER_RETARGET_FEDUBA.json']:
        with target.open('x', encoding='utf-8', newline='\n') as f:
            json.dump(result, f, indent=2); f.write('\n')
    print(json.dumps({'state': result['state'], 'completed_rows_preserved': 2,
                      'unstarted_rows_preserved': 8, 'other_apps_stopped': False}))


if __name__ == '__main__':
    main()
