#!/usr/bin/env python3
"""Port the historical prompt construction without bundling dataset text.

All GSM problem/solution records and the two authored strings are supplied
separately. Writes inert capture jobs, never an active queue or model request.
Use the redacted-input manifest to verify exact reconstructed bytes.
"""
import argparse
import json
from pathlib import Path
import re


def construct(records, productive_suffix, recheck_sentence):
    probes = []
    for i, row in enumerate(records[:4]):
        solution = re.sub(r'<<.*?>>', '', row['solution'].split('####')[0]).strip()
        good = solution+'\n'+productive_suffix
        repeated = solution.split('.')[0]+'.\n'+recheck_sentence*5
        for label, prefix in [('productive', good), ('repetitive', repeated)]:
            probes.append({'name': f'{i*2+1:03d}_capture_{i}_{label}', 'pair': i, 'label': label,
                           'record': {'id': f'constructed_{i}_{label}', 'problem': row['problem'], 'prefix': prefix}})
    return probes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--discovery-json', type=Path, required=True, help='Authorized ordered records, with problem/solution fields')
    parser.add_argument('--productive-suffix-file', type=Path, required=True)
    parser.add_argument('--recheck-sentence-file', type=Path, required=True, help='Includes its historical terminating newline')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.discovery_json.read_text())
    records = data['discovery'] if isinstance(data, dict) else data
    if len(records) < 4 or args.output_dir.exists():
        raise ValueError('Need four records and a new private output directory')
    probes = construct(records, args.productive_suffix_file.read_text(), args.recheck_sentence_file.read_text())
    args.output_dir.mkdir(parents=True)
    (args.output_dir/'constructed_probes.json').write_text(json.dumps(probes, indent=2)+'\n')
    for item in probes:
        (args.output_dir/(item['name']+'.json')).write_text(json.dumps({'op': 'capture', 'records': [item['record']]}, indent=2)+'\n')


if __name__ == '__main__':
    main()
