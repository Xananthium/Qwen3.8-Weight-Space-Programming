#!/usr/bin/env python3
"""Small offline checks on public synthetic fixtures; never makes HTTP calls.

--conditions optionally validates all fourteen published source routes.
--with-fit additionally requires NumPy/GGUF and checks the rank-one algebra.
"""
import argparse
import copy
import json
from pathlib import Path

import api_batch_eval
import graph_certificate
import hle_score
import lab_routing
import score_state_transfer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--conditions', type=Path)
    parser.add_argument('--with-fit', action='store_true')
    args = parser.parse_args()
    checks = []
    source = {'id': 'synthetic_fixture', 'answer': 'X', 'choices': {'X': 'fixture', 'Y': 'alternative'},
              'category': 'synthetic', 'subject': 'protocol'}
    out = {'id': source['id'], 'text': 'work</think>Answer: X\nConfidence: 90%', 'tokens': 7, 'finish_reason': 'stop'}
    result = {'job': {'records': [source], 'max_tokens': 10}, 'outputs': [out]}
    assert hle_score.score(result)['rows'][0]['status'] == 'correct'
    limited = copy.deepcopy(result)
    limited['outputs'][0]['finish_reason'] = 'length'
    assert hle_score.score(limited)['rows'][0]['status'] == 'cutoff'
    assert hle_score.parse_answer('work Answer: X')[0] is None
    assert hle_score.parse_answer('work</think>The answer is X.')[0] is None
    checks.append('Frozen choice parser: explicit final / cutoff / unfinished / strict format distinction')
    def boxed(payload, reason='stop'):
        return {'text': 'work</think>\\boxed{'+payload+'}', 'finish_reason': reason}
    queue = ['Juno', 'Kai']
    assert score_state_transfer.score_output(boxed('Juno,Kai'), queue)['status'] == 'correct'
    assert score_state_transfer.score_output(boxed('Kai,Juno'), queue)['status'] == 'wrong'
    assert score_state_transfer.score_output(boxed('Juno,Kai,Lee'), queue)['status'] == 'wrong'
    assert score_state_transfer.score_output(boxed('Juno,Kai', 'length'), queue)['status'] == 'cutoff'
    parts = {'text': r'work</think>\boxed{North}\boxed{West}', 'finish_reason': 'stop'}
    expected = {'room': 'North', 'next_room': 'West'}
    assert score_state_transfer.score_output(parts, expected)['status'] == 'correct'
    parts['text'] += r'\boxed{unfinished'
    assert score_state_transfer.score_output(parts, expected)['status'] == 'unparsed'
    checks.append('Frozen state parser: order / extra entity / cutoff / multipart / malformed last box')
    job = {'op': 'generate', 'temperature': 1.3, 'seed': 20261105, 'max_tokens': 2,
           'records': [{'id': 'synthetic_protocol', 'prompt': 'Synthetic protocol fixture.', 'reasoning_effort': 'medium'}]}
    body, kind = api_batch_eval.build_request(job, 'caller-supplied-model', 20261105)
    assert kind == 'text' and body['max_tokens'] == 2 and body['temperature'] == 1.3
    assert body['top_p'] == .95 and body['top_k'] == 20
    streamed = {'initial_prompt_token_ids': None, 'token_ids': [], 'text': '',
                'finish_reason': None, 'first_token_elapsed_s': None, 'api_logprob_chunks': []}
    event = {'choices': [{'index': 0, 'prompt_token_ids': [1, 2], 'token_ids': [3], 'text': 'fixture', 'finish_reason': 'stop'}]}
    api_batch_eval.consume_event(event, [streamed], .1)
    assert streamed['token_ids'] == [3] and streamed['initial_prompt_token_ids'] == [1, 2]
    try:
        api_batch_eval.consume_event(event, [streamed], .2)
    except ValueError:
        pass
    else:
        raise AssertionError('Tokens after finish were accepted')
    checks.append('Request/SSE token accounting and rejection after finish; no request sent')
    assert graph_certificate.verify([['a', 'b', 'c'], ['a', 'd', 'b'], ['a', 'c', 'd'], ['b', 'd', 'c']])['edges'] == 6
    checks.append('Generic tetrahedral sphere certificate; no benchmark fixture')
    if args.conditions:
        conditions = json.loads(args.conditions.read_text())
        for item in conditions:
            route = item['original_layer_sequence']
            assert lab_routing.expand(lab_routing.segments_from_route(route)) == route
        assert len(conditions) == 14
        checks.append('All fourteen published source routes round-trip; no worker/queue execution')
    if args.with_fit:
        import numpy as np
        from fit_sparse_contrasts import fit
        rng = np.random.default_rng(41)
        weight = rng.normal(size=(4, 9)).astype(np.float32)
        good_h = rng.normal(size=(4, 4)).astype(np.float32)
        bad_h = good_h+np.array([1, 2, 3, 4], dtype=np.float32)
        good_x = rng.normal(size=(4, 9)).astype(np.float32)
        bad_x = good_x+rng.normal(size=(4, 9)).astype(np.float32)
        unit, coeff, report = fit(weight, good_h, bad_h, good_x, bad_x, columns=3)
        assert np.count_nonzero(coeff) == 3 and len(report['selected_columns']) == 3
        x = rng.normal(size=(2, 9)).astype(np.float32)
        merged = weight-.7*np.outer(unit, coeff)
        assert np.allclose(x@merged.T, x@weight.T-.7*(x@coeff)[:, None]*unit[None, :], atol=2e-6)
        checks.append('Synthetic sparse rank-one fit support and materialized-update algebra')
    print(json.dumps({'status': 'passed', 'model_calls': 0, 'HTTP_calls': 0, 'GPU_operations': 0, 'checks': checks}, indent=2))


if __name__ == '__main__':
    main()
