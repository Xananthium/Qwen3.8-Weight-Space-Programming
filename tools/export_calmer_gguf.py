#!/usr/bin/env python3
"""Export the selected sparse rank-one delta without requantizing edited tensors.

The native GGUF execution representation is distinct from the tested packed-matmul
plus FP32-sidecar representation. Its historical benchmark scores are not known.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import gguf
import numpy as np

BASE_SHA = 'ba36dc3c2b2ff5e0aa5d71092a8894546996a6a119ae391803dda07cdc08516d'
DELTA_SHA = 'ebb80ab4f906b7c7fbc61e95dd285b1e27b82b35e3e68982e575ccbfe80f8b51'
BASE_REPO = 'HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF'
BASE_REV = '993a5971fda8f30dd1b7eb2654792ba4415c7460'
ALPHA = 1.5


def digest_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(16 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def digest_array(array):
    return hashlib.sha256(memoryview(np.ascontiguousarray(array)).cast('B')).hexdigest()


def validate_output_paths(base, delta, output, manifest):
    """Reject aliases and existing destinations before reading either input."""
    base_path, delta_path = base.resolve(), delta.resolve()
    output_path, manifest_path = output.resolve(), manifest.resolve()
    if output_path == manifest_path:
        raise ValueError('Output and manifest paths must differ')
    if base_path == delta_path:
        raise ValueError('Base and delta paths must differ')
    inputs = {base_path, delta_path}
    if output_path in inputs or manifest_path in inputs:
        raise ValueError('Output and manifest must not alias either input')
    for label, path in [('output', output), ('manifest', manifest)]:
        # exists() alone does not catch a dangling symlink.
        if path.exists() or path.is_symlink():
            raise FileExistsError(f'Refuse {label} overwrite: {path}')


def verify_input_identities(base, delta):
    """Identity guards stay active under python -O."""
    if digest_file(base) != BASE_SHA:
        raise ValueError('Unexpected base checkpoint SHA256')
    if digest_file(delta) != DELTA_SHA:
        raise ValueError('Unexpected delta SHA256')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    if sys.flags.optimize:
        parser.error('Python optimization (-O/-OO) is unsupported; run without optimization to retain all scientific verification checks')
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--delta', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    try:
        validate_output_paths(args.base, args.delta, args.output, args.manifest)
        verify_input_identities(args.base, args.delta)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print('Base and selected delta identities verified.', flush=True)
    reader = gguf.GGUFReader(str(args.base))
    delta = np.load(args.delta, allow_pickle=False)
    layers = [int(x) for x in delta['layers']]
    assert layers == [49, 50, 51], layers
    names = {f'blk.{layer}.ffn_down.weight':layer for layer in layers}
    edited = {}
    changes = []
    rng = np.random.default_rng(20261105)
    for tensor in reader.tensors:
        if tensor.name not in names:
            continue
        layer = names[tensor.name]
        assert tensor.tensor_type == gguf.GGMLQuantizationType.Q5_K
        original = gguf.dequantize(tensor.data, tensor.tensor_type).astype(np.float32)
        u = np.asarray(delta[f'u_{layer}'], dtype=np.float32)
        coeff = np.asarray(delta[f'coeff_{layer}'], dtype=np.float32)
        assert original.shape == (5120, 17408)
        assert u.shape == (5120,) and coeff.shape == (17408,)
        columns = np.flatnonzero(coeff)
        assert len(columns) == 64
        new = original.copy()
        new[:, columns] -= ALPHA * u[:, None] * coeff[columns][None, :]
        assert np.array_equal(new[:, coeff == 0], original[:, coeff == 0])
        probes = rng.standard_normal((4, original.shape[1])).astype(np.float32)
        expected = probes @ original.T - ALPHA * (probes @ coeff)[:, None] * u[None, :]
        materialized = probes @ new.T
        max_error = float(np.max(np.abs(materialized - expected)))
        assert np.allclose(expected, materialized, atol=3e-4, rtol=3e-4), max_error
        edited[tensor.name] = new
        changes.append({
            'tensor':tensor.name, 'layer_zero_based':layer,
            'source_type':'Q5_K', 'export_type':'F32', 'shape':list(new.shape),
            'selected_columns':columns.tolist(),
            'changed_entries':int(np.count_nonzero(original != new)),
            'relative_frobenius_change':float(np.linalg.norm(new - original) / np.linalg.norm(original)),
            'max_random_probe_algebra_error':max_error,
            'algebra_scope':'CPU FP32 algebra; not BF16 kernel or inference equivalence',
            'original_encoded_sha256':digest_array(tensor.data),
            'edited_float32_sha256':digest_array(new),
        })
        print(json.dumps({'layer':layer, 'max_algebra_error':max_error}), flush=True)
    assert set(edited) == set(names)
    writer = gguf.GGUFWriter(str(args.output), reader.fields['general.architecture'].contents())
    for field in reader.fields.values():
        if field.name.startswith('GGUF.') or field.name in {'general.architecture', 'general.name'}:
            continue
        subtype = field.types[-1] if field.types[0] == gguf.GGUFValueType.ARRAY else None
        writer.add_key_value(field.name, field.contents(), field.types[0], sub_type=subtype)
    writer.add_string('general.name', 'Calmer Qwen 3.8 27B 4-bit base with F32 edits')
    writer.add_string('weight_edit.base_repo', BASE_REPO)
    writer.add_string('weight_edit.base_revision', BASE_REV)
    writer.add_string('weight_edit.base_sha256', BASE_SHA)
    writer.add_string('weight_edit.delta_sha256', DELTA_SHA)
    writer.add_string('weight_edit.formula', 'W_new = dequant(W) - alpha * outer(u, coeff)')
    writer.add_string('weight_edit.execution_note', 'Merged F32 matrices; historical scores belong to packed GGUF plus fixed FP32 sidecar, not this execution representation.')
    writer.add_string('weight_edit.layers', '49,50,51; zero based; original64 route once')
    writer.add_float32('weight_edit.alpha', ALPHA)
    for tensor in reader.tensors:
        if tensor.name in edited:
            writer.add_tensor(tensor.name, edited[tensor.name], raw_dtype=gguf.GGMLQuantizationType.F32)
        else:
            writer.add_tensor(tensor.name, tensor.data, raw_dtype=tensor.tensor_type)
    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_tensors_to_file(progress=True)
    writer.close()
    check = gguf.GGUFReader(str(args.output))
    inventory = []
    for before, after in zip(reader.tensors, check.tensors, strict=True):
        assert before.name == after.name
        if before.name in edited:
            assert after.tensor_type == gguf.GGMLQuantizationType.F32
            assert np.array_equal(after.data, edited[before.name])
        else:
            assert before.tensor_type == after.tensor_type
            assert np.array_equal(before.data, after.data), before.name
        inventory.append({'tensor':after.name, 'type':after.tensor_type.name,
                          'encoded_bytes':after.data.nbytes, 'sha256':digest_array(after.data),
                          'edited':before.name in edited})
    result = {
        'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'name':'Calmer-Qwen3.8-27B-4bit', 'base_repo':BASE_REPO, 'base_revision':BASE_REV,
        'source_sha256':BASE_SHA, 'delta_file':'calmer_delta.npz', 'delta_sha256':DELTA_SHA,
        'global_alpha':ALPHA, 'effective_layer_strengths':{'49':0.25,'50':1.5,'51':0.25},
        'block_route':'original64_once', 'architecture':reader.fields['general.architecture'].contents(),
        'output_file':args.output.name, 'output_bytes':args.output.stat().st_size,
        'output_sha256':digest_file(args.output),
        'quantization':'Original mixed Q4_K_P base; only three down-projection tensors promoted from Q5_K to F32.',
        'tensor_type_counts':dict(Counter(t.tensor_type.name for t in check.tensors)),
        'changes':changes, 'all_other_tensor_payloads_byte_identical':True,
        'merged_inference_benchmark_status':'not evaluated; historical scores apply only to original packed matmul plus fixed FP32 sidecar',
        'tensor_inventory':inventory,
    }
    args.manifest.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['output_file','output_bytes','output_sha256','tensor_type_counts','all_other_tensor_payloads_byte_identical']}), flush=True)


if __name__ == '__main__':
    main()
