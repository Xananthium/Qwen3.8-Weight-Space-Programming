# Contributing to Calmer Qwen

Help us understand which weight edits change reasoning usefully, where they fail, and whether the effects reproduce. Documentation improvements, original diagnostic tasks, analysis tools, replications, and negative results all belong here.

You do not need a GPU or access to HLE to make your first contribution.

## Start in five minutes

```bash
git clone https://github.com/Xananthium/Qwen3.8-Weight-Space-Programming.git
cd Qwen3.8-Weight-Space-Programming
python3 tools/check_public_release.py
python3 tools/verify_selected_excerpts.py
python3 -B research_code/validate_cpu.py --conditions evidence/laboratory_conditions.json
```

These commands use Python 3.12+ and its standard library. They check public artifacts, selected quotes, synthetic grading fixtures, and recorded layer routes. They do not load a model or send inference requests. The optional figure and numerical-fitting dependencies are documented in their respective directories.

Fork the repository, make a focused branch, and open a pull request describing what changes and how you checked it. The [pull-request template](.github/PULL_REQUEST_TEMPLATE.md) is deliberately short. For a larger experiment, open an [experiment proposal](https://github.com/Xananthium/Qwen3.8-Weight-Space-Programming/issues/new?template=experiment.yml) first so others can help refine it; that is an invitation, not a requirement for small fixes.

## Good first contributions

| Contribution | A useful result looks like |
|---|---|
| Make an explanation clearer | A small documentation diff with the supporting case or source |
| Test a grader edge case | An original synthetic fixture that exposes a specific parsing ambiguity |
| Study a language metric | A script and comparison on the public measurements; clear definitions and denominators |
| Design a diagnostic | An original question with an independently checkable solution and a stated failure mode |
| Reproduce a run | Exact artifact/runtime identities, settings, seeds, budgets, and all outcomes |

See [ROADMAP.md](ROADMAP.md) for concrete research questions. Please distinguish a proposed direction from a completed result.

## Keep the evidence interpretable

For experimental contributions, record:

1. **What changed:** base/model/delta hashes, edit layers and strengths, and runtime representation. A merged GGUF and the historical sidecar are different numerical artifacts.
2. **What stayed matched:** prompts or authorized record IDs, sampler, seed, reasoning effort, output budget, runtime, and comparison order. The reference setting is medium reasoning at temperature 1.3; report deviations explicitly.
3. **What happened:** all selected cases, including wrong answers, cutoffs, unparsed outputs and exceptions. Report thinking/final token counts separately when available.
4. **What was checked:** strict grades, intended-answer review, and proof validity as separate fields. State who or what reviewed the explanations.
5. **What the result supports:** identify reused development cases, held-out cases, selection history and unanswered questions. A short answer or a confident sentence is not itself a correctness result.

Public issues should contain the smallest reproducible example and sanitized metadata. Do not upload gated benchmark questions, reference keys, complete benchmark-containing traces, credentials, machine environment dumps, or reversible token arrays. Use original synthetic examples where possible. Selected model-output excerpts need a content review, explicit omissions, and source offsets/hashes; see [examples/](examples/SELECTED_CONVERSATIONS.md).

## Preserve the historical record

The checked-in metrics and frozen source copies describe a particular experiment. Add new runs under a clearly named directory with their own provenance rather than replacing the original scores. If a historical result is wrong, document the correction and retain enough information to understand the change.

Some files are covered by hash inventories. An intentional documentation or source change may require updating the corresponding manifest entry; explain that update in the PR. Do not regenerate hashes simply to conceal an unexpected mismatch. Preserve the exact bytes of unmodified vendor code, pinned deltas and scientific data. `.gitattributes` disables newline conversion for this reason.

The public checks do not certify a GPU runtime, numerical equivalence, benchmark accuracy, or the validity of every proof. Those need their own evidence.

## Working together

Be specific, curious and respectful. Challenge claims with examples and measurements; welcome corrections. Disclose substantial AI assistance and distinguish automated grading from qualitative review. Contributions to original project material use the repository's Apache-2.0 license; keep third-party attributions and component licenses intact.
