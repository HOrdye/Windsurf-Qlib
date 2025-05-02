"""
多源数据融合增强模块
提供跨市场数据对齐、多频率数据重采样和数据源可靠性评分等功能
"""

from .base import (
    BaseDataFusion,
    BaseDataAligner,
    BaseDataResampler,
    BaseReliabilityScorer
)

from .aligner import (
    CrossMarketDataAligner,
    TimeZoneAligner,
    AsynchronousDataAligner
)

from .resampler import (
    MultiFrequencyResampler,
    UpSampler,
    DownSampler,
    AdaptiveResampler
)

from .reliability import (
    DataSourceReliabilityScorer,
    LatencyScorer,
    AccuracyScorer,
    CompletenessScorer,
    ConsistencyScorer
)

from .fusion import (
    DataFusionEngine,
    WeightedAverageFusion,
    KalmanFilterFusion,
    MachineLearningFusion
)

__all__ = [
    # 基类
    "BaseDataFusion",
    "BaseDataAligner",
    "BaseDataResampler",
    "BaseReliabilityScorer",
    
    # 数据对齐器
    "CrossMarketDataAligner",
    "TimeZoneAligner",
    "AsynchronousDataAligner",
    
    # 数据重采样器
    "MultiFrequencyResampler",
    "UpSampler",
    "DownSampler",
    "AdaptiveResampler",
    
    # 可靠性评分器
    "DataSourceReliabilityScorer",
    "LatencyScorer",
    "AccuracyScorer",
    "CompletenessScorer",
    "ConsistencyScorer",
    
    # 数据融合引擎
    "DataFusionEngine",
    "WeightedAverageFusion",
    "KalmanFilterFusion",
    "MachineLearningFusion"
]
