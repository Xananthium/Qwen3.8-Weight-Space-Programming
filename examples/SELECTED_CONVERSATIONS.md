# Selected conversations and thinking excerpts

These six **post-hoc illustrations** show stopping, useful rechecking, incorrect finalization, retained behavior and failure. They are not representative samples, additional tests, or measures of a model mental state. “Original” means control; “selected” means the measured half-dose sidecar representation. Full-run correctness and proof caveats accompany the language.

Quoted blocks are exact saved strings. Editorial omissions appear **outside** them; noncontiguous fragments are not rewritten into a continuous conversation. Actual thinking delimiters appear only when quoted from the source. The [machine-readable manifest](selected_excerpts.json) binds every span to a source hash, output ID, field, Unicode offsets and excerpt hash. Raw sources remain private; see [reconstruction](../evidence/RECONSTRUCTION.txt).

## 1. A constructed repetition loop finally stops

Both conditions were supplied the same primed continuation, containing **five complete copies** of this sentence. This is supplied context, not new reasoning generated in the comparison. The benchmark question and worked-prefix calculation are not reproduced.

**Supplied priming sentence (one of five; identical for both):**

````text
Wait, I should check that again. The calculation seems right, but perhaps I missed something. Let me go back and verify the same steps before I give the answer.

````


The original generates **117 further complete copies plus a partial “Wait”**, reaches the 4,096-token limit and emits no final answer. Here are its first two copies and its last complete copy plus partial ending.

**Original — generated thinking excerpts:**

````text
Wait, I should check that again. The calculation seems right, but perhaps I missed something. Let me go back and verify the same steps before I give the answer.
Wait, I should check that again. The calculation seems right, but perhaps I missed something. Let me go back and verify the same steps before I give the answer.

````

[... 18,354 intervening source characters omitted ...]

````text
Wait, I should check that again. The calculation seems right, but perhaps I missed something. Let me go back and verify the same steps before I give the answer.
Wait
````


The selected edit generates **six further complete copies**. They are all shown, rather than implying the repetitive language disappears.

**Selected half dose — all generated thinking:**

````text
Wait, I should check that again. The calculation seems right, but perhaps I missed something. Let me go back and verify the same steps before I give the answer.
Wait, I should check that again. The calculation seems right, but perhaps I missed something. Let me go back and verify the same steps before I give the answer.
Wait, I should check that again. The calculation seems right, but perhaps I missed something. Let me go back and verify the same steps before I give the answer.
Wait, I should check that again. The calculation seems right, but perhaps I missed something. Let me go back and verify the same steps before I give the answer.
Wait, I should check that again. The calculation seems right, but perhaps I missed something. Let me go back and verify the same steps before I give the answer.
Wait, I should check that again. The calculation seems right, but perhaps I missed something. Let me go back and verify the same steps before I give the answer.

````


**Actual closing marker:**

````text
</think>
````


[Final introduction and steps 1–2 omitted. The following is the exact remaining calculation and result.]

**Selected half dose — generated final:**

````text
3. **How many towels can she wash per day?**
7 towels per wash × 2 washes per day = 14 towels per day.

4. **How many days to wash all 98 towels?**
98 towels ÷ 14 towels per day = 7 days.

It will take Sanya \boxed{7} days to wash all the bath towels.
````


This case finishes correctly in 392 generated tokens. Its local `wait` density is almost unchanged: 34.77 versus 34.48 regex occurrences per 1,000 thinking words. The gain is stopping/completion on a constructed example reused during discovery, not demonstrated suppression of a universal reasoning loop. Source formatting is preserved.

<details>
<summary>Case IDs, seeds, token counts and full-run review</summary>

| Condition | Seed | Total / thinking / final tokens | Strict status |
|---|---:|---:|---|
| control | 20261106 | 4,096 / 4,096 / 0 | cutoff |
| halfdose | 20261106 | 392 / 210 / 180 | correct |

Case ID: `primed_gsm8k_train:2451`. Counts describe whole generated outputs; supplied prompts are excluded. Remaining tokens are separately accounted control tokens.

</details>

## 2. Rechecking helps the original; a wrong state survives in the edit

This compact task was authored for the experiment. The full actual user message, including the appended answer-format instruction, is shown once because both conditions receive identical text.

**User:**

> A text editor starts with CABIN and the cursor immediately after N. Backspace removes the character immediately left of the cursor; Delete removes the character immediately right of it. Inserting a letter puts it at the cursor and advances the cursor past that letter. Perform these operations in order: Backspace once; move the cursor left two positions; Delete once; insert T; move left one position; insert R. What is the final text, and how many characters are left of the cursor?
> Please reason step by step, and put your final answer within \boxed{}.


The original initially misindexes a character, then repairs the state by rechecking. Earlier reasoning is omitted.

**Original — generated thinking excerpt and final:**

````text
Wait, cursor at position 2 means between index 1 and index 2. The character immediately right is at index 2, which is 'B'.

Hmm, let me reconsider. If text is "CABI", positions are:
- Position 0: before C
- Position 1: between C and A (after C)
- Position 2: between A and B (after A)
- Position 3: between B and I (after B)
- Position 4: after I

Cursor at position 2 means between A and B. Delete removes the character to the right, which is 'B' (index 2).

Text becomes: "CAI", cursor stays at position 2.

4. Insert T at position 2: C, A, T, I → "CATI", cursor at position 3.

5. Move left one: cursor 3 → 2. Cursor at position 2 (between A and T).
   Text: "CATI".

6. Insert R at position 2: C, A, R, T, I → "CARTI", cursor at position 3.

So final text is "CARTI" with 3 characters left of the cursor (C, A, R).


````

[... 2,130 intervening source characters omitted ...]

````text
## Final Result

The text is: **C A R T I**

Characters left of the cursor (positions 0–2): **C, A, R** = **3 characters**

$$\boxed{3}$$
````


Its corrected prose gives the intended text, but only the cursor count is boxed. Frozen strict grading is **unparsed**; agent-reviewed intended correctness is a separate observation.

The selected run also rechecks. Its late operation diagrams show one character order, but the following literal and final box carry a different order. Earlier reasoning and the intervening final walkthrough are omitted.

**Selected half dose — generated thinking excerpt and final:**

````text
Let me re-verify this carefully.

Start: C-A-B-I-N, cursor after N (position 5)

1. Backspace: delete char before cursor (N). Text: C-A-B-I. Cursor at position 4 (after I).

2. Move left 2: Cursor goes to position 2. Position 2 is after "CA", before "BI".
   C-A-|B-I

3. Delete: delete char right of cursor (B). Text: C-A-I. Cursor still at position 2 (after "CA", before "I").
   C-A-|I

4. Insert T: T goes at cursor. Text: C-A-T-I. Cursor at position 3 (after "CAT", before "I").
   C-A-T-|I

5. Move left 1: Cursor at position 2 (after "CA", before "TI").
   C-A-|T-I

6. Insert R: R goes at cursor. Text: C-A-R-T-I. Cursor at position 3 (after "CAR", before "TI").
   C-A-R-|T-I

Final text: "CARIT"
Characters left of cursor: C, A, R = 3

That's the answer.

````

[... 905 intervening source characters omitted ...]

````text
## Final Result

- **Final text:** `CARIT`
- **Characters left of the cursor:** C, A, R → **3 characters**

$$\boxed{CARIT,\ 3}$$
````


This is a genuine wrong final state, not a format-only miss. The edited run is slightly shorter (1,711 versus 1,791 tokens), illustrating why shorter thought and fewer recheck words are not quality scores.

<details>
<summary>Case IDs, seeds, token counts and full-run review</summary>

| Condition | Seed | Total / thinking / final tokens | Strict status |
|---|---:|---:|---|
| control | 20261106 | 1,791 / 1,470 / 319 | unparsed |
| halfdose | 20261106 | 1,711 / 1,381 / 328 | wrong |

Case ID: `state_holdout_v1_04`. Counts describe whole generated outputs; supplied prompts are excluded. Remaining tokens are separately accounted control tokens.

</details>

## 3. A retained tool correction, not a newly repaired loop

This supplied conversation is synthetic. It repeats a failed action and feedback three times; only the user request and last failure pair are shown below. These are authored sandbox paths, not private host paths. No displayed or generated tool calls were executed in this evaluation.

**Supplied user request:**

````text
Inspect changes in the project.
````


**Supplied assistant action (last of three identical failures):**

````text
git diff
````


**Supplied tool feedback:**

````text
Exit 128. Not a git repository. Current directory: /tmp. The repository is /app/project; execute git -C /app/project diff.
````


**Original and selected — byte-identical generated thinking:**

````text
The current directory is /tmp and it's telling me the repo is /app/project. Let me run the command as suggested.

````


[The actual closing-thinking marker is omitted here.]

**Original and selected — byte-identical generated tool-call text:**

````text


<tool_call>
<function=shell>
<parameter=command>
git -C /app/project diff
</parameter>
</function>
</tool_call>
````


Both already produce the prescribed corrective action, using 61 tokens each. This is retention; it is not evidence that the edit repaired a baseline agent loop.

<details>
<summary>Case IDs, seeds, token counts and full-run review</summary>

| Condition | Seed | Total / thinking / final tokens | Strict status |
|---|---:|---:|---|
| control | 20261106 | 61 / 27 / 32 | correct |
| halfdose | 20261106 | 61 / 27 / 32 | correct |

Case ID: `tool_git`. Counts describe whole generated outputs; supplied prompts are excluded. Remaining tokens are separately accounted control tokens.

</details>

## 4. Similar rechecking language, different proof quality

Only reviewed, formula-free language fragments are quoted from this HLE case. Questions, solutions and answer labels are omitted. On seed 07, both choices pass strict grading, but the selected run has an invalid general proof.

**Original, seed 07 — thinking fragment:**

````text
Actually, I want to make sure I haven't made an error.
````


**Selected half dose, seed 07 — noncontiguous thinking fragments:**

````text
Wait, let me re-examine. We need:
````

[... 6,234 intervening source characters omitted ...]

````text
This is the definition I used above. So my analysis is correct.
````


The original uses 6,598 tokens with a valid reviewed proof; selected uses 4,605 with an invalid proof. Assertive wording is not a validated confidence or cognition measure, and both runs recheck.

**Seed05 counterbalance — original thinking fragment:**

````text
Wait, I confused myself. Let me be very careful.
````


**Seed05 counterbalance — selected thinking fragment:**

````text
Wait, I'm confusing myself. Let me be very careful.
````


On seed 05 both reviewed proofs are valid, with nearly identical confusion/recheck wording, while selected grows from 4,270 to 8,812 tokens. Original is strict unparsed and selected strict correct. The surrounding problem-specific reasoning and answers are omitted in every fragment.

<details>
<summary>Case IDs, seeds, token counts and full-run review</summary>

| Condition | Seed | Total / thinking / final tokens | Strict status |
|---|---:|---:|---|
| control | 20261107 | 6,598 / 5,972 / 624 | correct |
| halfdose | 20261107 | 4,605 / 4,022 / 581 | correct |
| control | 20261105 | 4,270 / 3,741 / 527 | unparsed |
| halfdose | 20261105 | 8,812 / 8,065 / 745 | correct |

Case ID: `hle:673722c82bfc8ab579ed111f`. Counts describe whole generated outputs; supplied prompts are excluded. Remaining tokens are separately accounted control tokens.

</details>

## 5. Rechecking persists when the tree attempt completes

These are noncontiguous, formula-free fragments, not a continuous transition or a shortened substitute for the solution.

**Original, seed 07 — generated thinking fragments:**

````text
Wait, I'm confusing myself. Let me be very precise.
````

[... 6,997 intervening source characters omitted ...]

````text
Wait no. Let me parse this more carefully.
````


**Selected half dose, seed 07 — generated thinking fragments:**

````text
Wait, that's not right either. Let me be more careful.
````

[... 4,881 intervening source characters omitted ...]

````text
This makes sense!
````


Original cuts off at 16,384 tokens; selected completes in 11,226 with a strict correct choice and a valid comparative certificate, but false final-history prose. Only generic language is displayed; solution and answer text are omitted. On seed 05 **both** profiles cut off at 16,384. This is not an across-seed completion or proof-quality win.

<details>
<summary>Case IDs, seeds, token counts and full-run review</summary>

| Condition | Seed | Total / thinking / final tokens | Strict status |
|---|---:|---:|---|
| control | 20261107 | 16,384 / 16,384 / 0 | cutoff |
| halfdose | 20261107 | 11,226 / 10,603 / 621 | correct |

Case ID: `hle:66ef3de8b8a1ba6e0ba23498`. Counts describe whole generated outputs; supplied prompts are excluded. Remaining tokens are separately accounted control tokens.

</details>

## 6. Character deterioration is distinct from word repetition

This inset compares early15 with selected half dose, not control. It concerns character form only. Early15 ends a 16,384-token cutoff with 656 consecutive exclamation marks; the exact final 80 are shown.

**Early15 — terminal generated-thinking excerpt:**

````text
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
````


**Selected half dose — late generated-thinking fragment and literal final suffix:**

````text
Wait, actually one more thought.
````

[... 2,181 intervening source characters omitted ...]

````text
Confidence: 72%
````


Selected completes in 13,577 tokens with a correct choice, but unjustified final arithmetic. The readable sentence is not the final line of thought; intervening problem-specific reasoning and final content are explicitly omitted. The quoted confidence suffix is a literal formatting observation, not calibrated confidence. Early15 has frozen word duplicate8=0 despite the punctuation collapse. Neither readable text nor a zero word-duplication statistic certifies a correct argument.

<details>
<summary>Case IDs, seeds, token counts and full-run review</summary>

| Condition | Seed | Total / thinking / final tokens | Strict status |
|---|---:|---:|---|
| early15 | 20261106 | 16,384 / 16,384 / 0 | cutoff |
| halfdose | 20261106 | 13,577 / 13,003 / 572 | correct |

Case ID: `hle:673735aa61f20f11eb1097d2`. Counts describe whole generated outputs; supplied prompts are excluded. Remaining tokens are separately accounted control tokens.

</details>

## Interpretation

These examples preserve positive, negative and null outcomes. They should be read with the [scientific report](../PAPER.md), [full language analysis](../language_analysis/REPORT.md), and complete per-case tables. They do not replace the disclosed denominators or make the selected edit a validated general upgrade.
