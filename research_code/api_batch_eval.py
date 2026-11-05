#!/usr/bin/env python3
"""One frozen raw-prompt batch through local /v1/completions, with SSE evidence.

--check performs no HTTP calls and writes no result. Prompts must already be
rendered at medium effort; this endpoint deliberately does not re-template them.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import traceback
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build_request(job, model, expected_seed=20261106):
    if job.get('op', 'generate') != 'generate':
        raise ValueError('Only frozen generate jobs are accepted')
    if float(job.get('temperature', 1.3)) != 1.3:
        raise ValueError('Temperature is locked to1.3')
    if type(job.get('max_tokens')) is not int or job['max_tokens'] < 1:
        raise ValueError('The frozen job must explicitly specify max_tokens')
    seed = job.get('seed', expected_seed)
    if type(seed) is not int or seed != expected_seed:
        raise ValueError('Job seed does not match the declared paired seed')
    records = job.get('records')
    if not isinstance(records, list) or not records:
        raise ValueError('A nonempty ordered records list is required')
    prompts, kinds = [], set()
    for index, record in enumerate(records):
        if 'id' not in record or record.get('reasoning_effort', 'medium') != 'medium':
            raise ValueError('Each record needs an id and medium reasoning effort')
        raw = record.get('prompt', {'prompt_token_ids': record.get('prompt_token_ids')})
        if isinstance(raw, str) and raw:
            if raw.startswith('<|im_start|>system\nReasoning effort is set to xhigh.'):
                raise ValueError('High-effort prompt rejected')
            value, kind = raw, 'text'
        elif isinstance(raw, dict) and set(raw) == {'prompt_token_ids'}:
            value, kind = raw['prompt_token_ids'], 'token_ids'
            if not isinstance(value, list) or not value or any(type(t) is not int or t < 0 for t in value):
                raise ValueError('Invalid raw prompt token IDs')
            value = list(value)
        else:
            raise ValueError(f'Record{index} must already contain a frozen raw prompt or token-ID prompt')
        prompts.append(value); kinds.add(kind)
    if len(kinds) != 1:
        raise ValueError('One batch must use all raw strings or all token-ID lists; normalize before freezing')
    body = {'model': model, 'prompt': prompts, 'n': 1, 'echo': False,
            'temperature': 1.3, 'top_p': 0.95, 'top_k': 20, 'min_p': 0.0,
            'presence_penalty': 0.0, 'frequency_penalty': 0.0, 'repetition_penalty': 1.0,
            'seed': seed, 'max_tokens': job['max_tokens'], 'stream': True,
            'stream_options': {'include_usage': True}, 'return_token_ids': True,
            'add_special_tokens': False, 'skip_special_tokens': True,
            'spaces_between_special_tokens': True}
    if job.get('logprobs') is not None:
        body['logprobs'] = job['logprobs']
        body['return_tokens_as_token_ids'] = True
    if any(key in job for key in ('stop', 'stop_token_ids', 'min_tokens', 'ignore_eos')):
        raise ValueError('This runner matches the existing job sampler; extra stop/length controls require explicit review')
    canonical = json.dumps(body, sort_keys=True, separators=(',', ':')).encode()
    body['request_id'] = 'paired-eval-' + sha(canonical)[:24]
    return body, next(iter(kinds))


def profile_identity(path):
    path = Path(path).resolve()
    manifest_bytes = (path / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    for name, expected in manifest['sha256'].items():
        if sha((path / name).read_bytes()) != expected:
            raise ValueError('Profile integrity mismatch: ' + name)
    profile = json.loads((path / 'profile.json').read_text())
    args = profile['args']
    model = args[args.index('--served-model-name') + 1]
    return model, {'path': str(path), 'manifest_sha256': sha(manifest_bytes),
                   'mode': profile.get('mode', 'static_patch'), 'candidate': profile.get('candidate'),
                   'layers': profile.get('layers', []), 'alpha': profile.get('alpha'),
                   'identity_limit': 'Caller-declared launched profile; match process/startup attestation separately. Alias alone cannot prove server weight identity.'}


def split_text(text):
    if '</think>' in text:
        reasoning, final = text.rsplit('</think>', 1)
        return reasoning, final, True
    return None, text, False


def consume_event(event, rows, elapsed):
    if 'error' in event:
        raise ValueError('Server streaming error: ' + json.dumps(event['error']))
    for choice in event.get('choices', []):
        index = choice['index']
        if type(index) is not int or not 0 <= index < len(rows):
            raise ValueError('Unexpected choice index')
        row = rows[index]
        prompt_ids = choice.get('prompt_token_ids')
        if prompt_ids is not None:
            if row['initial_prompt_token_ids'] is not None and row['initial_prompt_token_ids'] != prompt_ids:
                raise ValueError('Server prompt tokens differ from the frozen input/history')
            row['initial_prompt_token_ids'] = list(prompt_ids)
        tokens = choice.get('token_ids')
        if tokens is None:
            raise ValueError('Server omitted requested delta token IDs')
        if row['finish_reason'] is not None and (tokens or choice.get('text')):
            raise ValueError('Generated tokens arrived after a finished choice')
        if tokens and row['first_token_elapsed_s'] is None:
            row['first_token_elapsed_s'] = elapsed
        row['token_ids'].extend(tokens)
        row['text'] += choice.get('text', '')
        if choice.get('logprobs') is not None:
            row['api_logprob_chunks'].append(choice['logprobs'])
        if choice.get('finish_reason') is not None:
            row['finish_reason'] = choice['finish_reason']
            row['stop_reason'] = choice.get('stop_reason')
            row['finished_elapsed_s'] = elapsed
    return event.get('usage')


def run(job, body, kind, identity, output, base_url, timeout=21600, opener=urlopen):
    output = Path(output).resolve()
    stem = output.stem.replace('.result', '')
    partial_path = output.with_name(stem + '.partial.jsonl')
    events_path = output.with_name(stem + '.events.jsonl')
    for path in (output, partial_path, events_path):
        if path.exists(): raise FileExistsError(path)
    rows = []
    for record, prompt in zip(job['records'], body['prompt'], strict=True):
        rows.append({'id': record['id'], 'prompt': record['prompt'] if 'prompt' in record else {'prompt_token_ids': list(prompt)},
                     'initial_prompt_token_ids': list(prompt) if kind == 'token_ids' else None,
                     'text': '', 'token_ids': [], 'finish_reason': None, 'stop_reason': None,
                     'first_token_elapsed_s': None, 'finished_elapsed_s': None, 'api_logprob_chunks': []})
    request_bytes = json.dumps(body, separators=(',', ':')).encode()
    request = Request(base_url.rstrip('/') + '/v1/completions', data=request_bytes,
                      headers={'Content-Type': 'application/json'}, method='POST')
    started = time.time(); start_clock = time.monotonic(); finished_written = set()
    result = {'runner_sha256': sha(Path(__file__).read_bytes()), 'job': job, 'started': started, 'started_at_utc': datetime.now(timezone.utc).isoformat(),
              'profile_identity': identity, 'evaluation_mode': 'actual_compiled_TQ4_DFlash_image5_raw_completions',
              'request': body, 'request_sha256': sha(request_bytes), 'endpoint': request.full_url,
              'partial_output': str(partial_path), 'events_output': str(events_path), 'outputs': rows,
              'reasoning_effort_source': 'frozen raw prompts, not a chat-template or unsupported completions parameter'}
    done = False
    try:
        with partial_path.open('x') as partial, events_path.open('x') as events:
            with opener(request, timeout=timeout) as response:
                result['http_status'] = response.status
                result['response_headers'] = dict(response.headers.items())
                if 'text/event-stream' not in response.headers.get('Content-Type', ''):
                    raise ValueError('Expected an SSE completion stream')
                data_lines = []
                for raw in response:
                    line = raw.decode('utf-8').rstrip('\r\n')
                    if line.startswith('data:'):
                        data_lines.append(line[5:].lstrip())
                        continue
                    if line or not data_lines:
                        continue
                    data = '\n'.join(data_lines); data_lines = []
                    if data == '[DONE]':
                        done = True; break
                    event = json.loads(data)
                    elapsed = time.monotonic() - start_clock
                    events.write(json.dumps({'elapsed_s': elapsed, 'event': event}) + '\n'); events.flush()
                    usage = consume_event(event, rows, elapsed)
                    if usage is not None: result['usage'] = usage
                    for key in ('id', 'model', 'created', 'system_fingerprint', 'metrics'):
                        if event.get(key) is not None: result.setdefault('response_metadata', {})[key] = event[key]
                    for index, row in enumerate(rows):
                        if row['finish_reason'] is not None and index not in finished_written:
                            if row['initial_prompt_token_ids'] is None: raise ValueError('Missing server prompt token IDs')
                            partial.write(json.dumps({'request_id': body['request_id'] + '-' + str(index),
                                'prompt_token_ids': row['initial_prompt_token_ids'],
                                'outputs': [{'text': row['text'], 'token_ids': row['token_ids'], 'finish_reason': row['finish_reason'], 'stop_reason': row['stop_reason']}]}) + '\n')
                            partial.flush(); finished_written.add(index)
        if not done or len(finished_written) != len(rows):
            raise ValueError('Stream ended without DONE and every requested completion')
        result['success'] = True
    except Exception:
        result['success'] = False; result['error'] = traceback.format_exc()
    for row in rows:
        row['tokens'] = len(row['token_ids'])
        row['prompt_tokens'] = len(row['initial_prompt_token_ids']) if row['initial_prompt_token_ids'] is not None else None
        row['thinking'], row['final_text'], row['reasoning_boundary_seen'] = split_text(row['text'])
        if row['tokens'] > body['max_tokens']:
            result['success'] = False
            result['error'] = result.get('error', '') + '\nServer exceeded the frozen requested token budget'

    result['elapsed_s'] = time.time() - started
    with output.open('x') as handle:handle.write(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--base-url', default='http://127.0.0.1:8002')
    parser.add_argument('--expected-seed', type=int, default=20261106)
    parser.add_argument('--timeout', type=float, default=21600)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    parsed = urlparse(args.base_url)
    if parsed.scheme not in ('http', 'https') or parsed.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('This paired runner is restricted to the local experiment server')
    job_bytes = args.job.read_bytes();job = json.loads(job_bytes)
    model, identity = profile_identity(args.profile)
    body, kind = build_request(job, model, args.expected_seed)
    identity['job_sha256'] = sha(job_bytes)
    if args.check:
        print(json.dumps({'success': True, 'HTTP_calls': 0, 'records': len(job['records']), 'record_order': [r['id'] for r in job['records']],
                          'input_kind': kind, 'seed': body['seed'], 'max_tokens': body['max_tokens'],
                          'request_sha256': sha(json.dumps(body, separators=(',', ':')).encode()),
                          'profile_identity': identity}, indent=2));return
    result = run(job, body, kind, identity, args.output, args.base_url, args.timeout)
    print(json.dumps({'success': result['success'], 'output': str(args.output.resolve()), 'elapsed_s': result['elapsed_s']}))
    if not result['success']:raise SystemExit(1)


if __name__ == '__main__':main()
