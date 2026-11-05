# Qwen3.8 Weight-Space Programming

**Calmer Qwen 3.8 27B · 4-bit** is an experimental, fixed edit to three MLP weight matrices. It grew out of an attempt to reduce repetitive thinking while preserving useful reasoning at **medium reasoning, temperature 1.3**.

**[Download the model on Hugging Face](https://huggingface.co/Xananthium/Calmer-Qwen3.8-27B-4bit)** · **[Scientific report](PAPER.md)** · **[Language and thinking analysis](language_analysis/REPORT.md)**

The selected edit helps two constructed repetition cases and completes both a game-theory and a phylogeny question with correct final choices in one development seed. The wider comparison also finds regressions, invalid explanations, and seed sensitivity. This repository preserves those outcomes alongside the gains.

## What changed

The source is the pinned [HauhauCS mixed-Q4 27B checkpoint](https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF). For each edited matrix, a fixed sparse rank-one update is subtracted:

```text
W_new = W - alpha * outer(u, coeff)
zero-based layers: 49, 50, 51
effective strengths: 0.25, 1.5, 0.25
64 supported MLP input columns per matrix
```

Four constructed productive/repetitive continuation pairs supplied the fitted directions and column selection. No gradient optimizer was used. The intervention has no answer lookup or prompt-dependent controller. All 64 original blocks execute once in the selected model; repeated-block experiments are reported separately.

The historical evaluation used **packed GGUF weights plus a fixed FP32 correction**, with a specific BF16 cast/subtraction order. Hugging Face also contains a **complete merged GGUF**, preserving every other tensor payload and storing the three edited matrices as F32. The merged file passed a native CPU load/decode smoke test, but **has not undergone the historical HLE/GSM evaluation**. Different kernels and rounding matter. The model card documents both representations and their launch instructions.

## Results at a glance

These are local diagnostic panels, not full benchmark results.

| Measurement | Original | Selected half-dose edit |
|---|---:|---:|
| Fixed 32-question HLE text subset, strict correct | 3/32 | 4/32 |
| Prespecified completed HLE misses repaired | — | 0/10 |
| HLE subset total generated tokens | 172,533 | 194,671 |
| Previously exposed GSM8K retention cases | 24/24 | 23/24 |
| Authored state tracking, agent-reviewed intended correct | 4/4 | 3/4 |
| Constructed repetition cases, completed correct | 1/2 | 2/2 |
| Tokens across those two repetition cases | 4,906 | 1,228 |
| Prescribed next-action tool corrections | 4/4 | 4/4 |

The HLE result comprises three gains and two losses, with **12.8% more tokens**. One gained choice has an arithmetic defect. The repetition pair uses **75.0% fewer tokens**, but was reused during discovery. No generated tool calls were executed; the original already handled all four next-action cases correctly.

For the game/tree pair, the selected model gets both choices strictly correct at seed `20261107`. The game explanation has an invalid existence argument; the tree has a valid count certificate followed by false history prose. At seed `20261105`, the game proof is valid and the tree cuts off. The report keeps choice correctness, proof validity, and completion separate.

Five actual-serving profiles were compared on **37 distinct HLE questions**, GSM retention, state tracking, and constructed loop cases. Fourteen additional laboratory conditions tested neighboring edits, early layers, repeated blocks, and constrained directions. Both cohorts and all conditions are retained in the [full report](PAPER.md), [actual case table](evidence/actual_case_metrics.csv), and [laboratory table](evidence/laboratory14_summary.csv).

## Language and thinking patterns

The [language report](language_analysis/REPORT.md) analyzes **503 saved generations**: 405 actual-serving and 98 laboratory. It includes six figures, per-generation measurements, exact thinking/final/control-token accounting, lexical rates, repetition, cutoff analysis, and 75 agent-reviewed output suffixes.

![Thinking tokens and rechecking across development seeds](language_analysis/public/figures/actual_development_tokens_and_wait.png)

Half dose reduces thinking tokens by **30.9%** on the second development seed, while increasing total tokens by **8.5%** on the first. Normalized “wait” density changes much less than the raw count, and “reconsider” density can increase. Shorter answers can be correct or wrong. Character-level degeneration appears in an early-layer alternative and is missed by a word-level repetition metric.

“Calmer” is a name for observed text behavior in specific tests. The analysis does not measure anxiety, wellbeing, or an internal mental state.

## Reproduce and inspect

| Location | Contents |
|---|---|
| [PAPER.md](PAPER.md) | Construction, protocol, all conditions, results, proof reviews, limitations and related work |
| [language_analysis/](language_analysis/README.md) | Measurement definitions, CPU analysis, public numerical data and figures |
| [evidence/](evidence/RECONSTRUCTION.txt) | Case IDs, frozen grades, timings, artifact hashes, cohort definitions and mechanistic diagnostics |
| [research_code/](research_code/README.md) | Curated fitting, assembly, request construction, API evaluation, frozen graders and laboratory routes; source provenance and redaction details |
| [runtime/](runtime/README.txt) | Portable source for the selected packed-base/FP32-correction representation; exact delta and pinned dependencies |
| [tools/export_calmer_gguf.py](tools/export_calmer_gguf.py) | Reproducible merged export with tensor preservation and algebra checks |
| [release/](release/) | Export inventory, native smoke evidence and release identities |

Regenerate public aggregate tables and plots without downloading a model or benchmark:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r language_analysis/requirements-figures.txt
python language_analysis/analyze_language.py \
  --from-metrics language_analysis/public/generation_metrics.json \
  --output-dir rebuilt
```

This reproduces aggregates from the released measurements. Independently recalculating the features or reviewing historical proofs requires the privately preserved raw traces. See [language-analysis methods](language_analysis/README.md) and [authorized HLE reconstruction](evidence/RECONSTRUCTION.txt). The supplied runtime source requires the pinned custom CUDA/vLLM stack; a clean rebuild has not inherited the original binary's numerical validation.

Public files omit HLE questions, keys, reference rationales, raw traces and reversible token arrays, respecting the [dataset card's redistribution request](https://huggingface.co/datasets/cais/hle). IDs and hashes bind the public measurements to the source records. The complete local reviewer archive preserves historical material, but is not part of this public repository.

## Interpretation and attribution

The panels were small, reused and adaptively exposed. Two development seeds reveal substantial sensitivity. Retrospective natural-prefix diagnostics also challenge the proposed mechanism: at center layer 50, two actual correctness regressions have the opposite projection sign to the constructed repetition hypothesis. This is evidence about a limited intervention, not a universal repetition or correctness circuit.

Prepared by **Xananthium with AI assistance**, including code, experiment design, literature review, language analysis and qualitative proof review. There was no independent human grading panel. Credit to Qwen and HauhauCS for the source checkpoint and to the cited research authors for the motivating methods. The model name follows the upstream Qwen3.8 label; its GGUF architecture metadata is `qwen35`.

Original project material is released under [Apache-2.0](LICENSE); third-party components retain their own notices. See [NOTICE.txt](NOTICE.txt), [runtime notices](runtime/NOTICE.txt), and [rights and attribution](evidence/RIGHTS_AND_ATTRIBUTION.txt).
