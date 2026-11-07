#!/usr/bin/env python3
"""Check public V2 release identities without downloading model weights."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELTA = 'c12820b9bc65e691853a1073c8647fed47cb5521ef3fbcd19817d684006debba'
MERGED = '8c046db3518f3711f797a832153362f413aa29e9ab8aef675f88a0842291c1a1'
BASE = 'ba36dc3c2b2ff5e0aa5d71092a8894546996a6a119ae391803dda07cdc08516d'
NAME = 'Calmer-V2-Qwen3.8-27B-Q4_K_P-F32Edits.gguf'


def read(name):
    return json.loads((ROOT / name).read_text())


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    edit = read('runtime/v2/edit_manifest.json')
    with (ROOT / 'runtime/v2/calmer_delta.npz').open('rb') as handle:
        require(hashlib.file_digest(handle, 'sha256').hexdigest() == DELTA, 'Delta bytes changed')
    require(edit['candidate']['sha256'] == DELTA, 'Edit manifest delta mismatch')
    require(edit['base_model']['sha256'] == BASE, 'Original base identity changed')
    require(edit['layers'] == [18, 49, 50, 51] and edit['alpha'] == 1.5, 'Edit layers/alpha changed')
    export = read('release/v2/merged_export_manifest.json')
    require(export['output_sha256'] == MERGED, 'Merged artifact identity changed')
    require(export['output_bytes'] == 19104353280, 'Merged artifact size changed')
    require(export['delta_sha256'] == DELTA and export['source_sha256'] == BASE, 'Export inputs mismatch')
    require(export['all_other_tensor_payloads_byte_identical'] is True, 'Missing preservation evidence')
    inventory = export['tensor_inventory']
    require(len(inventory) == 866, 'Tensor inventory count changed')
    require(sum(t['edited'] for t in inventory) == 4, 'Edited tensor count changed')
    require({t['layer_zero_based'] for t in export['changes']} == {18, 49, 50, 51}, 'Wrong changed layers')
    require(all(t['source_type'] == 'Q5_K' and t['export_type'] == 'F32'
                for t in export['changes']), 'Wrong edited tensor representation')
    smoke = read('release/v2/native_smoke.json')
    require(smoke['gpu_layers'] == 0 and smoke['exit_code'] == 0, 'CPU smoke did not complete')
    require(smoke['simple_arithmetic_correct'] is True
            and smoke['final_answer_before_interactive_eof_marker'] == '4', 'Smoke result mismatch')
    release = read('release/v2/release_manifest.json')
    files = {row['path']: row for row in release['files']}
    require(files[NAME]['sha256'] == MERGED, 'Hub inventory merged identity mismatch')
    for name in ('calmer_delta.npz', 'runtime/calmer_delta.npz'):
        require(files[name]['sha256'] == DELTA, 'Hub inventory delta mismatch')
    publication = read('release/v2/hub_publication.json')
    require(publication['repo_id'] == 'Xananthium/Calmer-V2-Qwen3.8-27B-4bit', 'Wrong Hub repository')
    require(publication['public'] is True and publication['all_expected_sizes_match'] is True,
            'Public Hub verification missing')
    require(publication['all_lfs_sha256_match'] is True, 'Hub large-file identity check failed')
    require(len(publication['revision']) == 40, 'Missing immutable Hub revision')
    print(json.dumps({'status':'passed', 'layers':[18,49,50,51],
                      'tensor_inventory':866, 'preserved_payloads':862,
                      'model_downloads':0, 'inference_calls':0,
                      'scope':'Public identity and evidence consistency, not an independent tensor or benchmark rerun.'},indent=2))


if __name__ == '__main__':
    main()
