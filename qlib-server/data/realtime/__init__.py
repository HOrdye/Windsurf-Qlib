"""
实时数据流接入模块
支持市场实时数据流接入、高频数据处理和数据流异常处理
"""
from .base import (
    BaseDataStreamAdapter,
    BaseHighFrequencyProcessor,
    BaseStreamAnomalyHandler
)

from .adapter import (
    MarketDataStreamAdapter,
    WebSocketDataAdapter,
    RESTfulDataAdapter
)

from .processor import (
    HighFrequencyDataProcessor,
    TickDataProcessor,
    OrderBookProcessor
)

from .handler import (
    StreamAnomalyHandler,
    DataContinuityHandler,
    DataRecoveryHandler
)

from .stream_monitor import DataStreamMonitor

__all__ = [
    # 基类
    "BaseDataStreamAdapter",
    "BaseHighFrequencyProcessor",
    "BaseStreamAnomalyHandler",
    
    # 适配器
    "MarketDataStreamAdapter",
    "WebSocketDataAdapter",
    "RESTfulDataAdapter",
    
    # 处理器
    "HighFrequencyDataProcessor",
    "TickDataProcessor",
    "OrderBookProcessor",
    
    # 异常处理
    "StreamAnomalyHandler",
    "DataContinuityHandler",
    "DataRecoveryHandler",
    
    # 监控
    "DataStreamMonitor"
]
