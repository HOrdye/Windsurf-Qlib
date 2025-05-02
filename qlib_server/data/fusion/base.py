"""
多源数据融合基类模块
定义数据融合、数据对齐、数据重采样和可靠性评分的基本接口
"""

import abc
import logging
from typing import Dict, List, Union, Any, Tuple, Optional, Callable
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 配置日志
logger = logging.getLogger(__name__)

class BaseDataFusion(abc.ABC):
    """
    数据融合基类
    定义数据融合的基本接口
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据融合基类
        
        参数:
            config: 配置字典，包含融合参数
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._validate_config()
        
    def _validate_config(self) -> None:
        """
        验证配置是否合法
        子类可以重写此方法以添加特定的验证逻辑
        
        异常:
            ValueError: 配置不合法时抛出
        """
        if not isinstance(self.config, dict):
            raise ValueError("配置必须是字典类型")
    
    @abc.abstractmethod
    def fuse(self, data_sources: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        融合多个数据源
        
        参数:
            data_sources: 数据源字典，键为数据源名称，值为数据源DataFrame
            
        返回:
            融合后的DataFrame
        """
        pass
    
    def preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        预处理数据
        
        参数:
            data: 输入数据
            
        返回:
            预处理后的数据
        """
        return data
    
    def postprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        后处理数据
        
        参数:
            data: 输入数据
            
        返回:
            后处理后的数据
        """
        return data


class BaseDataAligner(abc.ABC):
    """
    数据对齐基类
    定义数据对齐的基本接口
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据对齐基类
        
        参数:
            config: 配置字典，包含对齐参数
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._validate_config()
    
    def _validate_config(self) -> None:
        """
        验证配置是否合法
        子类可以重写此方法以添加特定的验证逻辑
        
        异常:
            ValueError: 配置不合法时抛出
        """
        if not isinstance(self.config, dict):
            raise ValueError("配置必须是字典类型")
    
    @abc.abstractmethod
    def align(self, data_sources: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        对齐多个数据源
        
        参数:
            data_sources: 数据源字典，键为数据源名称，值为数据源DataFrame
            
        返回:
            对齐后的数据源字典
        """
        pass
    
    def get_common_timestamps(self, data_sources: Dict[str, pd.DataFrame]) -> List[datetime]:
        """
        获取多个数据源的共同时间戳
        
        参数:
            data_sources: 数据源字典
            
        返回:
            共同时间戳列表
        """
        if not data_sources:
            return []
        
        # 假设时间戳在索引中
        timestamp_sets = []
        for source_name, df in data_sources.items():
            if df.empty:
                self.logger.warning(f"数据源 {source_name} 为空")
                continue
                
            # 确保索引是DatetimeIndex
            if not isinstance(df.index, pd.DatetimeIndex):
                self.logger.warning(f"数据源 {source_name} 的索引不是DatetimeIndex，尝试转换")
                try:
                    df.index = pd.DatetimeIndex(df.index)
                except Exception as e:
                    self.logger.error(f"无法将数据源 {source_name} 的索引转换为DatetimeIndex: {e}")
                    continue
            
            timestamp_sets.append(set(df.index))
        
        # 计算交集
        if not timestamp_sets:
            return []
            
        common_timestamps = timestamp_sets[0]
        for ts_set in timestamp_sets[1:]:
            common_timestamps = common_timestamps.intersection(ts_set)
        
        # 转换为列表并排序
        return sorted(list(common_timestamps))


class BaseDataResampler(abc.ABC):
    """
    数据重采样基类
    定义数据重采样的基本接口
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据重采样基类
        
        参数:
            config: 配置字典，包含重采样参数
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._validate_config()
    
    def _validate_config(self) -> None:
        """
        验证配置是否合法
        子类可以重写此方法以添加特定的验证逻辑
        
        异常:
            ValueError: 配置不合法时抛出
        """
        if not isinstance(self.config, dict):
            raise ValueError("配置必须是字典类型")
        
        # 检查目标频率
        if "target_freq" not in self.config:
            raise ValueError("配置必须包含目标频率(target_freq)")
    
    @abc.abstractmethod
    def resample(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        重采样数据
        
        参数:
            data: 输入数据
            
        返回:
            重采样后的数据
        """
        pass
    
    def get_target_freq(self) -> str:
        """
        获取目标频率
        
        返回:
            目标频率字符串
        """
        return self.config["target_freq"]
    
    def infer_data_freq(self, data: pd.DataFrame) -> str:
        """
        推断数据频率
        
        参数:
            data: 输入数据
            
        返回:
            推断的频率字符串
        """
        if data.empty:
            return None
            
        # 确保索引是DatetimeIndex
        if not isinstance(data.index, pd.DatetimeIndex):
            try:
                data.index = pd.DatetimeIndex(data.index)
            except Exception as e:
                self.logger.error(f"无法将索引转换为DatetimeIndex: {e}")
                return None
        
        # 使用pandas的infer_freq
        freq = pd.infer_freq(data.index)
        
        # 如果pandas无法推断，则手动计算
        if freq is None:
            # 计算时间差的中位数
            if len(data.index) > 1:
                diffs = np.diff(data.index.astype(np.int64)) / 10**9  # 转换为秒
                median_diff = np.median(diffs)
                
                # 根据中位数推断频率
                if median_diff < 1:  # 小于1秒
                    freq = f"{int(median_diff * 1000)}ms"
                elif median_diff < 60:  # 小于1分钟
                    freq = f"{int(median_diff)}s"
                elif median_diff < 3600:  # 小于1小时
                    freq = f"{int(median_diff / 60)}min"
                elif median_diff < 86400:  # 小于1天
                    freq = f"{int(median_diff / 3600)}h"
                else:  # 大于等于1天
                    freq = f"{int(median_diff / 86400)}d"
        
        return freq


class BaseReliabilityScorer(abc.ABC):
    """
    数据源可靠性评分基类
    定义数据源可靠性评分的基本接口
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据源可靠性评分基类
        
        参数:
            config: 配置字典，包含评分参数
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._validate_config()
        
        # 初始化评分历史
        self.score_history = {}
    
    def _validate_config(self) -> None:
        """
        验证配置是否合法
        子类可以重写此方法以添加特定的验证逻辑
        
        异常:
            ValueError: 配置不合法时抛出
        """
        if not isinstance(self.config, dict):
            raise ValueError("配置必须是字典类型")
    
    @abc.abstractmethod
    def score(self, data_source: str, data: pd.DataFrame, reference: Optional[pd.DataFrame] = None) -> float:
        """
        评估数据源的可靠性
        
        参数:
            data_source: 数据源名称
            data: 数据源数据
            reference: 参考数据，可选
            
        返回:
            可靠性评分，范围[0, 1]
        """
        pass
    
    def update_score_history(self, data_source: str, score: float) -> None:
        """
        更新评分历史
        
        参数:
            data_source: 数据源名称
            score: 评分
        """
        if data_source not in self.score_history:
            self.score_history[data_source] = []
        
        self.score_history[data_source].append({
            "timestamp": datetime.now(),
            "score": score
        })
        
        # 限制历史记录数量
        max_history = self.config.get("max_history", 100)
        if len(self.score_history[data_source]) > max_history:
            self.score_history[data_source] = self.score_history[data_source][-max_history:]
    
    def get_average_score(self, data_source: str, window: int = None) -> float:
        """
        获取数据源的平均评分
        
        参数:
            data_source: 数据源名称
            window: 窗口大小，如果为None则使用所有历史记录
            
        返回:
            平均评分
        """
        if data_source not in self.score_history or not self.score_history[data_source]:
            return 0.0
        
        history = self.score_history[data_source]
        if window is not None:
            history = history[-min(window, len(history)):]
        
        scores = [record["score"] for record in history]
        return sum(scores) / len(scores)
