"""Render only the explicitly content-reviewed public excerpt allowlist."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
records=json.loads((P/'examples/selected_excerpts.json').read_text())['records']
by={r['id']:r for r in records}
lines=['# Selected literal language examples','',
 'These post-hoc illustrations are not representative samples, new tests or a complete proof audit. Questions, HLE solution content and answer labels remain withheld. All quoted strings are exact saved output spans. Omissions appear outside fences; distinct spans are never rewritten into a continuous conversation.','',
 'The [manifest](selected_excerpts.json) records source-relative locators, whole-source/output hashes, raw-field Unicode offsets, excerpt hashes, phase and content-review scope. Source files are withheld; the public checker cannot authenticate a private source without separately authorized access. A newline added to display a closing fence is not part of the quoted span.','']
def quote(key):
    r=by[key]
    lines.extend([f"**{key} — {r['phase']}:**",'', '````text',r['text'],'````','',f"Source output `{r['output_id']}`; raw `text` offsets [{r['start']},{r['end']}).",''])
lines+=['## 1. Repetition remains visible','',
 'Both continuations were primed with repeated synthetic checking language. The existing Calmer run generates15 complete copies; the layer18 pilot generates one. One exact copy from each output is shown. Supplied context and the benchmark calculation are omitted.','']
quote('calmer_cookie_recheck');quote('pilot_cookie_recheck')
lines+=['The full cookie completions use862 and554 tokens respectively. On another candidate, one generated copy coexists with a longer1,024-token response. An unstable19-marker completion contains an early correct answer but later malformed content. These outcomes are separated in the [language summary](../LANGUAGE.md); low repetition alone is not a success grade.','',
 '## 2. A correct rule can coexist with a wrong literal','',
 'This editor task was authored locally. The pilot states the insertion rule correctly and shows the intended index sequence, but the next literal string reverses two characters. The conflict is preserved verbatim rather than silently repaired.','']
quote('pilot_editor_rule_and_literal_conflict')
lines+=['[Intervening thinking and final walkthrough omitted.]','',
 'Its final prose gives the correct authored state and cursor count:','']
quote('pilot_editor_correct_final_content')
lines+=['The final box contains only the cursor count. Frozen strict grading is unparsed, while reviewed content is correct. The complete editor response grows rather than shrinks. This is not evidence that every recheck was removed or that intermediate literals stayed correct.','',
 '## 3. Generic HLE rechecking language is not a proof','',
 'Only nonsolution, formula-free metareasoning is displayed. The pilot game response completes with a sound general argument, but the following sentence by itself does not demonstrate that argument. Problem-specific reasoning and the answer are withheld.','']
quote('pilot_generic_game_recheck')
lines+=['The additional hat response keeps reconsidering and reaches its32K cap without a final answer. This late generic fragment contains no puzzle assignment, answer or solution:','']
quote('pilot_hat_reconsideration')
lines+=['[All surrounding problem-specific reasoning omitted.]','',
 '## 4. Punctuation collapse after a good fitting score','',
 'The refitted-selector expansion is interrupted by the operator after the hats trace has emitted14,199 saved tokens. Its terminal run contains8,044 consecutive exclamation characters; the first96 are shown. The separate topology output had already stopped naturally with2,573 such characters. Neither delivers a final answer.','']
quote('interrupted_hat_punctuation')
lines+=['[The rest of the punctuation run is omitted. The hats request was externally interrupted; it is not a natural ending or a32K cutoff.]','',
 'The selector had matched circular fitting-window RMS while reducing productive fitting RMS. That does not make the generated result successful, nor identify why it failed. The [report](../REPORT.md) keeps operator norm, limited replay diagnostics and free-generation outcomes separate.']
text='\n'.join(lines)+'\n'
for old,new in [('generates15','generates 15'),('layer18','layer 18'),('use862','use 862'),('and554','and 554'),('longer1,024','longer 1,024'),('unstable19','unstable 19'),('its32K','its 32K'),('emitted14,199','emitted 14,199'),('contains8,044','contains 8,044'),('first96','first 96'),('with2,573','with 2,573'),('a32K','a 32K')]:text=text.replace(old,new)
for r in records:assert r['text'] in text
(P/'examples/SELECTED_LANGUAGE.md').write_text(text)
