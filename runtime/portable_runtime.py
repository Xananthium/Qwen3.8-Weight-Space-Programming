"""Portable artifact verification and local manifest generation; no model loads."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha256_file(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def verify_config(config_path):
    config_path = Path(config_path).expanduser().resolve()
    for name, expected in read(ROOT / 'hf_config_hashes.json').items():
        if sha256_file(config_path / name) != expected:
            raise ValueError('HF config/tokenizer/template differs from tested assets: ' + name)
    return config_path


def prepare(model_path, state_dir, delta_path=None, *, edit=None):
    """Hash the large base once; reuse only the same path/stat/hash receipt.

    Local state contains machine paths and is intentionally outside the release.
    ``edit`` is an internal hook for small independent CPU fixtures, not a CLI
    bypass for the published artifact's pins.
    """
    spec = read(ROOT / 'edit_manifest.json') if edit is None else edit
    model_path = Path(model_path).expanduser().resolve()
    delta_path = Path(delta_path or ROOT / spec['candidate']['filename']).expanduser().resolve()
    state_dir = Path(state_dir).expanduser().resolve()
    if state_dir.is_relative_to(ROOT):
        raise ValueError('Local state must be outside the distributable runtime directory')
    if sha256_file(delta_path) != spec['candidate']['sha256']:
        raise ValueError('Sidecar SHA256 mismatch')
    stat = model_path.stat()
    identity = {'path': str(model_path), 'st_size': stat.st_size,
                'st_mtime_ns': stat.st_mtime_ns, 'st_ino': stat.st_ino}
    if stat.st_size != spec['base_model']['size']:
        raise ValueError('Base GGUF size mismatch')
    receipt_path = state_dir / 'base_verification.json'
    receipt = read(receipt_path) if receipt_path.is_file() else {}
    expected = dict(identity, sha256=spec['base_model']['sha256'])
    if receipt != expected:
        if sha256_file(model_path) != spec['base_model']['sha256']:
            raise ValueError('Base GGUF SHA256 mismatch')
    state_dir.mkdir(parents=True, exist_ok=True)
    write(receipt_path, expected)
    manifest = {'schema_version': 1, 'alpha': spec['alpha'], 'layers': spec['layers'],
                'tensor_parallel_size': spec['tensor_parallel_size'], 'dimensions': spec['dimensions'],
                'required_anchor': spec['required_anchor'],
                'base_model': dict(identity, sha256=spec['base_model']['sha256']),
                'candidate': {'path': str(delta_path), 'sha256': spec['candidate']['sha256']},
                'verify_base_sha256_in_each_worker': False,
                'note': 'Base SHA256 verified by portable prepare; workers also require this exact path/stat identity.'}
    path = state_dir / 'patch_manifest.json'
    write(path, manifest)
    # Do not share outer AOT artifacts across edits, code snapshots or locations.
    fingerprint = hashlib.sha256()
    for item in [ROOT / 'edit_manifest.json', ROOT / 'python/qwen_static_patch/core.py',
                 ROOT / 'python/qwen_static_patch/integration.py', ROOT / 'overlay/manifest.json',
                 ROOT / 'SOURCE_PROVENANCE.json', ROOT / 'requirements-tested.txt',
                 ROOT / 'runtime_versions.json', ROOT / 'hf_config_hashes.json',
                 ROOT / 'portable_runtime.py', ROOT / 'launch_exact.py', ROOT / 'overlay/sitecustomize.py']:
        fingerprint.update(item.read_bytes())
    for item in sorted((ROOT / 'vendor/gguf_plugin/vllm_gguf_plugin').rglob('*')):
        if item.is_file() and item.suffix in ('.py', '.toml', '.so'):
            fingerprint.update(str(item.relative_to(ROOT)).encode())
            fingerprint.update(bytes.fromhex(sha256_file(item)))
    fingerprint.update(str(state_dir).encode())
    key = fingerprint.hexdigest()
    return {'manifest_path': path, 'state_dir': state_dir,
            'aot_cache_root': state_dir / 'aot' / key,
            'compile_cache_dir': state_dir / 'compile' / key,
            'base_sha256': spec['base_model']['sha256'], 'delta_sha256': spec['candidate']['sha256']}
