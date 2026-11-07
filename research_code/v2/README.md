# Calmer V2 layer-18 fit

`fit_mlp18.py` is a CPU-only, portable port of the **selected** V2 MLP addition. It uses the six original authored matched pairs in `authored_pairs.json`. The productive side repairs an error; the circular side repeats a correct check. Both sides end with the same correct answer. These are discovery examples, not a held-out benchmark, a natural-loop classifier, or a guarantee of reasoning improvement.

## Fit

The input is the last 32 prefill tokens of each endpoint, captured while the original three-layer Calmer edit ran at global alpha 1.5. At layer 18, `xt_18` is the input to `ffn_down`, split into two 8,704-column tensor-parallel shards, concatenated rank 0 then rank 1. `ht_18` is the 5,120-wide post-block state, replicated across ranks. The capture boundary is the end of each `*_capture_prefix`, before the identical final-result tail. The hook location and rendering/template matter; text alone cannot recreate historical activations.

For each input column, the fitter divides by the pooled productive/circular RMS (with a small floor) and selects the 32 largest standardized absolute mean differences using stable sort. On those columns it solves the no-intercept ridge objective

`mean_c[(x·a − 1)^2] + 8 mean_p[(x·a)^2] + 0.1 ||a_standardized||²`.

It normalizes each pair's mean post-block circular-minus-productive residual, averages six unit vectors equally, then unit-normalizes to obtain `u_18`. The ideal FP32 update is `−1.5 u_18 (x·coeff_18)`. It scales `coeff_18` so the pooled productive-token 95th percentile of `||update|| / ||h||` is 0.005 on the fitting captures. The base edit's layers 49, 50, and 51 are preserved byte for byte. This calibration is an **ideal arithmetic proxy**, not a measured BF16 serving update or output probability constraint.

The layer/support choice came from a separate 64-layer × {32,64}-support scan using six leave-one-pair-out refits and a fixed criterion. This script reconstructs the chosen 18/32 fit; it does not rerun the whole search. Its report includes six held-out selector gaps and direction cosines for inspection. The six pairs were authored for discovery and cannot establish generalization.

## Inputs and use

```bash
python fit_mlp18.py \
  --capture-map PRIVATE/queued_captures.json \
  --captures PRIVATE/captures \
  --base-npz PRIVATE/v1_three_layer_edit.npz \
  --output PRIVATE/rebuilt_v2_candidate.npz \
  --report PRIVATE/rebuilt_v2_fit.json
```

Requires Python and NumPy; the recorded fit used NumPy 2.3.5. All paths are supplied by the caller, and the script refuses to overwrite results. The capture map is a list of 12 objects with `pair_id`, `side` (`productive`/`circular`), and `job_name`. For each `job_name`, supply `.rank0.npz` and `.rank1.npz` files containing `xt_18` and `ht_18`. The base NPZ must have `layers=[49,50,51]` and `u_L`/`coeff_L` arrays. The frozen source base has SHA-256 `ebb80ab4f906b7c7fbc61e95dd285b1e27b82b35e3e68982e575ccbfe80f8b51`; the selected four-layer candidate has SHA-256 `c12820b9bc65e691853a1073c8647fed47cb5521ef3fbcd19817d684006debba`.

The capture NPZs, original model weights, and model-specific capture/serving glue are not bundled. The [V1 research code](../README.md) documents the earlier capture stack and its reconstruction limits. This script performs fitting from already captured arrays; it cannot create captures, load the model, or test behavior. The public [runtime/release documentation](../../release/v2/) describes application of the merged artifact separately. The output candidate is a sidecar format, while the released GGUF contains rounded merged tensors; their file hashes must differ.

`PROVENANCE.json` records source hashes and transformations. Run `python verify_public.py` for standard-library syntax, file-hash, and schema checks. It does not validate unavailable private captures or model outputs.
