# Publication scope and attribution

This subtree follows the repository's [rights and attribution findings](../evidence/RIGHTS_AND_ATTRIBUTION.txt) and [existing selective-excerpt pattern](../examples/SELECTED_CONVERSATIONS.md). It publishes derived scientific observations, not the underlying benchmark archive.

Included:

- Numerical outcomes, case IDs, caps, seeds, batch position, timings, language counts, profile/candidate hashes and source/output hashes.
- All completed compiled alternatives and the interrupted batch, including failures.
- Separately reviewed, short literal output spans: authored diagnostics, generic formula-free HLE metareasoning and punctuation-only failures.
- Dated method notes, plotting inputs and scripts, and transformation/integrity checks.

Withheld:

- Full HLE questions/options/images, official answer labels, reference rationales and complete HLE solutions.
- Full generated traces and losslessly decodable prompt/output token arrays.
- Private host paths, endpoints, credentials, launch configurations, process identifiers and system/service internals.
- Blanket copies of the private experiment, capture tensors or operational recovery logs.

The HLE dataset's benchmark-integrity request is respected independently of its license declaration and gating mechanism. A model-generated passage can reconstruct benchmark content; being generated does not make it automatically safe to publish. Each HLE excerpt here was reviewed as nonsolution language or punctuation. Hash/slice verification establishes authenticity, not publication rights or an independently complete proof audit.

Offsets are zero-based Python Unicode-codepoint half-open intervals in the identified source field. SHA256 is calculated over exact UTF-8 with no normalization. Editorial omissions appear outside quoted blocks. Source locators describe withheld evidence; they are not public download links. No standalone answer hashes are published.

Credit Qwen/Alibaba Cloud for the base model and HauhauCS for the Aggressive mixed-precision GGUF. The source GGUF hash is `ba36dc3c2b2ff5e0aa5d71092a8894546996a6a119ae391803dda07cdc08516d`. This is a derivative experiment, not an official Qwen or HauhauCS release or endorsement. Applicable upstream notices and the repository's [Apache-2.0 license](../LICENSE) remain in force; this document does not grant blanket rights to third-party benchmarks or linked papers.

The [Calmer V2 model card](https://huggingface.co/Xananthium/Calmer-V2-Qwen3.8-27B-4bit) identifies release artifacts and their representation limits. Numerical results here describe the evaluated packed-weight/FP32-sidecar/BF16-cast path, not automatic validation of another export.
