"""
多频率数据重采样功能
提供上采样、下采样和自适应重采样功能
"""

import logging
import warnings
from typing import Dict, List, Union, Any, Tuple, Optional, Callable
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from statsmodels.tsa.stattools import acf
from scipy import signal, stats

from .base import BaseDataResampler

# 配置日志
logger = logging.getLogger(__name__)

# 忽略特定警告
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

class MultiFrequencyResampler(BaseDataResampler):
    """
    多频率数据重采样器
    支持不同频率数据的重采样，包括上采样和下采样
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化多频率数据重采样器
        
        参数:
            config: 配置字典，包含以下字段:
                - target_freq: 目标频率，如'1min', '5min', '1h', '1d'等
                - method: 重采样方法，可选值为'auto', 'upsample', 'downsample'
                - aggregation: 下采样聚合方法，可选值为'mean', 'median', 'sum', 'min', 'max', 'first', 'last'
                - interpolation: 上采样插值方法，可选值为'linear', 'time', 'index', 'values', 'nearest', 'zero', 'slinear', 'quadratic', 'cubic', 'barycentric', 'polynomial'
                - columns: 要处理的列，如果为空则处理所有列
        """
        # 在调用父类__init__之前先设置属性，避免_validate_config中的属性访问错误
        self.method = config.get("method", "auto")
        self.aggregation = config.get("aggregation", "mean")
        self.interpolation = config.get("interpolation", "linear")
        self.columns = config.get("columns", [])
        
        # 调用父类__init__
        super().__init__(config)
    
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        super()._validate_config()
        
        # 检查重采样方法
        valid_methods = ["auto", "upsample", "downsample"]
        if self.method not in valid_methods:
            raise ValueError(f"重采样方法必须是以下之一: {valid_methods}")
        
        # 检查聚合方法
        valid_aggregations = ["mean", "median", "sum", "min", "max", "first", "last"]
        if self.aggregation not in valid_aggregations:
            raise ValueError(f"聚合方法必须是以下之一: {valid_aggregations}")
        
        # 检查插值方法
        valid_interpolations = ["linear", "time", "index", "values", "nearest", "zero", 
                               "slinear", "quadratic", "cubic", "barycentric", "polynomial"]
        if self.interpolation not in valid_interpolations:
            raise ValueError(f"插值方法必须是以下之一: {valid_interpolations}")
    
    def resample(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        重采样数据
        
        参数:
            data: 输入数据
            
        返回:
            重采样后的数据
        """
        if data.empty:
            return data
        
        # 确保索引是DatetimeIndex
        if not isinstance(data.index, pd.DatetimeIndex):
            try:
                data.index = pd.DatetimeIndex(data.index)
            except Exception as e:
                self.logger.error(f"无法将索引转换为DatetimeIndex: {e}")
                return data
        
        # 推断数据频率
        source_freq = self.infer_data_freq(data)
        if source_freq is None:
            self.logger.warning("无法推断数据频率，将使用目标频率进行重采样")
            source_freq = self.get_target_freq()
        
        # 确定重采样方法
        method = self.method
        if method == "auto":
            # 自动确定是上采样还是下采样
            source_seconds = self._freq_to_seconds(source_freq)
            target_seconds = self._freq_to_seconds(self.get_target_freq())
            
            if source_seconds is None or target_seconds is None:
                self.logger.warning("无法自动确定重采样方法，将使用下采样")
                method = "downsample"
            elif source_seconds > target_seconds:
                # 源频率大于目标频率，需要上采样（增加数据点）
                method = "upsample"
            else:
                # 源频率小于等于目标频率，需要下采样（减少数据点）
                method = "downsample"
        
        # 选择要处理的列
        columns = self.columns if self.columns else data.columns
        
        # 根据方法进行重采样
        if method == "upsample":
            return self._upsample(data, columns)
        else:  # downsample
            return self._downsample(data, columns)
    
    def _upsample(self, data: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """
        上采样数据（增加数据点）
        
        参数:
            data: 输入数据
            columns: 要处理的列
            
        返回:
            上采样后的数据
        """
        # 创建新的索引
        start = data.index.min()
        end = data.index.max()
        new_index = pd.date_range(start=start, end=end, freq=self.get_target_freq())
        
        # 如果新索引与原索引相同，则无需重采样
        if len(new_index) == len(data.index) and all(new_index == data.index):
            return data
        
        # 创建结果DataFrame
        result = pd.DataFrame(index=new_index)
        
        # 对每列进行插值
        for col in columns:
            if col not in data.columns:
                continue
                
            # 如果列是数值类型，则使用插值
            if np.issubdtype(data[col].dtype, np.number):
                # 重采样并插值
                s = data[col].reindex(new_index)
                
                # 使用指定的插值方法
                if self.interpolation == "polynomial":
                    # 多项式插值需要额外的参数
                    s = s.interpolate(method=self.interpolation, order=3)
                else:
                    s = s.interpolate(method=self.interpolation)
                
                result[col] = s
            else:
                # 非数值类型使用前向填充
                result[col] = data[col].reindex(new_index).ffill()
        
        # 复制其他列
        for col in data.columns:
            if col not in columns and col not in result.columns:
                result[col] = data[col].reindex(new_index).ffill()
        
        return result
    
    def _downsample(self, data: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """
        下采样数据（减少数据点）
        
        参数:
            data: 输入数据
            columns: 要处理的列
            
        返回:
            下采样后的数据
        """
        # 创建重采样器
        resampler = data.resample(self.get_target_freq())
        
        # 根据聚合方法进行重采样
        if self.aggregation == "mean":
            result = resampler.mean()
        elif self.aggregation == "median":
            result = resampler.median()
        elif self.aggregation == "sum":
            result = resampler.sum()
        elif self.aggregation == "min":
            result = resampler.min()
        elif self.aggregation == "max":
            result = resampler.max()
        elif self.aggregation == "first":
            result = resampler.first()
        elif self.aggregation == "last":
            result = resampler.last()
        else:
            self.logger.warning(f"未知的聚合方法: {self.aggregation}，使用mean")
            result = resampler.mean()
        
        # 对于非数值列，使用first或last
        for col in data.columns:
            if col not in result.columns:
                if self.aggregation in ["first", "last"]:
                    # 已经使用first或last，无需额外处理
                    continue
                
                # 使用first方法处理非数值列
                result[col] = data[col].resample(self.get_target_freq()).first()
        
        return result
    
    def _freq_to_seconds(self, freq: str) -> Optional[float]:
        """
        将频率字符串转换为秒数
        
        参数:
            freq: 频率字符串
            
        返回:
            秒数，如果无法转换则返回None
        """
        if not freq:
            return None
        
        # 提取数字和单位
        import re
        match = re.match(r"(\d+)([a-zA-Z]+)", freq)
        if not match:
            return None
        
        value = int(match.group(1))
        unit = match.group(2).lower()
        
        # 转换为秒
        if unit in ["ms", "milli", "millisecond", "milliseconds"]:
            return value / 1000
        elif unit in ["s", "sec", "second", "seconds"]:
            return value
        elif unit in ["min", "minute", "minutes", "t"]:
            return value * 60
        elif unit in ["h", "hour", "hours"]:
            return value * 3600
        elif unit in ["d", "day", "days"]:
            return value * 86400
        elif unit in ["w", "week", "weeks"]:
            return value * 604800
        elif unit in ["m", "month", "months"]:
            return value * 2592000  # 假设一个月为30天
        elif unit in ["y", "year", "years", "a"]:
            return value * 31536000  # 假设一年为365天
        else:
            return None


class UpSampler(MultiFrequencyResampler):
    """
    上采样器
    专门用于上采样（增加数据点）
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化上采样器
        
        参数:
            config: 配置字典
        """
        # 强制使用上采样方法
        config["method"] = "upsample"
        super().__init__(config)


class DownSampler(MultiFrequencyResampler):
    """
    下采样器
    专门用于下采样（减少数据点）
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化下采样器
        
        参数:
            config: 配置字典
        """
        # 强制使用下采样方法
        config["method"] = "downsample"
        super().__init__(config)


class AdaptiveResampler(BaseDataResampler):
    """
    自适应重采样器
    根据数据特性自动选择最佳重采样频率和方法
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化自适应重采样器
        
        参数:
            config: 配置字典，包含以下字段:
                - target_freq: 目标频率，如果为None则自动确定
                - min_freq: 最小频率，自动确定频率时的下限
                - max_freq: 最大频率，自动确定频率时的上限
                - method: 重采样方法，可选值为'auto', 'nyquist', 'acf', 'entropy'
                - columns: 要处理的列，如果为空则处理所有列
        """
        super().__init__(config)
        self.min_freq = self.config.get("min_freq")
        self.max_freq = self.config.get("max_freq")
        self.method = self.config.get("method", "auto")
        self.columns = self.config.get("columns", [])
        
        # 如果未指定目标频率，则在重采样时自动确定
        self.auto_determine = "target_freq" not in self.config
    
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        # 不调用父类的验证，因为可能没有target_freq
        if not isinstance(self.config, dict):
            raise ValueError("配置必须是字典类型")
        
        # 检查重采样方法
        valid_methods = ["auto", "nyquist", "acf", "entropy"]
        if self.method not in valid_methods:
            raise ValueError(f"重采样方法必须是以下之一: {valid_methods}")
    
    def resample(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        自适应重采样数据
        
        参数:
            data: 输入数据
            
        返回:
            重采样后的数据
        """
        if data.empty:
            return data
        
        # 确保索引是DatetimeIndex
        if not isinstance(data.index, pd.DatetimeIndex):
            try:
                data.index = pd.DatetimeIndex(data.index)
            except Exception as e:
                self.logger.error(f"无法将索引转换为DatetimeIndex: {e}")
                return data
        
        # 如果需要自动确定目标频率
        if self.auto_determine:
            target_freq = self._determine_optimal_frequency(data)
            self.config["target_freq"] = target_freq
            self.logger.info(f"自动确定的最佳重采样频率: {target_freq}")
        
        # 创建多频率重采样器进行重采样
        resampler = MultiFrequencyResampler(self.config)
        return resampler.resample(data)
    
    def _determine_optimal_frequency(self, data: pd.DataFrame) -> str:
        """
        确定最佳重采样频率
        
        参数:
            data: 输入数据
            
        返回:
            最佳频率字符串
        """
        # 选择要处理的列
        columns = self.columns if self.columns else data.columns
        
        # 只考虑数值列
        numeric_columns = [col for col in columns if col in data.columns and np.issubdtype(data[col].dtype, np.number)]
        if not numeric_columns:
            self.logger.warning("没有数值列可用于确定最佳频率，将使用默认频率")
            return "1min"  # 默认频率
        
        # 根据方法确定最佳频率
        if self.method == "nyquist":
            return self._nyquist_frequency(data, numeric_columns)
        elif self.method == "acf":
            return self._acf_frequency(data, numeric_columns)
        elif self.method == "entropy":
            return self._entropy_frequency(data, numeric_columns)
        else:  # auto
            # 尝试多种方法，选择最佳结果
            freqs = [
                self._nyquist_frequency(data, numeric_columns),
                self._acf_frequency(data, numeric_columns),
                self._entropy_frequency(data, numeric_columns)
            ]
            
            # 转换为秒数进行比较
            freq_seconds = [self._freq_to_seconds(freq) for freq in freqs if freq is not None]
            if not freq_seconds:
                return "1min"  # 默认频率
            
            # 取中位数作为最佳频率
            median_seconds = np.median(freq_seconds)
            
            # 转换回频率字符串
            return self._seconds_to_freq(median_seconds)
    
    def _nyquist_frequency(self, data: pd.DataFrame, columns: List[str]) -> str:
        """
        使用奈奎斯特采样定理确定最佳频率
        
        参数:
            data: 输入数据
            columns: 要处理的列
            
        返回:
            最佳频率字符串
        """
        # 计算每列的频谱
        max_freqs = []
        
        for col in columns:
            try:
                # 去除NaN值
                values = data[col].dropna().values
                if len(values) < 10:  # 需要足够的数据点
                    continue
                
                # 计算功率谱密度
                f, psd = signal.welch(values, fs=1.0, nperseg=min(256, len(values)))
                
                # 找到能量90%的频率
                cumsum = np.cumsum(psd)
                cutoff_idx = np.where(cumsum >= 0.9 * cumsum[-1])[0][0]
                max_freq = f[cutoff_idx]
                
                # 奈奎斯特采样定理：采样频率应至少为最高频率的2倍
                nyquist_freq = 2 * max_freq
                max_freqs.append(nyquist_freq)
            
            except Exception as e:
                self.logger.warning(f"计算列 {col} 的奈奎斯特频率时出错: {e}")
        
        if not max_freqs:
            return None
        
        # 取中位数作为最佳频率
        median_freq = np.median(max_freqs)
        
        # 应用最小/最大频率限制
        if self.min_freq:
            min_freq_seconds = self._freq_to_seconds(self.min_freq)
            if min_freq_seconds and 1/median_freq < min_freq_seconds:
                median_freq = 1/min_freq_seconds
        
        if self.max_freq:
            max_freq_seconds = self._freq_to_seconds(self.max_freq)
            if max_freq_seconds and 1/median_freq > max_freq_seconds:
                median_freq = 1/max_freq_seconds
        
        # 转换为频率字符串
        return self._seconds_to_freq(1/median_freq)
    
    def _acf_frequency(self, data: pd.DataFrame, columns: List[str]) -> str:
        """
        使用自相关函数确定最佳频率
        
        参数:
            data: 输入数据
            columns: 要处理的列
            
        返回:
            最佳频率字符串
        """
        # 计算每列的自相关函数
        acf_lags = []
        
        for col in columns:
            try:
                # 去除NaN值
                values = data[col].dropna().values
                if len(values) < 10:  # 需要足够的数据点
                    continue
                
                # 计算自相关函数
                acf_values = acf(values, nlags=min(40, len(values)//2), fft=True)
                
                # 找到第一个局部最小值
                for i in range(1, len(acf_values)-1):
                    if acf_values[i] < acf_values[i-1] and acf_values[i] < acf_values[i+1]:
                        acf_lags.append(i)
                        break
            
            except Exception as e:
                self.logger.warning(f"计算列 {col} 的自相关函数时出错: {e}")
        
        if not acf_lags:
            return None
        
        # 计算原始数据的平均时间间隔
        time_diffs = np.diff(data.index.astype(np.int64)) / 10**9  # 转换为秒
        avg_interval = np.mean(time_diffs)
        
        # 取中位数作为最佳滞后
        median_lag = np.median(acf_lags)
        
        # 计算最佳频率
        best_interval = avg_interval * median_lag
        
        # 应用最小/最大频率限制
        if self.min_freq:
            min_freq_seconds = self._freq_to_seconds(self.min_freq)
            if min_freq_seconds and best_interval < min_freq_seconds:
                best_interval = min_freq_seconds
        
        if self.max_freq:
            max_freq_seconds = self._freq_to_seconds(self.max_freq)
            if max_freq_seconds and best_interval > max_freq_seconds:
                best_interval = max_freq_seconds
        
        # 转换为频率字符串
        return self._seconds_to_freq(best_interval)
    
    def _entropy_frequency(self, data: pd.DataFrame, columns: List[str]) -> str:
        """
        使用信息熵确定最佳频率
        
        参数:
            data: 输入数据
            columns: 要处理的列
            
        返回:
            最佳频率字符串
        """
        # 计算原始数据的平均时间间隔
        time_diffs = np.diff(data.index.astype(np.int64)) / 10**9  # 转换为秒
        avg_interval = np.mean(time_diffs)
        
        # 尝试不同的重采样频率
        test_intervals = [
            avg_interval / 4,
            avg_interval / 2,
            avg_interval,
            avg_interval * 2,
            avg_interval * 4
        ]
        
        # 计算每个频率的信息熵
        entropy_results = []
        
        for interval in test_intervals:
            try:
                # 创建重采样频率
                freq = self._seconds_to_freq(interval)
                
                # 重采样数据
                resampled = data[columns].resample(freq).mean()
                
                # 计算信息熵
                entropy = 0
                for col in columns:
                    if col in resampled.columns:
                        # 去除NaN值
                        values = resampled[col].dropna().values
                        if len(values) < 10:  # 需要足够的数据点
                            continue
                        
                        # 计算直方图
                        hist, _ = np.histogram(values, bins=min(20, len(values)//5), density=True)
                        
                        # 计算信息熵
                        hist = hist[hist > 0]  # 去除零概率
                        col_entropy = -np.sum(hist * np.log2(hist))
                        entropy += col_entropy
                
                entropy_results.append((interval, entropy))
            
            except Exception as e:
                self.logger.warning(f"计算重采样频率 {freq} 的信息熵时出错: {e}")
        
        if not entropy_results:
            return None
        
        # 找到信息熵最大的频率
        best_interval = max(entropy_results, key=lambda x: x[1])[0]
        
        # 应用最小/最大频率限制
        if self.min_freq:
            min_freq_seconds = self._freq_to_seconds(self.min_freq)
            if min_freq_seconds and best_interval < min_freq_seconds:
                best_interval = min_freq_seconds
        
        if self.max_freq:
            max_freq_seconds = self._freq_to_seconds(self.max_freq)
            if max_freq_seconds and best_interval > max_freq_seconds:
                best_interval = max_freq_seconds
        
        # 转换为频率字符串
        return self._seconds_to_freq(best_interval)
    
    def _freq_to_seconds(self, freq: Union[str, float]) -> Optional[float]:
        """
        将频率字符串或秒数转换为秒数
        
        参数:
            freq: 频率字符串或秒数
            
        返回:
            秒数，如果无法转换则返回None
        """
        if isinstance(freq, (int, float)):
            return float(freq)
        
        # 使用MultiFrequencyResampler的方法
        resampler = MultiFrequencyResampler({"target_freq": "1min"})
        return resampler._freq_to_seconds(freq)
    
    def _seconds_to_freq(self, seconds: float) -> str:
        """
        将秒数转换为频率字符串
        
        参数:
            seconds: 秒数
            
        返回:
            频率字符串
        """
        if seconds < 1:
            # 毫秒级
            return f"{int(seconds * 1000)}ms"
        elif seconds < 60:
            # 秒级
            return f"{int(seconds)}s"
        elif seconds < 3600:
            # 分钟级
            return f"{int(seconds / 60)}min"
        elif seconds < 86400:
            # 小时级
            return f"{int(seconds / 3600)}h"
        else:
            # 天级
            return f"{int(seconds / 86400)}d"
