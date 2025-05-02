"""
跨市场数据对齐工具
提供跨市场数据对齐、时区对齐和异步数据对齐功能
"""

import logging
import pytz
from typing import Dict, List, Union, Any, Tuple, Optional, Callable
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from .base import BaseDataAligner

# 配置日志
logger = logging.getLogger(__name__)

class CrossMarketDataAligner(BaseDataAligner):
    """
    跨市场数据对齐器
    处理不同市场的数据对齐问题，包括交易时间不同、交易日历不同等
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化跨市场数据对齐器
        
        参数:
            config: 配置字典，包含以下字段:
                - market_calendars: 市场日历字典，键为市场名称，值为交易日列表
                - market_hours: 市场交易时间字典，键为市场名称，值为交易时间范围
                - reference_market: 参考市场，用于对齐其他市场
                - alignment_method: 对齐方法，可选值为'inner'、'outer'、'forward'、'backward'
                - max_time_diff: 最大时间差，单位为秒
        """
        super().__init__(config)
        self.market_calendars = self.config.get("market_calendars", {})
        self.market_hours = self.config.get("market_hours", {})
        self.reference_market = self.config.get("reference_market")
        self.alignment_method = self.config.get("alignment_method", "inner")
        self.max_time_diff = self.config.get("max_time_diff", 300)  # 默认5分钟
    
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        super()._validate_config()
        
        # 检查对齐方法
        valid_methods = ["inner", "outer", "forward", "backward"]
        if self.config.get("alignment_method") not in valid_methods:
            raise ValueError(f"对齐方法必须是以下之一: {valid_methods}")
        
        # 检查参考市场
        if "reference_market" in self.config and self.config["reference_market"] not in self.config.get("market_calendars", {}):
            raise ValueError(f"参考市场 {self.config['reference_market']} 不在市场日历中")
    
    def align(self, data_sources: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        对齐多个数据源
        
        参数:
            data_sources: 数据源字典，键为数据源名称，值为数据源DataFrame
            
        返回:
            对齐后的数据源字典
        """
        if not data_sources:
            return {}
        
        # 提取市场信息
        market_info = {}
        for source_name, df in data_sources.items():
            # 从数据源名称中提取市场名称，假设格式为 "market_name.data_type"
            market_name = source_name.split(".")[0] if "." in source_name else source_name
            
            if market_name not in market_info:
                market_info[market_name] = {
                    "sources": [],
                    "data": []
                }
            
            market_info[market_name]["sources"].append(source_name)
            market_info[market_name]["data"].append(df)
        
        # 确定参考市场
        reference_market = self.reference_market
        if reference_market is None or reference_market not in market_info:
            # 如果未指定参考市场或参考市场不在数据中，则使用第一个市场作为参考
            reference_market = list(market_info.keys())[0]
            self.logger.warning(f"未指定参考市场或参考市场不在数据中，使用 {reference_market} 作为参考")
        
        # 获取参考时间戳
        reference_timestamps = self._get_reference_timestamps(
            market_info[reference_market]["data"],
            self.market_calendars.get(reference_market, []),
            self.market_hours.get(reference_market)
        )
        
        if not reference_timestamps:
            self.logger.warning("参考时间戳为空，无法对齐数据")
            return data_sources
        
        # 对齐每个市场的数据
        aligned_data = {}
        for market_name, info in market_info.items():
            for i, source_name in enumerate(info["sources"]):
                df = info["data"][i]
                
                if market_name == reference_market:
                    # 参考市场的数据只需要过滤到参考时间戳
                    aligned_df = df[df.index.isin(reference_timestamps)]
                else:
                    # 非参考市场需要进行时间对齐
                    aligned_df = self._align_to_reference(
                        df,
                        reference_timestamps,
                        self.market_calendars.get(market_name, []),
                        self.market_hours.get(market_name),
                        self.alignment_method
                    )
                
                aligned_data[source_name] = aligned_df
        
        return aligned_data
    
    def _get_reference_timestamps(self, dfs: List[pd.DataFrame], calendar: List[datetime], hours: Dict[str, List[str]]) -> List[datetime]:
        """
        获取参考时间戳
        
        参数:
            dfs: DataFrame列表
            calendar: 交易日历
            hours: 交易时间
            
        返回:
            参考时间戳列表
        """
        # 合并所有数据源的时间戳
        all_timestamps = []
        for df in dfs:
            if df.empty:
                continue
                
            # 确保索引是DatetimeIndex
            if not isinstance(df.index, pd.DatetimeIndex):
                try:
                    df.index = pd.DatetimeIndex(df.index)
                except Exception as e:
                    self.logger.error(f"无法将索引转换为DatetimeIndex: {e}")
                    continue
            
            all_timestamps.extend(df.index)
        
        if not all_timestamps:
            return []
        
        # 去重并排序
        unique_timestamps = sorted(set(all_timestamps))
        
        # 如果有交易日历，则过滤非交易日
        if calendar:
            trading_days = set(pd.DatetimeIndex(calendar).date)
            unique_timestamps = [ts for ts in unique_timestamps if ts.date() in trading_days]
        
        # 如果有交易时间，则过滤非交易时间
        if hours:
            # 交易时间格式为 {"weekday": [["start1", "end1"], ["start2", "end2"], ...]}
            # weekday 为 0-6，0 表示周一
            filtered_timestamps = []
            for ts in unique_timestamps:
                weekday = ts.weekday()
                if str(weekday) in hours:
                    # 检查是否在交易时间范围内
                    in_trading_hours = False
                    for start_end in hours[str(weekday)]:
                        start_time = datetime.strptime(start_end[0], "%H:%M").time()
                        end_time = datetime.strptime(start_end[1], "%H:%M").time()
                        if start_time <= ts.time() <= end_time:
                            in_trading_hours = True
                            break
                    
                    if in_trading_hours:
                        filtered_timestamps.append(ts)
            
            unique_timestamps = filtered_timestamps
        
        return unique_timestamps
    
    def _align_to_reference(self, df: pd.DataFrame, reference_timestamps: List[datetime], 
                           calendar: List[datetime], hours: Dict[str, List[str]], method: str) -> pd.DataFrame:
        """
        将数据对齐到参考时间戳
        
        参数:
            df: 输入数据
            reference_timestamps: 参考时间戳
            calendar: 交易日历
            hours: 交易时间
            method: 对齐方法
            
        返回:
            对齐后的数据
        """
        if df.empty:
            return df
        
        # 确保索引是DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            try:
                df.index = pd.DatetimeIndex(df.index)
            except Exception as e:
                self.logger.error(f"无法将索引转换为DatetimeIndex: {e}")
                return df
        
        # 根据对齐方法处理
        if method == "inner":
            # 内连接：只保留同时存在于参考时间戳和数据中的时间点
            return df[df.index.isin(reference_timestamps)]
        
        elif method == "outer":
            # 外连接：保留所有时间点，缺失值填充为NaN
            result = pd.DataFrame(index=reference_timestamps)
            result = result.join(df, how="left")
            return result
        
        elif method in ["forward", "backward"]:
            # 前向/后向填充：对于参考时间戳中的每个点，找到最近的数据点
            result = pd.DataFrame(index=reference_timestamps)
            
            # 对于每个参考时间戳，找到最近的数据点
            for ref_ts in reference_timestamps:
                # 计算时间差
                time_diffs = [(ts, abs((ref_ts - ts).total_seconds())) for ts in df.index]
                
                # 根据方法筛选时间差
                if method == "forward":
                    # 前向填充：只考虑早于或等于参考时间的数据点
                    valid_diffs = [(ts, diff) for ts, diff in time_diffs if ts <= ref_ts]
                else:  # backward
                    # 后向填充：只考虑晚于或等于参考时间的数据点
                    valid_diffs = [(ts, diff) for ts, diff in time_diffs if ts >= ref_ts]
                
                if valid_diffs:
                    # 找到时间差最小的数据点
                    nearest_ts, min_diff = min(valid_diffs, key=lambda x: x[1])
                    
                    # 如果时间差小于最大允许时间差，则使用该数据点
                    if min_diff <= self.max_time_diff:
                        result.loc[ref_ts] = df.loc[nearest_ts]
            
            return result
        
        else:
            self.logger.warning(f"未知的对齐方法: {method}，使用内连接")
            return df[df.index.isin(reference_timestamps)]


class TimeZoneAligner(BaseDataAligner):
    """
    时区对齐器
    处理不同时区的数据对齐问题
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化时区对齐器
        
        参数:
            config: 配置字典，包含以下字段:
                - source_timezones: 数据源时区字典，键为数据源名称，值为时区字符串
                - target_timezone: 目标时区
                - type: 可选，对齐器类型，用于DataFusionEngine中区分不同对齐器
        """
        # 在调用父类__init__之前先设置属性，避免_validate_config中的属性访问错误
        self.source_timezones = config.get("source_timezones", {})
        self.target_timezone = config.get("target_timezone", "UTC")
        
        # 调用父类__init__
        super().__init__(config)
    
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        super()._validate_config()
        
        # 检查目标时区
        try:
            pytz.timezone(self.target_timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"未知的目标时区: {self.target_timezone}")
        
        # 检查数据源时区
        for source, timezone in self.source_timezones.items():
            try:
                pytz.timezone(timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                raise ValueError(f"未知的数据源时区: {timezone} (数据源: {source})")
    
    def align(self, data_sources: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        对齐多个数据源的时区
        
        参数:
            data_sources: 数据源字典，键为数据源名称，值为数据源DataFrame
            
        返回:
            时区对齐后的数据源字典
        """
        if not data_sources:
            return {}
        
        # 获取目标时区
        target_tz = pytz.timezone(self.target_timezone)
        
        # 对齐每个数据源的时区
        aligned_data = {}
        for source_name, df in data_sources.items():
            if df.empty:
                aligned_data[source_name] = df
                continue
            
            # 确保索引是DatetimeIndex
            if not isinstance(df.index, pd.DatetimeIndex):
                try:
                    df.index = pd.DatetimeIndex(df.index)
                except Exception as e:
                    self.logger.error(f"无法将数据源 {source_name} 的索引转换为DatetimeIndex: {e}")
                    aligned_data[source_name] = df
                    continue
            
            # 获取数据源时区
            source_tz_str = self.source_timezones.get(source_name)
            if source_tz_str is None:
                # 如果未指定数据源时区，则检查索引是否已有时区信息
                if df.index.tz is not None:
                    source_tz = df.index.tz
                else:
                    # 如果索引没有时区信息，则假设为UTC
                    self.logger.warning(f"数据源 {source_name} 未指定时区且索引无时区信息，假设为UTC")
                    source_tz = pytz.UTC
            else:
                source_tz = pytz.timezone(source_tz_str)
            
            # 转换时区
            if df.index.tz is None:
                # 如果索引没有时区信息，则先本地化到源时区
                df.index = df.index.tz_localize(source_tz)
            
            # 转换到目标时区
            df.index = df.index.tz_convert(target_tz)
            
            aligned_data[source_name] = df
        
        return aligned_data


class AsynchronousDataAligner(BaseDataAligner):
    """
    异步数据对齐器
    处理不同数据源更新频率不同、延迟不同的问题
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化异步数据对齐器
        
        参数:
            config: 配置字典，包含以下字段:
                - time_field: 时间戳字段名，默认为索引
                - max_delay: 最大延迟，单位为秒，默认为60
                - interpolation_method: 插值方法，可选值为'linear'、'nearest'、'zero'、'slinear'、'quadratic'、'cubic'
                - window_size: 滑动窗口大小，用于计算数据源之间的延迟
        """
        super().__init__(config)
        self.time_field = self.config.get("time_field")
        self.max_delay = self.config.get("max_delay", 60)
        self.interpolation_method = self.config.get("interpolation_method", "linear")
        self.window_size = self.config.get("window_size", 100)
        
        # 存储数据源延迟信息
        self.source_delays = {}
    
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        super()._validate_config()
        
        # 检查插值方法
        valid_methods = ["linear", "nearest", "zero", "slinear", "quadratic", "cubic"]
        if self.interpolation_method not in valid_methods:
            raise ValueError(f"插值方法必须是以下之一: {valid_methods}")
    
    def align(self, data_sources: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        对齐异步数据源
        
        参数:
            data_sources: 数据源字典，键为数据源名称，值为数据源DataFrame
            
        返回:
            对齐后的数据源字典
        """
        if not data_sources:
            return {}
        
        # 估计数据源延迟
        self._estimate_delays(data_sources)
        
        # 获取所有时间戳
        all_timestamps = self._get_all_timestamps(data_sources)
        if not all_timestamps:
            return data_sources
        
        # 对齐每个数据源
        aligned_data = {}
        for source_name, df in data_sources.items():
            if df.empty:
                aligned_data[source_name] = df
                continue
            
            # 获取数据源延迟
            delay = self.source_delays.get(source_name, 0)
            
            # 调整时间戳以补偿延迟
            if delay > 0:
                # 创建新的DataFrame，索引为调整后的时间戳
                adjusted_df = df.copy()
                adjusted_df.index = adjusted_df.index - pd.Timedelta(seconds=delay)
                df = adjusted_df
            
            # 重采样到所有时间戳
            resampled_df = self._resample_to_timestamps(df, all_timestamps)
            
            aligned_data[source_name] = resampled_df
        
        return aligned_data
    
    def _estimate_delays(self, data_sources: Dict[str, pd.DataFrame]) -> None:
        """
        估计数据源之间的延迟
        
        参数:
            data_sources: 数据源字典
        """
        if len(data_sources) < 2:
            return
        
        # 选择参考数据源（假设第一个数据源为参考）
        reference_source = list(data_sources.keys())[0]
        reference_df = data_sources[reference_source]
        
        # 如果参考数据源为空，则无法估计延迟
        if reference_df.empty:
            return
        
        # 确保参考数据源的索引是DatetimeIndex
        if not isinstance(reference_df.index, pd.DatetimeIndex):
            try:
                reference_df.index = pd.DatetimeIndex(reference_df.index)
            except Exception as e:
                self.logger.error(f"无法将参考数据源的索引转换为DatetimeIndex: {e}")
                return
        
        # 对于每个数据源，计算与参考数据源的延迟
        for source_name, df in data_sources.items():
            if source_name == reference_source or df.empty:
                continue
            
            # 确保数据源的索引是DatetimeIndex
            if not isinstance(df.index, pd.DatetimeIndex):
                try:
                    df.index = pd.DatetimeIndex(df.index)
                except Exception as e:
                    self.logger.error(f"无法将数据源 {source_name} 的索引转换为DatetimeIndex: {e}")
                    continue
            
            # 找到共同的列，用于比较
            common_columns = set(reference_df.columns) & set(df.columns)
            if not common_columns:
                self.logger.warning(f"数据源 {source_name} 与参考数据源没有共同的列，无法估计延迟")
                continue
            
            # 选择第一个共同列进行比较
            column = list(common_columns)[0]
            
            # 计算互相关，找到最大相关性对应的延迟
            try:
                # 重采样到相同的频率
                freq = pd.infer_freq(reference_df.index)
                if freq is None:
                    # 如果无法推断频率，则使用最小时间间隔作为频率
                    min_diff = min(np.diff(reference_df.index.astype(np.int64))) / 10**9  # 转换为秒
                    freq = f"{int(min_diff)}s"
                
                # 重采样
                ref_resampled = reference_df[column].resample(freq).mean()
                df_resampled = df[column].resample(freq).mean()
                
                # 计算互相关
                ref_values = ref_resampled.values
                df_values = df_resampled.values
                
                # 使用滑动窗口计算延迟
                max_lag = min(self.window_size, len(ref_values) // 2)
                correlations = []
                
                for lag in range(-max_lag, max_lag + 1):
                    if lag < 0:
                        corr = np.corrcoef(ref_values[:lag], df_values[-lag:])[0, 1]
                    elif lag > 0:
                        corr = np.corrcoef(ref_values[lag:], df_values[:-lag])[0, 1]
                    else:
                        corr = np.corrcoef(ref_values, df_values)[0, 1]
                    
                    correlations.append((lag, corr))
                
                # 找到最大相关性对应的延迟
                max_corr_lag, max_corr = max(correlations, key=lambda x: x[1])
                
                # 计算延迟（秒）
                delay = max_corr_lag * pd.Timedelta(freq).total_seconds()
                
                # 如果延迟超过最大允许延迟，则截断
                if abs(delay) > self.max_delay:
                    delay = self.max_delay if delay > 0 else -self.max_delay
                
                # 更新数据源延迟
                self.source_delays[source_name] = delay
                self.logger.info(f"估计数据源 {source_name} 相对于 {reference_source} 的延迟为 {delay} 秒")
            
            except Exception as e:
                self.logger.error(f"估计数据源 {source_name} 的延迟时出错: {e}")
    
    def _get_all_timestamps(self, data_sources: Dict[str, pd.DataFrame]) -> List[datetime]:
        """
        获取所有数据源的时间戳并合并
        
        参数:
            data_sources: 数据源字典
            
        返回:
            合并后的时间戳列表
        """
        all_timestamps = []
        
        for source_name, df in data_sources.items():
            if df.empty:
                continue
            
            # 确保索引是DatetimeIndex
            if not isinstance(df.index, pd.DatetimeIndex):
                try:
                    df.index = pd.DatetimeIndex(df.index)
                except Exception as e:
                    self.logger.error(f"无法将数据源 {source_name} 的索引转换为DatetimeIndex: {e}")
                    continue
            
            # 添加时间戳
            all_timestamps.extend(df.index)
        
        # 去重并排序
        return sorted(set(all_timestamps))
    
    def _resample_to_timestamps(self, df: pd.DataFrame, timestamps: List[datetime]) -> pd.DataFrame:
        """
        将数据重采样到指定的时间戳
        
        参数:
            df: 输入数据
            timestamps: 目标时间戳列表
            
        返回:
            重采样后的数据
        """
        if df.empty or not timestamps:
            return df
        
        # 创建新的DataFrame，索引为目标时间戳
        result = pd.DataFrame(index=timestamps)
        
        # 对每列进行插值
        for column in df.columns:
            # 如果列是数值类型，则使用插值
            if np.issubdtype(df[column].dtype, np.number):
                # 创建插值函数
                f = lambda x: np.interp(
                    x,
                    df.index.astype(np.int64) // 10**9,  # 转换为秒
                    df[column].values,
                    left=np.nan,
                    right=np.nan
                )
                
                # 应用插值函数
                result[column] = f(np.array([ts.timestamp() for ts in timestamps]))
            else:
                # 非数值类型使用前向填充
                result[column] = pd.Series(df[column].values, index=df.index).reindex(
                    timestamps, method="ffill"
                )
        
        return result
