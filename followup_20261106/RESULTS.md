# Complete compiled development outcomes

All completed numerical comparisons are retained. These are repeated exposed development observations, not independent benchmark items. HLE choice correctness, sound full-scope arguments and error-free explanations are separate. Missing/cutoff finals earn neither proof criterion. No official answer labels are published.

| Run / panel | Seed; cap; batch | HLE choices | GSM | Sound core | Error-free final | Tokens | Cutoffs | Wait |
|---|---|---:|---:|---:|---:|---:|---:|---:|
|`000_calmer` / `fast5_seed06`|20261106; 16,384; 1|2/2|3/3|2/2|1/2|23,831|0|31|
|`001_original` / `fast5_seed06`|20261106; 16,384; 1|2/2|3/3|2/2|1/2|28,481|0|54|
|`002_l62_01pct` / `fast5_seed06`|20261106; 16,384; 1|1/2|3/3|0/2|1/2|20,501|0|34|
|`003_l62_03pct` / `fast5_seed06`|20261106; 16,384; 1|2/2|3/3|1/2|0/2|16,042|0|26|
|`004_attention55_005pct` / `fast5_seed06`|20261106; 16,384; 1|1/2|3/3|1/2|1/2|32,616|1|58|
|`005_mlp53_005pct` / `fast5_seed06`|20261106; 16,384; 1|1/2|3/3|1/2|1/2|26,223|1|29|
|`006_neuron18_zero` / `fast5_seed06`|20261106; 16,384; 1|1/2|3/3|0/2|0/2|23,463|1|40|
|`007_mlp53_random_u` / `fast5_seed06`|20261106; 16,384; 1|2/2|3/3|1/2|1/2|21,530|0|34|
|`008_calmer_expanded` / `expansion2_seed06`|20261106; 32,768; 2|1/2|—|1/2|0/2|56,262|0|123|
|`008_calmer_expanded` / `fast5_seed06_cap32768`|20261106; 32,768; 4|2/2|3/3|2/2|1/2|18,589|0|34|
|`008_calmer_expanded` / `fast5_seed08`|20261108; 16,384; 1|1/2|3/3|1/2|0/2|28,675|1|57|
|`008_calmer_expanded` / `gsm_retention24_seed06`|20261106; 8,192; 3|—|24/24|—|—|9,986|0|5|
|`008a_combo53_attention55` / `expansion2_seed06`|20261106; 32,768; 3|1/2|—|1/2|0/2|58,804|1|111|
|`008a_combo53_attention55` / `fast5_seed06_cap32768`|20261106; 32,768; 1|1/2|3/3|1/2|0/2|25,887|0|39|
|`008b_calmer_reproducibility` / `fast5_seed06`|20261106; 16,384; 2|1/2|3/3|1/2|0/2|20,072|0|32|
|`008b_calmer_reproducibility` / `fast5_seed06_cap32768`|20261106; 32,768; 1|2/2|3/3|2/2|1/2|23,831|0|31|
|`008b_calmer_reproducibility` / `fast5_seed06_duplicate`|20261106; 16,384; 3|1/2|3/3|1/2|0/2|20,072|0|32|
|`009_l62_02pct` / `expansion2_seed06`|20261106; 32,768; 3|0/2|—|0/2|0/2|65,536|2|123|
|`009_l62_02pct` / `fast5_seed06`|20261106; 16,384; 1|2/2|3/3|1/2|1/2|26,311|0|48|
|`010_l61_01pct` / `fast5_seed06`|20261106; 16,384; 1|1/2|3/3|1/2|1/2|33,784|1|45|
|`011_attention55_cap32768` / `fast5_seed06_cap32768`|20261106; 32,768; 1|2/2|3/3|2/2|1/2|27,187|0|47|
|`012_l62_03pct_eosprotected` / `expansion2_seed06`|20261106; 32,768; 3|0/2|—|0/2|0/2|65,536|2|127|
|`012_l62_03pct_eosprotected` / `fast5_seed06`|20261106; 16,384; 1|2/2|3/3|1/2|1/2|30,833|0|47|
|`012a_l62_eosclosingprotected` / `fast5_seed06`|20261106; 16,384; 1|1/2|3/3|1/2|1/2|25,017|1|42|
|`012b_l62_adaptive_selector` / `fast5_seed06`|20261106; 16,384; 1|0/2|3/3|0/2|0/2|21,496|1|18|
|`013_mlp18_005pct` / `expansion2_seed06`|20261106; 32,768; 3|1/2|—|1/2|0/2|43,416|1|112|
|`013_mlp18_005pct` / `fast5_seed06`|20261106; 16,384; 1|2/2|3/3|2/2|1/2|18,481|0|30|
|`014_attention63_005pct` / `fast5_seed06`|20261106; 16,384; 1|2/2|3/3|1/2|0/2|20,962|0|33|

The exact counts and request-reuse positions are in [experiments.csv](metrics/experiments.csv). These manual proof judgments include preserved review corrections to coding/parse assumptions; they are not blind automatic proof scores.

## Six-case continuation and retention panel

The panel includes reused constructed loops and seeded authored continuations. It does not consist of six independent unseen benchmark questions. A format-only box miss can retain correct prose; a correct early box followed by malformed output is not a coherent finalization success.

| Run | Strict boxed grade | Reviewed coherent content | Tokens | Cutoffs |
|---|---:|---:|---:|---:|
|`000_calmer`|5/6|6/6|3,291|0|
|`001_original`|3/6|4/6|11,059|1|
|`002_l62_01pct`|5/6|6/6|3,585|0|
|`003_l62_03pct`|4/6|4/6|3,349|0|
|`004_attention55_005pct`|5/6|6/6|3,200|0|
|`005_mlp53_005pct`|6/6|6/6|3,597|0|
|`006_neuron18_zero`|6/6|6/6|3,452|0|
|`007_mlp53_random_u`|5/6|6/6|3,663|0|
|`008_calmer_expanded`|5/6|6/6|3,291|0|
|`008a_combo53_attention55`|6/6|6/6|3,152|0|
|`009_l62_02pct`|5/6|6/6|3,933|0|
|`010_l61_01pct`|6/6|6/6|3,423|0|
|`012_l62_03pct_eosprotected`|4/6|6/6|3,574|0|
|`012a_l62_eosclosingprotected`|5/6|6/6|3,582|0|
|`012b_l62_adaptive_selector`|6/6|6/6|3,686|0|
|`013_mlp18_005pct`|5/6|6/6|4,694|0|
|`014_attention63_005pct`|3/6|5/6|10,626|1|

## Interrupted batch and missing confirmation

- `012b_l62_adaptive_selector`: expanded topology naturally stops after 10,631 tokens with no final answer. Hats is operator interrupted; the saved prefix has 14,199 tokens and no natural finish reason. The run is not given a completed-batch grade or reported as a 32K cutoff.
- `016_mlp18_warm16`: infrastructure failure during startup before readiness; no evaluation requests or model answers.
- `017_mlp18_expanded`: did not launch during the experiment. Candidate second-seed and GSM24 results remain missing.
- Later user-selected pilot activation and readiness smoke are operational checks, not benchmark replications.

## Inventory and access

14 additional weight variants; 20 startup attempts; 45 completed batches plus one interrupted batch; 248 saved response records; 933,411 observed generated tokens. Counts exclude earlier busy-service/eager generations and activation replays. No unfavorable completed comparison was removed.

[All batch metrics](metrics/batches.csv), [all response metrics](metrics/generations.csv), [source hashes and transformations](metrics/source_manifest.json), and [scope](RIGHTS_AND_SCOPE.md) identify the public evidence boundary. Raw questions, keys, full traces and token arrays remain withheld.
