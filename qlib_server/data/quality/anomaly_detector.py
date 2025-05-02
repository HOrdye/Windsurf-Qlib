"""
数据异常检测器实现
包含统计异常检测、时序异常检测、文本异常检测和图像异常检测
"""
from typing import Dict, List, Union, Optional, Any, Tuple
import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime
import json
from pathlib import Path
import warnings

from .base import BaseAnomalyDetector

# 配置日志
logger = logging.getLogger(__name__)


class StatisticalAnomalyDetector(BaseAnomalyDetector):
    """
    统计异常检测器
    基于统计方法检测数值特征中的异常值
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化统计异常检测器
        
        参数:
            config: 配置字典，包含以下字段:
                - threshold: 异常阈值，标准差的倍数
                - method: 检测方法，支持'zscore'、'iqr'、'isolation_forest'
                - columns: 要检测的列，如果为空则检测所有数值列
        """
        super().__init__(config)
        self.method = config.get("method", "zscore")
        self.columns = config.get("columns", [])
        
        # 检查是否有可选依赖
        if self.method == "isolation_forest":
            try:
                from sklearn.ensemble import IsolationForest
                self.isolation_forest = True
            except ImportError:
                self.isolation_forest = False
                warnings.warn("scikit-learn未安装，无法使用IsolationForest方法")
                self.method = "zscore"  # 降级到zscore方法
    
    def detect(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        检测数据异常
        
        参数:
            data: 待检测的数据框
            
        返回:
            检测结果字典，包含异常信息
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError("数据必须是pandas DataFrame类型")
        
        # 选择要检测的列
        if self.columns:
            # 确保所有指定的列都存在
            missing_cols = set(self.columns) - set(data.columns)
            if missing_cols:
                self.logger.warning(f"以下列不存在: {missing_cols}")
            
            # 筛选存在的列
            cols = [col for col in self.columns if col in data.columns]
        else:
            # 选择所有数值列
            cols = data.select_dtypes(include=np.number).columns.tolist()
        
        if not cols:
            return {"anomalies": [], "message": "没有可检测的数值列"}
        
        # 检测异常
        anomalies = []
        
        if self.method == "zscore":
            # Z-score方法
            for col in cols:
                # 计算Z-score
                mean = data[col].mean()
                std = data[col].std()
                
                if std == 0:
                    self.logger.warning(f"列 {col} 的标准差为0，跳过")
                    continue
                
                z_scores = (data[col] - mean) / std
                
                # 找出异常值
                threshold = self.config["threshold"]
                anomaly_indices = np.where(np.abs(z_scores) > threshold)[0]
                
                for idx in anomaly_indices:
                    if isinstance(data.index, pd.MultiIndex):
                        # 处理多级索引
                        index_str = str(data.index[idx])
                    else:
                        index_str = str(data.index[idx])
                    
                    anomalies.append({
                        "column": col,
                        "index": index_str,
                        "value": float(data.iloc[idx][col]),
                        "z_score": float(z_scores.iloc[idx]),
                        "threshold": threshold,
                        "method": "zscore"
                    })
        
        elif self.method == "iqr":
            # IQR方法
            for col in cols:
                # 计算IQR
                q1 = data[col].quantile(0.25)
                q3 = data[col].quantile(0.75)
                iqr = q3 - q1
                
                if iqr == 0:
                    self.logger.warning(f"列 {col} 的IQR为0，跳过")
                    continue
                
                # 找出异常值
                threshold = self.config["threshold"]
                lower_bound = q1 - threshold * iqr
                upper_bound = q3 + threshold * iqr
                
                anomaly_indices = np.where((data[col] < lower_bound) | (data[col] > upper_bound))[0]
                
                for idx in anomaly_indices:
                    if isinstance(data.index, pd.MultiIndex):
                        # 处理多级索引
                        index_str = str(data.index[idx])
                    else:
                        index_str = str(data.index[idx])
                    
                    value = float(data.iloc[idx][col])
                    anomalies.append({
                        "column": col,
                        "index": index_str,
                        "value": value,
                        "bound": float(lower_bound) if value < lower_bound else float(upper_bound),
                        "threshold": threshold,
                        "method": "iqr"
                    })
        
        elif self.method == "isolation_forest" and self.isolation_forest:
            # Isolation Forest方法
            from sklearn.ensemble import IsolationForest
            
            # 准备数据
            X = data[cols].copy()
            
            # 处理缺失值
            X = X.fillna(X.mean())
            
            # 训练模型
            model = IsolationForest(
                contamination=float(self.config.get("contamination", 0.05)),
                random_state=42
            )
            
            # 预测异常
            y_pred = model.fit_predict(X)
            anomaly_indices = np.where(y_pred == -1)[0]
            
            # 计算异常分数
            scores = model.decision_function(X)
            
            for idx in anomaly_indices:
                if isinstance(data.index, pd.MultiIndex):
                    # 处理多级索引
                    index_str = str(data.index[idx])
                else:
                    index_str = str(data.index[idx])
                
                anomalies.append({
                    "index": index_str,
                    "score": float(scores[idx]),
                    "threshold": self.config.get("contamination", 0.05),
                    "method": "isolation_forest"
                })
        
        return {
            "anomalies": anomalies,
            "method": self.method,
            "columns": cols,
            "threshold": self.config["threshold"],
            "total_anomalies": len(anomalies),
            "total_samples": len(data)
        }


class TimeSeriesAnomalyDetector(BaseAnomalyDetector):
    """
    时序异常检测器
    检测时间序列数据中的异常模式
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化时序异常检测器
        
        参数:
            config: 配置字典，包含以下字段:
                - threshold: 异常阈值
                - method: 检测方法，支持'moving_avg'、'ewma'、'arima'
                - window: 移动窗口大小
                - columns: 要检测的列，如果为空则检测所有数值列
                - time_col: 时间列名，默认为'datetime'
                - group_col: 分组列名，默认为'instrument'
        """
        super().__init__(config)
        self.method = config.get("method", "moving_avg")
        self.window = config.get("window", 5)
        self.columns = config.get("columns", [])
        self.time_col = config.get("time_col", "datetime")
        self.group_col = config.get("group_col", "instrument")
        
        # 检查是否有可选依赖
        if self.method == "arima":
            try:
                import statsmodels.api as sm
                self.statsmodels_available = True
            except ImportError:
                self.statsmodels_available = False
                warnings.warn("statsmodels未安装，无法使用ARIMA方法")
                self.method = "moving_avg"  # 降级到moving_avg方法
    
    def detect(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        检测时间序列异常
        
        参数:
            data: 待检测的数据框
            
        返回:
            检测结果字典，包含异常信息
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError("数据必须是pandas DataFrame类型")
        
        # 确保时间列存在
        if self.time_col not in data.columns and not (isinstance(data.index, pd.MultiIndex) and self.time_col in data.index.names):
            if isinstance(data.index, pd.DatetimeIndex):
                # 如果索引是DatetimeIndex，则重置索引
                data = data.reset_index()
                self.time_col = "index"
            else:
                return {"anomalies": [], "message": f"时间列 {self.time_col} 不存在"}
        
        # 选择要检测的列
        if self.columns:
            # 确保所有指定的列都存在
            missing_cols = set(self.columns) - set(data.columns)
            if missing_cols:
                self.logger.warning(f"以下列不存在: {missing_cols}")
            
            # 筛选存在的列
            cols = [col for col in self.columns if col in data.columns]
        else:
            # 选择所有数值列
            cols = data.select_dtypes(include=np.number).columns.tolist()
            
            # 排除时间列和分组列
            if self.time_col in cols:
                cols.remove(self.time_col)
            if self.group_col in cols:
                cols.remove(self.group_col)
        
        if not cols:
            return {"anomalies": [], "message": "没有可检测的数值列"}
        
        # 检测异常
        anomalies = []
        
        # 如果有分组列，则按分组处理
        if self.group_col in data.columns:
            groups = data[self.group_col].unique()
            for group in groups:
                group_data = data[data[self.group_col] == group].copy()
                
                # 确保时间排序
                if self.time_col in group_data.columns:
                    group_data = group_data.sort_values(by=self.time_col)
                
                # 对每一列进行检测
                for col in cols:
                    col_anomalies = self._detect_column_anomalies(group_data, col, group)
                    anomalies.extend(col_anomalies)
        else:
            # 确保时间排序
            if self.time_col in data.columns:
                data = data.sort_values(by=self.time_col)
            
            # 对每一列进行检测
            for col in cols:
                col_anomalies = self._detect_column_anomalies(data, col)
                anomalies.extend(col_anomalies)
        
        return {
            "anomalies": anomalies,
            "method": self.method,
            "columns": cols,
            "window": self.window,
            "threshold": self.config["threshold"],
            "total_anomalies": len(anomalies),
            "total_samples": len(data)
        }
    
    def _detect_column_anomalies(self, data: pd.DataFrame, column: str, group: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        检测单列的时间序列异常
        
        参数:
            data: 待检测的数据框
            column: 列名
            group: 分组值，可选
            
        返回:
            异常列表
        """
        anomalies = []
        
        if self.method == "moving_avg":
            # 移动平均法
            # 计算移动平均
            ma = data[column].rolling(window=self.window, min_periods=1).mean()
            
            # 计算残差
            residuals = data[column] - ma
            
            # 计算残差的标准差
            std = residuals.std()
            
            if std == 0:
                self.logger.warning(f"列 {column} 的残差标准差为0，跳过")
                return []
            
            # 找出异常值
            threshold = self.config["threshold"]
            anomaly_indices = np.where(np.abs(residuals / std) > threshold)[0]
            
            for idx in anomaly_indices:
                time_value = data.iloc[idx][self.time_col] if self.time_col in data.columns else idx
                
                anomalies.append({
                    "column": column,
                    "time": str(time_value),
                    "group": str(group) if group is not None else None,
                    "value": float(data.iloc[idx][column]),
                    "expected": float(ma.iloc[idx]),
                    "residual": float(residuals.iloc[idx]),
                    "normalized_residual": float(residuals.iloc[idx] / std),
                    "threshold": threshold,
                    "method": "moving_avg"
                })
        
        elif self.method == "ewma":
            # 指数加权移动平均法
            # 计算EWMA
            ewma = data[column].ewm(span=self.window).mean()
            
            # 计算残差
            residuals = data[column] - ewma
            
            # 计算残差的标准差
            std = residuals.std()
            
            if std == 0:
                self.logger.warning(f"列 {column} 的残差标准差为0，跳过")
                return []
            
            # 找出异常值
            threshold = self.config["threshold"]
            anomaly_indices = np.where(np.abs(residuals / std) > threshold)[0]
            
            for idx in anomaly_indices:
                time_value = data.iloc[idx][self.time_col] if self.time_col in data.columns else idx
                
                anomalies.append({
                    "column": column,
                    "time": str(time_value),
                    "group": str(group) if group is not None else None,
                    "value": float(data.iloc[idx][column]),
                    "expected": float(ewma.iloc[idx]),
                    "residual": float(residuals.iloc[idx]),
                    "normalized_residual": float(residuals.iloc[idx] / std),
                    "threshold": threshold,
                    "method": "ewma"
                })
        
        elif self.method == "arima" and self.statsmodels_available:
            # ARIMA方法
            import statsmodels.api as sm
            
            # 准备数据
            series = data[column].copy()
            
            # 处理缺失值
            series = series.fillna(method='ffill').fillna(method='bfill')
            
            try:
                # 拟合ARIMA模型
                model = sm.tsa.ARIMA(
                    series,
                    order=(1, 0, 0)  # 简单的AR(1)模型
                )
                model_fit = model.fit()
                
                # 获取预测值
                predictions = model_fit.predict()
                
                # 计算残差
                residuals = series - predictions
                
                # 计算残差的标准差
                std = residuals.std()
                
                if std == 0:
                    self.logger.warning(f"列 {column} 的残差标准差为0，跳过")
                    return []
                
                # 找出异常值
                threshold = self.config["threshold"]
                anomaly_indices = np.where(np.abs(residuals / std) > threshold)[0]
                
                for idx in anomaly_indices:
                    time_value = data.iloc[idx][self.time_col] if self.time_col in data.columns else idx
                    
                    anomalies.append({
                        "column": column,
                        "time": str(time_value),
                        "group": str(group) if group is not None else None,
                        "value": float(series.iloc[idx]),
                        "expected": float(predictions.iloc[idx]),
                        "residual": float(residuals.iloc[idx]),
                        "normalized_residual": float(residuals.iloc[idx] / std),
                        "threshold": threshold,
                        "method": "arima"
                    })
            except Exception as e:
                self.logger.warning(f"ARIMA模型拟合失败: {e}")
        
        return anomalies
