"""Read-only Windows process names/PIDs/parents. Never starts a shell or alters privileges."""
import ctypes as C
from ctypes import wintypes as W
import os

class PROCESSENTRY32W(C.Structure):
    _fields_ = [('dwSize', W.DWORD), ('cntUsage', W.DWORD), ('th32ProcessID', W.DWORD),
        ('th32DefaultHeapID', C.c_size_t), ('th32ModuleID', W.DWORD), ('cntThreads', W.DWORD),
        ('th32ParentProcessID', W.DWORD), ('pcPriClassBase', W.LONG), ('dwFlags', W.DWORD),
        ('szExeFile', W.WCHAR * 260)]


def processes():
    assert os.name == 'nt' and C.sizeof(C.c_void_p) == 8 and C.sizeof(PROCESSENTRY32W) == 568
    k = C.WinDLL('kernel32', use_last_error=True)
    k.CreateToolhelp32Snapshot.argtypes = [W.DWORD, W.DWORD]; k.CreateToolhelp32Snapshot.restype = W.HANDLE
    k.Process32FirstW.argtypes = k.Process32NextW.argtypes = [W.HANDLE, C.POINTER(PROCESSENTRY32W)]
    k.Process32FirstW.restype = k.Process32NextW.restype = W.BOOL
    k.CloseHandle.argtypes = [W.HANDLE]; k.CloseHandle.restype = W.BOOL
    k.GetCommandLineW.argtypes = []; k.GetCommandLineW.restype = W.LPWSTR
    handle = k.CreateToolhelp32Snapshot(2, 0)
    if handle == C.c_void_p(-1).value: raise C.WinError(C.get_last_error())
    rows = []
    try:
        v = PROCESSENTRY32W(); v.dwSize = C.sizeof(v)
        ok = k.Process32FirstW(handle, C.byref(v))
        if not ok: raise C.WinError(C.get_last_error())
        while ok:
            if v.szExeFile.lower() in ['python.exe', 'pythonw.exe', 'mpiexec.exe']:
                rows.append({'ProcessId': int(v.th32ProcessID), 'ParentProcessId': int(v.th32ParentProcessID),
                    'Name': v.szExeFile, 'CommandLine': k.GetCommandLineW() if v.th32ProcessID == os.getpid() else None})
            ok = k.Process32NextW(handle, C.byref(v))
        if C.get_last_error() != 18: raise C.WinError(C.get_last_error())
    finally:
        if not k.CloseHandle(handle): raise C.WinError(C.get_last_error())
    assert len({r['ProcessId'] for r in rows}) == len(rows)
    return rows
