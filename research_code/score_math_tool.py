"""Score saved generations, keeping truncation separate from actual repetition."""
import collections
import json
from pathlib import Path
import re
import statistics
import sys
from math_verify import parse, verify, LatexExtractionConfig, ExprExtractionConfig

ROOT=Path(__file__).resolve().parent
GRADER_VERSION='math_verify_with_ordinal_grade_normalization_v2'

def normalize_answer(answer):
    if answer is None:
        return None
    plain=re.sub(r'\\(?:text|mathrm)\{([^{}]*)\}',r'\1',answer).strip()
    grade=re.fullmatch(r'(\d+)\s*(?:\^\s*\{\s*(?:st|nd|rd|th)\s*\}|(?:st|nd|rd|th))\s*grade',plain,flags=re.I)
    return grade.group(1) if grade else answer

def last_box(text):
    matches=list(re.finditer(r'\\(?:boxed|fbox)\s*\{',text))
    for match in reversed(matches):
        start=match.end(); depth=1
        for j in range(start,len(text)):
            if text[j]=='{': depth+=1
            elif text[j]=='}': depth-=1
            if depth==0: return text[start:j]
    return None

def duplication(text):
    words=text[-12000:].split()[-512:]
    grams=[tuple(words[i:i+8]) for i in range(max(0,len(words)-7))]
    return 0.0 if not grams else 1-len(set(grams))/len(grams)

def score(result):
    records={r['id']:r for r in result['job']['records']}
    rows=[]
    for out in result.get('outputs',[]):
        source=records[out['id']]
        text=out['text']
        final=text.split('</think>')[-1] if '</think>' in text else text
        answer=last_box(final)
        extra={}
        if source.get('kind')=='tool':
            calls=re.findall(r'<tool_call>(.*?)</tool_call>',final,flags=re.S)
            action='\n'.join(calls)
            commands=re.findall(r'<parameter=command>(.*?)</parameter>',action,flags=re.S)
            commands += re.findall(r'"command"\s*:\s*"([^"]+)"',action)
            correct=bool(calls) and source['expected'] in action and not any(c.strip()==source['forbidden'] for c in commands)
            extra={'tool_commands':[c.strip() for c in commands],
                   'repeated_failed_action':any(c.strip()==source['forbidden'] for c in commands),
                   'repeated_failed_operation':any(re.match(re.escape(source['forbidden'])+r'(?=$|[\s;&|<>])', c.strip()) is not None for c in commands),
                   'valid_tool_call':bool(commands), 'direct_corrective_action':bool(correct)}
        else:
            gold=parse('\\boxed{'+source['answer']+'}',extraction_config=[LatexExtractionConfig()])
            normalized=normalize_answer(answer)
            pred=parse('\\boxed{'+normalized+'}',extraction_config=[LatexExtractionConfig()]) if normalized is not None else []
            if normalized != answer:
                extra['normalized_answer']=normalized
            correct=bool(gold and pred and verify(gold,pred))
        rows.append({'id':out['id'],'source':source.get('source',source.get('kind','unknown')),
            'correct':bool(correct),'extracted_answer':answer,'tokens':out['tokens'],
            'completed_correct':bool(correct) and '</think>' in text and out['finish_reason']!='length',
            'truncated':out['finish_reason']=='length','thinking_closed':'</think>' in text,
            'duplicate8_tail':duplication(text), 'repetitive_tail':duplication(text)>0.5, **extra})
    groups={}
    for key in sorted({r['source'] for r in rows}|{'all'}):
        rr=rows if key=='all' else [r for r in rows if r['source']==key]
        groups[key]={'n':len(rr),'correct':sum(r['correct'] for r in rr),
            'completed_correct':sum(r['completed_correct'] for r in rr),
            'accuracy':sum(r['correct'] for r in rr)/len(rr),
            'truncated':sum(r['truncated'] for r in rr),
            'repetitive_tails':sum(r['repetitive_tail'] for r in rr),
            'mean_tokens':statistics.mean(r['tokens'] for r in rr),
            'mean_duplicate8_tail':statistics.mean(r['duplicate8_tail'] for r in rr)}
        if any('tool_commands' in r for r in rr):
            groups[key]['repeated_failed_actions']=sum(r.get('repeated_failed_action',False) for r in rr)
            groups[key]['repeated_failed_operations']=sum(r.get('repeated_failed_operation',False) for r in rr)
            groups[key]['valid_tool_calls']=sum(r.get('valid_tool_call',False) for r in rr)
            groups[key]['direct_corrective_actions']=sum(r.get('direct_corrective_action',False) for r in rr)
    return {'grader_version':GRADER_VERSION,'groups':groups,'rows':rows}

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Frozen math_verify/tool predicates; no tool execution.")
    parser.add_argument("result", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() == args.result.resolve():
        parser.error("Refuse existing output or input overwrite")
    result = json.loads(args.result.read_text())
    if result.get("error"):
        raise ValueError("Cannot score an errored result")
    report = score(result)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["groups"]))

if __name__ == "__main__":
    main()
