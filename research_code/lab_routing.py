#!/usr/bin/env python3
"""Write inert laboratory job plans from public route metadata and a private job.

Does not start a worker or place files in any active queue. The historical
worker needs independently cached spare blocks; repeated source indices must
not simply reuse a stateful attention object. Runtime implementation excluded.
"""
import argparse
import json
from pathlib import Path


def expand(segments, blocks=64):
    insertions = {}
    for segment in segments:
        after = segment['after']
        if type(after) is not int or not 0 <= after < blocks or after in insertions:
            raise ValueError('Invalid or duplicate insertion boundary')
        sources = segment['sources']
        if any(type(i) is not int or not 0 <= i < blocks for i in sources):
            raise ValueError('Invalid source block')
        insertions[after] = list(sources)
    route = []
    for original in range(blocks):
        route.append(original)
        route.extend(insertions.get(original, []))
    return route


def segments_from_route(route, blocks=64):
    # The recorded fourteen routes retain all originals in order. Inserted
    # sources do not conflict with the next original at any insertion boundary.
    position, segments = 0, []
    for original in range(blocks):
        if position >= len(route) or route[position] != original:
            raise ValueError('Route is not in the supported historical insertion form')
        position += 1
        sources = []
        while position < len(route) and (original == blocks-1 or route[position] != original+1):
            sources.append(route[position])
            position += 1
        if sources:
            segments.append({'after': original, 'sources': sources})
    if position != len(route) or expand(segments, blocks) != route:
        raise ValueError('Route reconstruction mismatch')
    return segments


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--conditions', type=Path, required=True, help='Public evidence/laboratory_conditions.json')
    parser.add_argument('--condition', required=True)
    parser.add_argument('--job', type=Path, required=True, help='Separately authorized frozen seven-record generate job')
    parser.add_argument('--candidate-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True, help='New private staging directory, never an active queue')
    args = parser.parse_args()
    matches = [x for x in json.loads(args.conditions.read_text()) if x['condition'] == args.condition]
    if len(matches) != 1:
        raise ValueError('Condition must identify exactly one recorded arm')
    item = matches[0]
    job = json.loads(args.job.read_text())
    if job['op'] != 'generate' or job['seed'] != 20261105 or job['max_tokens'] != 12288 or job['temperature'] != 1.3 or len(job['records']) != 7:
        raise ValueError('Not the frozen laboratory7 / seed05 / 12K job')
    segments = segments_from_route(item['original_layer_sequence'])
    candidate = str(args.candidate_dir/item['candidate_file']) if item['candidate_file'] else None
    jobs = [('00_set_relayer', {'op': 'set_relayer', 'segments': segments}),
            ('01_set_edit', {'op': 'set_edit', 'path': candidate, 'alpha': item['global_alpha']}),
            ('02_generate', job),
            ('03_reset_relayer', {'op': 'set_relayer', 'segments': []}),
            ('04_reset_edit', {'op': 'set_edit', 'path': None, 'alpha': 0})]
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    for name, data in jobs:
        (args.output_dir/(name+'.json')).write_text(json.dumps(data, indent=2)+'\n')
    (args.output_dir/'PLAN_ONLY.txt').write_text('Inert private job plan. No jobs queued or executed. Requires historical worker/cache routing and numerical validation.\n')


if __name__ == '__main__':
    main()
