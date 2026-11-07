CALMER V2: PORTABLE PACKED-BASE + FIXED FOUR-LAYER SIDECAR

This directory is the V2 override for the pinned runtime source closure in
the parent runtime/ directory. V1 is preserved there. The V2 candidate is the
exact 362698-byte NPZ used by the tested layer-18 pilot (SHA256
c12820b9bc65e691853a1073c8647fed47cb5521ef3fbcd19817d684006debba).
Its 49/50/51 vectors are byte-identical to V1; the additional learned layer-18
component uses the same FP32 rank-one down_proj arithmetic. The global alpha
is 1.5 and must not be folded into the coefficient arrays:

    scale = x.float() @ coeff_shard
    output = output - (1.5 * scale[:, None] * u[None, :]).to(output.dtype)

The original packed GGUF is unmodified. Do not apply this sidecar to the
separately exported V2 merged GGUF; that would apply the edit twice.

ASSEMBLY

From the repository root, create a flat runtime directory for packaging:

    python -B runtime/v2/assemble_flat_runtime.py --output /path/to/stage/runtime

The helper copies the unchanged pinned source, overlay, licenses and vendor
closure from runtime/, then installs these V2 overrides. It removes V1-only
validation reports and regenerates MANIFEST.json and SHA256SUMS. It refuses to
overwrite an existing output. The Hugging Face package can place this flat
runtime/ beside hf-config/, calmer_delta.npz and the BF16 projector. The root
calmer_delta.npz must also have the SHA256 printed above. Do not upload the
nested runtime/v2/ directory as part of the flat runtime package.

PINNED ASSETS AND BUILD

The flat edit_manifest.json pins the original packed GGUF, BF16 projector,
DFlash2 draft weights and draft config by SHA256. It also pins the V2 NPZ and
the layer-50 anchor vectors. The same nine hf-config/tokenizer/template hashes
from V1 are checked before serving. The pinned versions are listed in
requirements-tested.txt and runtime_versions.json: Python 3.12, PyTorch
2.13.0+cu130 (C++11 ABI), CUDA runtime 13.0 and vLLM 0.32.0 at commit
5df63a720. The supplied seven-file vLLM overlay requires exactly matching
installed-source hashes. Build the vendored CUDA extension for a local matching
toolkit and GPU architecture:

    cd runtime/vendor/gguf_plugin
    TORCH_CUDA_ARCH_LIST=8.6 python setup.py build_ext --inplace

CUDA_HOME must point to the matching local toolkit. This source package does
not include the original incremental CUDA binary. A clean rebuild has not
been validated as numerically or benchmark equivalent to that binary.

Download the unedited packed base at the pinned upstream revision:

    hf download HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF \
      Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-Q4_K_P.gguf \
      --revision 993a5971fda8f30dd1b7eb2654792ba4415c7460 \
      --local-dir upstream-base

The separate draft is required for the measured DFlash7 stack:

    hf download syvai/Qwen3.8-27B-DFlash2-W4A16 \
      --revision 4d30ec736ffc6b8688dc2ae2b502d9b48bdec279 \
      --local-dir dflash-draft

The tested stack used two RTX 3090s, TP2/BF16, TQ4 KV, native 80 GiB KV
offload, GPU memory utilization 0.95, DFlash7, 200000 context, full-decode
compilation, image limit 5, and medium reasoning with temperature 1.3. The V2
launcher preserves these settings and serves the alias
Calmer-V2-Qwen3.8-27B-4bit. A local deployment with an already matching pinned
stack can use the same launcher with machine-local asset paths.

CPU PREPARATION AND STARTUP CHECK

In the packaged model directory, with the flat runtime/ present:

    python -B runtime/cpu_checks.py
    python -B runtime/prepare_runtime.py --model-path "$CALMER_BASE_PATH" \
      --state-dir "$CALMER_STATE_DIR"
    python -B runtime/launch_exact.py --model-path "$CALMER_BASE_PATH" \
      --hf-config hf-config --mmproj-path mmproj-Qwen3.8-27B-BF16.gguf \
      --draft-dir "$CALMER_DRAFT_DIR" --state-dir "$CALMER_STATE_DIR" \
      --check-imports

Set CALMER_BASE_PATH to the local original packed GGUF, CALMER_DRAFT_DIR to
the pinned DFlash draft, and CALMER_STATE_DIR to a writable directory outside
runtime/. The full base is SHA256-verified on first preparation; unchanged
path/stat/hash receipts avoid rehashing it on later launches. The CPU check
does not initialize CUDA or run generation. Serve with the same launch command
without --check-imports after inspecting its output and both workers' startup
audit for the four expected layers and candidate hash.

The exact serving results are local pilot observations, not a broad benchmark
claim. Rebuilt source and new hardware need fresh validation. Existing working
production installations should keep their pinned stack and use an isolated
state/AOT cache for V2.
