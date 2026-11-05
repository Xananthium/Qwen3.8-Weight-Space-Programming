"""Extend an unfinished attempt from its exact token history; retain raw chunks."""
import copy
import hashlib
import json
from pathlib import Path


def initial_prompt_ids(result_path, output):
    if 'initial_prompt_token_ids' in output:
        return output['initial_prompt_token_ids']
    path = Path(result_path).with_name(Path(result_path).stem.replace('.result','') + '.partial.jsonl')
    for line in path.read_text().splitlines():
        entry = json.loads(line)
        if entry['outputs'][0]['token_ids'] == output['token_ids']:
            ids = entry['prompt_token_ids']
            assert len(ids) == output['prompt_tokens']
            return ids
    raise ValueError('No exact token-history match in ' + str(path))


def continuation_record(record, output, result_path, total_max_tokens, context_limit=32768):
    assert record['reasoning_effort'] == 'medium'
    assert output['finish_reason'] == 'length'
    ids = initial_prompt_ids(result_path, output)
    assert len(ids) + total_max_tokens <= context_limit
    row = copy.deepcopy(record)
    row['prompt'] = {'prompt_token_ids': ids + output['token_ids']}
    parent_job = json.loads(Path(result_path).read_text())['job']
    parent_record = next(r for r in parent_job['records'] if r['id'] == record['id'])
    # Legacy continuation artifacts all began at 20261104; their job seed is
    # the restarted RNG seed, not the initial attempt's seed.
    fallback_seed = (20261104 if parent_job.get('continuation_total_max_tokens')
                     else parent_job.get('seed', 20261104))
    initial_seed = parent_record.get('continuation', {}).get(
        'initial_sampling_seed', parent_job.get('initial_sampling_seed', fallback_seed))
    row['continuation'] = {'base_record': copy.deepcopy(record), 'prefix_text': output['text'],
                           'prefix_token_ids': output['token_ids'], 'initial_prompt_token_ids': ids,
                           'parent_file': str(result_path),
                           'parent_sha256': hashlib.sha256(Path(result_path).read_bytes()).hexdigest(),
                           'total_max_tokens': total_max_tokens,
                           'initial_sampling_seed': initial_seed}
    return row


def canonicalize(result):
    if not result['job'].get('continuation_total_max_tokens') or result.get('canonical_continuation'):
        return result
    joined = copy.deepcopy(result)
    source = {r['id']: r for r in result['job']['records']}
    joined['job']['records'] = [r['continuation']['base_record'] for r in result['job']['records']]
    joined['job']['max_tokens'] = result['job']['continuation_total_max_tokens']
    joined['job']['continuation_sampling_seed'] = result['job']['seed']
    initial_seeds = {r['continuation'].get('initial_sampling_seed', 20261104)
                     for r in result['job']['records']}
    assert len(initial_seeds) == 1, 'Mixed initial seeds in one continuation batch'
    joined['job']['initial_sampling_seed'] = initial_seeds.pop()
    for output in joined['outputs']:
        continuation = source[output['id']]['continuation']
        output['text'] = continuation['prefix_text'] + output['text']
        output['token_ids'] = continuation['prefix_token_ids'] + output['token_ids']
        output['tokens'] = len(output['token_ids'])
        output['prompt'] = continuation['base_record']['prompt']
        output['initial_prompt_token_ids'] = continuation['initial_prompt_token_ids']
        output['prompt_tokens'] = len(continuation['initial_prompt_token_ids'])
    joined['canonical_continuation'] = True
    joined['continuation_note'] = ('The same generated token prefix is re-prefilled; no new instruction or answer key is added. '
                                  'The sampling RNG restarts at a documented deterministic seed, so this is not claimed to be '
                                  'bitwise identical to uninterrupted decoding. Raw initial/continuation artifacts are retained.')
    return joined
