#!/usr/bin/env python3
"""Check frozen public inventories and replay numeric summaries without a GPU."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def resolve_member(directory, name):
    member = (directory / name).resolve()
    require(member.is_relative_to(directory.resolve()), f'Inventory path escapes its directory: {name}')
    require(member.is_file(), f'Missing inventory file: {name}')
    return member


def main():
    checked = 0
    for relative in ('evidence/PUBLIC_SHA256SUMS', 'runtime/SHA256SUMS'):
        manifest = ROOT / relative
        for line in manifest.read_text().splitlines():
            if not line.strip():
                continue
            expected, name = line.split(None, 1)
            member = resolve_member(manifest.parent, name.strip().lstrip('*'))
            require(digest(member) == expected, f'Hash mismatch: {member.relative_to(ROOT)}')
            checked += 1
    for relative in ('language_analysis/PUBLICATION_MANIFEST.json', 'research_code/RELEASE_MANIFEST.json'):
        manifest = ROOT / relative
        for row in json.loads(manifest.read_text())['files']:
            member = resolve_member(manifest.parent, row['file'])
            require(member.stat().st_size == row['bytes'], f'Size mismatch: {row["file"]}')
            require(digest(member) == row['sha256'], f'Hash mismatch: {row["file"]}')
            checked += 1

    numeric_files = (
        'cohort_summary.csv', 'cohort_summary.json',
        'panel_family_summary.csv', 'panel_family_summary.json',
        'outcome_stratified_descriptive.csv', 'paired_vs_control.csv', 'primary_cases.csv',
    )
    with tempfile.TemporaryDirectory(prefix='calmer-public-check-') as temp:
        subprocess.run([
            sys.executable, '-B', str(ROOT / 'language_analysis/analyze_language.py'),
            '--from-metrics', str(ROOT / 'language_analysis/public/generation_metrics.json'),
            '--output-dir', temp,
        ], check=True, cwd=ROOT, capture_output=True, text=True)
        for name in numeric_files:
            original = ROOT / 'language_analysis/public' / name
            rebuilt = Path(temp) / 'public' / name
            require(rebuilt.read_bytes() == original.read_bytes(), f'Numeric replay changed: {name}')

    print(json.dumps({
        'status': 'passed', 'inventory_entries_checked': checked,
        'byte_identical_numeric_replays': len(numeric_files),
        'model_downloads': 0, 'inference_calls': 0,
        'scope': 'Public file integrity and aggregate replay, not raw-feature or GPU validation.',
    }, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Public release check failed: {error}') from error
