#!/usr/bin/env python3
"""Standard-library checks for the curated V2 method package."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
manifest = json.loads((ROOT / 'PROVENANCE.json').read_text())
for name, expected in manifest['public_sha256'].items():
    path = ROOT / name
    content = path.read_bytes()
    assert hashlib.sha256(content).hexdigest() == expected, name
    if name.endswith('.py'):
        ast.parse(content, filename=name)
    assert (b'/' + b'home/' not in content), name
pairs = json.loads((ROOT / 'authored_pairs.json').read_text())['records']
assert len(pairs) == 6
assert len({p['pair_id'] for p in pairs}) == 6
for p in pairs:
    for side in ('productive', 'circular'):
        text = p[f'{side}_capture_prefix']
        assert text and '\nCurrent result:' not in text
    assert p['problem'] and p['shared_final_result']
print('V2 public source, hashes, and six authored pairs: OK')
