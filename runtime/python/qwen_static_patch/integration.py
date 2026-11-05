"""Startup-only subclass integration with the frozen production GGUF plugin.

Future plugin entry point: gguf_static_patch = qwen_static_patch.integration:register
Select that sole GGUF entry point; it registers the frozen base plugin first.
"""
import json
import os
from vllm.logger import init_logger
_STATIC_AUDIT_LOGGER = init_logger("vllm.qwen_static_patch.integration")
from pathlib import Path
import re

import torch
from vllm.model_executor.layers.linear import register_weight_loader_v2_supported_method
from vllm.model_executor.layers.quantization import register_quantization_config
from vllm.model_executor.model_loader import register_model_loader
from vllm_gguf_plugin.loader import GGUFModelLoader
from vllm_gguf_plugin.quantization.config import GGUFConfig
from vllm_gguf_plugin.quantization.linear import GGUFLinearMethod

from .core import COEFF_BUFFER, U_BUFFER, apply_correction, bind_buffers, load_manifest

MANIFEST_ENV = 'QWEN_STATIC_PATCH_MANIFEST'
# Actual VL target prefixes are language_model.model.layers.N..., optionally
# under model.; model.layers.N... covers its native text-only wrapper.
TARGET_PREFIX = re.compile(r'^(?:model\.)?(?:language_model\.)?model\.layers\.(\d+)\.mlp\.down_proj$')
_REGISTERED = False


def tp_context():
    from vllm.distributed import get_tensor_model_parallel_rank, get_tensor_model_parallel_world_size
    return get_tensor_model_parallel_rank(), get_tensor_model_parallel_world_size()


@register_weight_loader_v2_supported_method
class StaticRankOneGGUFMethod(GGUFLinearMethod):
    def __init__(self, original, delta, alpha, tp_size, on_ready):
        if original.layout is not None:
            raise ValueError('Static down_proj coefficients require the unpermuted input layout')
        super().__init__(original.quant_config, layout=original.layout)
        self._static_delta = delta
        self._static_alpha = float(alpha)
        self._static_expected_tp_size = tp_size
        self._static_on_ready = on_ready

    def process_weights_after_loading(self, layer):
        super().process_weights_after_loading(layer)
        if layer.weight.dtype != torch.uint8 or layer.weight_type.weight_type != 13:
            raise ValueError('Target down_proj must retain original packed Q5_K weights')
        if getattr(layer.weight, 'shard_id', []):
            raise ValueError('Expected one unfused down_proj weight per TP rank')
        rank, size = tp_context()
        metadata = bind_buffers(layer, self._static_delta, rank, size, self._static_expected_tp_size)
        metadata.update({'layer': self._static_delta.layer, 'alpha': self._static_alpha,
                         'original_quantization_type': 13})
        self._static_on_ready(self._static_delta.layer, metadata)

    def apply(self, layer, x, bias=None):
        y = super().apply(layer, x, bias)
        return apply_correction(layer, x, y, self._static_alpha)


class StaticPatchGGUFConfig(GGUFConfig):
    def __init__(self, unquantized_modules=None):
        super().__init__(unquantized_modules)
        self._static_spec = None
        self._static_bindings = {}
        self._static_ready = {}

    def activate(self, spec):
        self._static_spec = spec
        self._static_bindings.clear()
        self._static_ready.clear()

    def _on_ready(self, layer, metadata):
        if layer in self._static_ready:
            raise ValueError('One selected layer was processed more than once')
        self._static_ready[layer] = metadata

    def get_quant_method(self, layer, prefix):
        original = super().get_quant_method(layer, prefix)
        spec = self._static_spec
        match = TARGET_PREFIX.fullmatch(prefix)
        if spec is None or match is None or int(match[1]) not in spec.deltas:
            return original
        index = int(match[1])
        if not isinstance(original, GGUFLinearMethod):
            raise ValueError('Selected target is unquantized or not a GGUF linear method')
        if index in self._static_bindings:
            raise ValueError('Selected layer matched multiple modules')
        self._static_bindings[index] = prefix
        return StaticRankOneGGUFMethod(original, spec.deltas[index], spec.alpha,
                                      spec.tensor_parallel_size, self._on_ready)

    def patch_metadata(self):
        spec = self._static_spec
        expected = set(spec.deltas)
        if set(self._static_bindings) != expected or set(self._static_ready) != expected:
            raise ValueError('Not every selected layer was wrapped and initialized')
        return {'manifest_path': spec.manifest_path, 'candidate_path': spec.candidate_path,
                'candidate_sha256': spec.candidate_sha256, 'alpha': spec.alpha,
                'base_model_path': spec.base_model_path, 'base_model_sha256': spec.base_model_sha256,
                'bindings': dict(self._static_bindings), 'local_buffers': dict(self._static_ready),
                'installation_point': 'model loading before drafter load, compilation, or graph capture'}


class StaticPatchGGUFModelLoader(GGUFModelLoader):
    def load_model(self, vllm_config, model_config, prefix=''):
        path = os.environ.get(MANIFEST_ENV)
        if not path:
            raise ValueError(f'{MANIFEST_ENV} must name the pinned static manifest')
        spec = load_manifest(str(Path(path).expanduser().resolve()))
        config = vllm_config.quant_config
        if not isinstance(config, StaticPatchGGUFConfig):
            raise ValueError('Static GGUF loader/config registration order is inconsistent')
        target_path = model_config.model_weights or model_config.model
        if not spec.matches_model(target_path):
            raise ValueError('Static-patch serving requires the exact pinned target GGUF; the current DFlash draft must keep its separate compressed-tensors loader')
        config.activate(spec)
        spec.verify_base_identity()
        text = model_config.hf_config.get_text_config()
        if text.num_hidden_layers != 64:
            raise ValueError('The patch targets the original64-layer model only')
        model = super().load_model(vllm_config, model_config, prefix)
        model._static_rankone_patch_metadata = config.patch_metadata()
        model._static_rankone_patch_metadata["worker_matmul_precision"] = {"float32_matmul_precision": torch.get_float32_matmul_precision(), "captured_at": "target_load_complete_before_compilation"}
        try:
            model._static_rankone_patch_metadata["worker_matmul_precision"]["cuda_allow_tf32"] = bool(torch.backends.cuda.matmul.allow_tf32)
        except Exception as precision_error:
            model._static_rankone_patch_metadata["worker_matmul_precision"]["cuda_allow_tf32"] = None
            model._static_rankone_patch_metadata["worker_matmul_precision"]["query_error"] = type(precision_error).__name__
        model._static_rankone_patch_metadata["compile_cache_namespace"] = {"vllm_cache_root": os.environ.get("VLLM_CACHE_ROOT"), "scope": "profile-specific physical AOT/Inductor cache isolation"}
        _STATIC_AUDIT_LOGGER.info("STATIC_PATCH_STARTUP_AUDIT %s", json.dumps(model._static_rankone_patch_metadata, sort_keys=True))
        return model


def register():
    """Register only in the process's plugin registries; writes no files."""
    global _REGISTERED
    if _REGISTERED:
        return
    from vllm_gguf_plugin import plugin as frozen_plugin
    frozen_plugin.register()
    register_quantization_config('gguf')(StaticPatchGGUFConfig)
    register_model_loader('gguf')(StaticPatchGGUFModelLoader)
    _REGISTERED = True


def inspect_static_patch_metadata(model):
    """Read-only apply_model probe; returns primitive startup metadata only."""
    metadata = getattr(model, '_static_rankone_patch_metadata', None)
    if metadata is None:
        raise ValueError('Loaded target is missing static-patch startup metadata')
    return json.loads(json.dumps(metadata))
