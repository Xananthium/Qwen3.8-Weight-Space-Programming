# Language, thinking-token, and completion analysis

This directory contains the offline language analysis for **Calmer-Qwen3.8-27B-4bit**, the selected half-dose weight-space edit. Start with [REPORT.md](REPORT.md). The model name is a project label; no psychological construct is measured.

The analysis includes **503 saved generations**: 405 from five actual-serving conditions and 98 from fourteen laboratory panels. It uses the saved generated token IDs, frozen grades, and existing agent proof reviews. It performs no inference, tool execution, service requests, or GPU operations.

## Reproduce

Python 3.10 or later is sufficient for JSON/CSV generation. Install the optional figure dependency with `pip install -r requirements-figures.txt`. The recorded run used Python 3.14.7 and Matplotlib 3.11.2.

```bash
python analyze_language.py \
  --experiment-root /path/to/private/experiment \
  --tokenizer-json /path/to/tokenizer.json \
  --output-dir /path/to/language_analysis
```

The script reads only an explicit list of completed result files and existing review artifacts. It does not read a question-source pool or the confirmation-reserve source dataset. Laboratory paths are resolved by basename under the supplied experiment root. Optional Matplotlib produces the figures; without it, numerical artifacts still regenerate. Exact input hashes, annotation hashes, tokenizer hash, and script hash are recorded in the exported JSON. All grading joins validate the reviewed result-file hash. The six loop cases use the frozen tool predicates and the two fixed integer-box predicates; the code refuses a noninteger continuation answer rather than silently substituting a new symbolic grader.

The input experiment artifacts are required to regenerate the measurements and are **not included here**. The public numeric data can be inspected without the original prompts or generations. Input access and redistribution remain subject to their respective rights and policies.

The tables and figures can also be regenerated directly from the public measurements, without any private inputs:

```bash
python analyze_language.py --from-metrics public/generation_metrics.json --output-dir rebuilt
```

This mode rederives aggregates and plots; it does not independently recompute token or language features from raw traces. The numerical input hash is recorded in the rebuilt output.

## Files

| File | Contents |
|---|---|
| `analyze_language.py` | CPU analysis, validation, and figure generation |
| `manual_tail_annotations.json` | Frozen, hash-bound agent annotations of 75 inspected suffixes; no trace excerpts |
| `public/generation_metrics.{json,csv}` | One row per generation; IDs, hashes, phase tokens, outcomes, lexical and repetition measures |
| `public/cohort_summary.{json,csv}` | Aggregates within condition, stage, seed, and token budget |
| `public/panel_family_summary.{json,csv}` | The same, with the four reserve batches also joined into their fixed 32-case panel |
| `public/primary_cases.csv` | Game and phylogeny rows, preserving cohort/seed separation |
| `public/paired_vs_control.csv` | Matched case/seed comparisons against the original within each runtime cohort |
| `public/outcome_stratified_descriptive.csv` | Descriptive correct/wrong/cutoff/unparsed strata; not causal estimates |
| `public/manual_tail_review.json` | Scoped qualitative suffix annotations with source/output hashes |
| `public/checks.json` | Accounting, source joins, frozen-total and boundary checks |
| `public/figures/` | PNG and SVG figures |
| `internal_pending_rights/audit_manifest.json` | Private source paths and selected generated suffixes; ignored by Git |

No public export includes a full HLE prompt, gold rationale, raw generation, raw token-ID array, or absolute input path. Trace suffixes and absolute paths are staged only in the ignored `internal_pending_rights/` directory. Review redistribution rights before deliberately adding that directory. A `.gitignore` is a packaging safeguard, not a rights determination. No upstream publication is performed by this code.

## Definitions and interpretation

* **Generation tokens:** exactly the length of the saved generated-token array; prompt and supplied continuation-prefix tokens are excluded.
* **Thinking/final content tokens:** saved tokens before/after the first generated `</think>` token, excluding tokenizer special tokens and thinking delimiters. Control tokens are reported separately. Their sum equals generation tokens exactly. This is protocol segmentation, not access to an unobserved mental state.
* **Unclosed thinking:** zero final tokens observed. A length cutoff is right-censored; it is not evidence that the model needed exactly the cap to finish, and not a completed wrong answer.
* **Strict status:** unchanged saved grading policy. Correct, wrong, cutoff, unparsed, and unfinished-thinking classes remain separate. `agent_reviewed_intended_correct` and proof validity are separate optional annotations; null means no normalized annotation was available, not false. No semantic review overrides strict parsing.
* **Words:** Python Unicode regex `\b\w+\b`; mathematical variables and numerals count. Rates are matches per 1,000 such words in the same phase. Aggregate rates pool numerator and denominator; they are not an unweighted mean of case rates.
* **Frozen lexical markers:** case-insensitive `wait`, `reconsider`, and `re[- ]?check|double[- ]?check|re[- ]?examine`, each with word boundaries. The exact patterns are exported. The additional modal/uncertainty and epistemic dictionaries are explicitly exploratory and were defined for this analysis. Dictionary classes can overlap and logical possibility is not necessarily hesitation.
* **Repeated n-grams:** `1 - unique/total` for whitespace-delimited 4- or 8-word windows within a phase. The frozen `duplicate8_tail_frozen` instead uses the last 512 whitespace words of the last 12,000 characters of the full output, exactly preserving the prior definition. Values are zero when no window exists.
* **Character screen:** longest contiguous nonword/nonspace run, longest repeated identical punctuation character, and symbol fraction in the last 1,200 characters. Threshold flags are review triggers. Markdown tables can trigger them. The qualitative suffix review remains separate from these counts.

There are no significance tests, population-accuracy estimates, survival-model estimates, or claims that lexical changes measure anxiety, confidence, wellbeing, or general reasoning quality. See the report for adaptive-selection, censoring, and proof-quality limitations.
