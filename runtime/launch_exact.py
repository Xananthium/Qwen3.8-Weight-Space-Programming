#!/usr/bin/env python3
"""Portable launch of the tested edit arithmetic with the pinned serving stack.

--check-imports constructs only the parser/config, never an LLM/EngineCore.
"""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
from portable_runtime import ROOT, prepare, read, sha256_file, verify_config


def command(options, local):
    cfg = verify_config(options.hf_config)
    edit = read(ROOT / 'edit_manifest.json')
    if sha256_file(options.mmproj_path) != edit['mmproj']['sha256']:
        raise ValueError('Vision projector SHA256 mismatch')
    draft = options.draft_dir.expanduser().resolve()
    if sha256_file(draft / 'model.safetensors') != edit['draft']['weights_sha256']:
        raise ValueError('DFlash weights differ from the pinned tested draft')
    if sha256_file(draft / 'config.json') != edit['draft']['config_sha256']:
        raise ValueError('DFlash config/tap mapping differs from the pinned tested draft')
    spec = {'method': 'dflash', 'model': str(draft), 'num_speculative_tokens': 7,
            'quantization': 'compressed-tensors', 'max_model_len': 200000,
            'draft_load_config': {'load_format': 'safetensors'},
            'draft_sample_method': 'probabilistic', 'attention_backend': 'TRITON_ATTN', 'kv_cache_dtype': 'auto'}
    compile_config = {'mode': 'VLLM_COMPILE', 'cudagraph_mode': 'FULL_DECODE_ONLY',
                      'cudagraph_capture_sizes': [1, 2, 4, 8, 16, 24, 32, 48],
                      'max_cudagraph_capture_size': 48, 'cache_dir': str(local['compile_cache_dir'])}
    args = ['serve', str(options.model_path.expanduser().resolve()), '--hf-config-path', str(cfg),
            '--tokenizer', str(cfg), '--load-format', 'gguf', '--quantization', 'gguf',
            '--speculative-config', json.dumps(spec), '--served-model-name', 'Calmer-Qwen3.8-27B-4bit',
            '--host', options.host, '--port', str(options.port), '--tensor-parallel-size', '2',
            '--dtype', 'bfloat16', '--gpu-memory-utilization', '0.95', '--max-model-len', '200000',
            '--max-num-seqs', '16', '--max-num-batched-tokens', '4096', '--kv-cache-dtype', 'turboquant_4bit_nc',
            '--kv-offloading-backend', 'native', '--kv-offloading-size', '80', '--enable-prefix-caching',
            '--prefix-caching-hash-algo', 'sha256_cbor', '--enable-auto-tool-choice', '--tool-call-parser', 'qwen3_coder',
            '--reasoning-parser', 'qwen3', '--generation-config', 'auto', '--override-generation-config',
            json.dumps({'min_p': 0.0, 'presence_penalty': 0.0, 'repetition_penalty': 1.0, 'temperature': 1.3,
                        'top_k': 20, 'top_p': 0.95}), '--default-chat-template-kwargs',
            json.dumps({'enable_thinking': True, 'reasoning_effort': 'medium'}), '--limit-mm-per-prompt',
            json.dumps({'image': 5, 'video': 0}), '--mm-processor-cache-gb', '0', '--compilation-config',
            json.dumps(compile_config), '--model-loader-extra-config',
            json.dumps({'mm_proj': str(options.mmproj_path.expanduser().resolve())}), '--mamba-cache-mode', 'align',
            '--mamba-ssm-cache-dtype', 'float32', '--chat-template', str(cfg / 'chat_template.jinja'), '--config-format', 'hf']
    return args


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-path', type=Path, required=True)
    p.add_argument('--delta-path', type=Path)
    p.add_argument('--hf-config', type=Path, required=True)
    p.add_argument('--mmproj-path', type=Path, required=True)
    p.add_argument('--draft-dir', type=Path, required=True)
    p.add_argument('--state-dir', type=Path, required=True)
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=8000)
    p.add_argument('--check-imports', action='store_true')
    o = p.parse_args()
    versions = read(ROOT / 'runtime_versions.json')
    if list(sys.version_info[:2]) != versions['python_major_minor']:
        raise RuntimeError('This exact-runtime profile requires the pinned Python major/minor')
    for name, expected in versions['distributions'].items():
        if importlib.metadata.version(name) != expected:
            raise RuntimeError('Pinned runtime dependency differs: ' + name)
    local = prepare(o.model_path, o.state_dir, o.delta_path)
    args = command(o, local)
    env = dict(os.environ)
    env.update({'PYTHONPATH': os.pathsep.join(str(ROOT / n) for n in ['overlay', 'python', 'vendor/gguf_plugin']),
                'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1', 'VLLM_PLUGINS': 'gguf_static_patch',
                'QWEN_STATIC_PATCH_MANIFEST': str(local['manifest_path']), 'VLLM_CACHE_ROOT': str(local['aot_cache_root']),
                'VLLM_USE_V2_MODEL_RUNNER': '1', 'VLLM_USE_FLASHINFER_SAMPLER': '0',
                'VLLM_TQ_UNIFIED_ATTN': '1', 'VLLM_KV_CACHE_LAYOUT': 'LBNHC',
                'VLLM_GGUF_CUDA_KERNEL': 'upstream', 'VLLM_LOGGING_LEVEL': 'INFO', 'PYTHONHASHSEED': '0'})
    # Resolve CUDA wheel libraries locally; never embed the publisher's paths.
    cuda_libraries = Path(importlib.metadata.distribution('nvidia-cuda-runtime').locate_file('nvidia/cu13/lib'))
    if cuda_libraries.is_dir():
        env['LD_LIBRARY_PATH'] = str(cuda_libraries) + (os.pathsep + env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
    if o.check_imports:
        env['CALMER_CPU_CHECK_RESULT'] = str(local['state_dir'] / 'cpu_import_check.json')
        # Fresh interpreter activates sitecustomize before any vLLM import.
        code = '''import json,sys,os,torch
from pathlib import Path
import hashlib
assert not torch.cuda.is_initialized()
torch.cuda._lazy_init=lambda *a,**k: (_ for _ in ()).throw(RuntimeError("CPU-only check"))
from vllm.plugins import load_general_plugins
load_general_plugins()
from vllm_gguf_plugin import ops
from qwen_static_patch.integration import StaticPatchGGUFConfig
from vllm.engine.arg_utils import EngineArgs
from vllm.entrypoints.launchers.cli_args import make_arg_parser
from vllm.utils.argparse_utils import FlexibleArgumentParser
from qwen_static_patch.core import load_manifest
args=json.loads(sys.argv[1])
namespace=make_arg_parser(FlexibleArgumentParser()).parse_args(["--model",args[1]]+args[2:])
config=EngineArgs.from_cli_args(namespace).create_engine_config()
patch=load_manifest(os.environ["QWEN_STATIC_PATCH_MANIFEST"])
assert sorted(patch.deltas)==[49,50,51] and patch.alpha==1.5
assert isinstance(config.quant_config,StaticPatchGGUFConfig)
assert config.parallel_config.tensor_parallel_size==2
assert config.cache_config.cache_dtype=="turboquant_4bit_nc"
assert config.speculative_config.method=="dflash"
assert config.compilation_config.mode.name=="VLLM_COMPILE"
assert torch.version.cuda=="13.0" and torch._C._GLIBCXX_USE_CXX11_ABI
assert not torch.cuda.is_initialized()
result={"plugin_imported":True,"full_EngineConfig_CPU":True,"LLM_or_EngineCore_constructed":False,"CUDA_initialized":False,"CUDA_extension_available":ops._CUDA_AVAILABLE,"runtime_ready":ops._CUDA_AVAILABLE,"candidate_sha256":patch.candidate_sha256,"layers":sorted(patch.deltas),"alpha":patch.alpha}
kernel_sha=hashlib.sha256(Path(ops._C_gguf.__file__).read_bytes()).hexdigest() if ops._CUDA_AVAILABLE else None
result.update({"CUDA_extension_sha256":kernel_sha,"matches_tested_CUDA_binary":kernel_sha=="e3cefbcc99a4008b96d52daeaddae770dad20b28f27432e18a4fdc894a912548","rebuilt_runtime_numerics_validated_by_this_check":False})
Path(os.environ["CALMER_CPU_CHECK_RESULT"]).write_text(json.dumps(result,indent=2)+"\\n")
print(json.dumps(result))
'''
        result = subprocess.run([sys.executable, '-B', '-c', code, json.dumps(args)], env=env)
        raise SystemExit(result.returncode)
    extension = ROOT / 'vendor/gguf_plugin/vllm_gguf_plugin/_C_gguf.abi3.so'
    if not extension.is_file():
        raise RuntimeError('Build the pinned vendored CUDA extension before serving; see README.txt')
    os.execve(sys.executable, [sys.executable, '-m', 'vllm.entrypoints.cli.main', *args], env)


if __name__ == '__main__':
    main()
