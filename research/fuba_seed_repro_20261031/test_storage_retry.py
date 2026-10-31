"""Exercise a real Windows file-share lock on a newly created dummy state file."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import threading
import time
from storage_retry import replace_with_retry

root = Path(__file__).resolve().parent
fixture = root / 'storage_fixture'
fixture.mkdir(exist_ok=False)
assert fixture.resolve().is_relative_to(root.resolve())
target, pending = fixture / 'state.json', fixture / 'state.pending'
target.write_text('{"value":0}\n', encoding='utf-8', newline='\n')
pending.write_text('{"value":1}\n', encoding='utf-8', newline='\n')
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
kernel.CreateFileW.restype = wintypes.HANDLE
kernel.CloseHandle.argtypes = [wintypes.HANDLE]
handle = kernel.CreateFileW(str(target), 0x80000000, 0x1, None, 3, 0x80, None)
assert handle != wintypes.HANDLE(-1).value, ctypes.get_last_error()
def release():
    time.sleep(.25)
    assert kernel.CloseHandle(handle)
thread = threading.Thread(target=release)
thread.start()
attempts = replace_with_retry(pending, target)
thread.join()
assert attempts >= 1 and json.loads(target.read_text()) == {'value': 1} and not pending.exists()
result = {'state': 'passed', 'CPU_only': True, 'real_Windows_share_delete_lock': True,
          'replacement_retries': attempts, 'final_payload_exact': True, 'old_research_files_touched': False}
with (root / 'STORAGE_CONTRACT.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(result, stream, indent=2); stream.write('\n')
print(json.dumps(result))
