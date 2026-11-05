#!/usr/bin/env python3
"""Verify curated excerpt metadata, and optionally authorized private sources.

Public mode checks quote hashes/lengths, optional public metric/inventory joins,
and literal presence in supplied Markdown. It does NOT authenticate private
source bytes or certify publication rights. --experiment-root additionally
checks source files, output fields, exact character slices and phase bounds.
All offsets are Python Unicode character indexes [start,end); hashes use exact
UTF-8 without whitespace or Unicode normalization. No inputs are written.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_bytes().decode('utf-8'))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def text_digest(text):
    return digest(text.encode('utf-8'))


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def valid_sha(value, label):
    require(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value), label + ': invalid SHA256')


def valid_id(value, label):
    require(isinstance(value, str) and bool(value.strip()), label + ': missing ID')


def relative_path(value, label):
    require(isinstance(value, str) and value and '\\' not in value, label + ': expected relative POSIX path')
    path = Path(value)
    require(not path.is_absolute() and '..' not in path.parts and not re.match(r'^[A-Za-z]:', value),
            label + ': path must stay relative to its root')
    return path


def inside(root, relative, label):
    path = (root / relative).resolve()
    require(path.is_relative_to(root), label + ': path escapes root')
    return path


def markdown_texts(paths):
    texts = []
    for path in paths:
        raw = path.read_bytes().decode('utf-8')
        # Support literal/fenced quotes and one outer Markdown blockquote level.
        texts.extend([raw, re.sub(r'(?m)^[ \t]{0,3}> ?', '', raw)])
    return texts


def verify(manifest, *, metrics=None, inventory=None, markdown=None, experiment_root=None):
    require(manifest.get('schema_version') == 1, 'Unsupported excerpt schema')
    cases = manifest.get('cases')
    require(isinstance(cases, list) and cases, 'Manifest requires nonempty cases')
    metric_index = {}
    if metrics is not None:
        rows = metrics.get('rows') if isinstance(metrics, dict) else metrics
        require(isinstance(rows, list), 'Public metrics requires rows')
        for row in rows:
            key = (row['source_sha256'], row['id'])
            metric_index.setdefault(key, []).append(row)
    inventory_index = {}
    if inventory is not None:
        for item in inventory['artifacts']:
            inventory_index.setdefault(item['artifact'], set()).add(item['sha256'])
    root = Path(experiment_root).resolve() if experiment_root else None
    sources = {}
    case_ids = set()
    totals = {'cases': 0, 'records': 0, 'spans': 0}
    for case in cases:
        case_id = case.get('id')
        valid_id(case_id, 'case')
        require(case_id not in case_ids, 'Duplicate case ID')
        case_ids.add(case_id)
        records = case.get('records')
        require(isinstance(records, list) and records, f'{case_id}: requires records')
        record_ids = set()
        totals['cases'] += 1
        for record in records:
            record_id = record.get('id')
            valid_id(record_id, case_id + '/record')
            label = f'{case_id}/{record_id}'
            require(record_id not in record_ids, label + ': duplicate record ID')
            record_ids.add(record_id)
            valid_id(record.get('output_id'), label + '/output')
            valid_id(record.get('condition'), label + '/condition')
            require(type(record.get('seed')) is int, label + ': seed must be an integer')
            relative = relative_path(record.get('source_relative_path'), label)
            for key in ('source_sha256', 'source_text_sha256'):
                valid_sha(record.get(key), label + '/' + key)
            field = record.get('field')
            require(field in ('text', 'prompt'), label + ': field must be text or prompt')
            reported_metrics = record.get('metrics', {})
            require(isinstance(reported_metrics, dict), label + ': metrics must be an object')
            metric = None
            if metrics is not None:
                candidates = metric_index.get((record['source_sha256'], record['output_id']), [])
                require(len(candidates) == 1, label + ': no unique public metric row')
                metric = candidates[0]
                require(metric['condition'] == record['condition'] and metric['seed'] == record['seed'],
                        label + ': condition/seed differs from public metrics')
                expected_hash = metric['output_text_sha256' if field == 'text' else 'prompt_sha256']
                require(record['source_text_sha256'] == expected_hash, label + ': field hash differs from public metrics')
                for key, value in reported_metrics.items():
                    require(key in metric and canonical(value) == canonical(metric[key]),
                            label + ': public metric mismatch: ' + key)
                for key in ('cohort', 'stage', 'source_key'):
                    if key in record:
                        require(canonical(record[key]) == canonical(metric[key]), label + ': metadata mismatch: ' + key)
            if inventory is not None:
                require(inventory_index.get(str(relative)) == {record['source_sha256']},
                        label + ': source path/hash differs from artifact inventory')
            source_text = None
            if root is not None:
                path = inside(root, relative, label)
                if path not in sources:
                    raw = path.read_bytes()
                    sources[path] = (digest(raw), json.loads(raw.decode('utf-8')))
                source_hash, data = sources[path]
                require(source_hash == record['source_sha256'], label + ': private result-file hash mismatch')
                matches = [row for row in data['outputs'] if row['id'] == record['output_id']]
                require(len(matches) == 1, label + ': no unique private output ID')
                source_text = matches[0].get(field)
                require(isinstance(source_text, str), label + ': private field must be a plain string')
                require(text_digest(source_text) == record['source_text_sha256'], label + ': private field hash mismatch')
                require(data['job']['seed'] == record['seed'], label + ': private job seed mismatch')
            spans = record.get('spans')
            require(isinstance(spans, list) and spans, label + ': requires spans')
            span_ids = set()
            totals['records'] += 1
            for span in spans:
                span_id = span.get('id')
                valid_id(span_id, label + '/span')
                where = f'{label}/{span_id}'
                require(span_id not in span_ids, where + ': duplicate span ID')
                span_ids.add(span_id)
                start, end, quote = span.get('start'), span.get('end'), span.get('text')
                require(type(start) is int and type(end) is int and 0 <= start < end,
                        where + ': invalid [start,end) character offsets')
                require(isinstance(quote, str) and len(quote) == end-start,
                        where + ': span length differs from character offsets')
                valid_sha(span.get('sha256'), where)
                require(text_digest(quote) == span['sha256'], where + ': quote SHA256 mismatch')
                phase = span.get('phase')
                require(phase in ('thinking', 'final', 'prompt', 'control'), where + ': invalid phase')
                require((field == 'prompt') == (phase == 'prompt'), where + ': field/phase mismatch')
                if phase == 'control':
                    require(quote in ('<think>', '</think>'), where + ': control span must be an exact thinking delimiter')
                labels = metric if metric is not None else reported_metrics
                if (phase == 'final' or (phase == 'control' and quote == '</think>')) and 'thinking_closed' in labels:
                    require(labels['thinking_closed'] is True, where + ': final phase contradicts available closure label')
                if source_text is not None:
                    require(end <= len(source_text) and source_text[start:end] == quote,
                            where + ': private character slice mismatch')
                    if field == 'text':
                        boundary = source_text.find('</think>')
                        if phase == 'thinking':
                            require(end <= (boundary if boundary >= 0 else len(source_text)),
                                    where + ': thinking span crosses first closing marker')
                        elif phase == 'final':
                            require(boundary >= 0 and start >= boundary+len('</think>'),
                                    where + ': final span precedes first closing marker')
                if markdown is not None:
                    require(any(quote in text for text in markdown), where + ': quote absent from supplied Markdown')
                totals['spans'] += 1
    return {'success': True, 'mode': 'authorized_private_archive' if root else 'public_consistency_only',
            **totals, 'span_hashes_and_character_lengths_checked': True,
            'public_metric_joins_checked': metrics is not None,
            'public_artifact_path_joins_checked': inventory is not None,
            'literal_Markdown_inclusion_checked': markdown is not None,
            'private_file_field_slice_and_phase_bounds_checked': root is not None,
            'publication_rights_or_content_review_certified': False,
            'private_source_text_printed_or_written': False,
            'limitations': 'Public-only checks do not authenticate private source bytes. Hash/slice authenticity does not certify redistribution rights, contextual completeness, proof validity or a model mental state.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, help='Default: examples/selected_excerpts.json below public root')
    parser.add_argument('--metrics', type=Path)
    parser.add_argument('--inventory', type=Path)
    parser.add_argument('--document', '--markdown', dest='documents', type=Path, action='append',
                        help='Additional Markdown source; all spans must occur in the checked documents collectively')
    parser.add_argument('--public-root', type=Path, default=Path(__file__).resolve().parents[1],
                        help='Default: repository root above tools/; contains bundled metrics/inventory/examples')
    parser.add_argument('--experiment-root', type=Path, help='Authorized private archive preserving source_relative_path layout')
    args = parser.parse_args()
    try:
        public_root = args.public_root.resolve()
        manifest = read(args.manifest or public_root / 'examples/selected_excerpts.json')
        default_document = public_root / 'examples/SELECTED_CONVERSATIONS.md'
        markdown_paths = [default_document] if default_document.exists() or not (args.documents or manifest.get('markdown_sources')) else []
        for document in args.documents or []:
            markdown_paths.append(document if document.is_absolute() else public_root / document)
        for value in manifest.get('markdown_sources', []):
            markdown_paths.append(inside(public_root, relative_path(value, 'markdown_sources'), 'markdown_sources'))
        result = verify(manifest, metrics=read(args.metrics or public_root / 'language_analysis/public/generation_metrics.json'),
                        inventory=read(args.inventory or public_root / 'evidence/artifact_inventory.json'),
                        markdown=markdown_texts(markdown_paths) if markdown_paths else None,
                        experiment_root=args.experiment_root)
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'success': False, 'error': str(error)}), file=sys.stderr)
        raise SystemExit(2)


if __name__ == '__main__':
    main()
