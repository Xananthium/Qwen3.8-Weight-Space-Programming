#!/usr/bin/env python3
"""Portable suite dispatcher. Default prints a plan; --run makes API requests.

No launch, stop, queue, candidate fitting, retries, or smoke/runtime duplication.
The plan supplies private job paths and seeds; no benchmark content is bundled.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan-file', type=Path, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    plan = json.loads(args.plan_file.read_text())
    if len({item['stage'] for item in plan}) != len(plan):
        raise ValueError('Duplicate stages')
    commands = []
    for item in plan:
        stage = item['stage']
        if not stage.replace('_', '').isalnum():
            raise ValueError('Invalid stage name')
        output = args.output_dir/(stage+'.result.json')
        if output.exists():
            raise FileExistsError(output)
        job = Path(item['job'])
        if not job.is_absolute():
            job = args.plan_file.resolve().parent/job
        cmd = [args.python, '-B', str(Path(__file__).with_name('api_batch_eval.py')),
               '--profile', str(args.profile), '--output', str(output), '--base-url', args.base_url,
               '--job', str(job), '--expected-seed', str(item['seed'])]
        commands.append({'stage': stage, 'argv': cmd})
    if not args.run:
        print(json.dumps({'HTTP_calls': 0, 'commands': commands}, indent=2))
        return
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for item in commands:
        subprocess.run(item['argv'], check=True)


if __name__ == '__main__':
    main()
