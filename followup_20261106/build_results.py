"""Rebuild the public result table from the public allowlisted ledgers."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
load=lambda n:json.loads((P/n).read_text())
fmt=lambda x:'—' if x is None else str(x)
rows=load('metrics/experiments.json');retention=load('metrics/retention.json')
lines=['# Complete compiled development outcomes','',
 'All completed numerical comparisons are retained. These are repeated exposed development observations, not independent benchmark items. HLE choice correctness, sound full-scope arguments and error-free explanations are separate. Missing/cutoff finals earn neither proof criterion. No official answer labels are published.','',
 '| Run / panel | Seed; cap; batch | HLE choices | GSM | Sound core | Error-free final | Tokens | Cutoffs | Wait |',
 '|---|---|---:|---:|---:|---:|---:|---:|---:|']
for r in rows:
    h=f"{r['HLE_correct']}/{r['HLE_n']}" if r['HLE_n'] else '—'
    g=f"{r['GSM_correct']}/{r['GSM_n']}" if r['GSM_n'] else '—'
    proof=lambda k:f"{r[k]}/{r['reviewed_HLE_cases']}" if r[k] is not None else '—'
    lines.append(f"|`{r['run']}` / `{r['panel']}`|{r['seed']}; {r['cap']:,}; {fmt(r['batch_position'])}|{h}|{g}|{proof('sound_core_arguments')}|{proof('error_free_finals')}|{r['total_tokens']:,}|{r['cutoffs']}|{r['wait_occurrences']}|")
lines+=['','The exact counts and request-reuse positions are in [experiments.csv](metrics/experiments.csv). These manual proof judgments include preserved review corrections to coding/parse assumptions; they are not blind automatic proof scores.','',
 '## Six-case continuation and retention panel','',
 'The panel includes reused constructed loops and seeded authored continuations. It does not consist of six independent unseen benchmark questions. A format-only box miss can retain correct prose; a correct early box followed by malformed output is not a coherent finalization success.','',
 '| Run | Strict boxed grade | Reviewed coherent content | Tokens | Cutoffs |','|---|---:|---:|---:|---:|']
for r in retention:lines.append(f"|`{r['run']}`|{r['strict_correct']}/{r['n']}|{r['reviewed_content_correct']}/{r['n']}|{r['tokens']:,}|{r['cutoffs']}|")
lines+=['','## Interrupted batch and missing confirmation','',
 '- `012b_l62_adaptive_selector`: expanded topology naturally stops after 10,631 tokens with no final answer. Hats is operator interrupted; the saved prefix has 14,199 tokens and no natural finish reason. The run is not given a completed-batch grade or reported as a 32K cutoff.',
 '- `016_mlp18_warm16`: infrastructure failure during startup before readiness; no evaluation requests or model answers.',
 '- `017_mlp18_expanded`: did not launch during the experiment. Candidate second-seed and GSM24 results remain missing.',
 '- Later user-selected pilot activation and readiness smoke are operational checks, not benchmark replications.','',
 '## Inventory and access','',
 '14 additional weight variants; 20 startup attempts; 45 completed batches plus one interrupted batch; 248 saved response records; 933,411 observed generated tokens. Counts exclude earlier busy-service/eager generations and activation replays. No unfavorable completed comparison was removed.','',
 '[All batch metrics](metrics/batches.csv), [all response metrics](metrics/generations.csv), [source hashes and transformations](metrics/source_manifest.json), and [scope](RIGHTS_AND_SCOPE.md) identify the public evidence boundary. Raw questions, keys, full traces and token arrays remain withheld.']
(P/'RESULTS.md').write_text('\n'.join(lines)+'\n')
