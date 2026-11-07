#!/usr/bin/env python3
"""Build a portable V2 runtime directory from the pinned V1 source closure.

CPU and filesystem only. The output must be a new, empty path outside this repo.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
V2 = Path(__file__).resolve().parent
SOURCE = V2.parent
OVERRIDES = (
    'README.txt', 'NOTICE.txt', 'SOURCE_PROVENANCE.json',
    'calmer_delta.npz', 'edit_manifest.json', 'launch_exact.py', 'cpu_checks.py',
)
DROP_V1_REPORTS = {
    'MANIFEST.json', 'SHA256SUMS', 'CONFIG_PARITY.json',
    'CPU_VALIDATION.json', 'PUBLICATION_PRIVACY_CHECK.json',
}


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def assemble(output):
    output = output.expanduser().resolve()
    if output == SOURCE or output.is_relative_to(SOURCE):
        raise ValueError('Output must be outside the source runtime directory')
    if output.exists():
        raise FileExistsError(f'Output already exists: {output}')

    def ignore(directory, names):
        parent = Path(directory)
        blocked = set()
        if parent == SOURCE:
            blocked |= {'v2'} | DROP_V1_REPORTS
        blocked |= {name for name in names if name in {'__pycache__', 'build', 'dist'}
                    or name.endswith(('.pyc', '.so'))}
        return blocked

    try:
        shutil.copytree(SOURCE, output, ignore=ignore)
        for name in OVERRIDES:
            shutil.copy2(V2 / name, output / name)
        files = sorted(p for p in output.rglob('*') if p.is_file())
        hashes = {p.relative_to(output).as_posix(): sha256(p) for p in files}
        expected = 'c12820b9bc65e691853a1073c8647fed47cb5521ef3fbcd19817d684006debba'
        if hashes['calmer_delta.npz'] != expected:
            raise ValueError('V2 sidecar SHA256 mismatch')
        manifest = {
            'schema_version': 1,
            'representation': 'original packed GGUF plus fixed FP32 four-layer edit',
            'model_name': 'Calmer-V2-Qwen3.8-27B-4bit',
            'candidate_sha256': expected,
            'alpha': 1.5,
            'layers': [18, 49, 50, 51],
            'prebuilt_CUDA_extension_distributed': False,
            'status': 'CPU-packaged source; local pinned-stack build and validation required',
            'sha256': hashes,
        }
        (output / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
        files = sorted(p for p in output.rglob('*') if p.is_file())
        (output / 'SHA256SUMS').write_text(''.join(
            f'{sha256(p)}  {p.relative_to(output).as_posix()}\n' for p in files))
    except BaseException:
        if output.exists():
            shutil.rmtree(output)
        raise
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    print(assemble(parser.parse_args().output))
