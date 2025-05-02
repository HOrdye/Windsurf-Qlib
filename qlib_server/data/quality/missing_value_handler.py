"""
数据缺失值处理器实现
包含基本填充方法、高级插值方法、时序特定方法和多模态协同填充
"""
from typing import Dict, List, Union, Optional, Any, Tuple
import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime
import warnings

from .base import BaseMissingValueHandler

# 配置日志
logger = logging.getLogger(__name__)


class BasicMissingValueHandler(BaseMissingValueHandler):
    """
    基本缺失值处理器
    实现常见的缺失值填充方法
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化基本缺失值处理器
        
        参数:
            config: 配置字典，包含以下字段:
                - method: 填充方法，支持'ffill'、'bfill'、'mean'、'median'、'mode'、'constant'
                - value: 填充值，用于constant方法
                - columns: 要处理的列，如果为空则处理所有数值列
                - group_col: 分组列名，默认为'instrument'
        """
        super().__init__(config)
        self.value = config.get("value", 0)
        self.columns = config.get("columns", [])
        self.group_col = config.get("group_col", "instrument")
    
    def fill(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        填充数据缺失值
        
        参数:
            data: 待处理的数据框
            
        返回:
            处理后的数据框
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError("数据必须是pandas DataFrame类型")
        
        # 复制数据，避免修改原始数据
        result = data.copy()
        
        # 选择要处理的列
        if self.columns:
            # 确保所有指定的列都存在
            missing_cols = set(self.columns) - set(result.columns)
            if missing_cols:
                self.logger.warning(f"以下列不存在: {missing_cols}")
            
            # 筛选存在的列
            cols = [col for col in self.columns if col in result.columns]
        else:
            # 选择所有数值列
            cols = result.select_dtypes(include=np.number).columns.tolist()
        
        if not cols:
            self.logger.warning("没有可处理的数值列")
            return result
        
        # 按分组处理
        if self.group_col in result.columns:
            groups = result[self.group_col].unique()
            for group in groups:
                group_mask = result[self.group_col] == group
                for col in cols:
                    result.loc[group_mask, col] = self._fill_column(result.loc[group_mask, col])
        else:
            # 不分组处理
            for col in cols:
                result[col] = self._fill_column(result[col])
        
        return result
    
    def _fill_column(self, series: pd.Series) -> pd.Series:
        """
        填充单列的缺失值
        
        参数:
            series: 待处理的列
            
        返回:
            处理后的列
        """
        method = self.config["method"]
        
        if method == "ffill":
            # 前向填充
            return series.fillna(method="ffill")
        
        elif method == "bfill":
            # 后向填充
            return series.fillna(method="bfill")
        
        elif method == "mean":
            # 均值填充
            return series.fillna(series.mean())
        
        elif method == "median":
            # 中位数填充
            return series.fillna(series.median())
        
        elif method == "mode":
            # 众数填充
            mode_value = series.mode()
            if len(mode_value) > 0:
                return series.fillna(mode_value[0])
            else:
                return series
        
        elif method == "constant":
            # 常数填充
            return series.fillna(self.value)
        
        else:
            self.logger.warning(f"不支持的填充方法: {method}，使用前向填充")
            return series.fillna(method="ffill")


class InterpolationMissingValueHandler(BaseMissingValueHandler):
    """
    插值缺失值处理器
    实现高级插值方法
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化插值缺失值处理器
        
        参数:
            config: 配置字典，包含以下字段:
                - method: 插值方法，支持'linear'、'spline'、'polynomial'、'nearest'
                - order: 插值阶数，用于spline和polynomial方法
                - columns: 要处理的列，如果为空则处理所有数值列
                - group_col: 分组列名，默认为'instrument'
                - time_col: 时间列名，默认为'datetime'
        """
        super().__init__(config)
        self.order = config.get("order", 3)
        self.columns = config.get("columns", [])
        self.group_col = config.get("group_col", "instrument")
        self.time_col = config.get("time_col", "datetime")
    
    def fill(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        填充数据缺失值
        
        参数:
            data: 待处理的数据框
            
        返回:
            处理后的数据框
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError("数据必须是pandas DataFrame类型")
        
        # 复制数据，避免修改原始数据
        result = data.copy()
        
        # 选择要处理的列
        if self.columns:
            # 确保所有指定的列都存在
            missing_cols = set(self.columns) - set(result.columns)
            if missing_cols:
                self.logger.warning(f"以下列不存在: {missing_cols}")
            
            # 筛选存在的列
            cols = [col for col in self.columns if col in result.columns]
        else:
            # 选择所有数值列
            cols = result.select_dtypes(include=np.number).columns.tolist()
            
            # 排除时间列
            if self.time_col in cols:
                cols.remove(self.time_col)
        
        if not cols:
            self.logger.warning("没有可处理的数值列")
            return result
        
        # 确保时间列存在
        time_col_in_index = False
        if self.time_col not in result.columns:
            if isinstance(result.index, pd.MultiIndex) and self.time_col in result.index.names:
                time_col_in_index = True
            elif isinstance(result.index, pd.DatetimeIndex):
                # 如果索引是DatetimeIndex，则重置索引
                result = result.reset_index()
                self.time_col = "index"
            else:
                self.logger.warning(f"时间列 {self.time_col} 不存在，无法进行基于时间的插值")
                return result
        
        # 按分组处理
        if self.group_col in result.columns:
            groups = result[self.group_col].unique()
            for group in groups:
                group_mask = result[self.group_col] == group
                group_data = result.loc[group_mask].copy()
                
                # 确保时间排序
                if not time_col_in_index:
                    group_data = group_data.sort_values(by=self.time_col)
                
                # 对每一列进行插值
                for col in cols:
                    if group_data[col].isna().any():
                        group_data[col] = self._interpolate_column(group_data[col], group_data[self.time_col] if not time_col_in_index else None)
                
                # 更新结果
                result.loc[group_mask, cols] = group_data[cols]
        else:
            # 不分组处理
            # 确保时间排序
            if not time_col_in_index:
                result = result.sort_values(by=self.time_col)
            
            # 对每一列进行插值
            for col in cols:
                if result[col].isna().any():
                    result[col] = self._interpolate_column(result[col], result[self.time_col] if not time_col_in_index else None)
        
        return result
    
    def _interpolate_column(self, series: pd.Series, time_series: Optional[pd.Series] = None) -> pd.Series:
        """
        插值单列的缺失值
        
        参数:
            series: 待处理的列
            time_series: 时间列，可选
            
        返回:
            处理后的列
        """
        method = self.config["method"]
        
        # 如果没有缺失值，直接返回
        if not series.isna().any():
            return series
        
        # 如果全是缺失值，无法插值
        if series.isna().all():
            self.logger.warning("列全是缺失值，无法插值")
            return series
        
        # 处理边界缺失值
        # 前向填充第一个非缺失值之前的缺失值
        first_valid_idx = series.first_valid_index()
        if first_valid_idx is not None and series.index[0] != first_valid_idx:
            mask = series.index < first_valid_idx
            series.loc[mask] = series.loc[first_valid_idx]
        
        # 后向填充最后一个非缺失值之后的缺失值
        last_valid_idx = series.last_valid_index()
        if last_valid_idx is not None and series.index[-1] != last_valid_idx:
            mask = series.index > last_valid_idx
            series.loc[mask] = series.loc[last_valid_idx]
        
        if method == "linear":
            # 线性插值
            return series.interpolate(method="linear")
        
        elif method == "spline":
            # 样条插值
            try:
                return series.interpolate(method="spline", order=self.order)
            except Exception as e:
                self.logger.warning(f"样条插值失败: {e}，使用线性插值")
                return series.interpolate(method="linear")
        
        elif method == "polynomial":
            # 多项式插值
            try:
                return series.interpolate(method="polynomial", order=self.order)
            except Exception as e:
                self.logger.warning(f"多项式插值失败: {e}，使用线性插值")
                return series.interpolate(method="linear")
        
        elif method == "nearest":
            # 最近邻插值
            return series.interpolate(method="nearest")
        
        else:
            self.logger.warning(f"不支持的插值方法: {method}，使用线性插值")
            return series.interpolate(method="linear")


class TimeSeriesMissingValueHandler(BaseMissingValueHandler):
    """
    时序缺失值处理器
    实现时间序列特定的缺失值处理方法
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化时序缺失值处理器
        
        参数:
            config: 配置字典，包含以下字段:
                - method: 处理方法，支持'seasonal'、'arima'、'kalman'、'prophet'
                - columns: 要处理的列，如果为空则处理所有数值列
                - group_col: 分组列名，默认为'instrument'
                - time_col: 时间列名，默认为'datetime'
                - seasonal_period: 季节性周期，用于seasonal方法
        """
        super().__init__(config)
        self.columns = config.get("columns", [])
        self.group_col = config.get("group_col", "instrument")
        self.time_col = config.get("time_col", "datetime")
        self.seasonal_period = config.get("seasonal_period", 5)
        
        # 检查是否有可选依赖
        if self.config["method"] == "arima":
            try:
                import statsmodels.api as sm
                self.statsmodels_available = True
            except ImportError:
                self.statsmodels_available = False
                warnings.warn("statsmodels未安装，无法使用ARIMA方法")
                self.config["method"] = "seasonal"  # 降级到seasonal方法
        
        if self.config["method"] == "kalman":
            try:
                from pykalman import KalmanFilter
                self.pykalman_available = True
            except ImportError:
                self.pykalman_available = False
                warnings.warn("pykalman未安装，无法使用Kalman滤波方法")
                self.config["method"] = "seasonal"  # 降级到seasonal方法
        
        if self.config["method"] == "prophet":
            try:
                from prophet import Prophet
                self.prophet_available = True
            except ImportError:
                self.prophet_available = False
                warnings.warn("prophet未安装，无法使用Prophet方法")
                self.config["method"] = "seasonal"  # 降级到seasonal方法
    
    def fill(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        填充数据缺失值
        
        参数:
            data: 待处理的数据框
            
        返回:
            处理后的数据框
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError("数据必须是pandas DataFrame类型")
        
        # 复制数据，避免修改原始数据
        result = data.copy()
        
        # 选择要处理的列
        if self.columns:
            # 确保所有指定的列都存在
            missing_cols = set(self.columns) - set(result.columns)
            if missing_cols:
                self.logger.warning(f"以下列不存在: {missing_cols}")
            
            # 筛选存在的列
            cols = [col for col in self.columns if col in result.columns]
        else:
            # 选择所有数值列
            cols = result.select_dtypes(include=np.number).columns.tolist()
            
            # 排除时间列
            if self.time_col in cols:
                cols.remove(self.time_col)
        
        if not cols:
            self.logger.warning("没有可处理的数值列")
            return result
        
        # 确保时间列存在
        time_col_in_index = False
        if self.time_col not in result.columns:
            if isinstance(result.index, pd.MultiIndex) and self.time_col in result.index.names:
                time_col_in_index = True
            elif isinstance(result.index, pd.DatetimeIndex):
                # 如果索引是DatetimeIndex，则重置索引
                result = result.reset_index()
                self.time_col = "index"
            else:
                self.logger.warning(f"时间列 {self.time_col} 不存在，无法进行基于时间的处理")
                return result
        
        # 按分组处理
        if self.group_col in result.columns:
            groups = result[self.group_col].unique()
            for group in groups:
                group_mask = result[self.group_col] == group
                group_data = result.loc[group_mask].copy()
                
                # 确保时间排序
                if not time_col_in_index:
                    group_data = group_data.sort_values(by=self.time_col)
                
                # 对每一列进行处理
                for col in cols:
                    if group_data[col].isna().any():
                        group_data[col] = self._fill_column_time_series(
                            group_data[col],
                            group_data[self.time_col] if not time_col_in_index else None
                        )
                
                # 更新结果
                result.loc[group_mask, cols] = group_data[cols]
        else:
            # 不分组处理
            # 确保时间排序
            if not time_col_in_index:
                result = result.sort_values(by=self.time_col)
            
            # 对每一列进行处理
            for col in cols:
                if result[col].isna().any():
                    result[col] = self._fill_column_time_series(
                        result[col],
                        result[self.time_col] if not time_col_in_index else None
                    )
        
        return result
    
    def _fill_column_time_series(self, series: pd.Series, time_series: Optional[pd.Series] = None) -> pd.Series:
        """
        填充单列的时间序列缺失值
        
        参数:
            series: 待处理的列
            time_series: 时间列，可选
            
        返回:
            处理后的列
        """
        method = self.config["method"]
        
        # 如果没有缺失值，直接返回
        if not series.isna().any():
            return series
        
        # 如果全是缺失值，无法处理
        if series.isna().all():
            self.logger.warning("列全是缺失值，无法处理")
            return series
        
        # 处理边界缺失值
        # 前向填充第一个非缺失值之前的缺失值
        first_valid_idx = series.first_valid_index()
        if first_valid_idx is not None and series.index[0] != first_valid_idx:
            mask = series.index < first_valid_idx
            series.loc[mask] = series.loc[first_valid_idx]
        
        # 后向填充最后一个非缺失值之后的缺失值
        last_valid_idx = series.last_valid_index()
        if last_valid_idx is not None and series.index[-1] != last_valid_idx:
            mask = series.index > last_valid_idx
            series.loc[mask] = series.loc[last_valid_idx]
        
        if method == "seasonal":
            # 季节性填充
            return self._fill_seasonal(series)
        
        elif method == "arima" and self.statsmodels_available:
            # ARIMA填充
            return self._fill_arima(series, time_series)
        
        elif method == "kalman" and self.pykalman_available:
            # Kalman滤波填充
            return self._fill_kalman(series)
        
        elif method == "prophet" and self.prophet_available:
            # Prophet填充
            return self._fill_prophet(series, time_series)
        
        else:
            self.logger.warning(f"不支持的方法或依赖缺失: {method}，使用季节性填充")
            return self._fill_seasonal(series)
    
    def _fill_seasonal(self, series: pd.Series) -> pd.Series:
        """
        使用季节性方法填充缺失值
        
        参数:
            series: 待处理的列
            
        返回:
            处理后的列
        """
        # 复制数据，避免修改原始数据
        result = series.copy()
        
        # 获取缺失值索引
        na_indices = np.where(result.isna())[0]
        
        if len(na_indices) == 0:
            return result
        
        # 获取非缺失值
        valid_values = result.dropna().values
        
        if len(valid_values) == 0:
            return result
        
        # 计算季节性周期
        period = min(self.seasonal_period, len(valid_values))
        
        # 填充缺失值
        for idx in na_indices:
            # 找到对应的季节性位置
            seasonal_idx = idx % period
            
            # 找到所有在相同季节性位置的非缺失值
            seasonal_values = []
            for i in range(len(result)):
                if i % period == seasonal_idx and not pd.isna(result.iloc[i]):
                    seasonal_values.append(result.iloc[i])
            
            if seasonal_values:
                # 使用相同季节性位置的均值填充
                result.iloc[idx] = np.mean(seasonal_values)
            else:
                # 如果没有相同季节性位置的非缺失值，使用整体均值填充
                result.iloc[idx] = np.mean(valid_values)
        
        return result
    
    def _fill_arima(self, series: pd.Series, time_series: Optional[pd.Series] = None) -> pd.Series:
        """
        使用ARIMA模型填充缺失值
        
        参数:
            series: 待处理的列
            time_series: 时间列，可选
            
        返回:
            处理后的列
        """
        import statsmodels.api as sm
        
        # 复制数据，避免修改原始数据
        result = series.copy()
        
        # 获取缺失值索引
        na_indices = np.where(result.isna())[0]
        
        if len(na_indices) == 0:
            return result
        
        try:
            # 使用线性插值先填充缺失值，作为初始估计
            temp_series = result.interpolate(method="linear")
            
            # 拟合ARIMA模型
            model = sm.tsa.ARIMA(
                temp_series,
                order=(1, 0, 0)  # 简单的AR(1)模型
            )
            model_fit = model.fit()
            
            # 获取预测值
            predictions = model_fit.predict()
            
            # 只用预测值填充缺失值
            for idx in na_indices:
                result.iloc[idx] = predictions.iloc[idx]
            
            return result
        
        except Exception as e:
            self.logger.warning(f"ARIMA填充失败: {e}，使用线性插值")
            return result.interpolate(method="linear")
    
    def _fill_kalman(self, series: pd.Series) -> pd.Series:
        """
        使用Kalman滤波填充缺失值
        
        参数:
            series: 待处理的列
            
        返回:
            处理后的列
        """
        from pykalman import KalmanFilter
        
        # 复制数据，避免修改原始数据
        result = series.copy()
        
        # 获取缺失值索引
        na_indices = np.where(result.isna())[0]
        
        if len(na_indices) == 0:
            return result
        
        try:
            # 准备数据
            measurements = np.ma.masked_array(
                result.values,
                mask=np.isnan(result.values)
            )
            
            # 初始化Kalman滤波器
            kf = KalmanFilter(
                initial_state_mean=0,
                initial_state_covariance=1,
                transition_matrices=1,
                observation_matrices=1,
                transition_covariance=0.01,
                observation_covariance=1
            )
            
            # 运行Kalman滤波
            state_means, _ = kf.smooth(measurements)
            
            # 填充缺失值
            for idx in na_indices:
                result.iloc[idx] = state_means[idx, 0]
            
            return result
        
        except Exception as e:
            self.logger.warning(f"Kalman滤波填充失败: {e}，使用线性插值")
            return result.interpolate(method="linear")
    
    def _fill_prophet(self, series: pd.Series, time_series: Optional[pd.Series]) -> pd.Series:
        """
        使用Prophet填充缺失值
        
        参数:
            series: 待处理的列
            time_series: 时间列，必需
            
        返回:
            处理后的列
        """
        from prophet import Prophet
        
        # 复制数据，避免修改原始数据
        result = series.copy()
        
        # 获取缺失值索引
        na_indices = np.where(result.isna())[0]
        
        if len(na_indices) == 0:
            return result
        
        if time_series is None:
            self.logger.warning("Prophet方法需要时间列，使用线性插值")
            return result.interpolate(method="linear")
        
        try:
            # 准备数据
            df = pd.DataFrame({
                'ds': time_series,
                'y': result
            })
            
            # 记录缺失值的日期
            na_dates = df.loc[na_indices, 'ds'].values
            
            # 删除缺失值行
            train_df = df.dropna()
            
            # 初始化Prophet模型
            model = Prophet()
            
            # 拟合模型
            model.fit(train_df)
            
            # 预测所有日期
            future = pd.DataFrame({'ds': df['ds']})
            forecast = model.predict(future)
            
            # 填充缺失值
            for date in na_dates:
                idx = df[df['ds'] == date].index[0]
                forecast_idx = forecast[forecast['ds'] == date].index[0]
                result.iloc[idx] = forecast.iloc[forecast_idx]['yhat']
            
            return result
        
        except Exception as e:
            self.logger.warning(f"Prophet填充失败: {e}，使用线性插值")
            return result.interpolate(method="linear")
