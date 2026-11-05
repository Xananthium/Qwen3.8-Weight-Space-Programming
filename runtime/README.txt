CALMER-QWEN3.8-27B-4BIT: PACKED BASE + FIXED FP32 EDIT

The tested edit representation is the separately downloaded original packed
GGUF plus calmer_delta.npz. The original packed base is not bundled in this
model repository; the pinned download command appears below.
The packed mixed-Q4 base remains intact, including Q5_K down projections.
Layers 49, 50 and 51 receive a fixed linear correction before TP all-reduce:

    scale = x.float() @ coeff_shard
    output = output - (1.5 * scale[:, None] * u[None, :]).to(output.dtype)

Global alpha is 1.5; effective original-direction strengths are .25, 1.5, .25.
The coefficients/u are fixed weights, not a prompt- or history-dependent
controller. Do not absorb alpha into the coefficient vectors: FP32 rounding
and BF16 cast order are part of this representation. Do not assign the tested
runtime scores to a merged F32/requantized GGUF execution representation.

The commands below assume this package is runtime/ in the downloaded model
repository. Run them from that model directory, alongside runtime/, hf-config/,
calmer_delta.npz and mmproj-Qwen3.8-27B-BF16.gguf.

WHAT IS PRESERVED

python/qwen_static_patch/core.py and integration.py are byte-identical to
the selected serving plugin. The delta bytes and their SHA256 are unchanged.
The integration wraps only the three selected packed Q5_K down projections,
registers per-rank FP32 nonpersistent buffers during loading, and leaves the
separate DFlash compressed-tensors draft unchanged. The patch is installed
before compilation or graph capture. Source hashes are in SOURCE_PROVENANCE.json.

The portable import hook and local-path preparation are packaging adaptations.
The CUDA extension binary is NOT bundled: it embeds private build paths and
was built incrementally with mixed nvcc 13.3/13.0 objects for SM86. The supplied
source closure can be rebuilt, but a clean rebuilt extension has not inherited
the original runtime's numerical or benchmark validation. The CPU checks below
verify source/weights, analytic basis-vector arithmetic and TP bindings only.

PINNED STACK AND CUDA BUILD

The tested machine used Python 3.12, PyTorch 2.13.0+cu130 (C++11 ABI), CUDA
runtime 13.0, vLLM 0.32.0 at commit 5df63a720, two RTX3090/SM86 GPUs, and the
versions in requirements-tested.txt. Seven vLLM files must match the pinned
installed-source hashes; the overlay fails closed on another source build.
Stock vLLM alone is not the measured TQ4/DFlash runtime.

Provision that matching environment first. Build the vendored extension from
this source checkout, using a coherent CUDA 13.0 toolkit and matching PyTorch:

    cd runtime/vendor/gguf_plugin
    TORCH_CUDA_ARCH_LIST=8.6 python setup.py build_ext --inplace
    cd ../../..

CUDA_HOME must identify that local toolkit for compilation. The launcher
resolves the CUDA runtime wheel's library directory from the local package
installation; it does not embed a publisher-specific LD_LIBRARY_PATH.

This is a build instruction, not a command already run by the publication
preparation. Do not select VLLM_GGUF_BUILD_LEGACY_ONLY or a Triton fallback
while calling the result the tested upstream-CUDA runtime. Other GPU/toolkit
builds need their own validation. The source baseline is plugin e62877c...
and llama.cpp 002a12ad...; full hashes and build caveats are recorded.

MODEL ASSETS

The model repository supplies the merged GGUF, calmer_delta.npz, the pinned
hf-config directory and unchanged BF16 mmproj. For this sidecar runtime,
download the ORIGINAL packed base at the exact revision:

    hf download HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF \
      Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-Q4_K_P.gguf \
      --revision 993a5971fda8f30dd1b7eb2654792ba4415c7460 \
      --local-dir upstream-base

For the measured DFlash7 stack, download its separate pinned draft:

    hf download syvai/Qwen3.8-27B-DFlash2-W4A16 \
      --revision 4d30ec736ffc6b8688dc2ae2b502d9b48bdec279 \
      --local-dir dflash-draft

The base, delta, HF assets, projector, draft weights and draft config are
hash-checked. Do not substitute the base's unrelated FastMTP sidecar for this
draft. Do not apply the delta to the merged F32-edits GGUF: that would edit
twice, and the launcher rejects it as a base by size/checksum.

CPU PREPARATION AND CHECKS

    CALMER_BASE_PATH="upstream-base/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-Q4_K_P.gguf"
    CALMER_STATE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/calmer-qwen38"
    python -B runtime/cpu_checks.py
    python -B runtime/prepare_runtime.py --model-path "$CALMER_BASE_PATH" \
      --delta-path calmer_delta.npz --state-dir "$CALMER_STATE_DIR"

The first prepare hashes the full base. Later prepares reuse a receipt only
for the same path/stat/hash identity. State contains local absolute paths and
must live OUTSIDE this distributable directory. Never upload local state.

    python -B runtime/launch_exact.py --model-path "$CALMER_BASE_PATH" \
      --delta-path calmer_delta.npz --hf-config hf-config \
      --mmproj-path mmproj-Qwen3.8-27B-BF16.gguf \
      --draft-dir dflash-draft --state-dir "$CALMER_STATE_DIR" --check-imports

The check imports the real plugin and creates EngineConfig on CPU without
LLM/EngineCore/CUDA initialization. Inspect CUDA_extension_available and
runtime_ready: absent compiled kernels are not a ready serving installation.
The check also reports the loaded kernel hash and whether it matches the
original tested binary. A successful import does not validate rebuilt-runtime
numerical equivalence.

SERVING

Use the same command without --check-imports to launch. No service manager is
installed or changed by this package. The default listener is 127.0.0.1:8000;
--host/--port are configurable. The public alias is Calmer-Qwen3.8-27B-4bit.

The launch preserves TP2/BF16, 200000 context, max16 sequences, batch4096,
TQ4 KV and native80GiB KV offload, compiled FULL_DECODE_ONLY with the measured
capture sizes, DFlash7, image5/video0, and medium/temperature1.3 defaults.
Both target workers emit STATIC_PATCH_STARTUP_AUDIT with hash, alpha, bindings,
rank-local buffer shapes, precision flags and the profile-isolated AOT root.
Check both workers before using benchmark results. Compiler/AOT caches are
local and edit/code/location-specific; they are never part of the release.

This is an experimental edit, not a demonstrated general benchmark upgrade.
The accompanying evaluation report includes observed gains, losses, cutoffs,
prior-exposed GSM retention and the half-dose hotel/editor regressions. Local
published counts are not full HLE/GSM8K benchmark estimates.
