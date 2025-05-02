"""
数据源可靠性评分机制
提供数据源延迟、准确性、完整性和一致性评分
"""

import logging
import warnings
from typing import Dict, List, Union, Any, Tuple, Optional, Callable
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy import stats

from .base import BaseReliabilityScorer

# 配置日志
logger = logging.getLogger(__name__)

# 忽略特定警告
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

class DataSourceReliabilityScorer(BaseReliabilityScorer):
    """
    数据源可靠性评分器
    综合评估数据源的延迟、准确性、完整性和一致性
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据源可靠性评分器
        
        参数:
            config: 配置字典，包含以下字段:
                - weights: 各项指标的权重，默认为均等权重
                - scorers: 使用的评分器列表，可选值为'latency', 'accuracy', 'completeness', 'consistency'
                - reference_source: 参考数据源，用于计算准确性
                - min_score: 最小评分，默认为0
                - max_score: 最大评分，默认为1
        """
        # 在调用父类__init__之前先设置属性，避免_validate_config中的属性访问错误
        self.weights = config.get("weights", {})
        self.scorers = config.get("scorers", ["latency", "accuracy", "completeness", "consistency"])
        self.reference_source = config.get("reference_source")
        self.min_score = config.get("min_score", 0)
        self.max_score = config.get("max_score", 1)
        
        # 调用父类__init__
        super().__init__(config)
        
        # 初始化评分器
        self.scorer_instances = {}
        self._init_scorers()
    
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        super()._validate_config()
        
        # 检查评分器列表
        valid_scorers = ["latency", "accuracy", "completeness", "consistency"]
        for scorer in self.scorers:
            if scorer not in valid_scorers:
                raise ValueError(f"评分器 {scorer} 不在有效评分器列表中: {valid_scorers}")
        
        # 检查权重
        if self.weights:
            for scorer, weight in self.weights.items():
                if scorer not in valid_scorers:
                    raise ValueError(f"权重中的评分器 {scorer} 不在有效评分器列表中: {valid_scorers}")
                if not isinstance(weight, (int, float)) or weight < 0:
                    raise ValueError(f"评分器 {scorer} 的权重必须是非负数")
    
    def _init_scorers(self) -> None:
        """初始化评分器"""
        # 创建各个评分器
        for scorer_name in self.scorers:
            if scorer_name == "latency":
                self.scorer_instances[scorer_name] = LatencyScorer(self.config)
            elif scorer_name == "accuracy":
                self.scorer_instances[scorer_name] = AccuracyScorer(self.config)
            elif scorer_name == "completeness":
                self.scorer_instances[scorer_name] = CompletenessScorer(self.config)
            elif scorer_name == "consistency":
                self.scorer_instances[scorer_name] = ConsistencyScorer(self.config)
        
        # 如果未指定权重，则使用均等权重
        if not self.weights:
            weight = 1.0 / len(self.scorer_instances)
            self.weights = {scorer: weight for scorer in self.scorer_instances}
    
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
        if data.empty:
            self.logger.warning(f"数据源 {data_source} 为空，评分为0")
            return 0.0
        
        # 计算各个评分器的评分
        scores = {}
        for scorer_name, scorer in self.scorer_instances.items():
            try:
                score = scorer.score(data_source, data, reference)
                scores[scorer_name] = score
            except Exception as e:
                self.logger.error(f"计算数据源 {data_source} 的 {scorer_name} 评分时出错: {e}")
                scores[scorer_name] = 0.0
        
        # 计算加权平均评分
        total_weight = sum(self.weights.get(scorer, 0) for scorer in scores)
        if total_weight == 0:
            self.logger.warning(f"数据源 {data_source} 的总权重为0，评分为0")
            return 0.0
        
        weighted_score = sum(scores[scorer] * self.weights.get(scorer, 0) for scorer in scores) / total_weight
        
        # 限制评分范围
        final_score = max(self.min_score, min(self.max_score, weighted_score))
        
        # 更新评分历史
        self.update_score_history(data_source, final_score)
        
        return final_score
    
    def get_detailed_scores(self, data_source: str, data: pd.DataFrame, reference: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """
        获取详细的评分结果
        
        参数:
            data_source: 数据源名称
            data: 数据源数据
            reference: 参考数据，可选
            
        返回:
            各项评分的字典
        """
        if data.empty:
            return {scorer: 0.0 for scorer in self.scorer_instances}
        
        # 计算各个评分器的评分
        scores = {}
        for scorer_name, scorer in self.scorer_instances.items():
            try:
                score = scorer.score(data_source, data, reference)
                scores[scorer_name] = score
            except Exception as e:
                self.logger.error(f"计算数据源 {data_source} 的 {scorer_name} 评分时出错: {e}")
                scores[scorer_name] = 0.0
        
        # 添加总评分
        total_weight = sum(self.weights.get(scorer, 0) for scorer in scores)
        if total_weight > 0:
            weighted_score = sum(scores[scorer] * self.weights.get(scorer, 0) for scorer in scores) / total_weight
            scores["total"] = max(self.min_score, min(self.max_score, weighted_score))
        else:
            scores["total"] = 0.0
        
        return scores


class LatencyScorer(BaseReliabilityScorer):
    """
    延迟评分器
    评估数据源的延迟情况
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化延迟评分器
        
        参数:
            config: 配置字典，包含以下字段:
                - latency_threshold: 延迟阈值，单位为秒，默认为1
                - latency_penalty: 延迟惩罚系数，默认为0.1
                - time_field: 时间戳字段名，默认为索引
        """
        super().__init__(config)
        self.latency_threshold = self.config.get("latency_threshold", 1.0)
        self.latency_penalty = self.config.get("latency_penalty", 0.1)
        self.time_field = self.config.get("time_field")
        
        # 存储数据源的最新时间戳
        self.latest_timestamps = {}
    
    def score(self, data_source: str, data: pd.DataFrame, reference: Optional[pd.DataFrame] = None) -> float:
        """
        评估数据源的延迟
        
        参数:
            data_source: 数据源名称
            data: 数据源数据
            reference: 参考数据，可选
            
        返回:
            延迟评分，范围[0, 1]
        """
        if data.empty:
            return 0.0
        
        # 获取当前时间
        current_time = datetime.now()
        
        # 获取数据的最新时间戳
        if self.time_field and self.time_field in data.columns:
            # 使用指定的时间字段
            latest_time = data[self.time_field].max()
            if isinstance(latest_time, str):
                try:
                    latest_time = pd.to_datetime(latest_time)
                except Exception as e:
                    self.logger.error(f"无法将时间字符串转换为datetime: {e}")
                    latest_time = None
        else:
            # 使用索引作为时间戳
            if isinstance(data.index, pd.DatetimeIndex):
                latest_time = data.index.max()
            else:
                try:
                    latest_time = pd.to_datetime(data.index.max())
                except Exception as e:
                    self.logger.error(f"无法将索引转换为datetime: {e}")
                    latest_time = None
        
        if latest_time is None:
            self.logger.warning(f"无法获取数据源 {data_source} 的最新时间戳")
            return 0.0
        
        # 计算延迟
        latency = (current_time - latest_time).total_seconds()
        
        # 更新最新时间戳
        self.latest_timestamps[data_source] = latest_time
        
        # 计算延迟评分
        if latency <= 0:
            # 异常情况，时间戳在未来
            self.logger.warning(f"数据源 {data_source} 的最新时间戳在未来: {latest_time}")
            return 0.0
        elif latency <= self.latency_threshold:
            # 延迟在阈值内，满分
            return 1.0
        else:
            # 延迟超过阈值，按比例扣分
            excess_latency = latency - self.latency_threshold
            penalty = excess_latency * self.latency_penalty
            score = max(0.0, 1.0 - penalty)
            return score
    
    def get_latency(self, data_source: str) -> Optional[float]:
        """
        获取数据源的延迟
        
        参数:
            data_source: 数据源名称
            
        返回:
            延迟，单位为秒
        """
        if data_source not in self.latest_timestamps:
            return None
        
        latest_time = self.latest_timestamps[data_source]
        current_time = datetime.now()
        
        return (current_time - latest_time).total_seconds()


class AccuracyScorer(BaseReliabilityScorer):
    """
    准确性评分器
    评估数据源的准确性，通过与参考数据源比较
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化准确性评分器
        
        参数:
            config: 配置字典，包含以下字段:
                - reference_source: 参考数据源，用于计算准确性
                - accuracy_metrics: 准确性度量方法，可选值为'mape', 'rmse', 'mae', 'correlation'
                - accuracy_threshold: 准确性阈值，超过此阈值视为不准确
                - columns: 要评估的列，如果为空则评估所有数值列
        """
        super().__init__(config)
        self.reference_source = self.config.get("reference_source")
        self.accuracy_metrics = self.config.get("accuracy_metrics", ["mape", "rmse", "correlation"])
        self.accuracy_threshold = self.config.get("accuracy_threshold", {
            "mape": 0.05,  # 5%
            "rmse": 0.1,
            "mae": 0.1,
            "correlation": 0.9
        })
        self.columns = self.config.get("columns", [])
    
    def score(self, data_source: str, data: pd.DataFrame, reference: Optional[pd.DataFrame] = None) -> float:
        """
        评估数据源的准确性
        
        参数:
            data_source: 数据源名称
            data: 数据源数据
            reference: 参考数据，可选
            
        返回:
            准确性评分，范围[0, 1]
        """
        if data.empty:
            return 0.0
        
        # 如果未提供参考数据，则无法评估准确性
        if reference is None:
            if data_source == self.reference_source:
                # 参考数据源自身的准确性视为满分
                return 1.0
            else:
                self.logger.warning(f"未提供参考数据，无法评估数据源 {data_source} 的准确性")
                return 0.5  # 默认中等评分
        
        # 确保两个数据集有相同的索引
        common_index = data.index.intersection(reference.index)
        if len(common_index) == 0:
            self.logger.warning(f"数据源 {data_source} 与参考数据没有共同的时间戳")
            return 0.0
        
        # 选择要评估的列
        if self.columns:
            columns = [col for col in self.columns if col in data.columns and col in reference.columns]
        else:
            # 选择共同的数值列
            numeric_cols_data = data.select_dtypes(include=[np.number]).columns
            numeric_cols_ref = reference.select_dtypes(include=[np.number]).columns
            columns = list(set(numeric_cols_data) & set(numeric_cols_ref))
        
        if not columns:
            self.logger.warning(f"数据源 {data_source} 与参考数据没有共同的数值列")
            return 0.0
        
        # 对齐数据
        aligned_data = data.loc[common_index, columns]
        aligned_reference = reference.loc[common_index, columns]
        
        # 计算各个度量的评分
        metric_scores = {}
        
        for metric in self.accuracy_metrics:
            if metric == "mape":
                # 平均绝对百分比误差
                score = self._calculate_mape_score(aligned_data, aligned_reference)
            elif metric == "rmse":
                # 均方根误差
                score = self._calculate_rmse_score(aligned_data, aligned_reference)
            elif metric == "mae":
                # 平均绝对误差
                score = self._calculate_mae_score(aligned_data, aligned_reference)
            elif metric == "correlation":
                # 相关系数
                score = self._calculate_correlation_score(aligned_data, aligned_reference)
            else:
                self.logger.warning(f"未知的准确性度量方法: {metric}")
                continue
            
            metric_scores[metric] = score
        
        if not metric_scores:
            self.logger.warning(f"数据源 {data_source} 的准确性评分为空")
            return 0.0
        
        # 计算平均评分
        avg_score = sum(metric_scores.values()) / len(metric_scores)
        
        return avg_score
    
    def _calculate_mape_score(self, data: pd.DataFrame, reference: pd.DataFrame) -> float:
        """
        计算平均绝对百分比误差评分
        
        参数:
            data: 数据源数据
            reference: 参考数据
            
        返回:
            MAPE评分，范围[0, 1]
        """
        mape_values = []
        
        for col in data.columns:
            # 计算非零值的MAPE
            mask = reference[col] != 0
            if mask.sum() == 0:
                continue
                
            mape = np.mean(np.abs((reference.loc[mask, col] - data.loc[mask, col]) / reference.loc[mask, col]))
            mape_values.append(mape)
        
        if not mape_values:
            return 0.0
        
        # 计算平均MAPE
        avg_mape = np.mean(mape_values)
        
        # 转换为评分
        threshold = self.accuracy_threshold.get("mape", 0.05)
        if avg_mape <= threshold:
            # MAPE在阈值内，满分
            score = 1.0
        else:
            # MAPE超过阈值，按比例扣分
            score = max(0.0, 1.0 - (avg_mape - threshold) / threshold * 5)
        
        return score
    
    def _calculate_rmse_score(self, data: pd.DataFrame, reference: pd.DataFrame) -> float:
        """
        计算均方根误差评分
        
        参数:
            data: 数据源数据
            reference: 参考数据
            
        返回:
            RMSE评分，范围[0, 1]
        """
        rmse_values = []
        
        for col in data.columns:
            # 标准化数据
            ref_std = reference[col].std()
            if ref_std == 0:
                continue
                
            # 计算标准化RMSE
            rmse = np.sqrt(np.mean((reference[col] - data[col])**2)) / ref_std
            rmse_values.append(rmse)
        
        if not rmse_values:
            return 0.0
        
        # 计算平均RMSE
        avg_rmse = np.mean(rmse_values)
        
        # 转换为评分
        threshold = self.accuracy_threshold.get("rmse", 0.1)
        if avg_rmse <= threshold:
            # RMSE在阈值内，满分
            score = 1.0
        else:
            # RMSE超过阈值，按比例扣分
            score = max(0.0, 1.0 - (avg_rmse - threshold) / threshold * 5)
        
        return score
    
    def _calculate_mae_score(self, data: pd.DataFrame, reference: pd.DataFrame) -> float:
        """
        计算平均绝对误差评分
        
        参数:
            data: 数据源数据
            reference: 参考数据
            
        返回:
            MAE评分，范围[0, 1]
        """
        mae_values = []
        
        for col in data.columns:
            # 标准化数据
            ref_std = reference[col].std()
            if ref_std == 0:
                continue
                
            # 计算标准化MAE
            mae = np.mean(np.abs(reference[col] - data[col])) / ref_std
            mae_values.append(mae)
        
        if not mae_values:
            return 0.0
        
        # 计算平均MAE
        avg_mae = np.mean(mae_values)
        
        # 转换为评分
        threshold = self.accuracy_threshold.get("mae", 0.1)
        if avg_mae <= threshold:
            # MAE在阈值内，满分
            score = 1.0
        else:
            # MAE超过阈值，按比例扣分
            score = max(0.0, 1.0 - (avg_mae - threshold) / threshold * 5)
        
        return score
    
    def _calculate_correlation_score(self, data: pd.DataFrame, reference: pd.DataFrame) -> float:
        """
        计算相关系数评分
        
        参数:
            data: 数据源数据
            reference: 参考数据
            
        返回:
            相关系数评分，范围[0, 1]
        """
        corr_values = []
        
        for col in data.columns:
            # 计算相关系数
            corr = np.corrcoef(reference[col], data[col])[0, 1]
            if np.isnan(corr):
                continue
                
            corr_values.append(corr)
        
        if not corr_values:
            return 0.0
        
        # 计算平均相关系数
        avg_corr = np.mean(corr_values)
        
        # 转换为评分
        threshold = self.accuracy_threshold.get("correlation", 0.9)
        if avg_corr >= threshold:
            # 相关系数在阈值以上，满分
            score = 1.0
        else:
            # 相关系数低于阈值，按比例扣分
            score = max(0.0, avg_corr / threshold)
        
        return score


class CompletenessScorer(BaseReliabilityScorer):
    """
    完整性评分器
    评估数据源的完整性，包括缺失值、数据覆盖率等
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化完整性评分器
        
        参数:
            config: 配置字典，包含以下字段:
                - missing_threshold: 缺失值阈值，默认为0.05
                - coverage_threshold: 覆盖率阈值，默认为0.9
                - expected_frequency: 预期数据频率，如'1min', '5min'等
                - time_field: 时间戳字段名，默认为索引
                - columns: 要评估的列，如果为空则评估所有列
        """
        super().__init__(config)
        self.missing_threshold = self.config.get("missing_threshold", 0.05)
        self.coverage_threshold = self.config.get("coverage_threshold", 0.9)
        self.expected_frequency = self.config.get("expected_frequency")
        self.time_field = self.config.get("time_field")
        self.columns = self.config.get("columns", [])
    
    def score(self, data_source: str, data: pd.DataFrame, reference: Optional[pd.DataFrame] = None) -> float:
        """
        评估数据源的完整性
        
        参数:
            data_source: 数据源名称
            data: 数据源数据
            reference: 参考数据，可选
            
        返回:
            完整性评分，范围[0, 1]
        """
        if data.empty:
            return 0.0
        
        # 选择要评估的列
        columns = self.columns if self.columns else data.columns
        columns = [col for col in columns if col in data.columns]
        
        if not columns:
            self.logger.warning(f"数据源 {data_source} 没有可评估的列")
            return 0.0
        
        # 计算缺失值评分
        missing_score = self._calculate_missing_score(data, columns)
        
        # 计算覆盖率评分
        coverage_score = self._calculate_coverage_score(data)
        
        # 计算平均评分
        avg_score = (missing_score + coverage_score) / 2
        
        return avg_score
    
    def _calculate_missing_score(self, data: pd.DataFrame, columns: List[str]) -> float:
        """
        计算缺失值评分
        
        参数:
            data: 数据源数据
            columns: 要评估的列
            
        返回:
            缺失值评分，范围[0, 1]
        """
        # 计算每列的缺失率
        missing_rates = []
        
        for col in columns:
            missing_rate = data[col].isna().mean()
            missing_rates.append(missing_rate)
        
        if not missing_rates:
            return 0.0
        
        # 计算平均缺失率
        avg_missing_rate = np.mean(missing_rates)
        
        # 转换为评分
        if avg_missing_rate <= self.missing_threshold:
            # 缺失率在阈值内，满分
            score = 1.0
        else:
            # 缺失率超过阈值，按比例扣分
            excess_missing = avg_missing_rate - self.missing_threshold
            score = max(0.0, 1.0 - excess_missing / (1 - self.missing_threshold))
        
        return score
    
    def _calculate_coverage_score(self, data: pd.DataFrame) -> float:
        """
        计算覆盖率评分
        
        参数:
            data: 数据源数据
            
        返回:
            覆盖率评分，范围[0, 1]
        """
        # 如果未指定预期频率，则无法评估覆盖率
        if not self.expected_frequency:
            return 1.0
        
        # 获取时间范围
        if self.time_field and self.time_field in data.columns:
            # 使用指定的时间字段
            min_time = data[self.time_field].min()
            max_time = data[self.time_field].max()
            if isinstance(min_time, str):
                try:
                    min_time = pd.to_datetime(min_time)
                    max_time = pd.to_datetime(max_time)
                except Exception as e:
                    self.logger.error(f"无法将时间字符串转换为datetime: {e}")
                    return 0.5  # 默认中等评分
        else:
            # 使用索引作为时间戳
            if isinstance(data.index, pd.DatetimeIndex):
                min_time = data.index.min()
                max_time = data.index.max()
            else:
                try:
                    min_time = pd.to_datetime(data.index.min())
                    max_time = pd.to_datetime(data.index.max())
                except Exception as e:
                    self.logger.error(f"无法将索引转换为datetime: {e}")
                    return 0.5  # 默认中等评分
        
        # 创建预期的时间索引
        expected_index = pd.date_range(start=min_time, end=max_time, freq=self.expected_frequency)
        
        # 如果预期索引为空，则无法评估覆盖率
        if len(expected_index) == 0:
            return 1.0
        
        # 计算实际数据点数与预期数据点数的比率
        if self.time_field and self.time_field in data.columns:
            # 使用指定的时间字段
            actual_times = pd.DatetimeIndex(data[self.time_field])
        else:
            # 使用索引作为时间戳
            if isinstance(data.index, pd.DatetimeIndex):
                actual_times = data.index
            else:
                try:
                    actual_times = pd.DatetimeIndex(data.index)
                except Exception as e:
                    self.logger.error(f"无法将索引转换为DatetimeIndex: {e}")
                    return 0.5  # 默认中等评分
        
        # 计算覆盖率
        coverage = len(actual_times) / len(expected_index)
        
        # 转换为评分
        if coverage >= self.coverage_threshold:
            # 覆盖率在阈值以上，满分
            score = 1.0
        else:
            # 覆盖率低于阈值，按比例扣分
            score = max(0.0, coverage / self.coverage_threshold)
        
        return score


class ConsistencyScorer(BaseReliabilityScorer):
    """
    一致性评分器
    评估数据源的一致性，包括数据的平稳性、异常值检测等
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化一致性评分器
        
        参数:
            config: 配置字典，包含以下字段:
                - outlier_threshold: 异常值阈值，默认为3.0（标准差的倍数）
                - stationarity_threshold: 平稳性阈值，默认为0.05（p值）
                - window_size: 滑动窗口大小，用于计算统计量
                - columns: 要评估的列，如果为空则评估所有数值列
        """
        super().__init__(config)
        self.outlier_threshold = self.config.get("outlier_threshold", 3.0)
        self.stationarity_threshold = self.config.get("stationarity_threshold", 0.05)
        self.window_size = self.config.get("window_size", 20)
        self.columns = self.config.get("columns", [])
    
    def score(self, data_source: str, data: pd.DataFrame, reference: Optional[pd.DataFrame] = None) -> float:
        """
        评估数据源的一致性
        
        参数:
            data_source: 数据源名称
            data: 数据源数据
            reference: 参考数据，可选
            
        返回:
            一致性评分，范围[0, 1]
        """
        if data.empty:
            return 0.0
        
        # 选择要评估的列
        if self.columns:
            columns = [col for col in self.columns if col in data.columns]
        else:
            # 选择数值列
            columns = data.select_dtypes(include=[np.number]).columns
        
        if not columns:
            self.logger.warning(f"数据源 {data_source} 没有可评估的数值列")
            return 0.0
        
        # 计算异常值评分
        outlier_score = self._calculate_outlier_score(data, columns)
        
        # 计算平稳性评分
        stationarity_score = self._calculate_stationarity_score(data, columns)
        
        # 计算平均评分
        avg_score = (outlier_score + stationarity_score) / 2
        
        return avg_score
    
    def _calculate_outlier_score(self, data: pd.DataFrame, columns: List[str]) -> float:
        """
        计算异常值评分
        
        参数:
            data: 数据源数据
            columns: 要评估的列
            
        返回:
            异常值评分，范围[0, 1]
        """
        # 计算每列的异常值比例
        outlier_rates = []
        
        for col in columns:
            # 计算Z分数
            values = data[col].dropna().values
            if len(values) < 2:
                continue
                
            mean = np.mean(values)
            std = np.std(values)
            
            if std == 0:
                # 如果标准差为0，则所有值相同，没有异常值
                outlier_rate = 0.0
            else:
                z_scores = np.abs((values - mean) / std)
                outliers = z_scores > self.outlier_threshold
                outlier_rate = np.mean(outliers)
            
            outlier_rates.append(outlier_rate)
        
        if not outlier_rates:
            return 0.0
        
        # 计算平均异常值比例
        avg_outlier_rate = np.mean(outlier_rates)
        
        # 转换为评分
        score = max(0.0, 1.0 - avg_outlier_rate * 10)  # 异常值比例每增加0.1，评分减少1
        
        return score
    
    def _calculate_stationarity_score(self, data: pd.DataFrame, columns: List[str]) -> float:
        """
        计算平稳性评分
        
        参数:
            data: 数据源数据
            columns: 要评估的列
            
        返回:
            平稳性评分，范围[0, 1]
        """
        # 如果数据点数量不足，则无法评估平稳性
        if len(data) < self.window_size * 2:
            return 1.0
        
        # 计算每列的平稳性
        stationarity_scores = []
        
        for col in columns:
            values = data[col].dropna().values
            if len(values) < self.window_size * 2:
                continue
            
            # 使用滑动窗口计算均值和方差的稳定性
            means = []
            stds = []
            
            for i in range(0, len(values) - self.window_size + 1, self.window_size // 2):
                window = values[i:i+self.window_size]
                means.append(np.mean(window))
                stds.append(np.std(window))
            
            # 计算均值和方差的变异系数
            mean_cv = np.std(means) / np.mean(means) if np.mean(means) != 0 else 0
            std_cv = np.std(stds) / np.mean(stds) if np.mean(stds) != 0 else 0
            
            # 计算平稳性得分
            # 变异系数越小，平稳性越好
            mean_score = max(0.0, 1.0 - mean_cv * 5)  # 均值变异系数每增加0.2，评分减少1
            std_score = max(0.0, 1.0 - std_cv * 5)    # 方差变异系数每增加0.2，评分减少1
            
            # 取均值和方差平稳性的平均值
            stationarity_scores.append((mean_score + std_score) / 2)
        
        if not stationarity_scores:
            return 0.0
        
        # 计算平均平稳性评分
        avg_stationarity_score = np.mean(stationarity_scores)
        
        return avg_stationarity_score
    
    def detect_anomalies(self, data: pd.DataFrame, column: str) -> pd.Series:
        """
        检测异常值
        
        参数:
            data: 数据源数据
            column: 要检测的列
            
        返回:
            异常值的布尔序列，True表示异常值
        """
        if column not in data.columns:
            return pd.Series(False, index=data.index)
        
        values = data[column].values
        mean = np.mean(values)
        std = np.std(values)
        
        if std == 0:
            return pd.Series(False, index=data.index)
        
        z_scores = np.abs((values - mean) / std)
        anomalies = z_scores > self.outlier_threshold
        
        return pd.Series(anomalies, index=data.index)
