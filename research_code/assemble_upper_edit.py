#!/usr/bin/env python3
"""Assemble the recorded upper-layer NPZ; no model or runtime is modified.

This preserves the center arrays and folds flank/nominal-center scaling into
coefficients, matching build_neighbor_candidates.py. Runtime alpha is separate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--center', type=Path, required=True)
    parser.add_argument('--neighbor49', type=Path, required=True)
    parser.add_argument('--neighbor51', type=Path, required=True)
    parser.add_argument('--nominal-center', type=float, default=3)
    parser.add_argument('--nominal-flank', type=float, default=.5)
    parser.add_argument('--evaluation-alpha', type=float, default=1.5)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.nominal_center == 0:
        parser.error('Refuse existing output / zero nominal center')
    with np.load(args.center, allow_pickle=False) as z:
        arrays = {'layers': np.array([49, 50, 51]), 'u_50': z['u_50'].copy(), 'coeff_50': z['coeff_50'].copy()}
    for layer, path in [(49, args.neighbor49), (51, args.neighbor51)]:
        with np.load(path, allow_pickle=False) as z:
            arrays[f'u_{layer}'] = z[f'u_{layer}'].copy()
            arrays[f'coeff_{layer}'] = z[f'coeff_{layer}']*np.float32(args.nominal_flank/args.nominal_center)
    if any(np.count_nonzero(arrays[f'coeff_{layer}']) != 64 for layer in [49, 50, 51]):
        raise ValueError('Expected historical 64-column support per layer')
    manifest_path = args.output.with_suffix('.manifest.json')
    if manifest_path.exists():
        raise FileExistsError(manifest_path)
    np.savez(args.output, **arrays)
    manifest = {'formula': 'W_new = W - runtime_alpha * outer(u, coeff)',
                'rank_per_matrix': 1, 'support_per_matrix': 64,
                'runtime_alpha': args.evaluation_alpha,
                'effective_strengths': {'49': args.evaluation_alpha*args.nominal_flank/args.nominal_center,
                                        '50': args.evaluation_alpha,
                                        '51': args.evaluation_alpha*args.nominal_flank/args.nominal_center},
                'inputs_sha256': [hashlib.sha256(p.read_bytes()).hexdigest() for p in [args.center, args.neighbor49, args.neighbor51]],
                'npz_sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(),
                'note': 'NPZ metadata does not install a runtime. Numerical source/runtime validation remains separate.'}
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    main()
