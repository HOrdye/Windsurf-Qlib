#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
保守型投资智能体实现
"""
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Union, Optional, Any, Tuple
import logging
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit
import joblib

from .agent_base import InvestmentAgent, RiskAppetite

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConservativeAgent(InvestmentAgent):
    """
    保守型投资智能体
    特点：
    1. 低风险偏好，追求稳定收益
    2. 偏好大盘蓝筹股和高股息股票
    3. 较低的换手率
    4. 严格的风险控制
    """
    
    def __init__(self, 
                 model_name: str = "ConservativeAgent",
                 data_dir: str = '/data/qlib',
                 config: Optional[Dict] = None):
        """
        初始化保守型投资智能体
        
        参数:
            model_name: 模型名称
            data_dir: 数据目录路径
            config: 模型配置参数
        """
        default_config = {
            'n_estimators': 100,
            'max_depth': 5,
            'min_samples_split': 10,
            'min_samples_leaf': 5,
            'random_state': 42,
            'n_jobs': -1,
            'transaction_cost_rate': 0.0005,  # 较低交易成本
            'max_stock_weight': 0.05,         # 单只股票最大权重
            'feature_selection_threshold': 0.01,  # 特征重要性阈值
        }
        
        if config:
            default_config.update(config)
        
        super().__init__(model_name, RiskAppetite.CONSERVATIVE, data_dir, default_config)
        self.model = None
        self.selected_features = None
    
    def preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        数据预处理方法，保守型策略更关注基本面和低波动性指标
        
        参数:
            data: 输入数据
            
        返回:
            处理后的数据
        """
        # 调用基类的预处理方法
        data = super().preprocess(data)
        
        # 保守型策略特有的预处理逻辑
        # 1. 添加波动率特征
        if 'close' in data.columns and 'open' in data.columns:
            # 计算日内波动率
            data['intraday_volatility'] = (data['high'] - data['low']) / data['open']
            
            # 计算N日波动率 (20日)
            data['volatility_20d'] = data['close'].pct_change().rolling(20).std()
            
        # 2. 添加股息率特征（如果有）
        if 'dividend' in data.columns and 'close' in data.columns:
            data['dividend_yield'] = data['dividend'] / data['close']
        
        # 3. 添加市值因子（偏好大盘股）
        if 'market_cap' in data.columns:
            data['log_market_cap'] = np.log(data['market_cap'])
        
        return data
    
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
        logger.info(f"开始训练保守型智能体模型: {self.model_name}")
        
        # 准备特征和标签
        X_train = train_data.drop(['label', 'date', 'stock_id'], axis=1, errors='ignore')
        y_train = train_data['label'].values
        
        # 初始化随机森林模型（保守型策略使用较为稳定的模型）
        self.model = RandomForestRegressor(
            n_estimators=self.config['n_estimators'],
            max_depth=self.config['max_depth'],
            min_samples_split=self.config['min_samples_split'],
            min_samples_leaf=self.config['min_samples_leaf'],
            random_state=self.config['random_state'],
            n_jobs=self.config['n_jobs']
        )
        
        # 训练模型
        self.model.fit(X_train, y_train)
        
        # 计算特征重要性
        feature_importance = pd.DataFrame({
            'feature': X_train.columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        # 特征选择（保留重要性大于阈值的特征）
        threshold = self.config['feature_selection_threshold']
        self.selected_features = feature_importance[feature_importance['importance'] > threshold]['feature'].tolist()
        logger.info(f"选择了 {len(self.selected_features)}/{len(X_train.columns)} 个特征")
        
        # 保存特征重要性
        self.feature_importance = feature_importance
        
        # 如果有验证集，计算验证集性能
        metrics = {}
        if valid_data is not None:
            X_valid = valid_data.drop(['label', 'date', 'stock_id'], axis=1, errors='ignore')
            y_valid = valid_data['label'].values
            
            # 在验证集上预测
            valid_pred = self.model.predict(X_valid)
            
            # 计算验证集指标
            valid_metrics = self._calculate_metrics(y_valid, valid_pred)
            metrics['valid'] = valid_metrics
            logger.info(f"验证集性能: {valid_metrics}")
        
        # 计算训练集性能
        train_pred = self.model.predict(X_train)
        train_metrics = self._calculate_metrics(y_train, train_pred)
        metrics['train'] = train_metrics
        logger.info(f"训练集性能: {train_metrics}")
        
        # 更新模型状态和性能指标
        self.is_trained = True
        self.performance_metrics.update(metrics)
        
        return metrics
    
    def predict(self, data: pd.DataFrame) -> np.ndarray:
        """
        模型预测方法
        
        参数:
            data: 输入数据
            
        返回:
            预测结果
        """
        if not self.is_trained:
            raise ValueError("模型尚未训练，无法进行预测")
        
        # 准备特征
        X = data.drop(['label', 'date', 'stock_id'], axis=1, errors='ignore')
        
        # 如果有选定的特征，只使用这些特征
        if self.selected_features:
            available_features = [f for f in self.selected_features if f in X.columns]
            X = X[available_features]
        
        # 进行预测
        predictions = self.model.predict(X)
        
        return predictions
    
    def _calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
        """
        计算评估指标
        
        参数:
            y_true: 真实标签
            y_pred: 预测值
            
        返回:
            评估指标字典
        """
        # 计算IC值
        ic = np.corrcoef(y_pred, y_true)[0, 1]
        
        # 计算RMSE
        rmse = np.sqrt(np.mean((y_pred - y_true) ** 2))
        
        # 计算排序准确率
        rank_pred = pd.Series(y_pred).rank(pct=True)
        rank_true = pd.Series(y_true).rank(pct=True)
        rank_corr = np.corrcoef(rank_pred, rank_true)[0, 1]
        
        return {
            'IC': ic,
            'RMSE': rmse,
            'Rank_Correlation': rank_corr
        }
    
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
            # 保存模型
            model_path = f"{path}.joblib"
            joblib.dump(self.model, model_path)
            
            # 保存元数据
            metadata = {
                'model_name': self.model_name,
                'risk_appetite': self.risk_appetite.value,
                'config': self.config,
                'selected_features': self.selected_features,
                'feature_importance': self.feature_importance.to_dict() if self.feature_importance is not None else None,
                'performance_metrics': self.performance_metrics
            }
            metadata_path = f"{path}_metadata.joblib"
            joblib.dump(metadata, metadata_path)
            
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
        model_path = f"{path}.joblib"
        metadata_path = f"{path}_metadata.joblib"
        
        if not os.path.exists(model_path) or not os.path.exists(metadata_path):
            raise FileNotFoundError(f"模型文件 {path} 不存在")
        
        try:
            # 加载模型
            self.model = joblib.load(model_path)
            
            # 加载元数据
            metadata = joblib.load(metadata_path)
            self.model_name = metadata['model_name']
            self.config = metadata['config']
            self.selected_features = metadata['selected_features']
            
            if metadata['feature_importance']:
                self.feature_importance = pd.DataFrame(metadata['feature_importance'])
            
            self.performance_metrics = metadata['performance_metrics']
            
            self.is_trained = True
            logger.info(f"模型已从 {path} 加载")
        except Exception as e:
            logger.error(f"加载模型失败: {str(e)}")
            raise
    
    def explain(self) -> Dict:
        """
        解释模型决策
        
        返回:
            决策解释字典
        """
        explanation = super().explain()
        
        # 添加保守型智能体特有的解释
        explanation['model_parameters'] = {
            'n_estimators': self.config['n_estimators'],
            'max_depth': self.config['max_depth'],
            'min_samples_split': self.config['min_samples_split'],
            'min_samples_leaf': self.config['min_samples_leaf'],
        }
        
        explanation['strategy_focus'] = [
            '偏好大盘蓝筹股',
            '低波动性策略',
            '高股息收益率',
            '严格风险控制'
        ]
        
        if self.selected_features:
            explanation['top_features'] = self.selected_features[:10]
        
        return explanation
