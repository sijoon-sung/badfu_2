"""Read-only Windows process names/PIDs/parents. Never starts a shell or alters privileges."""
import ctypes as C
from ctypes import wintypes as W
import os

class PROCESSENTRY32W(C.Structure):
    _fields_ = [('dwSize', W.DWORD), ('cntUsage', W.DWORD), ('th32ProcessID', W.DWORD),
        ('th32DefaultHeapID', C.c_size_t), ('th32ModuleID', W.DWORD), ('cntThreads', W.DWORD),
        ('th32ParentProcessID', W.DWORD), ('pcPriClassBase', W.LONG), ('dwFlags', W.DWORD),
        ('szExeFile', W.WCHAR * 260)]



class UNICODE_STRING(C.Structure):
    _fields_ = [('Length', W.USHORT), ('MaximumLength', W.USHORT), ('Buffer', C.c_void_p)]


def _command_line(kernel, pid):
    # Limited read-only process metadata. No VM read/write, privileges, or shell child.
    kernel.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]; kernel.OpenProcess.restype = W.HANDLE
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        error = C.get_last_error()
        if error == 87: return None  # PID ceased to exist after the process snapshot.
        raise C.WinError(error)
    try:
        native = C.WinDLL('ntdll')
        native.NtQueryInformationProcess.argtypes = [W.HANDLE, W.ULONG, C.c_void_p, W.ULONG, C.POINTER(W.ULONG)]
        native.NtQueryInformationProcess.restype = W.LONG
        buffer = C.create_string_buffer(131072); returned = W.ULONG()
        status = native.NtQueryInformationProcess(handle, 60, buffer, len(buffer), C.byref(returned))
        if status < 0:
            kernel.GetExitCodeProcess.argtypes = [W.HANDLE, C.POINTER(W.DWORD)]; kernel.GetExitCodeProcess.restype = W.BOOL
            exit_code = W.DWORD()
            if kernel.GetExitCodeProcess(handle, C.byref(exit_code)) and exit_code.value != 259: return None
            raise OSError('Read-only ProcessCommandLineInformation pid='+str(pid)+' NTSTATUS='+hex(status & 0xffffffff))
        value = UNICODE_STRING.from_buffer(buffer)
        assert C.sizeof(UNICODE_STRING) == 16 and value.Length % 2 == 0 and value.Length > 0
        begin = C.addressof(buffer); pointer = value.Buffer
        assert pointer is not None and begin <= pointer and pointer + value.Length <= begin + len(buffer)
        return C.wstring_at(pointer, value.Length // 2)
    finally:
        if not kernel.CloseHandle(handle): raise C.WinError(C.get_last_error())


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
                command = k.GetCommandLineW() if v.th32ProcessID == os.getpid() else _command_line(k, int(v.th32ProcessID))
                if command is not None:
                    rows.append({'ProcessId': int(v.th32ProcessID), 'ParentProcessId': int(v.th32ParentProcessID),
                        'Name': v.szExeFile, 'CommandLine': command})
            ok = k.Process32NextW(handle, C.byref(v))
        if C.get_last_error() != 18: raise C.WinError(C.get_last_error())
    finally:
        if not k.CloseHandle(handle): raise C.WinError(C.get_last_error())
    assert len({r['ProcessId'] for r in rows}) == len(rows)
    return rows
