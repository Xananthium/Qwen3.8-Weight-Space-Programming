"""Portable, fail-closed import routing for the seven tested vLLM overrides.

Adapted from the tested profile hook: installed paths are resolved from the
local distribution instead of embedding the author's filesystem paths.
"""
import hashlib
import importlib.abc
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parent
_SPEC = json.loads((_ROOT / 'manifest.json').read_text())
_DIST = importlib.metadata.distribution('vllm')
if _DIST.version != _SPEC['vllm_version']:
    raise SystemExit('This overlay requires the pinned vLLM version')
_FILES = {}
for _row in _SPEC['files']:
    _installed = Path(_DIST.locate_file(_row['relative_path']))
    _override = _ROOT / 'overrides' / _row['relative_path']
    if hashlib.sha256(_installed.read_bytes()).hexdigest() != _row['original_sha256']:
        raise SystemExit('Installed vLLM source differs from the tested runtime: ' + _row['module'])
    if hashlib.sha256(_override.read_bytes()).hexdigest() != _row['patched_sha256']:
        raise SystemExit('Packaged override integrity mismatch: ' + _row['module'])
    if _row['module'] in sys.modules:
        raise SystemExit('Override installed after module import: ' + _row['module'])
    _FILES[_row['module']] = _override


class _PortableOverrides(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        override = _FILES.get(fullname)
        if override is not None:
            return importlib.util.spec_from_file_location(fullname, override)
        return None


sys.meta_path.insert(0, _PortableOverrides())
