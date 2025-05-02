"""
数值特征处理模块
包含数值特征处理器实现
"""

import logging
from typing import Any, Dict, List, Optional, Union, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer

from .base import BaseNumericalEncoder


class NumericalFeatureProcessor(BaseNumericalEncoder):
    """
    数值特征处理器
    处理数值特征，包括缺失值填充、标准化、归一化和降维
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数值特征处理器
        
        参数:
            config: 配置字典，包含以下字段:
                - scaler: 缩放器类型，可选值为'standard', 'minmax', 'robust'，默认为'standard'
                - imputer: 缺失值填充策略，可选值为'mean', 'median', 'most_frequent', 'constant'，默认为'mean'
                - imputer_fill_value: 当imputer为'constant'时的填充值，默认为0
                - use_pca: 是否使用PCA降维，默认为False
                - pca_n_components: PCA组件数，默认为0.95（保留95%的方差）
                - feature_selection: 特征选择方法，可选值为None, 'variance_threshold'，默认为None
                - variance_threshold: 方差阈值，当feature_selection为'variance_threshold'时使用，默认为0.0
                - columns: 要处理的列，如果为空则处理所有数值列
        """
        super().__init__(config)
        
        self.scaler_type = self.config.get("scaler", "standard")
        self.imputer_strategy = self.config.get("imputer", "mean")
        self.imputer_fill_value = self.config.get("imputer_fill_value", 0)
        self.use_pca = self.config.get("use_pca", False)
        self.pca_n_components = self.config.get("pca_n_components", 0.95)
        self.feature_selection = self.config.get("feature_selection", None)
        self.variance_threshold = self.config.get("variance_threshold", 0.0)
        self.columns = self.config.get("columns", [])
        
        # 初始化处理器
        self._init_processors()
        
        # 存储列信息
        self.fitted_columns = []
        self.feature_names = []
        self.output_dim = 0
        
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        super()._validate_config()
        
        # 检查缩放器类型
        valid_scalers = ["standard", "minmax", "robust", None]
        if self.config.get("scaler") not in valid_scalers:
            raise ValueError(f"缩放器类型必须是以下之一: {valid_scalers}")
        
        # 检查缺失值填充策略
        valid_imputers = ["mean", "median", "most_frequent", "constant", None]
        if self.config.get("imputer") not in valid_imputers:
            raise ValueError(f"缺失值填充策略必须是以下之一: {valid_imputers}")
        
        # 检查特征选择方法
        valid_feature_selections = [None, "variance_threshold"]
        if self.config.get("feature_selection") not in valid_feature_selections:
            raise ValueError(f"特征选择方法必须是以下之一: {valid_feature_selections}")
    
    def _init_processors(self) -> None:
        """初始化处理器"""
        # 初始化缺失值填充器
        if self.imputer_strategy is not None:
            self.imputer = SimpleImputer(
                strategy=self.imputer_strategy,
                fill_value=self.imputer_fill_value
            )
        else:
            self.imputer = None
        
        # 初始化缩放器
        if self.scaler_type == "standard":
            self.scaler = StandardScaler()
        elif self.scaler_type == "minmax":
            self.scaler = MinMaxScaler()
        elif self.scaler_type == "robust":
            self.scaler = RobustScaler()
        else:
            self.scaler = None
        
        # 初始化PCA
        if self.use_pca:
            self.pca = PCA(n_components=self.pca_n_components)
        else:
            self.pca = None
        
        # 初始化特征选择器
        if self.feature_selection == "variance_threshold":
            from sklearn.feature_selection import VarianceThreshold
            self.feature_selector = VarianceThreshold(threshold=self.variance_threshold)
        else:
            self.feature_selector = None
    
    def fit(self, data: pd.DataFrame) -> 'NumericalFeatureProcessor':
        """
        拟合数值特征处理器
        
        参数:
            data: 数值特征DataFrame
            
        返回:
            拟合后的处理器
        """
        # 选择要处理的列
        if self.columns:
            # 检查列是否存在
            missing_columns = [col for col in self.columns if col not in data.columns]
            if missing_columns:
                self.logger.warning(f"以下列不存在: {missing_columns}")
            
            # 过滤出存在的列
            columns = [col for col in self.columns if col in data.columns]
        else:
            # 选择所有数值列
            columns = data.select_dtypes(include=[np.number]).columns.tolist()
        
        if not columns:
            raise ValueError("没有可处理的数值列")
        
        # 存储列信息
        self.fitted_columns = columns
        
        # 提取特征
        X = data[columns].values
        
        # 填充缺失值
        if self.imputer is not None:
            X = self.imputer.fit_transform(X)
        
        # 特征选择
        if self.feature_selector is not None:
            X = self.feature_selector.fit_transform(X)
            # 更新列名
            selected_indices = self.feature_selector.get_support(indices=True)
            self.feature_names = [columns[i] for i in selected_indices]
        else:
            self.feature_names = columns
        
        # 缩放特征
        if self.scaler is not None:
            X = self.scaler.fit_transform(X)
        
        # PCA降维
        if self.pca is not None:
            X = self.pca.fit_transform(X)
            # 更新特征名
            self.feature_names = [f"PC{i+1}" for i in range(X.shape[1])]
        
        # 存储输出维度
        self.output_dim = X.shape[1]
        
        return self
    
    def transform(self, data: pd.DataFrame) -> np.ndarray:
        """
        转换数值特征
        
        参数:
            data: 数值特征DataFrame
            
        返回:
            转换后的特征向量
        """
        if not self.fitted_columns:
            raise ValueError("处理器尚未拟合")
        
        # 检查列是否存在
        missing_columns = [col for col in self.fitted_columns if col not in data.columns]
        if missing_columns:
            raise ValueError(f"以下列不存在: {missing_columns}")
        
        # 提取特征
        X = data[self.fitted_columns].values
        
        # 填充缺失值
        if self.imputer is not None:
            X = self.imputer.transform(X)
        
        # 特征选择
        if self.feature_selector is not None:
            X = self.feature_selector.transform(X)
        
        # 缩放特征
        if self.scaler is not None:
            X = self.scaler.transform(X)
        
        # PCA降维
        if self.pca is not None:
            X = self.pca.transform(X)
        
        return X
    
    def get_feature_names(self) -> List[str]:
        """
        获取特征名称
        
        返回:
            特征名称列表
        """
        if not self.fitted_columns:
            raise ValueError("处理器尚未拟合")
        
        return self.feature_names
    
    def get_output_dim(self) -> int:
        """
        获取输出维度
        
        返回:
            输出特征向量的维度
        """
        if not self.fitted_columns:
            raise ValueError("处理器尚未拟合")
        
        return self.output_dim
