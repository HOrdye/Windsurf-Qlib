#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
激进型投资智能体实现
"""
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Union, Optional, Any, Tuple
import logging
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
import joblib

from .agent_base import InvestmentAgent, RiskAppetite

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AggressiveAgent(InvestmentAgent):
    """
    激进型投资智能体
    特点：
    1. 高风险偏好，追求高收益
    2. 偏好成长型股票和高Beta股票
    3. 较高的换手率
    4. 更激进的仓位管理
    """
    
    def __init__(self, 
                 model_name: str = "AggressiveAgent",
                 data_dir: str = '/data/qlib',
                 config: Optional[Dict] = None):
        """
        初始化激进型投资智能体
        
        参数:
            model_name: 模型名称
            data_dir: 数据目录路径
            config: 模型配置参数
        """
        default_config = {
            'n_estimators': 300,
            'max_depth': 10,
            'learning_rate': 0.1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'transaction_cost_rate': 0.0015,  # 较高交易成本（因为换手率高）
            'max_stock_weight': 0.12,         # 单只股票最大权重
            'feature_selection_threshold': 0.003,  # 特征重要性阈值
        }
        
        if config:
            default_config.update(config)
        
        super().__init__(model_name, RiskAppetite.AGGRESSIVE, data_dir, default_config)
        self.model = None
        self.selected_features = None
    
    def preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        数据预处理方法，激进型策略更关注技术面和动量指标
        
        参数:
            data: 输入数据
            
        返回:
            处理后的数据
        """
        # 调用基类的预处理方法
        data = super().preprocess(data)
        
        # 激进型策略特有的预处理逻辑
        # 1. 添加更多动量特征
        if 'close' in data.columns:
            # 计算多周期动量
            for period in [3, 5, 10, 20, 30, 60]:
                data[f'momentum_{period}d'] = data['close'].pct_change(period)
            
            # 计算动量加速度
            data['momentum_accel_5_10'] = data['momentum_5d'] - data['momentum_10d']
            data['momentum_accel_10_20'] = data['momentum_10d'] - data['momentum_20d']
            data['momentum_accel_20_60'] = data['momentum_20d'] - data['momentum_60d']
        
        # 2. 添加波动率特征
        if 'close' in data.columns and 'high' in data.columns and 'low' in data.columns:
            # 计算波动率
            for period in [5, 10, 20]:
                data[f'volatility_{period}d'] = data['close'].pct_change().rolling(period).std()
            
            # 计算真实波动幅度均值
            data['atr_5'] = (data['high'] - data['low']).rolling(5).mean() / data['close']
            data['atr_10'] = (data['high'] - data['low']).rolling(10).mean() / data['close']
        
        # 3. 添加交易量特征
        if 'volume' in data.columns:
            # 计算交易量变化
            data['volume_change_5d'] = data['volume'].pct_change(5)
            data['volume_change_10d'] = data['volume'].pct_change(10)
            
            # 计算交易量相对均值
            data['volume_ratio_5d'] = data['volume'] / data['volume'].rolling(5).mean()
            data['volume_ratio_10d'] = data['volume'] / data['volume'].rolling(10).mean()
        
        # 4. 添加技术指标
        if 'close' in data.columns and 'high' in data.columns and 'low' in data.columns:
            # RSI指标
            delta = data['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss
            data['rsi_14'] = 100 - (100 / (1 + rs))
            
            # MACD指标
            exp1 = data['close'].ewm(span=12, adjust=False).mean()
            exp2 = data['close'].ewm(span=26, adjust=False).mean()
            data['macd'] = exp1 - exp2
            data['macd_signal'] = data['macd'].ewm(span=9, adjust=False).mean()
            data['macd_hist'] = data['macd'] - data['macd_signal']
        
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
        logger.info(f"开始训练激进型智能体模型: {self.model_name}")
        
        # 准备特征和标签
        X_train = train_data.drop(['label', 'date', 'stock_id'], axis=1, errors='ignore')
        y_train = train_data['label'].values
        
        # 初始化XGBoost模型（激进型策略使用更复杂的模型）
        self.model = xgb.XGBRegressor(
            n_estimators=self.config['n_estimators'],
            max_depth=self.config['max_depth'],
            learning_rate=self.config['learning_rate'],
            subsample=self.config['subsample'],
            colsample_bytree=self.config['colsample_bytree'],
            random_state=self.config['random_state'],
            tree_method='hist',  # 更快的训练方法
            n_jobs=-1  # 使用所有CPU核心
        )
        
        # 训练模型
        eval_set = None
        if valid_data is not None:
            X_valid = valid_data.drop(['label', 'date', 'stock_id'], axis=1, errors='ignore')
            y_valid = valid_data['label'].values
            eval_set = [(X_valid, y_valid)]
        
        self.model.fit(
            X_train, y_train,
            eval_set=eval_set,
            eval_metric=['rmse', 'mae'],
            early_stopping_rounds=50,
            verbose=True
        )
        
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
        
        # 计算MAE
        mae = np.mean(np.abs(y_pred - y_true))
        
        # 计算排序准确率
        rank_pred = pd.Series(y_pred).rank(pct=True)
        rank_true = pd.Series(y_true).rank(pct=True)
        rank_corr = np.corrcoef(rank_pred, rank_true)[0, 1]
        
        # 计算方向准确率
        direction_accuracy = np.mean((y_pred > 0) == (y_true > 0))
        
        # 计算Top/Bottom分组收益差
        n = len(y_true)
        top_n = max(1, n // 10)  # 前10%
        
        # 按预测值排序
        sorted_indices = np.argsort(y_pred)
        top_indices = sorted_indices[-top_n:]
        bottom_indices = sorted_indices[:top_n]
        
        # 计算Top组和Bottom组的实际收益
        top_return = np.mean(y_true[top_indices])
        bottom_return = np.mean(y_true[bottom_indices])
        return_spread = top_return - bottom_return
        
        return {
            'IC': ic,
            'RMSE': rmse,
            'MAE': mae,
            'Rank_Correlation': rank_corr,
            'Direction_Accuracy': direction_accuracy,
            'Return_Spread': return_spread
        }
    
    def generate_portfolio(self, 
                          predictions: np.ndarray, 
                          stock_pool: List[str],
                          date: str) -> pd.DataFrame:
        """
        根据预测结果生成投资组合，激进型策略更集中于高收益预期的股票
        
        参数:
            predictions: 预测结果
            stock_pool: 股票池
            date: 日期
            
        返回:
            投资组合DataFrame，包含股票代码和权重
        """
        # 创建预测结果DataFrame
        pred_df = pd.DataFrame({
            'stock_code': stock_pool,
            'prediction': predictions,
            'date': date
        })
        
        # 根据预测值排序
        pred_df = pred_df.sort_values('prediction', ascending=False)
        
        # 选择前30%的股票
        top_k = max(5, int(len(pred_df) * 0.3))
        selected = pred_df.iloc[:top_k]
        
        # 对预测值进行指数变换，增强权重差异
        selected['exp_pred'] = np.exp(selected['prediction'] * 10)
        
        # 计算权重
        total_exp_pred = selected['exp_pred'].sum()
        if total_exp_pred > 0:
            selected['weight'] = selected['exp_pred'] / total_exp_pred
        else:
            # 如果预测值之和不为正，则等权重配置
            selected['weight'] = 1.0 / len(selected)
        
        # 应用单只股票最大仓位限制
        max_weight = self.position_limits['single_position_limit']
        selected['weight'] = selected['weight'].clip(upper=max_weight)
        
        # 重新归一化权重
        selected['weight'] = selected['weight'] / selected['weight'].sum()
        
        # 应用最大总仓位限制
        selected['weight'] = selected['weight'] * self.position_limits['max_position']
        
        # 保存投资组合
        self.portfolio = selected[['stock_code', 'weight', 'date']]
        
        return self.portfolio
    
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
            model_path = f"{path}.json"
            self.model.save_model(model_path)
            
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
        model_path = f"{path}.json"
        metadata_path = f"{path}_metadata.joblib"
        
        if not os.path.exists(model_path) or not os.path.exists(metadata_path):
            raise FileNotFoundError(f"模型文件 {path} 不存在")
        
        try:
            # 加载模型
            self.model = xgb.XGBRegressor()
            self.model.load_model(model_path)
            
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
        
        # 添加激进型智能体特有的解释
        explanation['model_parameters'] = {
            'n_estimators': self.config['n_estimators'],
            'max_depth': self.config['max_depth'],
            'learning_rate': self.config['learning_rate'],
            'subsample': self.config['subsample'],
            'colsample_bytree': self.config['colsample_bytree'],
        }
        
        explanation['strategy_focus'] = [
            '偏好高成长性股票',
            '高动量策略',
            '较高换手率',
            '集中持仓于高预期收益股票',
            '技术指标驱动'
        ]
        
        if self.selected_features:
            explanation['top_features'] = self.selected_features[:10]
        
        return explanation
