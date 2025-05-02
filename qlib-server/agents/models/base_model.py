#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基础模型类定义
"""
import os
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Union, Optional, Any, Tuple
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BaseModel(ABC):
    """
    投资智能体基础模型类
    所有智能体模型必须继承此类并实现其抽象方法
    """
    
    def __init__(self, 
                 model_name: str, 
                 data_dir: str = '/data/qlib',
                 config: Optional[Dict] = None):
        """
        初始化基础模型
        
        参数:
            model_name: 模型名称
            data_dir: 数据目录路径
            config: 模型配置参数
        """
        self.model_name = model_name
        self.data_dir = data_dir
        self.config = config or {}
        self.model = None
        self.is_trained = False
        self.feature_importance = None
        self.performance_metrics = {}
        
        # 检查数据目录是否存在
        if not os.path.exists(data_dir):
            logger.warning(f"数据目录 {data_dir} 不存在，将在训练时创建")
    
    @abstractmethod
    def preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        数据预处理方法
        
        参数:
            data: 输入数据
            
        返回:
            处理后的数据
        """
        pass
    
    @abstractmethod
    def train(self, 
              train_data: pd.DataFrame, 
              valid_data: Optional[pd.DataFrame] = None,
              **kwargs) -> Dict:
        """
        模型训练方法
        
        参数:
            train_data: 训练数据
            valid_data: 验证数据
            **kwargs: 其他训练参数
            
        返回:
            训练结果指标
        """
        pass
    
    @abstractmethod
    def predict(self, data: pd.DataFrame) -> np.ndarray:
        """
        模型预测方法
        
        参数:
            data: 输入数据
            
        返回:
            预测结果
        """
        pass
    
    @abstractmethod
    def evaluate(self, 
                 test_data: pd.DataFrame, 
                 predictions: Optional[np.ndarray] = None) -> Dict:
        """
        模型评估方法
        
        参数:
            test_data: 测试数据
            predictions: 预测结果，如果为None则调用predict方法生成
            
        返回:
            评估指标
        """
        pass
    
    def save_model(self, path: str) -> None:
        """
        保存模型
        
        参数:
            path: 保存路径
        """
        if not self.is_trained:
            raise ValueError("模型尚未训练，无法保存")
        
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        
        try:
            # 实现具体保存逻辑
            logger.info(f"模型已保存至 {path}")
        except Exception as e:
            logger.error(f"保存模型失败: {str(e)}")
            raise
    
    def load_model(self, path: str) -> None:
        """
        加载模型
        
        参数:
            path: 模型路径
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"模型文件 {path} 不存在")
        
        try:
            # 实现具体加载逻辑
            self.is_trained = True
            logger.info(f"模型已从 {path} 加载")
        except Exception as e:
            logger.error(f"加载模型失败: {str(e)}")
            raise
    
    def get_feature_importance(self) -> pd.DataFrame:
        """
        获取特征重要性
        
        返回:
            特征重要性DataFrame
        """
        if not self.is_trained:
            raise ValueError("模型尚未训练，无法获取特征重要性")
        
        if self.feature_importance is None:
            logger.warning("该模型不支持特征重要性分析")
            return pd.DataFrame()
        
        return self.feature_importance
    
    def get_performance_metrics(self) -> Dict:
        """
        获取模型性能指标
        
        返回:
            性能指标字典
        """
        return self.performance_metrics
