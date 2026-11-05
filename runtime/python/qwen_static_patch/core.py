"""Startup validation and the exact tested rank-one arithmetic."""
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
from types import MappingProxyType

import numpy as np
import torch

COEFF_BUFFER = '_static_rankone_coeff'
U_BUFFER = '_static_rankone_u'


def sha256_file(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


@dataclass(frozen=True)
class LayerDelta:
    layer: int
    u: np.ndarray
    coeff: np.ndarray


@dataclass(frozen=True)
class PatchSpec:
    manifest_path: str
    candidate_path: str
    candidate_sha256: str
    base_model_path: str
    base_model_sha256: str
    base_identity: tuple
    alpha: float
    tensor_parallel_size: int
    input_size: int
    output_size: int
    deltas: object

    def matches_model(self, path):
        return str(Path(path).expanduser().resolve()) == self.base_model_path

    def verify_base_identity(self):
        stat = Path(self.base_model_path).stat()
        actual = (stat.st_size, stat.st_mtime_ns, stat.st_ino)
        if actual != self.base_identity:
            raise ValueError('Pinned base model stat identity changed')


def load_npz(path, expected_sha256, input_size, output_size, layer_count=64):
    """Read once at startup. Enforce the exact float32 sidecar schema."""
    if sha256_file(path) != expected_sha256:
        raise ValueError('Candidate NPZ SHA256 mismatch')
    with np.load(path, allow_pickle=False) as archive:
        layers = archive['layers']
        if layers.ndim != 1 or layers.dtype.kind not in 'iu' or not len(layers):
            raise ValueError('layers must be a nonempty integer vector')
        ids = [int(n) for n in layers]
        if len(set(ids)) != len(ids) or any(n < 0 or n >= layer_count for n in ids):
            raise ValueError('Duplicate or out-of-range layer ID')
        expected_keys = {'layers'} | {f'{name}_{n}' for n in ids for name in ('u', 'coeff')}
        if set(archive.files) != expected_keys:
            raise ValueError('Unexpected or missing NPZ keys')
        result = {}
        for n in ids:
            values = []
            for name, width in [('u', output_size), ('coeff', input_size)]:
                value = archive[f'{name}_{n}']
                if value.dtype != np.float32 or value.shape != (width,):
                    raise ValueError(f'{name}_{n} must be float32 with shape({width},)')
                if not np.isfinite(value).all() or not np.any(value):
                    raise ValueError(f'{name}_{n} contains nonfinite values or is entirely zero')
                value = np.array(value, dtype=np.float32, copy=True, order='C')
                value.flags.writeable = False
                values.append(value)
            result[n] = LayerDelta(n, values[0], values[1])
    return MappingProxyType(result)


@lru_cache(maxsize=4)
def load_manifest(path):
    """Immutable startup snapshot; there are no manifest reads in forward."""
    path = Path(path).expanduser().resolve()
    data = json.loads(path.read_text())
    if data.get('schema_version') != 1:
        raise ValueError('Unsupported patch manifest schema')
    alpha = data['alpha']
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not math.isfinite(alpha) or alpha <= 0:
        raise ValueError('alpha must be a positive finite scalar')
    dims = data['dimensions']
    input_size, output_size = dims['input_size'], dims['output_size']
    tp_size = data['tensor_parallel_size']
    if any(type(v) is not int or v <= 0 for v in (input_size, output_size, tp_size)) or input_size % tp_size:
        raise ValueError('Invalid dimensions or TP partition')
    base = data['base_model']
    base_path = str(Path(base['path']).expanduser().resolve())
    base_sha = base['sha256']
    if len(base_sha) != 64 or any(c not in '0123456789abcdef' for c in base_sha):
        raise ValueError('Invalid base model SHA256 pin')
    candidate = data['candidate']
    candidate_path = str(Path(candidate['path']).expanduser().resolve())
    deltas = load_npz(candidate_path, candidate['sha256'], input_size, output_size)
    anchor = data.get('required_anchor')
    if anchor:
        n = anchor['layer']
        if n not in deltas or alpha != anchor['alpha']:
            raise ValueError('Required layer/global alpha anchor missing')
        for key in ('u', 'coeff'):
            digest = hashlib.sha256(getattr(deltas[n], key).tobytes()).hexdigest()
            if digest != anchor[f'{key}_sha256']:
                raise ValueError('Required anchor vector changed')
    spec = PatchSpec(str(path), candidate_path, candidate['sha256'], base_path, base_sha,
                     (base['st_size'], base['st_mtime_ns'], base['st_ino']),
                     float(alpha), tp_size, input_size, output_size, deltas)
    spec.verify_base_identity()
    # Frozen serving launchers already pin the original large artifact's stat
    # identity. A new builder must also verify its full SHA256 once. This
    # optional strict mode supports rehashing in each worker if desired.
    if data.get('verify_base_sha256_in_each_worker', False) and sha256_file(base_path) != base_sha:
        raise ValueError('Base model SHA256 mismatch')
    return spec


def bind_buffers(layer, delta, rank, tp_size, expected_tp_size):
    """Install FP32 nonpersistent buffers on the loaded local weight device."""
    if tp_size != expected_tp_size or not 0 <= rank < tp_size:
        raise ValueError('Unexpected tensor parallel rank/world size')
    if any(hasattr(layer, name) for name in (COEFF_BUFFER, U_BUFFER)):
        raise ValueError('Patch buffers already installed')
    shape = tuple(layer.weight.tensor_shape)
    if len(shape) != 2:
        raise ValueError('Expected a two-dimensional down projection')
    rows, local_width = shape
    if rows != len(delta.u) or local_width * tp_size != len(delta.coeff):
        raise ValueError('Sidecar dimensions disagree with loaded TP weight')
    start, stop = rank * local_width, (rank + 1) * local_width
    coeff = torch.tensor(np.array(delta.coeff[start:stop], copy=True),
                         dtype=torch.float32, device=layer.weight.device)
    u = torch.tensor(np.array(delta.u, copy=True), dtype=torch.float32, device=layer.weight.device)
    layer.register_buffer(COEFF_BUFFER, coeff, persistent=False)
    layer.register_buffer(U_BUFFER, u, persistent=False)
    return {'rank': rank, 'tp_size': tp_size, 'coeff_slice': [start, stop],
            'coeff_shape': list(coeff.shape), 'u_shape': list(u.shape),
            'dtype': str(coeff.dtype), 'device': str(coeff.device), 'persistent': False}


def apply_correction(layer, x, y, alpha):
    # This is deliberately the laboratory's multiplication/cast/subtraction
    # order. Do not fold alpha into coeff or u; that changes FP32 rounding.
    scale = x.float() @ getattr(layer, COEFF_BUFFER)
    return y - (alpha * scale[:, None] * getattr(layer, U_BUFFER)[None, :]).to(y.dtype)
