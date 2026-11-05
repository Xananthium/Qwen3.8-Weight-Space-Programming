#!/usr/bin/env python3
"""CPU port of the recorded four-pair contrast / sparse-writer construction.

No inference: --capture-map supplies name/pair/label metadata and --captures
supplies existing rank0/rank1 mean-activation NPZs. No prompt text is needed.
Original arithmetic and argsort selection are retained; CLI and checks are new.
"""
import argparse
import hashlib
import json
from pathlib import Path

import gguf
import numpy as np


def file_sha(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(16*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def fit(weight, productive_h, repetitive_h, productive_x, repetitive_x, columns=64):
    differences = np.stack([bad-good for good, bad in zip(productive_h, repetitive_h, strict=True)])
    norms = np.linalg.norm(differences, axis=1)
    if not np.all(norms > 0):
        raise ValueError('Zero residual contrast')
    unit = (differences/norms[:, None]).mean(0)
    unit /= np.linalg.norm(unit)
    projection = unit @ weight
    scores = ((repetitive_x-productive_x)*projection[None, :]).mean(0)
    selected = np.argsort(scores)[-columns:]
    coeff = np.zeros(weight.shape[1], dtype=np.float32)
    coeff[selected] = projection[selected]
    return unit, coeff, {
        'direction_consistency': float((differences@unit/norms).mean()),
        'selected_columns': selected.tolist(),
        'selected_writer_difference': float(scores[selected].sum()),
        'total_writer_difference': float(scores.sum()),
        'relative_frobenius_per_alpha': float(np.linalg.norm(coeff)/np.linalg.norm(weight)),
        'productive_write': float((productive_x@coeff).mean()),
        'repetitive_write': float((repetitive_x@coeff).mean()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gguf', type=Path, required=True)
    parser.add_argument('--capture-map', type=Path, required=True)
    parser.add_argument('--captures', type=Path, required=True)
    parser.add_argument('--layers', type=int, nargs='+', required=True)
    parser.add_argument('--columns', type=int, default=64)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error('Use a new or empty output directory')
    mapping = json.loads(args.capture_map.read_text())
    groups, inputs = {}, []
    for item in mapping:
        key = (item['pair'], item['label'])
        if key in groups:
            raise ValueError('Duplicate pair/label')
        rank0 = args.captures/(item['name']+'.rank0.npz')
        rank1 = args.captures/(item['name']+'.rank1.npz')
        with np.load(rank0, allow_pickle=False) as a, np.load(rank1, allow_pickle=False) as b:
            groups[key] = {k: a[k].copy() if k.startswith('h_') else np.concatenate([a[k], b[k]]) for k in a.files}
        inputs.append({'name': item['name'], 'pair': item['pair'], 'label': item['label'],
                       'rank0_sha256': file_sha(rank0), 'rank1_sha256': file_sha(rank1)})
    pairs = sorted({pair for pair, _ in groups})
    if len(pairs) != 4 or set(groups) != {(i, label) for i in pairs for label in ('productive', 'repetitive')}:
        raise ValueError('Historical fit requires exactly four complete paired captures')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    reader = gguf.GGUFReader(str(args.gguf))
    for tensor in reader.tensors:
        if not tensor.name.endswith('.ffn_down.weight'):
            continue
        layer = int(tensor.name.split('.')[1])
        if layer not in args.layers:
            continue
        weight = gguf.dequantize(tensor.data, tensor.tensor_type).astype(np.float32)
        if not 0 < args.columns <= weight.shape[1]:
            raise ValueError('Invalid support width')
        good_h = [groups[i, 'productive'][f'h_{layer}'] for i in pairs]
        bad_h = [groups[i, 'repetitive'][f'h_{layer}'] for i in pairs]
        good_x = np.stack([groups[i, 'productive'][f'x_{layer}'] for i in pairs])
        bad_x = np.stack([groups[i, 'repetitive'][f'x_{layer}'] for i in pairs])
        unit, coeff, row = fit(weight, good_h, bad_h, good_x, bad_x, args.columns)
        np.savez(args.output_dir/f'candidate_layer{layer}.npz', layers=np.array([layer]),
                 **{f'u_{layer}': unit, f'coeff_{layer}': coeff})
        rows.append({'layer': layer, **row})
    if {row['layer'] for row in rows} != set(args.layers):
        raise ValueError('Requested layer missing from GGUF')
    report = {'gguf_sha256': file_sha(args.gguf), 'capture_map_sha256': file_sha(args.capture_map),
              'capture_inputs': inputs, 'layers': rows,
              'interpretation': 'Constructed contrast hypothesis; not a validated natural-loop or correctness classifier.',
              'equivalence_limit': 'Ported arithmetic; requires original captures, source GGUF, NumPy/GGUF versions and preprocessing for historical array equivalence.'}
    (args.output_dir/'fit_manifest.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
