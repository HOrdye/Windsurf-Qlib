"""
多模态特征编码模块
包含文本编码器、图像编码器、数值特征处理和特征融合组件
"""

from .base import (
    BaseFeatureEncoder,
    BaseTextEncoder,
    BaseImageEncoder,
    BaseNumericalEncoder,
    BaseFeatureFusion
)

from .text_encoder import BERTTextEncoder
from .image_encoder import ResNetImageEncoder
from .numerical_encoder import NumericalFeatureProcessor
from .fusion import MultiModalFeatureFusion, FeatureEncodingPipeline

__all__ = [
    "BaseFeatureEncoder",
    "BaseTextEncoder",
    "BaseImageEncoder",
    "BaseNumericalEncoder",
    "BaseFeatureFusion",
    "BERTTextEncoder",
    "ResNetImageEncoder",
    "NumericalFeatureProcessor",
    "MultiModalFeatureFusion",
    "FeatureEncodingPipeline"
]
