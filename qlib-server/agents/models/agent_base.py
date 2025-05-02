#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
投资智能体基类定义
"""
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Union, Optional, Any, Tuple
import logging
from enum import Enum

from .base_model import BaseModel

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RiskAppetite(Enum):
    """风险偏好枚举"""
    CONSERVATIVE = 'conservative'  # 保守型
    BALANCED = 'balanced'          # 平衡型
    AGGRESSIVE = 'aggressive'      # 激进型

class InvestmentAgent(BaseModel):
    """
    投资智能体基类
    继承BaseModel并扩展投资智能体特定功能
    """
    
    def __init__(self, 
                 model_name: str,
                 risk_appetite: RiskAppetite,
                 data_dir: str = '/data/qlib',
                 config: Optional[Dict] = None):
        """
        初始化投资智能体
        
        参数:
            model_name: 模型名称
            risk_appetite: 风险偏好
            data_dir: 数据目录路径
            config: 模型配置参数
        """
        super().__init__(model_name, data_dir, config)
        self.risk_appetite = risk_appetite
        self.position_limits = self._set_position_limits()
        self.portfolio = None
        self.transaction_cost_rate = self.config.get('transaction_cost_rate', 0.001)
        self.max_stock_weight = self.config.get('max_stock_weight', 0.1)
        
    def _set_position_limits(self) -> Dict:
        """
        根据风险偏好设置仓位限制
        
        返回:
            仓位限制参数字典
        """
        if self.risk_appetite == RiskAppetite.CONSERVATIVE:
            return {
                'max_position': 0.7,  # 最大仓位
                'single_position_limit': 0.05,  # 单只股票最大仓位
                'industry_position_limit': 0.2,  # 行业最大仓位
                'turnover_limit': 0.3,  # 换手率限制
            }
        elif self.risk_appetite == RiskAppetite.BALANCED:
            return {
                'max_position': 0.9,
                'single_position_limit': 0.08,
                'industry_position_limit': 0.3,
                'turnover_limit': 0.5,
            }
        elif self.risk_appetite == RiskAppetite.AGGRESSIVE:
            return {
                'max_position': 1.0,
                'single_position_limit': 0.12,
                'industry_position_limit': 0.4,
                'turnover_limit': 0.8,
            }
        else:
            raise ValueError(f"不支持的风险偏好类型: {self.risk_appetite}")
    
    def preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        数据预处理方法
        
        参数:
            data: 输入数据
            
        返回:
            处理后的数据
        """
        # 基础数据清洗
        data = data.copy()
        
        # 处理缺失值
        data = data.fillna(method='ffill').fillna(0)
        
        # 去除异常值
        for col in data.select_dtypes(include=[np.number]).columns:
            mean = data[col].mean()
            std = data[col].std()
            data[col] = data[col].clip(mean - 3 * std, mean + 3 * std)
        
        # 特征标准化
        for col in data.select_dtypes(include=[np.number]).columns:
            if col != 'label' and 'date' not in col.lower() and 'time' not in col.lower():
                mean = data[col].mean()
                std = data[col].std()
                if std > 0:
                    data[col] = (data[col] - mean) / std
        
        return data
    
    def evaluate(self, test_data: pd.DataFrame, predictions: Optional[np.ndarray] = None) -> Dict:
        """
        模型评估方法
        
        参数:
            test_data: 测试数据
            predictions: 预测结果，如果为None则调用predict方法生成
            
        返回:
            评估指标
        """
        if predictions is None:
            predictions = self.predict(test_data)
        
        # 计算基础评估指标
        y_true = test_data['label'].values if 'label' in test_data.columns else None
        
        metrics = {}
        
        if y_true is not None:
            # 计算IC值
            ic = np.corrcoef(predictions, y_true)[0, 1]
            metrics['IC'] = ic
            
            # 计算RMSE
            rmse = np.sqrt(np.mean((predictions - y_true) ** 2))
            metrics['RMSE'] = rmse
            
            # 计算排序准确率
            rank_pred = pd.Series(predictions).rank(pct=True)
            rank_true = pd.Series(y_true).rank(pct=True)
            rank_corr = np.corrcoef(rank_pred, rank_true)[0, 1]
            metrics['Rank_Correlation'] = rank_corr
        
        # 保存评估指标
        self.performance_metrics.update(metrics)
        
        return metrics
    
    def generate_portfolio(self, 
                          predictions: np.ndarray, 
                          stock_pool: List[str],
                          date: str) -> pd.DataFrame:
        """
        根据预测结果生成投资组合
        
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
        
        # 根据风险偏好确定选股数量
        if self.risk_appetite == RiskAppetite.CONSERVATIVE:
            top_k = int(len(pred_df) * 0.1)  # 保守型选择前10%
        elif self.risk_appetite == RiskAppetite.BALANCED:
            top_k = int(len(pred_df) * 0.2)  # 平衡型选择前20%
        else:
            top_k = int(len(pred_df) * 0.3)  # 激进型选择前30%
        
        # 至少选择5只股票
        top_k = max(5, top_k)
        
        # 选择TopK股票
        selected = pred_df.iloc[:top_k]
        
        # 计算权重
        total_pred = selected['prediction'].sum()
        if total_pred > 0:
            selected['weight'] = selected['prediction'] / total_pred
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
    
    def backtest(self, 
                start_date: str, 
                end_date: str, 
                data: pd.DataFrame,
                benchmark: Optional[pd.DataFrame] = None) -> Dict:
        """
        回测方法
        
        参数:
            start_date: 开始日期
            end_date: 结束日期
            data: 回测数据
            benchmark: 基准数据
            
        返回:
            回测结果指标
        """
        if not self.is_trained:
            raise ValueError("模型尚未训练，无法进行回测")
        
        # 实现回测逻辑
        logger.info(f"开始回测，时间范围: {start_date} 至 {end_date}")
        
        # 回测结果指标
        backtest_metrics = {
            'annualized_return': 0.0,
            'annualized_volatility': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'turnover_rate': 0.0,
        }
        
        # 更新性能指标
        self.performance_metrics.update(backtest_metrics)
        
        return backtest_metrics
    
    def explain(self) -> Dict:
        """
        解释模型决策
        
        返回:
            决策解释字典
        """
        if not self.is_trained:
            raise ValueError("模型尚未训练，无法解释决策")
        
        explanation = {
            'feature_importance': self.get_feature_importance(),
            'risk_appetite': self.risk_appetite.value,
            'position_limits': self.position_limits,
            'model_parameters': {},  # 子类实现具体参数
        }
        
        return explanation
