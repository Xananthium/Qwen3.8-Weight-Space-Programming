# Pinned GGUF runtime source snapshot

This is the frozen Python GGUF runtime plus the pinned CUDA bridge/kernel
source closure used by the experiment. See the parent runtime's README.txt,
SOURCE_PROVENANCE.json, NOTICE.txt, and the original license texts.

The tested prebuilt CUDA extension is intentionally absent. It embedded
private build paths and came from a mixed-toolchain incremental build. A clean
rebuild is not asserted to reproduce its bytes or sampled outputs exactly.
