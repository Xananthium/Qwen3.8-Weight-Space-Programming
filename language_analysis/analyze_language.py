#!/usr/bin/env python3
"""Offline, CPU-only analysis of saved generations; never reads reserve source pools.

Python >=3.10 standard library; optional matplotlib for figures. Input prompts,
gold answers, full generations, and absolute paths never enter public exports.
Existing strict grades are joined, not repaired by semantic interpretation.
"""
import argparse
import collections
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import statistics
import sys

VERSION = 'language_analysis_v1_20261105'
CONDITIONS = ['control', 'candidate', 'secondary', 'halfdose', 'early15']
STAGES = ['development7', 'development7_seed07', 'hle_reserve8',
          'hle_reserve_next8', 'hle_reserve_16_24', 'hle_reserve_24_32',
          'planar1', 'gsm_retention24', 'state_transfer4', 'loop_retention6']
GAME = 'hle:673722c82bfc8ab579ed111f'
TREE = 'hle:66ef3de8b8a1ba6e0ba23498'
MARKERS = {
    'wait': r'\bwait\b',
    'reconsider': r'\breconsider\b',
    'recheck_or_reexamine': r'\b(?:re[- ]?check|double[- ]?check|re[- ]?examine)\b',
    'exploratory_modal_uncertainty': r'\b(?:maybe|perhaps|possibly|probably|likely|seems?|appears?|might|could)\b',
    'exploratory_epistemic_phrase': r'\b(?:I\s+(?:think|believe|suspect|guess)|(?:I\s+am\s+)?not\s+sure|uncertain)\b',
}
PATTERNS = {k: re.compile(v, re.I) for k, v in MARKERS.items()}
WORD = re.compile(r'\b\w+\b')
PUNCT = re.compile(r'[^\w\s]+')
IDENTICAL_PUNCT = re.compile(r'([^\w\s])\1*')


def digest_bytes(b):
    return hashlib.sha256(b).hexdigest()


def digest_text(s):
    return digest_bytes(s.encode('utf-8'))


def read(path):
    return json.loads(path.read_text())


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def duplicate_ngram(text, n=8, tail=False):
    words = text[-12000:].split()[-512:] if tail else text.split()
    grams = [tuple(words[i:i+n]) for i in range(max(0, len(words)-n+1))]
    return 1 - len(set(grams))/len(grams) if grams else 0.0


def text_metrics(text, prefix):
    n = len(WORD.findall(text))
    d = {prefix + '_words': n, prefix + '_characters': len(text),
         prefix + '_duplicate4_fraction': duplicate_ngram(text, n=4),
         prefix + '_duplicate8_fraction': duplicate_ngram(text)}
    for name, pattern in PATTERNS.items():
        count = len(pattern.findall(text))
        d[prefix + '_' + name + '_count'] = count
        d[prefix + '_' + name + '_per_1000_words'] = 1000*count/n if n else None
    return d


def split_phases(out, close_id, control_ids):
    ids = out['token_ids']
    text = out['text']
    positions = [i for i, token in enumerate(ids) if token == close_id]
    text_count = text.count('</think>')
    assert len(positions) == text_count, 'Token/text boundary disagreement'
    assert len(ids) == out['tokens'], 'Declared token count disagreement'
    first = positions[0] if positions else len(ids)
    before, after = ids[:first], ids[first+1:] if positions else []
    thinking_ids = sum(t not in control_ids for t in before)
    final_ids = sum(t not in control_ids for t in after)
    controls = sum(t in control_ids for t in ids)
    assert thinking_ids + final_ids + controls == len(ids)
    if positions:
        thinking, final = text.split('</think>', 1)
    else:
        thinking, final = text, ''
    thinking = thinking.replace('<think>', '').replace('</think>', '')
    final = final.replace('<think>', '').replace('</think>', '')
    return {
        'generation_tokens': len(ids), 'thinking_content_tokens': thinking_ids,
        'final_content_tokens': final_ids, 'control_tokens': controls,
        'thinking_closed': bool(positions), 'closing_marker_count': len(positions),
        'first_closing_token_index': first if positions else None,
        'last_closing_token_index': positions[-1] if positions else None,
        'tokens_between_first_last_close': positions[-1]-positions[0] if positions else None,
        'token_ids_sha256': digest_text(json.dumps(ids, separators=(',', ':'))),
    }, thinking, final


def tail_metrics(text):
    tail = text[-1200:]
    runs = [m.group() for m in PUNCT.finditer(tail)]
    repeats = [m.group() for m in IDENTICAL_PUNCT.finditer(tail)]
    longest = max(runs, key=len, default='')
    repeated = max(repeats, key=len, default='')
    nonspace = sum(not x.isspace() for x in tail)
    symbol = sum(not (x.isalnum() or x.isspace() or x == '_') for x in tail)
    fraction = symbol/nonspace if nonspace else 0.0
    # Screening rules, not a degeneration diagnosis: tables/separators can flag.
    flagged = len(longest) >= 30 or len(repeated) >= 20 or (nonspace >= 100 and fraction >= .8)
    return {
        'tail_characters': len(tail), 'tail_longest_punctuation_run': len(longest),
        'tail_longest_identical_punctuation_run': len(repeated),
        'tail_symbol_fraction_nonspace': fraction, 'tail_character_screen_flag': flagged,
        'duplicate8_tail_frozen': duplicate_ngram(text, tail=True),
    }


def reviewed_annotations(root):
    base = root/'hle/agent_research/checkable'
    annotations, sources = {}, []
    def load(path):
        sources.append({'path': str(path), 'sha256': digest_bytes(path.read_bytes())})
        return read(path)
    lab = load(base/'repetition_trials_fresh_panel_comparison.quality_review.json')['rows']
    for panel in lab:
        detail = load(base/panel['quality_review'])
        details = {q['id']: q for q in detail['questions']}
        for q in panel['questions']:
            annotations[('laboratory', panel['condition'], 'development7', q['id'])] = {
                **details.get(q['id'], {}), 'strict_status': q['strict_status'],
                'parsed_final': q.get('parsed_final'),
                '_review_source_sha256': panel['source_sha256'],
            }
    for condition in CONDITIONS:
        for stage in STAGES[:2]:
            panel = load(base/f'actual_serving_{condition}_{stage}.quality_review.json')
            for q in panel['questions']:
                annotations[('actual_serving', condition, stage, q['id'])] = {**q, '_review_source_sha256': panel['source_sha256']}
    reserve = load(base/'actual_reserve_review/comparison.json')
    names = {'primary_half_flanks': 'candidate', 'secondary_joint64': 'secondary',
             'halfdose_a1p5': 'halfdose', 'control': 'control', 'early15': 'early15'}
    for panel in reserve['panels']:
        for q in panel['rows']:
            annotations[('actual_serving', names[panel['condition']], panel['panel'], q['id'])] = {
                'strict_status': q['strict']['status'],
                'agent_reviewed_status': q.get('agent_reviewed_status'),
                'agent_reviewed_intended_correct': q.get('agent_reviewed_status') == 'correct',
                '_review_source_sha256': panel['source_sha256'],
            }
    retention = root/'hle/agent_research/diagnostics/actual_retention_review'
    for condition in CONDITIONS:
        panel = load(retention/f'{condition}.review.json')
        for q in panel['gsm']['rows']:
            annotations[('actual_serving', condition, 'gsm_retention24', q['id'])] = {
                'strict_status': 'correct' if q['strict_completed_correct'] else 'wrong',
                'agent_reviewed_intended_correct': q['strict_completed_correct'],
                '_review_source_sha256': panel['gsm']['sha256'],
            }
        for q in panel['state']['rows']:
            annotations[('actual_serving', condition, 'state_transfer4', q['id'])] = {
                'strict_status': q['strict_status'],
                'agent_reviewed_intended_correct': q.get('intended_answer_correct'),
                '_review_source_sha256': panel['state']['sha256'],
            }
    return annotations, sources, lab


def loop_grade(out, record):
    """Frozen score.py predicates for the six fixed records; no tool execution.

    The two constructed continuation keys and outputs are plain integer boxes;
    assert this rather than replacing general math_verify with a new grader.
    """
    text = out['text']
    final = text.split('</think>')[-1]
    repeated = False
    if record.get('kind') == 'tool':
        calls = re.findall(r'<tool_call>(.*?)</tool_call>', final, flags=re.S)
        action = '\n'.join(calls)
        commands = re.findall(r'<parameter=command>(.*?)</parameter>', action, flags=re.S)
        commands += re.findall(r'"command"\s*:\s*"([^\"]+)"', action)
        correct = bool(calls) and record['expected'] in action and not any(c.strip() == record['forbidden'] for c in commands)
        repeated = any(re.match(re.escape(record['forbidden']) + r'(?=$|[\s;&|<>])', c.strip()) is not None for c in commands)
    else:
        boxes = re.findall(r'\\(?:boxed|fbox)\s*\{([^{}]*)\}', final)
        answer = boxes[-1].strip() if boxes else None
        assert str(record['answer']).isdigit()
        assert answer is None or answer.isdigit(), 'Use original math_verify scorer for noninteger output'
        correct = answer is not None and int(answer) == int(record['answer'])
    status = 'cutoff' if out['finish_reason'] == 'length' else (
        'unfinished_thinking' if '</think>' not in text else ('correct' if correct else 'wrong'))
    return {'strict_status': status, 'agent_reviewed_intended_correct': None,
            'repeated_failed_operation_frozen': repeated}


def analyze(root, outdir, tokenizer):
    public, internal = outdir/'public', outdir/'internal_pending_rights'
    public.mkdir(parents=True, exist_ok=True)
    internal.mkdir(parents=True, exist_ok=True)
    tok = read(tokenizer)
    controls = {x['id'] for x in tok['added_tokens'] if x.get('special')}
    lookup = {x['content']: x['id'] for x in tok['added_tokens']}
    controls |= {lookup['<think>'], lookup['</think>']}
    annotations, annotation_sources, lab = reviewed_annotations(root)
    files = [('actual_serving', c, s, root/'serving_confirmation_20261105'/c/f'{s}.result.json')
             for c in CONDITIONS for s in STAGES]
    files += [('laboratory', p['condition'], 'development7', root/Path(p['source_file']).name) for p in lab]
    rows, audits, sources = [], [], []
    for cohort, condition, stage, path in files:
        data = read(path)
        sha = digest_bytes(path.read_bytes())
        source_key = f'{cohort}/{condition}/{stage}'
        sources.append({'source_key': source_key, 'path': str(path), 'sha256': sha,
                        'job_sha256': digest_text(json.dumps(data['job'], sort_keys=True))})
        job = data['job']
        records = {x['id']: x for x in job['records']}
        for output in data['outputs']:
            key = (cohort, condition, stage, output['id'])
            ann = loop_grade(output, records[output['id']]) if stage == 'loop_retention6' else annotations[key]
            if stage != 'loop_retention6':
                assert ann['_review_source_sha256'] == sha, f'Stale review/source join: {key}'
            phase, thinking, final = split_phases(output, lookup['</think>'], controls)
            # Preserve all frozen outcome classes; cutoffs cannot turn into passes.
            status = ann['strict_status']
            if output['finish_reason'] == 'length':
                assert status == 'cutoff', (key, status)
            assert status in {'correct', 'wrong', 'cutoff', 'unparsed', 'unfinished_thinking'}
            intended = ann.get('agent_reviewed_intended_correct', ann.get('manual_key_match'))
            if intended is None and isinstance(ann.get('semantic_review'), dict):
                intended = ann['semantic_review'].get('key_match')
            proof = ann.get('final_proof_valid', ann.get('final_proof_fully_valid'))
            row = {
                'cohort': cohort, 'condition': condition, 'stage': stage,
                'seed': job['seed'], 'max_tokens': job['max_tokens'],
                'temperature': job['temperature'], 'id': output['id'],
                'case_family': 'game' if output['id'] == GAME else 'phylogeny' if output['id'] == TREE else records[output['id']].get('source', output['id'].split(':')[0]),
                'source_key': source_key, 'source_sha256': sha,
                'output_text_sha256': digest_text(output['text']),
                'prompt_sha256': digest_text(output.get('prompt', '')),
                'strict_status': status, 'strict_correct': status == 'correct',
                'agent_reviewed_intended_correct': intended,
                'rubric_score': ann.get('rubric_score'), 'rubric_max': ann.get('rubric_max'),
                'reviewed_final_proof_valid': proof,
                'finish_reason': output['finish_reason'],
                'budget_censored': output['finish_reason'] == 'length',
                'completion_observed': phase['thinking_closed'] and output['finish_reason'] != 'length',
                'repeated_failed_operation_frozen': ann.get('repeated_failed_operation_frozen'),
                **phase, **text_metrics(thinking, 'thinking'), **text_metrics(final, 'final'),
                **tail_metrics(output['text']),
            }
            rows.append(row)
            audit = {'source_key': source_key, 'id': output['id'], 'source_sha256': sha,
                     'output_text_sha256': row['output_text_sha256'], 'source_path': str(path)}
            if row['tail_character_screen_flag'] or status in ('cutoff', 'unparsed', 'unfinished_thinking') or phase['closing_marker_count'] > 1:
                audit['tail_1200_characters_pending_rights_review'] = output['text'][-1200:]
            audits.append(audit)
    assert len(rows) == 503
    assert collections.Counter(r['cohort'] for r in rows) == {'actual_serving': 405, 'laboratory': 98}
    assert len({(r['cohort'], r['condition'], r['stage'], r['id']) for r in rows}) == len(rows)
    lexical_path = root/'hle/agent_research/checkable/actual_serving_development7_all_profiles.lexical_counts.descriptive.json'
    lexical = read(lexical_path)
    lexical_index = {(r['condition'], r['seed'], r['id']): r for r in rows if r['cohort'] == 'actual_serving' and r['stage'] in STAGES[:2]}
    for frozen in lexical['rows']:
        measured = lexical_index[(frozen['condition'], frozen['seed'], frozen['id'])]
        assert measured['thinking_words'] == frozen['thinking_words']
        for marker, count in frozen['counts'].items():
            assert measured['thinking_'+marker+'_count'] == count
    annotation_sources.append({'path': str(lexical_path), 'sha256': digest_bytes(lexical_path.read_bytes())})
    aggregates = aggregate(rows)
    panel_family_rows = [{**r, 'stage': 'hle_reserve32' if r['stage'].startswith('hle_reserve') else r['stage']} for r in rows]
    families = aggregate(panel_family_rows)
    pairs = paired(rows)
    outcome_groups = aggregate(rows, outcome=True)
    metadata = {
        'analysis_version': VERSION, 'n_outputs': len(rows),
        'python_version': sys.version,
        'cohort_counts': dict(collections.Counter(r['cohort'] for r in rows)),
        'tokenizer_sha256': digest_bytes(tokenizer.read_bytes()),
        'think_close_id': lookup['</think>'], 'control_token_ids': sorted(controls),
        'script_sha256': digest_bytes(Path(__file__).read_bytes()),
        'frozen_marker_patterns': {k: MARKERS[k] for k in list(MARKERS)[:3]},
        'exploratory_marker_patterns': {k: MARKERS[k] for k in list(MARKERS)[3:]},
        'word_regex': WORD.pattern, 'tail_screen_characters': 1200,
        'tail_screen_rules': ['punctuation_run>=30', 'identical_punctuation_run>=20', 'nonspace>=100 and symbol_fraction>=0.8'],
        'boundary_policy': 'First closing marker; all tokenizer special tokens and think markers separately counted as control. No retokenization. Unclosed output has zero observed final tokens and censored thinking if finish=length.',
        'grades_changed': False, 'raw_prompts_exported': False, 'raw_generations_public': False,
        'frozen_lexical_rows_reproduced': len(lexical['rows']),
        'input_source_hashes': [{'source_key': x['source_key'], 'sha256': x['sha256']} for x in sources],
        'annotation_source_hashes': [x['sha256'] for x in annotation_sources],
        'smoke_policy': 'Five smoke.result.json files excluded as a separate four-case task/schema cohort; their response objects retain generated token IDs.',
    }
    tail_annotation_path = Path(__file__).with_name('manual_tail_annotations.json')
    if tail_annotation_path.exists():
        tail_annotations = read(tail_annotation_path)
        index = {(r['source_key'], r['id']): r for r in rows}
        for annotation in tail_annotations['rows']:
            item = index[(annotation['source_key'], annotation['id'])]
            assert item['source_sha256'] == annotation['source_sha256']
            assert item['output_text_sha256'] == annotation['output_text_sha256']
        metadata['manual_tail_annotations_sha256'] = digest_bytes(tail_annotation_path.read_bytes())
        write_json(public/'manual_tail_review.json', tail_annotations)
    write_json(public/'generation_metrics.json', {'metadata': metadata, 'rows': rows})
    write_csv(public/'generation_metrics.csv', rows)
    write_json(public/'cohort_summary.json', aggregates)
    write_csv(public/'cohort_summary.csv', aggregates)
    write_json(public/'panel_family_summary.json', families)
    write_csv(public/'panel_family_summary.csv', families)
    write_csv(public/'outcome_stratified_descriptive.csv', outcome_groups)
    write_csv(public/'paired_vs_control.csv', pairs)
    write_json(internal/'audit_manifest.json', {'sources': sources, 'annotation_sources': annotation_sources,
                                              'tokenizer_path': str(tokenizer), 'rows': audits})
    write_json(public/'checks.json', checks(rows))
    write_csv(public/'primary_cases.csv', [r for r in rows if r['id'] in (GAME, TREE)])
    (outdir/'.gitignore').write_text('internal_pending_rights/\n__pycache__/\n.mplconfig/\n')
    plot(public, rows, aggregates)
    return metadata


def aggregate(rows, outcome=False):
    keys = ['cohort', 'condition', 'stage', 'seed', 'max_tokens'] + (['strict_status'] if outcome else [])
    grouped = collections.defaultdict(list)
    for r in rows:
        grouped[tuple(r[k] for k in keys)].append(r)
    result = []
    for key, rr in grouped.items():
        d = dict(zip(keys, key))
        d.update(n=len(rr), **{f'n_{s}': sum(r['strict_status'] == s for r in rr) for s in ['correct', 'wrong', 'cutoff', 'unparsed', 'unfinished_thinking']})
        for phase in ['generation', 'thinking_content', 'final_content', 'control']:
            name = phase + '_tokens'
            d[name + '_sum'] = sum(r[name] for r in rr)
            d[name + '_median'] = statistics.median(r[name] for r in rr)
        for phase in ['thinking', 'final']:
            words = sum(r[phase+'_words'] for r in rr)
            d[phase+'_words_sum'] = words
            for marker in MARKERS:
                name = phase+'_'+marker
                count = sum(r[name+'_count'] for r in rr)
                d[name+'_count'] = count
                d[name+'_pooled_per_1000_words'] = 1000*count/words if words else None
        d['character_screen_flags'] = sum(r['tail_character_screen_flag'] for r in rr)
        d['max_tail_identical_punctuation_run'] = max(r['tail_longest_identical_punctuation_run'] for r in rr)
        d['mean_duplicate8_tail_frozen'] = statistics.mean(r['duplicate8_tail_frozen'] for r in rr)
        result.append(d)
    return result


def paired(rows):
    index = {(r['cohort'], r['condition'], r['stage'], r['seed'], r['id']): r for r in rows}
    result = []
    for r in rows:
        control = 'control' if r['cohort'] == 'actual_serving' else 'original'
        if r['condition'] == control:
            continue
        other = index[(r['cohort'], control, r['stage'], r['seed'], r['id'])]
        d = {k: r[k] for k in ['cohort', 'condition', 'stage', 'seed', 'max_tokens', 'id']}
        d.update(control_condition=control, control_status=other['strict_status'],
                 condition_status=r['strict_status'], both_strict_correct=other['strict_correct'] and r['strict_correct'],
                 control_censored=other['budget_censored'], condition_censored=r['budget_censored'])
        for k in ['generation_tokens', 'thinking_content_tokens', 'final_content_tokens']:
            d[k+'_control'] = other[k]
            d[k+'_condition'] = r[k]
            d[k+'_observed_difference'] = r[k]-other[k]
        for k in list(MARKERS)[:3]:
            for suffix in ['_count', '_per_1000_words']:
                name = 'thinking_'+k+suffix
                d[name+'_control'] = other[name]
                d[name+'_condition'] = r[name]
        result.append(d)
    return result


def checks(rows):
    def select(c, s, i=None):
        return [r for r in rows if r['cohort'] == 'actual_serving' and r['condition'] == c and r['stage'] == s and (i is None or r['id'] == i)]
    for c, expected in zip(CONDITIONS, [3, 2, 1, 4, 4]):
        rr = [r for r in rows if r['cohort'] == 'actual_serving' and r['condition'] == c and r['stage'].startswith('hle_reserve')]
        assert len(rr) == 32 and sum(r['strict_correct'] for r in rr) == expected
    assert sum(r['strict_correct'] for r in select('halfdose', 'gsm_retention24')) == 23
    assert select('early15', 'hle_reserve_next8', 'hle:673735aa61f20f11eb1097d2')[0]['tail_longest_identical_punctuation_run'] == 656
    assert select('early15', 'hle_reserve_next8', 'hle:6714e9dacbabe50aa0256711')[0]['tail_longest_identical_punctuation_run'] == 22
    assert all(not r['strict_correct'] for r in rows if r['budget_censored'])
    prompts = collections.defaultdict(set)
    for r in rows:
        prompts[(r['cohort'], r['stage'], r['seed'], r['id'])].add(r['prompt_sha256'])
    assert all(len(hashes) == 1 for hashes in prompts.values()), 'Matched prompt hashes differ'
    # Meaningful synthetic checks isolate phase and punctuation behavior.
    a, t, f = split_phases({'token_ids': [11, 248069, 12, 248046], 'text': 'a</think>b', 'tokens': 4}, 248069, {248069, 248046})
    assert (a['thinking_content_tokens'], a['final_content_tokens'], a['control_tokens']) == (1, 1, 2)
    a, t, f = split_phases({'token_ids': [11, 248069, 248069, 12], 'text': 'a</think></think>b', 'tokens': 4}, 248069, {248069})
    assert a['closing_marker_count'] == 2 and a['final_content_tokens'] == 1 and f == 'b'
    a, t, f = split_phases({'token_ids': [11, 12], 'text': 'unfinished', 'tokens': 2}, 248069, {248069})
    assert not a['thinking_closed'] and a['final_content_tokens'] == 0
    assert tail_metrics('table\n' + '-'*40)['tail_character_screen_flag']  # not automatically degeneration
    return {'status': 'passed', 'checks': ['503 unique outputs;405 actual+98 laboratory', 'all saved token counts and text/token boundaries agree',
            'exact phase+control token accounting', 'all frozen full32 totals reproduced', 'selected GSM retention23/24 preserved',
            'early15 punctuation failures656/22 reproduced', 'no cutoff passes', 'matched prompt hashes identical within each cohort/seed/case', 'synthetic redundant boundary and unfinished thought accounting'],
            'boundary_marker_count_histogram': dict(collections.Counter(r['closing_marker_count'] for r in rows)),
            'actual_cutoffs': sum(r['budget_censored'] for r in rows if r['cohort'] == 'actual_serving'),
            'laboratory_cutoffs': sum(r['budget_censored'] for r in rows if r['cohort'] == 'laboratory')}


def plot(public, rows, aggregates):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        return
    figs = public/'figures'
    figs.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'svg.fonttype': 'none', 'svg.hashsalt': VERSION, 'axes.spines.top': False, 'axes.spines.right': False})
    colors = {'control': '#555555', 'candidate': '#4477AA', 'secondary': '#AA66AA', 'halfdose': '#228833', 'early15': '#CC6677'}
    def save(fig, name):
        fig.savefig(figs/(name+'.png'), dpi=180, bbox_inches='tight')
        fig.savefig(figs/(name+'.svg'), bbox_inches='tight', metadata={'Date': None})
        plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    for col, stage in enumerate(STAGES[:2]):
        for i, c in enumerate(CONDITIONS):
            a = next(a for a in aggregates if a['cohort'] == 'actual_serving' and a['condition'] == c and a['stage'] == stage)
            axes[0,col].bar(i, a['thinking_content_tokens_sum'], color=colors[c])
            axes[0,col].bar(i, a['final_content_tokens_sum'], bottom=a['thinking_content_tokens_sum'], color=colors[c], alpha=.35)
            axes[0,col].text(i, a['generation_tokens_sum']+300, f"{a['n_correct']}/7", ha='center', fontsize=9)
        axes[0,col].set_title(f"Actual development: seed {20261105 if col == 0 else 20261107}")
        axes[0,col].set_ylabel('Observed content tokens (7 cases)')
        axes[0,col].set_xticks(range(5), CONDITIONS, rotation=20)
        for i, c in enumerate(CONDITIONS):
            rr = [r for r in rows if r['cohort'] == 'actual_serving' and r['condition'] == c and r['stage'] == stage]
            for j, r in enumerate(rr):
                axes[1,col].scatter(i+(j-3)*.045, r['thinking_wait_per_1000_words'], marker='x' if r['budget_censored'] else 'o', s=30, color=colors[c])
        axes[1,col].set_xticks(range(5), CONDITIONS, rotation=20)
        axes[1,col].set_ylabel("'wait' per 1,000 thinking words")
    upper_limit = max(a['generation_tokens_sum'] for a in aggregates if a['cohort'] == 'actual_serving' and a['stage'] in STAGES[:2])*1.09
    for ax in axes[0]:
        ax.set_ylim(0, upper_limit)
    density_limit = max(r['thinking_wait_per_1000_words'] or 0 for r in rows if r['cohort'] == 'actual_serving' and r['stage'] in STAGES[:2])*1.12
    for ax in axes[1]:
        ax.set_ylim(-.2, density_limit)
    fig.suptitle('Exact saved tokens; pale bars = final content; labels = strict passes\nPoints are cases; x = budget-censored. Lexical density is not proof quality.', fontsize=12)
    fig.tight_layout()
    save(fig, 'actual_development_tokens_and_wait')
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    for ax, case in zip(axes, [GAME, TREE]):
        for r in rows:
            if r['cohort'] != 'actual_serving' or r['id'] != case:
                continue
            x = CONDITIONS.index(r['condition']) + (-.09 if r['seed'] == 20261105 else .09)
            marker = '^' if r['budget_censored'] else 'o' if r['strict_correct'] else 'X'
            ax.scatter(x, r['thinking_content_tokens'], color=colors[r['condition']], marker=marker, s=85)
            ax.text(x, r['thinking_content_tokens']+250, str(r['seed'])[-2:], ha='center', fontsize=8)
        ax.axhline(16384, color='gray', linestyle=':', lw=1)
        ax.set_xticks(range(5), CONDITIONS, rotation=25)
        ax.set_ylabel('Observed thinking content tokens')
        ax.set_title('Game' if case == GAME else 'Phylogeny')
    fig.suptitle('Actual primary cases: seeds 05/07; circle correct, X other stopped, triangle cutoff\nA correct choice does not establish a valid proof.', fontsize=12)
    fig.tight_layout()
    save(fig, 'actual_primary_case_tokens')
    labs = list(dict.fromkeys(r['condition'] for r in rows if r['cohort'] == 'laboratory'))
    fig, ax = plt.subplots(figsize=(12, 6))
    for i, c in enumerate(labs):
        for j, case in enumerate([GAME, TREE]):
            r = next(r for r in rows if r['cohort'] == 'laboratory' and r['condition'] == c and r['id'] == case)
            ax.scatter(r['generation_tokens'], i+(j-.5)*.25, color='#228833' if r['strict_correct'] else '#CC6677', marker='>' if r['budget_censored'] else 'o', s=60)
    ax.set_yticks(range(len(labs)), labs)
    ax.invert_yaxis()
    ax.set_xlabel('Observed generation tokens; each pair: game above, phylogeny below')
    ax.axvline(12288, color='gray', ls=':')
    ax.set_title('Laboratory only, seed20261105 / 12,288-token cap\nGreen = strict correct; red = other; triangle = right-censored')
    fig.tight_layout()
    save(fig, 'laboratory_primary_cases')
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for i, c in enumerate(CONDITIONS):
        rr = [r for r in rows if r['cohort'] == 'actual_serving' and r['condition'] == c and r['stage'].startswith('hle_reserve')]
        axes[0].bar(i, sum(r['generation_tokens'] for r in rr), color=colors[c])
        axes[0].text(i, sum(r['generation_tokens'] for r in rr)+2000, f"{sum(r['strict_correct'] for r in rr)}/32", ha='center')
        axes[1].scatter([i]*32, [r['tail_longest_identical_punctuation_run'] for r in rr], color=colors[c], alpha=.5)
    axes[0].set_ylabel('Observed generation tokens / fixed 32 cases')
    axes[1].set_ylabel('Longest identical punctuation run / last1,200 chars')
    axes[1].set_yscale('symlog', linthresh=10)
    for ax in axes:
        ax.set_xticks(range(5), CONDITIONS, rotation=20)
    fig.suptitle('Adaptive actual reserve characterization; labels = strict passes\nCharacter runs are a screen: Markdown separators can flag.', fontsize=12)
    fig.tight_layout()
    save(fig, 'reserve_tokens_and_character_screen')
    # Fixed question/seed pairs, shown separately from outcome-conditioned views.
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    marker_names = list(MARKERS)[:3]
    for ax, marker_name in zip(axes, marker_names):
        for i, c in enumerate(CONDITIONS):
            for stage, offset in [('development7', -.1), ('development7_seed07', .1)]:
                a = next(a for a in aggregates if a['cohort'] == 'actual_serving' and a['condition'] == c and a['stage'] == stage)
                ax.scatter(i+offset, a['thinking_'+marker_name+'_pooled_per_1000_words'], color=colors[c], marker='o' if offset < 0 else 's', s=60)
        ax.set_xticks(range(5), CONDITIONS, rotation=25)
        ax.set_title(marker_name.replace('_', ' '))
        ax.set_ylabel('Matches / 1,000 thinking words')
    fig.suptitle('Descriptive lexical density: actual development; circle=seed05, square=seed07\nDictionary counts are neither mental-state measures nor proof-quality scores.', fontsize=12)
    fig.tight_layout()
    save(fig, 'actual_development_lexical_density')
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    outcomes = ['correct', 'wrong', 'cutoff', 'unparsed']
    measurements = ['thinking_content_tokens', 'thinking_wait_per_1000_words', 'thinking_recheck_or_reexamine_per_1000_words']
    labels = ['Observed thinking content tokens', "'wait' / 1,000 thinking words", 'Recheck class / 1,000 thinking words']
    for ax, measurement, label in zip(axes, measurements, labels):
        for i, c in enumerate(CONDITIONS):
            rr = [r for r in rows if r['cohort'] == 'actual_serving' and r['condition'] == c and r['stage'].startswith('hle_reserve')]
            for j, r in enumerate(rr):
                ax.scatter(outcomes.index(r['strict_status'])+(i-2)*.11+(j%3-1)*.015, r[measurement], color=colors[c], alpha=.65, s=18, label=c if j == 0 else None)
        ax.set_xticks(range(4), outcomes, rotation=20)
        ax.set_ylabel(label)
    axes[0].legend(fontsize=8)
    fig.suptitle('Fixed32 actual characterization: individual outputs by frozen strict outcome\nOutcome strata are descriptive, not causal efficiency estimates; cap censors cutoff lengths.', fontsize=12)
    fig.tight_layout()
    save(fig, 'reserve_outcome_stratified_descriptive')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment-root', type=Path)
    parser.add_argument('--from-metrics', type=Path, help='Rebuild tables/figures from the public per-generation export; needs no private traces.')
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--tokenizer-json', type=Path)
    args = parser.parse_args()
    if args.from_metrics:
        data = read(args.from_metrics)
        rows = data['rows']
        public = args.output_dir/'public'
        public.mkdir(parents=True, exist_ok=True)
        aggregates = aggregate(rows)
        families = aggregate([{**r, 'stage': 'hle_reserve32' if r['stage'].startswith('hle_reserve') else r['stage']} for r in rows])
        write_json(public/'cohort_summary.json', aggregates)
        write_csv(public/'cohort_summary.csv', aggregates)
        write_json(public/'panel_family_summary.json', families)
        write_csv(public/'panel_family_summary.csv', families)
        write_csv(public/'outcome_stratified_descriptive.csv', aggregate(rows, outcome=True))
        write_csv(public/'paired_vs_control.csv', paired(rows))
        write_csv(public/'primary_cases.csv', [r for r in rows if r['id'] in (GAME, TREE)])
        plot(public, rows, aggregates)
        write_json(public/'regeneration_from_metrics.json', {
            'input_metrics_sha256': digest_bytes(args.from_metrics.read_bytes()),
            'script_sha256': digest_bytes(Path(__file__).read_bytes()), 'n_outputs': len(rows),
            'method': 'Derived aggregates and figures only. Does not recompute token/text features or independently revalidate private raw-source joins.',
        })
        print(json.dumps({'method': 'public_metrics_replay', 'outputs': len(rows)}))
        return
    if not args.experiment_root:
        parser.error('Supply --experiment-root or --from-metrics')
    tokenizer = args.tokenizer_json or args.experiment_root/'relayer_bank/hf-config/tokenizer.json'
    metadata = analyze(args.experiment_root.resolve(), args.output_dir.resolve(), tokenizer.resolve())
    print(json.dumps({'analysis_version': VERSION, 'outputs': metadata['n_outputs'], 'cohorts': metadata['cohort_counts'], 'output_dir': str(args.output_dir)}))


if __name__ == '__main__':
    main()
