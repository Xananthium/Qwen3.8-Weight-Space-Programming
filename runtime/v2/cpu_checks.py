#!/usr/bin/env python3
"""Small independent CPU checks; never initialize CUDA or load a model."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'python'))
import numpy as np
import torch
from qwen_static_patch.core import apply_correction, bind_buffers, load_manifest, load_npz
from portable_runtime import prepare, read, sha256_file


def must_fail(action, expected):
    try:
        action()
    except expected:
        return
    raise AssertionError('Expected rejection did not occur')


def main():
    assert not torch.cuda.is_initialized()
    torch.cuda._lazy_init = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('CPU-only checks'))
    provenance = read(ROOT / 'SOURCE_PROVENANCE.json')
    for name in ('core', 'integration'):
        assert sha256_file(ROOT / 'python/qwen_static_patch' / (name+'.py')) == provenance['selected_'+name+'_sha256']
    edit = read(ROOT / 'edit_manifest.json')
    deltas = load_npz(ROOT / 'calmer_delta.npz', edit['candidate']['sha256'], 17408, 5120)
    assert sorted(deltas) == [18, 49, 50, 51] and edit['alpha'] == 1.5
    checks = []
    for layer_id, delta in deltas.items():
        for rank in (0, 1):
            layer = torch.nn.Module()
            layer.weight = torch.empty(0, dtype=torch.uint8)
            layer.weight.tensor_shape = (5120, 8704)
            metadata = bind_buffers(layer, delta, rank, 2, 2)
            assert metadata['coeff_slice'] == [rank*8704, (rank+1)*8704]
            assert metadata['dtype'] == 'torch.float32' and not metadata['persistent']
            assert not any('static_rankone' in k for k in layer.state_dict())
            # Basis vectors make the independent oracle an indexed coefficient,
            # rather than another implementation of the same matrix multiply.
            x = torch.zeros((3, 8704), dtype=torch.bfloat16)
            active = np.flatnonzero(delta.coeff[rank*8704:(rank+1)*8704])
            assert len(active) > 0
            idx = [int(active[0]), int(active[len(active)//2]), int(active[-1])]
            values = [1.0, -2.0, .5]
            y = ((torch.arange(3*5120).reshape(3, 5120) % 7).float()/8).to(torch.bfloat16)
            for row, (j, value) in enumerate(zip(idx, values)):
                x[row, j] = value
            scales = np.array([np.float32(values[i])*delta.coeff[rank*8704+j]
                               for i, j in enumerate(idx)], dtype=np.float32)
            correction = (np.float32(1.5)*scales[:, None])*delta.u[None, :]
            assert np.any(correction)
            expected = y - torch.from_numpy(correction).to(torch.bfloat16)
            assert torch.equal(apply_correction(layer, x, y, 1.5), expected)
            must_fail(lambda: bind_buffers(layer, delta, rank, 2, 2), ValueError)
            wrong_tp = torch.nn.Module()
            wrong_tp.weight = layer.weight
            must_fail(lambda: bind_buffers(wrong_tp, delta, 0, 1, 2), ValueError)
            checks.append({'layer': layer_id, 'rank': rank, 'basis_oracle_bitwise_equal': True,
                           'TP_slice_correct': True, 'nonpersistent_FP32_buffers': True})
    with tempfile.TemporaryDirectory(prefix='calmer-cpu-') as tmp:
        tmp = Path(tmp)
        fixture = tmp / 'base.gguf'
        fixture.write_bytes(b'GGUF independent portable path fixture\n')
        small = copy.deepcopy(edit)
        small['base_model']['size'] = fixture.stat().st_size
        small['base_model']['sha256'] = sha256_file(fixture)
        one = prepare(fixture, tmp/'state-one', ROOT/'calmer_delta.npz', edit=small)
        two = prepare(fixture, tmp/'state-two', ROOT/'calmer_delta.npz', edit=small)
        assert one['aot_cache_root'] != two['aot_cache_root']
        patch = load_manifest(str(one['manifest_path']))
        assert sorted(patch.deltas) == [18, 49, 50, 51] and patch.alpha == 1.5
        assert patch.matches_model(fixture)
        fixture.write_bytes(b'corrupted GGUF fixture\n')
        must_fail(patch.verify_base_identity, ValueError)
        must_fail(lambda: prepare(fixture, tmp/'state-three', ROOT/'calmer_delta.npz', edit=small), ValueError)
        must_fail(lambda: load_npz(ROOT/'calmer_delta.npz', '0'*64, 17408, 5120), ValueError)
    assert not torch.cuda.is_initialized()
    result = {'success': True, 'scope': 'CPU source/basis arithmetic/binding/portable-manifest checks only',
              'core_and_integration_match_selected_source': True, 'candidate_sha256': edit['candidate']['sha256'],
              'alpha': 1.5, 'checks': checks, 'path_relocation_and_cache_isolation': True,
              'bad_base_sidecar_and_TP_rejected': True, 'CUDA_initialized': False,
              'GPU_model_or_inference_runs': 0,
              'not_claimed': 'CUDA rebuilt kernel identity, compiled/eager equivalence, or cross-machine sampled-token equality'}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
