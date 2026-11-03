"""Recovery adapter: unchanged original metadata gates and explicit old input routing."""
from pathlib import Path
from recovery_io import ROOT, OLD, FOUNDATION, read, sha, tensor_path, original_module, require_published_run


def checked(meta):
    path = tensor_path(meta)
    assert sha(path) == meta['sha256'], str(path)
    if 'bytes' in meta: assert path.stat().st_size == meta['bytes'], str(path)


def foundation_history():
    return original_module().foundation_history()
