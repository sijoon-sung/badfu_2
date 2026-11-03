"""Evaluation recovery adapter; no original finite main is called."""
from evaluation_io import ROOT, OLD, FOUNDATION, read, sha, tensor_path, original_recovery, require_published_run

def checked(meta):
    path=tensor_path(meta);assert sha(path)==meta['sha256'],str(path)
    if 'bytes' in meta:assert path.stat().st_size==meta['bytes'],str(path)

def foundation_history():return original_recovery().original_module().foundation_history()
