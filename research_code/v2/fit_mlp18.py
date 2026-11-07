#!/usr/bin/env python3
"""CPU reconstruction of the selected V2 layer-18 rank-one MLP addition.

Requires separately supplied original capture NPZs and the V1 base edit NPZ.
No model, server, or GPU code is imported.
"""
import os
for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

LAYER = 18
ALPHA = 1.5
SUPPORT = 32
ETA = 8.0
RIDGE = 0.1
TARGET = 0.005


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def unit(a):
    n = float(np.linalg.norm(a))
    if n <= 1e-12:
        raise ValueError('degenerate output direction')
    return a / n


def sparse_fit(xp, xc):
    p = xp.reshape(-1, xp.shape[-1]).astype(np.float64)
    c = xc.reshape(-1, xc.shape[-1]).astype(np.float64)
    rms = np.sqrt((np.mean(p * p, axis=0) + np.mean(c * c, axis=0)) / 2)
    rms = np.maximum(rms, max(float(np.median(rms)) * 1e-3, 1e-8))
    score = np.abs(c.mean(0) - p.mean(0)) / rms
    indices = np.sort(np.argsort(score, kind='stable')[-SUPPORT:])
    zp, zc = p[:, indices] / rms[indices], c[:, indices] / rms[indices]
    gram = zc.T @ zc / len(zc) + ETA * (zp.T @ zp) / len(zp) + RIDGE * np.eye(SUPPORT)
    standard = np.linalg.solve(gram, zc.mean(0))
    coeff = np.zeros(xp.shape[-1], dtype=np.float64)
    coeff[indices] = standard / rms[indices]
    return coeff, indices, float(np.linalg.cond(gram))


def output_direction(hp, hc):
    contrasts = hc.mean(1) - hp.mean(1)
    lengths = np.linalg.norm(contrasts, axis=1)
    if np.any(lengths <= 1e-8):
        raise ValueError('degenerate pair contrast')
    mean = (contrasts / lengths[:, None]).mean(0)
    if np.linalg.norm(mean) <= 1e-3:
        raise ValueError('pair directions cancel')
    return unit(mean)


def load_captures(mapping, capture_dir):
    rows = json.loads(mapping.read_text())
    pairs = sorted({row['pair_id'] for row in rows})
    if len(rows) != 12 or len(pairs) != 6:
        raise ValueError('expected six pairs and twelve endpoints')
    lookup = {(row['pair_id'], row['side']): row['job_name'] for row in rows}
    if len(lookup) != 12 or set(side for _, side in lookup) != {'productive', 'circular'}:
        raise ValueError('incomplete or duplicate endpoint mapping')
    data = {side: {'x': [], 'h': []} for side in ('productive', 'circular')}
    hashes = {}
    for pair in pairs:
        for side in data:
            job = lookup[pair, side]
            if Path(job).name != job:
                raise ValueError('job_name must be a file stem')
            files = [capture_dir / f'{job}.rank{rank}.npz' for rank in (0, 1)]
            hashes[f'{pair}:{side}'] = [sha256(path) for path in files]
            with np.load(files[0], allow_pickle=False) as r0, np.load(files[1], allow_pickle=False) as r1:
                h0, h1 = r0[f'ht_{LAYER}'], r1[f'ht_{LAYER}']
                x0, x1 = r0[f'xt_{LAYER}'], r1[f'xt_{LAYER}']
                if h0.shape != (32, 5120) or h1.shape != h0.shape or not np.array_equal(h0, h1):
                    raise ValueError('replicated post-block states disagree')
                if x0.shape != (32, 8704) or x1.shape != x0.shape:
                    raise ValueError('expected two 8704-column input shards')
                if not all(np.isfinite(v).all() for v in (x0, x1, h0)):
                    raise ValueError('nonfinite capture')
                data[side]['x'].append(np.concatenate((x0, x1), axis=1))
                data[side]['h'].append(h0)
    return pairs, *(np.stack(data[side][key]) for side, key in
                     (('productive', 'x'), ('circular', 'x'), ('productive', 'h'), ('circular', 'h'))), hashes


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--capture-map', type=Path, required=True)
    ap.add_argument('--captures', type=Path, required=True)
    ap.add_argument('--base-npz', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--report', type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists() or args.report.exists():
        ap.error('refusing to overwrite an output')
    pairs, xp, xc, hp, hc, hashes = load_captures(args.capture_map, args.captures)
    a, indices, condition = sparse_fit(xp, xc)
    u = output_direction(hp, hc).astype(np.float32)
    pscore = xp.astype(np.float64) @ a
    p95 = float(np.quantile(ALPHA * np.linalg.norm(u.astype(np.float64)) *
                            np.abs(pscore) / np.linalg.norm(hp.astype(np.float64), axis=-1), .95))
    if p95 <= 1e-10:
        raise ValueError('productive calibration is degenerate')
    gamma = TARGET / p95
    coeff = (gamma * a).astype(np.float32)
    with np.load(args.base_npz, allow_pickle=False) as source:
        base = {key: source[key].copy() for key in source.files}
    if not np.array_equal(base['layers'], [49, 50, 51]):
        raise ValueError('base must have precisely layers 49,50,51')
    for layer in (49, 50, 51):
        if base[f'u_{layer}'].shape != (5120,) or base[f'coeff_{layer}'].shape != (17408,):
            raise ValueError('bad base edit shape')
    arrays = {key: val.copy() for key, val in base.items() if key != 'layers'}
    arrays['layers'] = np.array([18, 49, 50, 51], dtype=base['layers'].dtype)
    arrays['u_18'], arrays['coeff_18'] = u, coeff
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.output, **arrays)
    with np.load(args.output, allow_pickle=False) as check:
        if any(check[key].tobytes() != value.tobytes() for key, value in base.items() if key != 'layers'):
            raise ValueError('base array changed')
    held = []
    for hold in range(6):
        train = np.arange(6) != hold
        fold_a, _, _ = sparse_fit(xp[train], xc[train])
        fold_u = output_direction(hp[train], hc[train])
        held.append({'pair': pairs[hold],
                     'selector_gap': float((xc[hold] @ fold_a).mean() - (xp[hold] @ fold_a).mean()),
                     'direction_cosine': float(np.dot(fold_u, unit((hc[hold] - hp[hold]).mean(0))))})
    report = {'schema': 'calmer-v2-mlp18-fit-v1', 'output_sha256': sha256(args.output),
              'base_sha256': sha256(args.base_npz), 'capture_map_sha256': sha256(args.capture_map),
              'capture_sha256_by_pair_side_rank': hashes, 'pair_order': pairs,
              'alpha': ALPHA, 'eta': ETA, 'ridge': RIDGE, 'support': SUPPORT,
              'selected_columns': indices.tolist(), 'gram_condition': condition,
              'target_productive_p95_relative_postblock_norm': TARGET,
              'uncalibrated_productive_p95': p95, 'gamma': gamma,
              'heldout_refit': held, 'base_arrays_byte_identical': True,
              'note': 'Ideal FP32 fit calibration; BF16 serving rounding and behavior require separate tests.'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
