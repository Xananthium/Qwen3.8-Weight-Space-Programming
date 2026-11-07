# Language counts are observations, not cognition scores

The public [per-generation ledger](metrics/generations.csv) covers all 248 isolated compiled response records, including the externally interrupted prefix. No question, full trace, answer label or token array is included. The [fast-panel language summary](metrics/language_summary.csv) includes request identities; later same-weight requests must not be confused with first-batch controls.

`wait` is counted case-insensitively as a whole word before the **first** generated closing-thinking marker. Thinking words are regex `\b\w+\b` matches in that same segment. Rates use the sum of word counts, not an unweighted mean of per-output rates. They are not tokenizer-token counts. Exact cookie repetition counts use the complete supplied synthetic sentence, and count only newly generated copies.

| Fast panel | Total tokens | Thinking words | Wait occurrences | Wait per 1,000 thinking words |
|---|---:|---:|---:|---:|
|Existing Calmer|23,831|11,155|31|2.779|
|Layer 18 pilot|18,481|8,053|30|3.725|

The pilot is shorter but does not have a lower normalized rate. Fewer repeated sentences, fewer markers, natural termination, correct answer content and a valid proof are different outcomes.

The cookie continuation improves from 15 generated sentence copies to 1 and from 862 to 554 tokens in the pilot. The 1% layer 62 alternative also produces only one copy, but grows to 1,024 tokens. The 3% alternative contains a correct early answer before an unstable malformed ending. The attention 63 alternative produces only three exact copies but ends in malformed text at the 8,192-token cap. None of those distinctions can be recovered from a sentence count alone.

The refitted-selector hat run has an 8,044-character exclamation run and is **operator interrupted** after 14,199 saved tokens. This is not a natural stop or a 32K cutoff. A zero word-duplication statistic can coexist with punctuation collapse; the public ledger therefore includes longest exclamation run and closing-marker counts alongside words.

[Literal examples](examples/SELECTED_LANGUAGE.md) are deliberately selected illustrations, not representative samples or extra tests. Generic HLE rechecking fragments do not display the private solution or independently certify the proof judgment. The fuller authored editor example retains the conflict between a correct rule and an incorrect intermediate literal.

“Thinking” names a model-output phase. These emitted words are not direct observations of subjective anxiety, calibrated confidence or an identified internal causal mechanism.
