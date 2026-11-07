# Selected literal language examples

These post-hoc illustrations are not representative samples, new tests or a complete proof audit. Questions, HLE solution content and answer labels remain withheld. All quoted strings are exact saved output spans. Omissions appear outside fences; distinct spans are never rewritten into a continuous conversation.

The [manifest](selected_excerpts.json) records source-relative locators, whole-source/output hashes, raw-field Unicode offsets, excerpt hashes, phase and content-review scope. Source files are withheld; the public checker cannot authenticate a private source without separately authorized access. A newline added to display a closing fence is not part of the quoted span.

## 1. Repetition remains visible

Both continuations were primed with repeated synthetic checking language. The existing Calmer run generates 15 complete copies; the layer 18 pilot generates one. One exact copy from each output is shown. Supplied context and the benchmark calculation are omitted.

**calmer_cookie_recheck — thinking:**

````text
Wait, I should check that again. The calculation seems right, but perhaps I missed something. Let me go back and verify the same steps before I give the answer.
````

Source output `primed_gsm8k_train:2079`; raw `text` offsets [0,160).

**pilot_cookie_recheck — thinking:**

````text
Wait, I should check that again. The calculation seems right, but perhaps I missed something. Let me go back and verify the same steps before I give the answer.
````

Source output `primed_gsm8k_train:2079`; raw `text` offsets [0,160).

The full cookie completions use 862 and 554 tokens respectively. On another candidate, one generated copy coexists with a longer 1,024-token response. An unstable 19-marker completion contains an early correct answer but later malformed content. These outcomes are separated in the [language summary](../LANGUAGE.md); low repetition alone is not a success grade.

## 2. A correct rule can coexist with a wrong literal

This editor task was authored locally. The pilot states the insertion rule correctly and shows the intended index sequence, but the next literal string reverses two characters. The conflict is preserved verbatim rather than silently repaired.

**pilot_editor_rule_and_literal_conflict — thinking:**

````text
Wait, no. Inserting at position 2 means the new character goes at index 2, and everything from index 2 onwards shifts right.

Text was: C(0), A(1), I(2)
Insert T at position 2: C(0), A(1), T(2), I(3)
Text: "CTAI", cursor = 3
````

Source output `state_holdout_v1_04`; raw `text` offsets [5313,5537).

[Intervening thinking and final walkthrough omitted.]

Its final prose gives the correct authored state and cursor count:

**pilot_editor_correct_final_content — post_first_close:**

````text
- **Final text:** `CARTI`
- **Characters left of the cursor:** 3
````

Source output `state_holdout_v1_04`; raw `text` offsets [9093,9157).

The final box contains only the cursor count. Frozen strict grading is unparsed, while reviewed content is correct. The complete editor response grows rather than shrinks. This is not evidence that every recheck was removed or that intermediate literals stayed correct.

## 3. Generic HLE rechecking language is not a proof

Only nonsolution, formula-free metareasoning is displayed. The pilot game response completes with a sound general argument, but the following sentence by itself does not demonstrate that argument. Problem-specific reasoning and the answer are withheld.

**pilot_generic_game_recheck — thinking:**

````text
Wait, I think I need to be more careful.
````

Source output `hle:673722c82bfc8ab579ed111f`; raw `text` offsets [12372,12412).

The additional hat response keeps reconsidering and reaches its 32K cap without a final answer. This late generic fragment contains no puzzle assignment, answer or solution:

**pilot_hat_reconsideration — thinking:**

````text
Actually, you know what, let me reconsider one more time. I realize that I should think about this problem more carefully in terms of information asymmetry.
````

Source output `hle:66fb931a089552943999ce86`; raw `text` offsets [98402,98558).

[All surrounding problem-specific reasoning omitted.]

## 4. Punctuation collapse after a good fitting score

The refitted-selector expansion is interrupted by the operator after the hats trace has emitted 14,199 saved tokens. Its terminal run contains 8,044 consecutive exclamation characters; the first 96 are shown. The separate topology output had already stopped naturally with 2,573 such characters. Neither delivers a final answer.

**interrupted_hat_punctuation — thinking:**

````text
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
````

Source output `hle:66fb931a089552943999ce86`; raw `text` offsets [18933,19029).

[The rest of the punctuation run is omitted. The hats request was externally interrupted; it is not a natural ending or a 32K cutoff.]

The selector had matched circular fitting-window RMS while reducing productive fitting RMS. That does not make the generated result successful, nor identify why it failed. The [report](../REPORT.md) keeps operator norm, limited replay diagnostics and free-generation outcomes separate.
