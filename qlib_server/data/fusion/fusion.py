"""
数据融合引擎
提供多源数据融合功能，支持加权平均、卡尔曼滤波和机器学习融合
"""

import logging
import warnings
from typing import Dict, List, Union, Any, Tuple, Optional, Callable
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from filterpy.kalman import KalmanFilter

from .base import BaseDataFusion
from .aligner import CrossMarketDataAligner, TimeZoneAligner, AsynchronousDataAligner
from .resampler import MultiFrequencyResampler
from .reliability import DataSourceReliabilityScorer

# 配置日志
logger = logging.getLogger(__name__)

# 忽略特定警告
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

class DataFusionEngine:
    """
    数据融合引擎
    整合数据对齐、重采样、可靠性评分和融合功能
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据融合引擎
        
        参数:
            config: 配置字典，包含以下字段:
                - aligner: 数据对齐器配置
                - resampler: 数据重采样器配置
                - reliability_scorer: 可靠性评分器配置
                - fusion: 融合器配置
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # 初始化组件
        self._init_components()
    
    def _init_components(self):
        """初始化各个组件"""
        # 初始化数据对齐器
        aligner_config = self.config.get("aligner", {})
        aligner_type = aligner_config.get("type", "cross_market")
        
        if aligner_type == "cross_market":
            self.aligner = CrossMarketDataAligner(aligner_config)
        elif aligner_type == "timezone":
            self.aligner = TimeZoneAligner(aligner_config)
        elif aligner_type == "async":
            self.aligner = AsynchronousDataAligner(aligner_config)
        else:
            raise ValueError(f"未知的数据对齐器类型: {aligner_type}")
        
        # 初始化数据重采样器
        resampler_config = self.config.get("resampler", {})
        self.resampler = MultiFrequencyResampler(resampler_config)
        
        # 初始化可靠性评分器
        reliability_config = self.config.get("reliability_scorer", {})
        self.reliability_scorer = DataSourceReliabilityScorer(reliability_config)
        
        # 初始化融合器
        fusion_config = self.config.get("fusion", {})
        fusion_type = fusion_config.get("type", "weighted_average")
        
        if fusion_type == "weighted_average":
            self.fusion = WeightedAverageFusion(fusion_config)
        elif fusion_type == "kalman_filter":
            self.fusion = KalmanFilterFusion(fusion_config)
        elif fusion_type == "machine_learning":
            self.fusion = MachineLearningFusion(fusion_config)
        else:
            raise ValueError(f"未知的融合器类型: {fusion_type}")
    
    def fuse(self, data_sources: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        融合多个数据源
        
        参数:
            data_sources: 数据源字典，键为数据源名称，值为数据源DataFrame
            
        返回:
            融合后的DataFrame
        """
        if not data_sources:
            return pd.DataFrame()
        
        # 对齐数据
        self.logger.info("对齐数据...")
        aligned_data = self.aligner.align(data_sources)
        
        # 重采样数据
        self.logger.info("重采样数据...")
        resampled_data = {}
        for source_name, df in aligned_data.items():
            resampled_data[source_name] = self.resampler.resample(df)
        
        # 评估数据源可靠性
        self.logger.info("评估数据源可靠性...")
        reliability_scores = {}
        reference_source = self.config.get("reliability_scorer", {}).get("reference_source")
        reference_data = resampled_data.get(reference_source) if reference_source else None
        
        for source_name, df in resampled_data.items():
            score = self.reliability_scorer.score(source_name, df, reference_data)
            reliability_scores[source_name] = score
            self.logger.info(f"数据源 {source_name} 的可靠性评分: {score:.4f}")
        
        # 融合数据
        self.logger.info("融合数据...")
        fused_data = self.fusion.fuse(resampled_data, reliability_scores)
        
        return fused_data
    
    def get_reliability_scores(self, data_sources: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, float]]:
        """
        获取详细的可靠性评分
        
        参数:
            data_sources: 数据源字典，键为数据源名称，值为数据源DataFrame
            
        返回:
            详细评分字典，格式为 {数据源名称: {评分项: 评分值}}
        """
        if not data_sources:
            return {}
        
        # 对齐数据
        aligned_data = self.aligner.align(data_sources)
        
        # 重采样数据
        resampled_data = {}
        for source_name, df in aligned_data.items():
            resampled_data[source_name] = self.resampler.resample(df)
        
        # 评估数据源可靠性
        detailed_scores = {}
        reference_source = self.config.get("reliability_scorer", {}).get("reference_source")
        reference_data = resampled_data.get(reference_source) if reference_source else None
        
        for source_name, df in resampled_data.items():
            scores = self.reliability_scorer.get_detailed_scores(source_name, df, reference_data)
            detailed_scores[source_name] = scores
        
        return detailed_scores


class WeightedAverageFusion(BaseDataFusion):
    """
    加权平均融合
    根据数据源的可靠性评分进行加权平均
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化加权平均融合器
        
        参数:
            config: 配置字典，包含以下字段:
                - weights: 数据源权重，如果为空则使用可靠性评分作为权重
                - min_weight: 最小权重，默认为0.1
                - columns: 要融合的列，如果为空则融合所有共同的数值列
        """
        super().__init__(config)
        self.weights = self.config.get("weights", {})
        self.min_weight = self.config.get("min_weight", 0.1)
        self.columns = self.config.get("columns", [])
    
    def fuse(self, data_sources: Dict[str, pd.DataFrame], reliability_scores: Optional[Dict[str, float]] = None) -> pd.DataFrame:
        """
        融合多个数据源
        
        参数:
            data_sources: 数据源字典，键为数据源名称，值为数据源DataFrame
            reliability_scores: 可靠性评分字典，键为数据源名称，值为评分
            
        返回:
            融合后的DataFrame
        """
        if not data_sources:
            return pd.DataFrame()
        
        # 预处理数据
        processed_data = {}
        for source_name, df in data_sources.items():
            processed_data[source_name] = self.preprocess(df)
        
        # 确定要融合的列
        if self.columns:
            # 使用指定的列
            columns_to_fuse = []
            for col in self.columns:
                # 检查每个数据源是否都有该列
                if all(col in df.columns for df in processed_data.values()):
                    columns_to_fuse.append(col)
        else:
            # 找出所有数据源共有的数值列
            common_columns = set()
            for i, (source_name, df) in enumerate(processed_data.items()):
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if i == 0:
                    common_columns = set(numeric_cols)
                else:
                    common_columns &= set(numeric_cols)
            
            columns_to_fuse = list(common_columns)
        
        if not columns_to_fuse:
            self.logger.warning("没有可融合的列")
            return pd.DataFrame()
        
        # 确定权重
        weights = {}
        if self.weights:
            # 使用指定的权重
            weights = self.weights
        elif reliability_scores:
            # 使用可靠性评分作为权重
            weights = reliability_scores
        else:
            # 使用均等权重
            weight = 1.0 / len(processed_data)
            weights = {source_name: weight for source_name in processed_data}
        
        # 确保所有数据源都有权重
        for source_name in processed_data:
            if source_name not in weights:
                weights[source_name] = self.min_weight
        
        # 应用最小权重
        for source_name in weights:
            weights[source_name] = max(weights[source_name], self.min_weight)
        
        # 归一化权重
        total_weight = sum(weights.values())
        if total_weight > 0:
            for source_name in weights:
                weights[source_name] /= total_weight
        
        # 创建结果DataFrame
        # 使用第一个数据源的索引作为结果索引
        result_index = next(iter(processed_data.values())).index
        result = pd.DataFrame(index=result_index)
        
        # 对每列进行加权平均
        for col in columns_to_fuse:
            # 初始化加权和和权重和
            weighted_sum = pd.Series(0.0, index=result_index)
            weight_sum = pd.Series(0.0, index=result_index)
            
            # 计算加权和
            for source_name, df in processed_data.items():
                if col in df.columns:
                    weight = weights[source_name]
                    weighted_sum += df[col] * weight
                    weight_sum += pd.Series(weight, index=df.index)
            
            # 计算加权平均
            # 避免除以零
            weight_sum = weight_sum.replace(0, np.nan)
            result[col] = weighted_sum / weight_sum
        
        # 后处理数据
        result = self.postprocess(result)
        
        return result


class KalmanFilterFusion(BaseDataFusion):
    """
    卡尔曼滤波融合
    使用卡尔曼滤波器融合多个数据源
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化卡尔曼滤波融合器
        
        参数:
            config: 配置字典，包含以下字段:
                - process_noise: 过程噪声协方差，默认为0.01
                - measurement_noise: 测量噪声协方差，如果为空则使用可靠性评分推导
                - columns: 要融合的列，如果为空则融合所有共同的数值列
        """
        super().__init__(config)
        self.process_noise = self.config.get("process_noise", 0.01)
        self.measurement_noise = self.config.get("measurement_noise", {})
        self.columns = self.config.get("columns", [])
        
        # 存储卡尔曼滤波器
        self.filters = {}
    
    def fuse(self, data_sources: Dict[str, pd.DataFrame], reliability_scores: Optional[Dict[str, float]] = None) -> pd.DataFrame:
        """
        融合多个数据源
        
        参数:
            data_sources: 数据源字典，键为数据源名称，值为数据源DataFrame
            reliability_scores: 可靠性评分字典，键为数据源名称，值为评分
            
        返回:
            融合后的DataFrame
        """
        if not data_sources:
            return pd.DataFrame()
        
        # 预处理数据
        processed_data = {}
        for source_name, df in data_sources.items():
            processed_data[source_name] = self.preprocess(df)
        
        # 确定要融合的列
        if self.columns:
            # 使用指定的列
            columns_to_fuse = []
            for col in self.columns:
                # 检查每个数据源是否都有该列
                if all(col in df.columns for df in processed_data.values()):
                    columns_to_fuse.append(col)
        else:
            # 找出所有数据源共有的数值列
            common_columns = set()
            for i, (source_name, df) in enumerate(processed_data.items()):
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if i == 0:
                    common_columns = set(numeric_cols)
                else:
                    common_columns &= set(numeric_cols)
            
            columns_to_fuse = list(common_columns)
        
        if not columns_to_fuse:
            self.logger.warning("没有可融合的列")
            return pd.DataFrame()
        
        # 确定测量噪声
        measurement_noise = {}
        if self.measurement_noise:
            # 使用指定的测量噪声
            measurement_noise = self.measurement_noise
        elif reliability_scores:
            # 使用可靠性评分推导测量噪声
            # 可靠性评分越高，测量噪声越小
            for source_name, score in reliability_scores.items():
                if score > 0:
                    measurement_noise[source_name] = 1.0 / (score * 10)  # 将评分转换为噪声
                else:
                    measurement_noise[source_name] = 100.0  # 默认高噪声
        else:
            # 使用默认测量噪声
            for source_name in processed_data:
                measurement_noise[source_name] = 1.0
        
        # 创建结果DataFrame
        # 使用第一个数据源的索引作为结果索引
        result_index = next(iter(processed_data.values())).index
        result = pd.DataFrame(index=result_index)
        
        # 对每列应用卡尔曼滤波
        for col in columns_to_fuse:
            # 初始化卡尔曼滤波器
            if col not in self.filters:
                self.filters[col] = self._init_kalman_filter()
            
            # 获取所有数据源的该列数据
            col_data = {}
            for source_name, df in processed_data.items():
                if col in df.columns:
                    col_data[source_name] = df[col]
            
            # 应用卡尔曼滤波
            filtered_values = self._apply_kalman_filter(col_data, measurement_noise, self.filters[col])
            
            # 将结果添加到结果DataFrame
            result[col] = filtered_values
        
        # 后处理数据
        result = self.postprocess(result)
        
        return result
    
    def _init_kalman_filter(self) -> KalmanFilter:
        """
        初始化卡尔曼滤波器
        
        返回:
            卡尔曼滤波器
        """
        # 创建一个简单的一维卡尔曼滤波器
        kf = KalmanFilter(dim_x=1, dim_z=1)
        
        # 初始化状态转移矩阵
        kf.F = np.array([[1.]])
        
        # 初始化测量矩阵
        kf.H = np.array([[1.]])
        
        # 初始化过程噪声协方差
        kf.Q = np.array([[self.process_noise]])
        
        # 初始化测量噪声协方差
        # 将在应用滤波器时设置
        
        # 初始化先验误差协方差
        kf.P = np.array([[1.]])
        
        return kf
    
    def _apply_kalman_filter(self, col_data: Dict[str, pd.Series], measurement_noise: Dict[str, float], kf: KalmanFilter) -> pd.Series:
        """
        应用卡尔曼滤波
        
        参数:
            col_data: 列数据字典，键为数据源名称，值为数据序列
            measurement_noise: 测量噪声字典，键为数据源名称，值为噪声值
            kf: 卡尔曼滤波器
            
        返回:
            滤波后的数据序列
        """
        # 获取所有时间戳
        all_timestamps = set()
        for series in col_data.values():
            all_timestamps.update(series.index)
        
        # 排序时间戳
        sorted_timestamps = sorted(all_timestamps)
        
        # 初始化结果序列
        filtered_values = pd.Series(index=sorted_timestamps)
        
        # 重置滤波器状态
        kf.x = np.array([[0.]])
        kf.P = np.array([[1.]])
        
        # 对每个时间戳应用卡尔曼滤波
        for ts in sorted_timestamps:
            # 预测步骤
            kf.predict()
            
            # 更新步骤
            # 收集该时间戳的所有测量值
            measurements = []
            noises = []
            
            for source_name, series in col_data.items():
                if ts in series.index and not np.isnan(series[ts]):
                    measurements.append(series[ts])
                    noises.append(measurement_noise.get(source_name, 1.0))
            
            if measurements:
                # 如果有多个测量值，则按噪声加权平均
                if len(measurements) > 1:
                    # 计算加权平均
                    weights = [1.0 / noise for noise in noises]
                    total_weight = sum(weights)
                    weighted_sum = sum(m * w for m, w in zip(measurements, weights))
                    avg_measurement = weighted_sum / total_weight
                    
                    # 计算加权平均噪声
                    avg_noise = 1.0 / total_weight
                else:
                    avg_measurement = measurements[0]
                    avg_noise = noises[0]
                
                # 设置测量噪声
                kf.R = np.array([[avg_noise]])
                
                # 更新
                kf.update(np.array([[avg_measurement]]))
            
            # 存储滤波后的值
            filtered_values[ts] = kf.x[0, 0]
        
        return filtered_values


class MachineLearningFusion(BaseDataFusion):
    """
    机器学习融合
    使用机器学习模型融合多个数据源
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化机器学习融合器
        
        参数:
            config: 配置字典，包含以下字段:
                - model_type: 模型类型，默认为'random_forest'
                - model_params: 模型参数
                - reference_source: 参考数据源，用作训练标签
                - columns: 要融合的列，如果为空则融合所有共同的数值列
                - feature_prefix: 特征前缀，用于区分不同数据源的特征
        """
        # 在调用父类__init__之前先设置属性，避免_validate_config中的属性访问错误
        self.model_type = config.get("model_type", "random_forest")
        self.model_params = config.get("model_params", {})
        self.reference_source = config.get("reference_source")
        self.columns = config.get("columns", [])
        self.feature_prefix = config.get("feature_prefix", "src_")
        
        # 调用父类__init__
        super().__init__(config)
        
        # 存储模型
        self.models = {}
    
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        super()._validate_config()
        
        # 检查模型类型
        valid_models = ["random_forest"]
        if self.model_type not in valid_models:
            raise ValueError(f"模型类型必须是以下之一: {valid_models}")
        
        # 检查参考数据源
        if not self.reference_source:
            raise ValueError("必须指定参考数据源")
    
    def fuse(self, data_sources: Dict[str, pd.DataFrame], reliability_scores: Optional[Dict[str, float]] = None) -> pd.DataFrame:
        """
        融合多个数据源
        
        参数:
            data_sources: 数据源字典，键为数据源名称，值为数据源DataFrame
            reliability_scores: 可靠性评分字典，键为数据源名称，值为评分
            
        返回:
            融合后的DataFrame
        """
        if not data_sources:
            return pd.DataFrame()
        
        # 检查参考数据源是否存在
        if self.reference_source not in data_sources:
            self.logger.error(f"参考数据源 {self.reference_source} 不存在")
            return pd.DataFrame()
        
        # 预处理数据
        processed_data = {}
        for source_name, df in data_sources.items():
            processed_data[source_name] = self.preprocess(df)
        
        # 确定要融合的列
        if self.columns:
            # 使用指定的列
            columns_to_fuse = []
            for col in self.columns:
                # 检查参考数据源是否有该列
                if col in processed_data[self.reference_source].columns:
                    columns_to_fuse.append(col)
        else:
            # 使用参考数据源的所有数值列
            numeric_cols = processed_data[self.reference_source].select_dtypes(include=[np.number]).columns
            columns_to_fuse = list(numeric_cols)
        
        if not columns_to_fuse:
            self.logger.warning("没有可融合的列")
            return pd.DataFrame()
        
        # 创建结果DataFrame
        # 使用参考数据源的索引作为结果索引
        result_index = processed_data[self.reference_source].index
        result = pd.DataFrame(index=result_index)
        
        # 对每列应用机器学习融合
        for col in columns_to_fuse:
            # 准备训练数据
            X, y = self._prepare_training_data(processed_data, col)
            
            if X.empty or y.empty:
                self.logger.warning(f"列 {col} 的训练数据为空，使用参考数据源的数据")
                # 使用参考数据源的数据作为回退
                result[col] = processed_data[self.reference_source][col]
                continue
            
            # 训练模型
            if col not in self.models:
                self.models[col] = self._train_model(X, y)
            
            # 准备预测数据
            X_pred = self._prepare_prediction_data(processed_data, col)
            
            if X_pred.empty:
                self.logger.warning(f"列 {col} 的预测数据为空，使用参考数据源的数据")
                # 使用参考数据源的数据作为回退
                result[col] = processed_data[self.reference_source][col]
                continue
            
            # 预测
            predictions = self.models[col].predict(X_pred)
            
            # 将结果添加到结果DataFrame
            result[col] = pd.Series(predictions, index=X_pred.index)
        
        # 后处理数据
        result = self.postprocess(result)
        
        return result
    
    def _prepare_training_data(self, data_sources: Dict[str, pd.DataFrame], column: str) -> Tuple[pd.DataFrame, pd.Series]:
        """
        准备训练数据
        
        参数:
            data_sources: 数据源字典
            column: 列名
            
        返回:
            特征DataFrame和标签Series
        """
        # 获取参考数据
        reference_data = data_sources[self.reference_source]
        
        # 创建特征DataFrame
        features = pd.DataFrame(index=reference_data.index)
        
        # 添加每个数据源的特征
        feature_count = 0
        for source_name, df in data_sources.items():
            if column in df.columns:
                # 对齐索引
                aligned_series = df[column].reindex(reference_data.index)
                
                # 添加特征
                if source_name != self.reference_source:
                    feature_name = f"{self.feature_prefix}{source_name}_{column}"
                    features[feature_name] = aligned_series
                    feature_count += 1
        
        # 如果没有足够的特征，使用参考数据源自身作为特征
        if feature_count == 0 and column in reference_data.columns:
            self.logger.warning(f"列 {column} 没有足够的非参考数据源特征，使用参考数据源自身作为特征")
            features[f"{self.feature_prefix}self_{column}"] = reference_data[column]
        
        # 获取标签
        labels = reference_data[column]
        
        # 删除含有NaN的行
        valid_rows = ~features.isna().any(axis=1) & ~labels.isna()
        features = features[valid_rows]
        labels = labels[valid_rows]
        
        return features, labels
    
    def _prepare_prediction_data(self, data_sources: Dict[str, pd.DataFrame], column: str) -> pd.DataFrame:
        """
        准备预测数据
        
        参数:
            data_sources: 数据源字典
            column: 列名
            
        返回:
            特征DataFrame
        """
        # 获取参考数据索引
        reference_index = data_sources[self.reference_source].index
        
        # 创建特征DataFrame
        features = pd.DataFrame(index=reference_index)
        
        # 添加每个数据源的特征
        feature_count = 0
        for source_name, df in data_sources.items():
            if column in df.columns:
                # 对齐索引
                aligned_series = df[column].reindex(reference_index)
                
                # 添加特征
                if source_name != self.reference_source:
                    feature_name = f"{self.feature_prefix}{source_name}_{column}"
                    features[feature_name] = aligned_series
                    feature_count += 1
        
        # 如果没有足够的特征，使用参考数据源自身作为特征
        if feature_count == 0 and column in data_sources[self.reference_source].columns:
            self.logger.warning(f"列 {column} 没有足够的非参考数据源特征用于预测，使用参考数据源自身作为特征")
            features[f"{self.feature_prefix}self_{column}"] = data_sources[self.reference_source][column]
        
        return features
    
    def _train_model(self, X: pd.DataFrame, y: pd.Series) -> Any:
        """
        训练模型
        
        参数:
            X: 特征DataFrame
            y: 标签Series
            
        返回:
            训练好的模型
        """
        if self.model_type == "random_forest":
            # 设置默认参数
            params = {
                "n_estimators": 100,
                "max_depth": 10,
                "random_state": 42
            }
            
            # 更新用户指定的参数
            params.update(self.model_params)
            
            # 创建模型
            model = RandomForestRegressor(**params)
        else:
            raise ValueError(f"未知的模型类型: {self.model_type}")
        
        # 训练模型
        model.fit(X, y)
        
        return model
