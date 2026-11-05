# Curated research code

This is a small source collection for inspecting and replaying the experiment's construction, evaluation, and grading methods. It contains **byte-identical originals**, **documented portability ports**, and **new offline validation/planning utilities**. [SOURCE_PROVENANCE.json](SOURCE_PROVENANCE.json) maps each public file to the exact original file hashes and lists changes. It is not a claim that every historical experiment can be reproduced from public files alone.

No model is loaded or request sent merely by importing these modules. `run_suite.py` prints a plan unless `--run` is supplied. `api_batch_eval.py` makes requests only when explicitly executed without `--check`. No script starts, stops, reconfigures, or installs a serving runtime. Runtime code is supplied separately with the model release; it is not duplicated here.

## Source collection

| Public file | Role and status |
|---|---|
| `make_constructed_probes.py` | Port of original productive/repetitive prefix construction; dataset records and both authored strings are external inputs; no queue writes |
| `fit_sparse_contrasts.py` | CPU port of normalized four-pair residual contrast, decoded-weight projection, and 64-column differential-writer selection |
| `assemble_upper_edit.py` | Port of center-preserving upper-flank assembly; folds relative flank scaling into coefficients |
| `api_batch_eval.py` | Byte-identical historical actual-serving request/SSE runner; externally supplied frozen raw prompts and profile attestation |
| `run_suite.py` | Portable dispatcher replacing machine-specific interpreter/job tables; prints a plan by default, no automatic retries |
| `hle_score.py` | Unchanged frozen choice parser/scoring functions; explicit output CLI replaces historical journal writes |
| `hle_continuation.py` | Byte-identical history-joining helper; preserves restarted-RNG caveat for older continued attempts |
| `score_math_tool.py` | Unchanged frozen math-verify/tool scoring functions; explicit output CLI; no tools executed |
| `score_state_transfer.py` | Frozen parser/output predicates; answer map required externally; data-dependent original self-tests omitted |
| `lab_routing.py` | New pure port of source-route planning; emits inert jobs, not an active queue; requires original worker/cache support |
| `graph_certificate.py` | Generic port of the triangulated-sphere certificate; specific HLE-derived face data and result literals removed |
| `validate_cpu.py` | New synthetic CPU checks; no model calls, HTTP requests, GPU use, or benchmark fixtures |

The frozen parsers intentionally preserve historical strict-format distinctions. They are not upgraded to accept answers merely because an agent review can infer intent. Cutoffs remain separate from completed wrong answers. Agent-reviewed proof achievements and final proof validity are qualitative annotations, not something these parsers infer automatically. The generic graph certificate does not validate arbitrary model prose or close the embedding gap identified in model-generated proofs.

## Inputs deliberately not bundled

There is no full HLE problem, official key, reference rationale, raw generation, reversible token history, credential, environment snapshot, or private absolute machine path in this collection. No GSM problem, worked solution, or authored continuation string is rehosted. This avoids relying on a redistribution determination for those inputs.

`templates/constructed_input_hashes.json` lists the four original GSM record IDs and UTF-8 hashes of the two authored strings. The two redacted capture maps retain names, pair/label metadata, and problem/prefix hashes. These hashes verify authorized reconstruction; they **do not recover missing text**. Exact reproduction requires the separately authorized original dataset records and authored strings or private experiment archive. Obtain dataset material from its publisher under its terms; see the main project's evidence reconstruction/rights notes. Do not replace the missing strings with a new paraphrase and call the result the historical fit.

Capture NPZs are also not included. The historical hooks recorded FP32 means over the last 32 prefill positions: sharded MLP inputs `x_LAYER` and residual-plus-block-output states `h_LAYER`. Rank0/rank1 input shards are concatenated in rank order; replicated residual states use rank0, as in the original fitter. Matching those capture points, histories, kernels, and source weights is necessary for historical array equivalence. These constructed means are not a validated natural correctness or repetitive-reasoning classifier.

## Inspect/replay the fit

The numerical construction uses `numpy` and `gguf`. Recorded fit environment package versions were NumPy 2.3.5 and GGUF 0.19.0. The graders use math-verify 0.9.0 and SymPy 1.14.0 where applicable. Standard-library utilities can run separately. [requirements.txt](requirements.txt) records these dependencies; installing them is not a complete recreation of the serving environment.

```bash
# Build private inert capture jobs from separately authorized ordered records.
python make_constructed_probes.py \
  --discovery-json PRIVATE/discovery.json \
  --productive-suffix-file PRIVATE/productive_suffix.txt \
  --recheck-sentence-file PRIVATE/recheck_sentence.txt \
  --output-dir PRIVATE/constructed_jobs

# Existing captures only: no inference is performed by this fit.
python fit_sparse_contrasts.py \
  --gguf PRIVATE/source.gguf \
  --capture-map templates/neighbor_capture_map.redacted.json \
  --captures PRIVATE/captures --layers 49 50 51 \
  --output-dir PRIVATE/fitted_layers

python assemble_upper_edit.py \
  --center PRIVATE/original_fitted_center50.npz \
  --neighbor49 PRIVATE/fitted_layers/candidate_layer49.npz \
  --neighbor51 PRIVATE/fitted_layers/candidate_layer51.npz \
  --evaluation-alpha 1.5 --output PRIVATE/upper_edit.npz
```

The center must be the original preserved center candidate; refitting it on a different capture batch is a different artifact. Assembly preserves its arrays and multiplies flank coefficients by 0.5/3. Runtime alpha 1.5 therefore produces effective strengths 0.25/1.5/0.25. This is rank one per matrix with 64 supported input columns, not rank 64. Hash the final arrays/artifact and compare the model release identity; no numerical equivalence is inferred from naming alone.

## Evaluation and grading

Fill `templates/suite_plan.template.json` with paths to authorized, frozen jobs. The job template intentionally has an empty record list and cannot accidentally run as a benchmark. The request runner keeps medium reasoning, temperature 1.3, sampler settings, raw input mode, requested budget, ordered records, and seed checks. It requires token-ID-bearing SSE responses and refuses result overwrite. Profile identity is caller-declared and hash-checked; an API model alias is not proof that a server loaded the intended weights. Process, compiled-graph, cache, and numerical attestation remain separate.

```bash
# Inspect argv only: no requests or service operations.
python run_suite.py --plan-file PRIVATE/suite_plan.json \
  --profile PRIVATE/attested_profile --output-dir PRIVATE/results \
  --base-url http://127.0.0.1:PORT

# Validate one supplied request without HTTP.
python api_batch_eval.py --check --job PRIVATE/job.json \
  --profile PRIVATE/attested_profile --output PRIVATE/result.json \
  --base-url http://127.0.0.1:PORT --expected-seed 20261106

# Grade supplied private results; these score files can contain answer fields.
python hle_score.py PRIVATE/result.json --output PRIVATE/hle_scores.json
python score_math_tool.py PRIVATE/result.json --output PRIVATE/math_tool_scores.json
python score_state_transfer.py PRIVATE/result.json \
  --scoring PRIVATE/frozen_state_map.json --output PRIVATE/state_scores.json
```

Adding `--run` to `run_suite.py` explicitly sends requests to an already supplied local server. Nothing in this publication task executed that mode. Generated tool calls are text under evaluation, never executed by these graders. The smoke task has a separate schema/task cohort and is not part of this dispatcher.

The ported score functions retain original output fields, including supplied reference answers in private reports. Keep both reconstructed inputs and newly generated result/score files out of the public repository. This directory's `.gitignore` excludes `PRIVATE/` and generated artifacts here.

## Laboratory route inspection

```bash
python lab_routing.py --conditions ../evidence/laboratory_conditions.json \
  --condition upper_cycle_twice --job PRIVATE/laboratory7.json \
  --candidate-dir PRIVATE/candidates --output-dir PRIVATE/inert_route_plan
```

This emits the recorded insertion route, edit, generation, and reset descriptions. It does not place them in a live queue. The original engine uses preallocated spare attention objects with independent state/cache identities while sharing stateless weights. Simply calling the same stateful block object twice is not the historical intervention. The GPU worker/engine files are omitted to avoid duplicating the runtime; their exact hashes and requirements are listed in the provenance manifest.

## Offline checks and limits

```bash
python validate_cpu.py --conditions ../evidence/laboratory_conditions.json
# Add --with-fit when NumPy/GGUF are installed; still no model or network calls.
```

Checks use synthetic choice/state examples, fake SSE events, a tetrahedral graph, fourteen public route descriptions, and optional small random matrices. They test cutoff handling, strict parsing, sequence order, extra entities, multipart/malformed finals, stream termination, routing, and rank-one algebra. They do not run an end-to-end experiment or validate a rebuilt GPU stack. [VALIDATION.json](VALIDATION.json) records what was actually checked.

Excluded original scripts include dataset preparation, historical queue/service control, model-specific worker capture/routing, the full constrained-key fitter, and question-specific proof inputs. [SOURCE_PROVENANCE.json](SOURCE_PROVENANCE.json) gives exact source hashes, reasons, and reconstruction requirements. The public code strengthens method inspection and authorized replay, while full historical generation reproducibility remains conditional on unavailable/private inputs and the pinned numerical runtime. Source hashes are provenance, not a substitute for those inputs.
