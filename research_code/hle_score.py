"""Deterministic HLE choice grading with token-limit hits kept separate."""
from pathlib import Path
from datetime import datetime, timezone
import collections
import hashlib
import json
import re
import statistics
import sys
from hle_continuation import canonicalize

ROOT = Path(__file__).resolve().parent


def parse_answer(text):
    final = text.split('</think>', 1)[-1] if '</think>' in text else ''
    clean = final.replace('**', '').replace('__', '')
    answers = re.findall(r'(?im)^\s*(?:final\s+)?answer\s*:\s*([^\n]+)', clean)
    if answers:
        raw = answers[-1].strip()
    else:
        # Explicit final boxes are common even when the requested Answer: field
        # is omitted. Parse balanced braces, including nested \text{...}.
        boxes = []
        for match in re.finditer(r'\\boxed\s*\{', clean):
            depth, end = 1, match.end()
            while end < len(clean) and depth:
                depth += (clean[end] == '{') - (clean[end] == '}')
                end += 1
            if depth == 0:
                boxes.append(clean[match.end():end - 1].strip())
        if not boxes:
            return None, None
        raw = boxes[-1]
    normalized = raw.strip().strip('$').strip()
    for _ in range(3):
        wrapper = re.fullmatch(r'\\(?:boxed|text|mathrm)\s*\{(.*)\}', normalized, re.S)
        if not wrapper:
            break
        normalized = wrapper[1].strip()
    choice = re.match(r'^\s*(?:option\s+)?[\(\[\{`$]*([A-Z])(?=\s*$|[\)\]\}`$.,:;]|\s+[-–—(])', normalized, flags=re.I)
    return (choice.group(1).upper() if choice else None), raw


def score(result):
    result=canonicalize(result)
    assert not result.get('error'), result.get('error')
    source = {r['id']: r for r in result['job']['records']}
    rows = []
    for out in result['outputs']:
        record = source[out['id']]
        pred, raw = parse_answer(out['text'])
        closed = '</think>' in out['text']
        if out['finish_reason'] == 'length':
            status = 'cutoff'
        elif not closed:
            status = 'unfinished_thinking'
        elif pred is None or pred not in record['choices']:
            status = 'unparsed'
        else:
            status = 'correct' if pred == record['answer'] else 'wrong'
        final = out['text'].split('</think>', 1)[-1] if closed else ''
        confidence = re.findall(r'(?im)confidence\s*:\s*(\d+(?:\.\d+)?)\s*%', final.replace('**', ''))
        words=out['text'][-12000:].split()[-512:]
        grams=[tuple(words[i:i+8]) for i in range(max(0,len(words)-7))]
        duplicate8=0.0 if not grams else 1-len(set(grams))/len(grams)
        rows.append({'id': out['id'], 'category': record['category'], 'subject': record['subject'],
                     'gold': record['answer'], 'predicted': pred, 'raw_answer': raw, 'status': status,
                     'tokens': out['tokens'], 'finish_reason': out['finish_reason'], 'thinking_closed': closed,
                     'confidence': float(confidence[-1]) if confidence else None,
                     'duplicate8_tail':duplicate8,'repetitive_tail_marker':duplicate8>0.5})
    counts = dict(collections.Counter(r['status'] for r in rows))
    return {'grader_version': 'hle_choice_label_v2_explicit_final_box', 'rows': rows,
            'summary': {'n': len(rows), 'counts': counts,
                        'condition': {'temperature': result['job'].get('temperature',1.0), 'max_tokens': result['job']['max_tokens'],
                                      'reasoning_effort': sorted({r.get('reasoning_effort','engine_default_medium') for r in result['job']['records']})},
                        'accuracy_including_unfinished': counts.get('correct', 0)/len(rows),
                        'mean_tokens': statistics.mean(r['tokens'] for r in rows),
                        'repetitive_tail_markers':sum(r['repetitive_tail_marker'] for r in rows),
                        'note': 'Use official benchmark keys. Completed wrong answers are separate from cutoffs, unfinished thinking, and unparsed responses.'}}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Frozen HLE parser/status rules; supplied private inputs only.")
    parser.add_argument("result", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="Private score output; contains supplied answer fields.")
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() == args.result.resolve():
        parser.error("Refuse existing output or input overwrite")
    report = score(json.loads(args.result.read_text()))
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"]))

if __name__ == "__main__":
    main()
