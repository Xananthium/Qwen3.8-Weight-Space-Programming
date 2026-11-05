# Release artifact identities

The model files are hosted at [Xananthium/Calmer-Qwen3.8-27B-4bit](https://huggingface.co/Xananthium/Calmer-Qwen3.8-27B-4bit). This directory preserves their publication identities and artifact-specific validation.

- `merged_export_manifest.json` records all 866 tensor payloads. Three down-projection matrices are changed and stored as F32; the other 863 encoded payloads remain byte-identical.
- `native_smoke.json` and `native_smoke_prompt.txt` record the merged GGUF's CPU load/decode test. It produced the correct simple arithmetic answer. This is not an HLE/GSM evaluation or a sidecar-equivalence test.
- `release_manifest.json` inventories the Hugging Face release files. Its paths are relative to the model repository, not this research repository.
- `hub_publication.json` pins the verified public model commit and large-file identities.

The export ran with Python 3.12, NumPy 2.3.5 and `gguf` 0.19.0. Recreate it using the pinned original base and selected delta:

```bash
pip install -r tools/requirements-export.txt
python tools/export_calmer_gguf.py \
  --base /path/to/original/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-Q4_K_P.gguf \
  --delta runtime/calmer_delta.npz \
  --output /path/to/new/Calmer-Qwen3.8-27B-Q4_K_P-F32Edits.gguf \
  --manifest /path/to/new/merged_export_manifest.json
```

Run in an environment with NumPy and the `gguf` Python package. The exporter verifies both source hashes, refuses output overwrite, checks the fixed sparse update algebra, and verifies preserved tensor payloads. The source checkpoint itself is never modified.

Historical scores belong to the original packed-base/FP32-correction representation. Numerical agreement of that runtime with a merged file or a new CUDA build requires fresh testing.
