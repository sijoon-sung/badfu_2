"""Read Windows memory counters directly; no subprocess/JSON, torch, or mutation."""
import ctypes
from ctypes import wintypes


class PerformanceInformation(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD)] + [(name, ctypes.c_size_t) for name in [
        'CommitTotal', 'CommitLimit', 'CommitPeak', 'PhysicalTotal', 'PhysicalAvailable',
        'SystemCache', 'KernelTotal', 'KernelPaged', 'KernelNonpaged', 'PageSize']
    ] + [(name, wintypes.DWORD) for name in ['HandleCount', 'ProcessCount', 'ThreadCount']]


def memory_information():
    assert ctypes.sizeof(ctypes.c_void_p) == 8
    assert ctypes.sizeof(PerformanceInformation) == 104
    info = PerformanceInformation()
    info.cb = ctypes.sizeof(info)
    api = ctypes.WinDLL('psapi.dll', use_last_error=True).GetPerformanceInfo
    api.argtypes = [ctypes.POINTER(PerformanceInformation), wintypes.DWORD]
    api.restype = wintypes.BOOL
    if not api(ctypes.byref(info), info.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    page = int(info.PageSize)
    assert page > 0 and page & (page - 1) == 0
    assert 0 <= info.PhysicalAvailable <= info.PhysicalTotal
    assert 0 <= info.CommitTotal <= info.CommitLimit
    return {'getter': 'Windows_GetPerformanceInfo', 'structure_bytes': info.cb,
            'page_bytes': page, 'availableBytes': int(info.PhysicalAvailable) * page,
            'committedBytes': int(info.CommitTotal) * page, 'commitLimit': int(info.CommitLimit) * page}
