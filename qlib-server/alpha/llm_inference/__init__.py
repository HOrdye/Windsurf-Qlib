"""
LLM驱动Alpha生成系统 - 推理优化模块
包含模型量化、模型并行推理框架和推理缓存机制
"""

from .base import (
    BaseLLMInference,
    BaseModelQuantizer,
    BaseParallelInference,
    BaseCachingMechanism
)

from .quantization import (
    Int8Quantizer,
    Int4Quantizer,
    DynamicQuantizer
)

from .parallel import (
    TensorParallelEngine,
    PipelineParallelEngine
)

from .parallel_hybrid import (
    HybridParallelEngine
)

from .caching import (
    KVCachingMechanism,
    PrefixCachingMechanism,
    AdaptiveCachingStrategy
)

from .inference_engine import (
    OptimizedLLMInference,
    InferenceConfig
)

__all__ = [
    "BaseLLMInference",
    "BaseModelQuantizer",
    "BaseParallelInference",
    "BaseCachingMechanism",
    "Int8Quantizer",
    "Int4Quantizer",
    "DynamicQuantizer",
    "TensorParallelEngine",
    "PipelineParallelEngine",
    "HybridParallelEngine",
    "KVCachingMechanism",
    "PrefixCachingMechanism",
    "AdaptiveCachingStrategy",
    "OptimizedLLMInference",
    "InferenceConfig"
]
