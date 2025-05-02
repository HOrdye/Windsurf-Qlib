#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Alpha验证模块，用于评估和验证提取的Alpha信号的质量和性能
"""
import logging
import json
import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd
import numpy as np
from .alpha_extractor import AlphaSignal

# 设置日志
logger = logging.getLogger(__name__)

class AlphaValidationResult:
    """Alpha信号验证结果类"""
    
    def __init__(self, 
                 signal_id: str,
                 signal_name: str,
                 validation_date: str = None,
                 is_valid: bool = False,
                 validation_score: float = None,
                 metrics: Dict[str, float] = None,
                 error_message: str = None,
                 details: Dict[str, Any] = None):
        """
        初始化验证结果
        
        参数:
            signal_id: 信号ID
            signal_name: 信号名称
            validation_date: 验证日期
            is_valid: 是否有效
            validation_score: 验证得分
            metrics: 验证指标
            error_message: 错误信息
            details: 详细结果
        """
        self.signal_id = signal_id
        self.signal_name = signal_name
        self.validation_date = validation_date or datetime.datetime.now().strftime("%Y-%m-%d")
        self.is_valid = is_valid
        self.validation_score = validation_score
        self.metrics = metrics or {}
        self.error_message = error_message
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将验证结果转换为字典
        
        返回:
            结果字典
        """
        return {
            "signal_id": self.signal_id,
            "signal_name": self.signal_name,
            "validation_date": self.validation_date,
            "is_valid": self.is_valid,
            "validation_score": self.validation_score,
            "metrics": self.metrics,
            "error_message": self.error_message,
            "details": self.details
        }
    
    def to_json(self) -> str:
        """
        将验证结果转换为JSON
        
        返回:
            JSON字符串
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlphaValidationResult':
        """
        从字典创建验证结果
        
        参数:
            data: 结果字典
            
        返回:
            验证结果实例
        """
        return cls(
            signal_id=data.get("signal_id"),
            signal_name=data.get("signal_name"),
            validation_date=data.get("validation_date"),
            is_valid=data.get("is_valid", False),
            validation_score=data.get("validation_score"),
            metrics=data.get("metrics"),
            error_message=data.get("error_message"),
            details=data.get("details")
        )


class BaseAlphaValidator:
    """Alpha信号验证器基类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化验证器
        
        参数:
            config: 配置参数
        """
        self.config = config or {}
        self.results = []
    
    def validate(self, signals: List[AlphaSignal]) -> List[AlphaValidationResult]:
        """
        验证Alpha信号
        
        参数:
            signals: Alpha信号列表
            
        返回:
            验证结果列表
        """
        raise NotImplementedError("子类必须实现validate方法")
    
    def save_results(self, results: List[AlphaValidationResult], output_path: str) -> str:
        """
        保存验证结果
        
        参数:
            results: 验证结果列表
            output_path: 输出路径
            
        返回:
            保存的文件路径
        """
        try:
            results_data = [result.to_dict() for result in results]
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存 {len(results)} 个验证结果到 {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"保存验证结果失败: {e}")
            return ""


class BasicValidator(BaseAlphaValidator):
    """基本Alpha信号验证器，检查信号的格式和完整性"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化基本验证器
        
        参数:
            config: 配置参数，可包含:
                - required_fields: 必需字段列表
                - minimum_confidence: 最低置信度
                - minimum_description_length: 最短描述长度
        """
        super().__init__(config)
        
        # 必需字段
        self.required_fields = self.config.get('required_fields', [
            'name', 'description', 'source', 'signal_type', 'direction'
        ])
        
        # 最低置信度
        self.minimum_confidence = self.config.get('minimum_confidence', 0.6)
        
        # 最短描述长度
        self.minimum_description_length = self.config.get('minimum_description_length', 30)
        
        # 有效的信号类型
        self.valid_signal_types = self.config.get('valid_signal_types', [
            'fundamental', 'technical', 'sentiment'
        ])
        
        # 有效的方向
        self.valid_directions = self.config.get('valid_directions', [
            'positive', 'negative', 'neutral'
        ])
        
        # 有效的时间范围
        self.valid_time_horizons = self.config.get('valid_time_horizons', [
            'short_term', 'medium_term', 'long_term'
        ])
    
    def validate(self, signals: List[AlphaSignal]) -> List[AlphaValidationResult]:
        """
        验证Alpha信号
        
        参数:
            signals: Alpha信号列表
            
        返回:
            验证结果列表
        """
        results = []
        
        for signal in signals:
            # 生成唯一ID
            signal_id = f"{signal.name}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # 验证结果初始化
            validation_result = AlphaValidationResult(
                signal_id=signal_id,
                signal_name=signal.name
            )
            
            # 验证必需字段
            missing_fields = self._check_missing_fields(signal)
            
            # 验证置信度
            confidence_valid = self._check_confidence(signal)
            
            # 验证描述长度
            description_valid = self._check_description_length(signal)
            
            # 验证信号类型
            signal_type_valid = self._check_signal_type(signal)
            
            # 验证方向
            direction_valid = self._check_direction(signal)
            
            # 验证时间范围
            time_horizon_valid = self._check_time_horizon(signal)
            
            # 汇总验证结果
            is_valid = (
                not missing_fields and
                confidence_valid and
                description_valid and
                signal_type_valid and
                direction_valid and
                (time_horizon_valid if signal.time_horizon else True)
            )
            
            # 计算验证得分
            validation_score = self._calculate_validation_score(
                signal, 
                missing_fields, 
                confidence_valid, 
                description_valid,
                signal_type_valid,
                direction_valid,
                time_horizon_valid
            )
            
            # 生成错误消息
            error_messages = []
            if missing_fields:
                error_messages.append(f"缺少必需字段: {', '.join(missing_fields)}")
            if not confidence_valid:
                error_messages.append(f"置信度低于最低要求: {signal.confidence} < {self.minimum_confidence}")
            if not description_valid:
                error_messages.append(f"描述长度不足: {len(signal.description)} < {self.minimum_description_length}")
            if not signal_type_valid:
                error_messages.append(f"无效的信号类型: {signal.signal_type}")
            if not direction_valid:
                error_messages.append(f"无效的方向: {signal.direction}")
            if not time_horizon_valid and signal.time_horizon:
                error_messages.append(f"无效的时间范围: {signal.time_horizon}")
            
            error_message = "; ".join(error_messages) if error_messages else None
            
            # 更新验证结果
            validation_result.is_valid = is_valid
            validation_result.validation_score = validation_score
            validation_result.error_message = error_message
            validation_result.metrics = {
                "confidence": signal.confidence,
                "description_length": len(signal.description),
                "missing_fields_count": len(missing_fields),
                "has_stock_codes": len(signal.stock_codes) > 0,
                "has_metrics": len(signal.metrics) > 0
            }
            
            # 添加详细结果
            validation_result.details = {
                "missing_fields": missing_fields,
                "confidence_valid": confidence_valid,
                "description_valid": description_valid,
                "signal_type_valid": signal_type_valid,
                "direction_valid": direction_valid,
                "time_horizon_valid": time_horizon_valid,
                "signal": signal.to_dict()
            }
            
            results.append(validation_result)
        
        self.results = results
        return results
    
    def _check_missing_fields(self, signal: AlphaSignal) -> List[str]:
        """检查缺失的必需字段"""
        missing = []
        signal_dict = signal.to_dict()
        
        for field in self.required_fields:
            if field not in signal_dict or signal_dict[field] is None:
                missing.append(field)
        
        return missing
    
    def _check_confidence(self, signal: AlphaSignal) -> bool:
        """检查置信度是否符合要求"""
        return signal.confidence is not None and signal.confidence >= self.minimum_confidence
    
    def _check_description_length(self, signal: AlphaSignal) -> bool:
        """检查描述长度是否符合要求"""
        return len(signal.description) >= self.minimum_description_length
    
    def _check_signal_type(self, signal: AlphaSignal) -> bool:
        """检查信号类型是否有效"""
        return signal.signal_type in self.valid_signal_types
    
    def _check_direction(self, signal: AlphaSignal) -> bool:
        """检查方向是否有效"""
        return signal.direction in self.valid_directions
    
    def _check_time_horizon(self, signal: AlphaSignal) -> bool:
        """检查时间范围是否有效"""
        if not signal.time_horizon:
            return True
        return signal.time_horizon in self.valid_time_horizons
    
    def _calculate_validation_score(self, 
                                   signal: AlphaSignal, 
                                   missing_fields: List[str], 
                                   confidence_valid: bool, 
                                   description_valid: bool,
                                   signal_type_valid: bool,
                                   direction_valid: bool,
                                   time_horizon_valid: bool) -> float:
        """计算验证得分"""
        # 基础分数
        score = 0.5
        
        # 扣分项
        penalty = 0.0
        
        # 缺少必需字段扣分
        penalty += 0.1 * len(missing_fields)
        
        # 置信度不符合要求扣分
        if not confidence_valid:
            penalty += 0.2
        
        # 描述长度不足扣分
        if not description_valid:
            penalty += 0.1
        
        # 信号类型无效扣分
        if not signal_type_valid:
            penalty += 0.1
        
        # 方向无效扣分
        if not direction_valid:
            penalty += 0.1
        
        # 时间范围无效扣分
        if not time_horizon_valid and signal.time_horizon:
            penalty += 0.05
        
        # 加分项
        bonus = 0.0
        
        # 额外信息加分
        if len(signal.stock_codes) > 0:
            bonus += 0.1
        
        if signal.industry:
            bonus += 0.05
        
        if len(signal.metrics) > 0:
            bonus += min(0.15, 0.05 * len(signal.metrics))
        
        # 描述详细程度加分
        description_length_bonus = min(0.1, (len(signal.description) - self.minimum_description_length) / 500)
        bonus += description_length_bonus
        
        # 计算最终得分
        final_score = score - penalty + bonus
        
        # 限制在0-1范围内
        return max(0.0, min(1.0, final_score))


class DataBacktestValidator(BaseAlphaValidator):
    """
    基于历史数据回测的Alpha信号验证器
    通过回测历史数据验证信号的有效性
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化回测验证器
        
        参数:
            config: 配置参数，可包含:
                - data_provider: 数据提供者
                - benchmark: 基准指数
                - lookback_days: 回溯天数
                - metrics_to_calculate: 待计算指标
        """
        super().__init__(config)
        
        # 数据提供者
        self.data_provider = self.config.get('data_provider')
        
        # 基准指数
        self.benchmark = self.config.get('benchmark', '000300.SH')
        
        # 回溯天数
        self.lookback_days = self.config.get('lookback_days', 60)
        
        # 待计算指标
        self.metrics_to_calculate = self.config.get('metrics_to_calculate', [
            'return', 'alpha', 'beta', 'sharpe', 'max_drawdown', 'win_rate'
        ])
        
        # 最小数据量
        self.minimum_data_points = self.config.get('minimum_data_points', 20)
        
        # 验证阈值
        self.validation_thresholds = self.config.get('validation_thresholds', {
            'positive': {'return': 0.0, 'alpha': 0.0, 'sharpe': 0.0},
            'negative': {'return': 0.0, 'alpha': 0.0, 'sharpe': 0.0},
            'neutral': {'max_drawdown': -0.3, 'win_rate': 0.45}
        })
    
    def validate(self, signals: List[AlphaSignal]) -> List[AlphaValidationResult]:
        """
        验证Alpha信号
        
        参数:
            signals: Alpha信号列表
            
        返回:
            验证结果列表
        """
        if not self.data_provider:
            logger.error("缺少数据提供者，无法进行回测验证")
            return []
        
        results = []
        
        for signal in signals:
            # 生成唯一ID
            signal_id = f"{signal.name}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # 验证结果初始化
            validation_result = AlphaValidationResult(
                signal_id=signal_id,
                signal_name=signal.name
            )
            
            # 获取股票代码
            stock_codes = signal.stock_codes
            
            if not stock_codes:
                # 无法进行回测
                validation_result.is_valid = False
                validation_result.error_message = "无法进行回测: 缺少股票代码"
                results.append(validation_result)
                continue
            
            try:
                # 获取历史数据
                historical_data = self._get_historical_data(stock_codes)
                
                if historical_data.empty or len(historical_data) < self.minimum_data_points:
                    validation_result.is_valid = False
                    validation_result.error_message = f"数据点数不足，无法进行有效回测: {len(historical_data)} < {self.minimum_data_points}"
                    results.append(validation_result)
                    continue
                
                # 计算回测指标
                metrics = self._calculate_backtest_metrics(historical_data, signal.direction)
                
                # 验证回测结果
                is_valid, score, details = self._evaluate_backtest_results(metrics, signal.direction)
                
                # 更新验证结果
                validation_result.is_valid = is_valid
                validation_result.validation_score = score
                validation_result.metrics = metrics
                validation_result.details = details
                
                results.append(validation_result)
            except Exception as e:
                validation_result.is_valid = False
                validation_result.error_message = f"回测验证失败: {e}"
                results.append(validation_result)
        
        self.results = results
        return results
    
    def _get_historical_data(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        获取历史数据
        
        参数:
            stock_codes: 股票代码列表
            
        返回:
            历史数据DataFrame
        """
        # 计算开始和结束日期
        end_date = datetime.datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.datetime.now() - datetime.timedelta(days=self.lookback_days)).strftime('%Y-%m-%d')
        
        # 调用数据提供者获取数据
        # 注意：具体实现依赖于数据提供者的接口
        try:
            data = self.data_provider.get_data(
                stock_codes=stock_codes,
                start_date=start_date,
                end_date=end_date,
                fields=['close', 'open', 'high', 'low', 'volume']
            )
            return data
        except Exception as e:
            logger.error(f"获取历史数据失败: {e}")
            return pd.DataFrame()
    
    def _calculate_backtest_metrics(self, data: pd.DataFrame, direction: str) -> Dict[str, float]:
        """
        计算回测指标
        
        参数:
            data: 历史数据
            direction: 信号方向
            
        返回:
            计算的指标
        """
        metrics = {}
        
        try:
            # 计算收益率
            data['returns'] = data['close'].pct_change()
            
            # 根据方向计算收益
            if direction == 'negative':
                data['strategy_returns'] = -data['returns']
            else:
                data['strategy_returns'] = data['returns']
            
            # 计算累计收益
            data['cum_returns'] = (1 + data['strategy_returns']).cumprod() - 1
            
            # 获取基准收益
            benchmark_data = self._get_benchmark_data()
            
            if not benchmark_data.empty:
                # 计算Alpha和Beta
                metrics['alpha'], metrics['beta'] = self._calculate_alpha_beta(
                    data['strategy_returns'], benchmark_data['returns']
                )
            
            # 计算总收益
            metrics['return'] = data['cum_returns'].iloc[-1]
            
            # 计算夏普比率
            metrics['sharpe'] = (
                data['strategy_returns'].mean() / data['strategy_returns'].std() * np.sqrt(252)
                if data['strategy_returns'].std() != 0 else 0
            )
            
            # 计算最大回撤
            metrics['max_drawdown'] = self._calculate_max_drawdown(data['cum_returns'])
            
            # 计算胜率
            metrics['win_rate'] = (data['strategy_returns'] > 0).mean()
            
            # 均值收益率
            metrics['mean_return'] = data['strategy_returns'].mean()
            
            # 波动率
            metrics['volatility'] = data['strategy_returns'].std() * np.sqrt(252)
            
        except Exception as e:
            logger.error(f"计算回测指标失败: {e}")
        
        return metrics
    
    def _calculate_alpha_beta(self, returns: pd.Series, benchmark_returns: pd.Series) -> Tuple[float, float]:
        """计算Alpha和Beta"""
        try:
            # 对齐数据
            aligned_data = pd.concat([returns, benchmark_returns], axis=1).dropna()
            if len(aligned_data) < 2:
                return 0.0, 0.0
            
            # 计算Beta
            covariance = np.cov(aligned_data.iloc[:, 0], aligned_data.iloc[:, 1])[0, 1]
            benchmark_variance = np.var(aligned_data.iloc[:, 1])
            beta = covariance / benchmark_variance if benchmark_variance != 0 else 0
            
            # 计算Alpha (年化)
            alpha = (aligned_data.iloc[:, 0].mean() - beta * aligned_data.iloc[:, 1].mean()) * 252
            
            return alpha, beta
        except Exception as e:
            logger.error(f"计算Alpha和Beta失败: {e}")
            return 0.0, 0.0
    
    def _calculate_max_drawdown(self, cum_returns: pd.Series) -> float:
        """计算最大回撤"""
        try:
            # 计算累计最大值
            running_max = cum_returns.cummax()
            # 计算回撤
            drawdown = (cum_returns - running_max) / (running_max + 1.0)
            # 最大回撤
            max_drawdown = drawdown.min()
            
            return max_drawdown
        except Exception as e:
            logger.error(f"计算最大回撤失败: {e}")
            return 0.0
    
    def _get_benchmark_data(self) -> pd.DataFrame:
        """获取基准数据"""
        # 计算开始和结束日期
        end_date = datetime.datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.datetime.now() - datetime.timedelta(days=self.lookback_days)).strftime('%Y-%m-%d')
        
        try:
            # 调用数据提供者获取基准数据
            data = self.data_provider.get_data(
                stock_codes=[self.benchmark],
                start_date=start_date,
                end_date=end_date,
                fields=['close']
            )
            
            # 计算收益率
            data['returns'] = data['close'].pct_change()
            
            return data
        except Exception as e:
            logger.error(f"获取基准数据失败: {e}")
            return pd.DataFrame()
    
    def _evaluate_backtest_results(self, metrics: Dict[str, float], direction: str) -> Tuple[bool, float, Dict[str, Any]]:
        """
        评估回测结果
        
        参数:
            metrics: 回测指标
            direction: 信号方向
            
        返回:
            (是否有效, 得分, 详细信息)
        """
        # 验证结果
        is_valid = True
        details = {
            'thresholds': self.validation_thresholds.get(direction, {}),
            'metric_validations': {}
        }
        
        # 根据信号方向获取阈值
        thresholds = self.validation_thresholds.get(direction, {})
        
        # 检查每个指标是否满足阈值
        for metric, threshold in thresholds.items():
            if metric in metrics:
                metric_valid = (
                    (threshold >= 0 and metrics[metric] >= threshold) or
                    (threshold < 0 and metrics[metric] <= threshold)
                )
                details['metric_validations'][metric] = {
                    'value': metrics[metric],
                    'threshold': threshold,
                    'valid': metric_valid
                }
                
                # 只要有一个关键指标不满足要求，就认为无效
                if not metric_valid:
                    is_valid = False
        
        # 计算验证得分
        score = self._calculate_validation_score(metrics, direction)
        
        details['validation_score'] = score
        
        return is_valid, score, details
    
    def _calculate_validation_score(self, metrics: Dict[str, float], direction: str) -> float:
        """计算验证得分"""
        # 基础分数
        score = 0.5
        
        # 根据方向不同，使用不同的评分标准
        if direction == 'positive' or direction == 'negative':
            # 收益率
            if 'return' in metrics:
                if metrics['return'] > 0.1:
                    score += 0.2
                elif metrics['return'] > 0.05:
                    score += 0.1
                elif metrics['return'] > 0.0:
                    score += 0.05
                elif metrics['return'] < -0.1:
                    score -= 0.2
                elif metrics['return'] < -0.05:
                    score -= 0.1
            
            # Alpha
            if 'alpha' in metrics:
                if metrics['alpha'] > 0.05:
                    score += 0.1
                elif metrics['alpha'] > 0.0:
                    score += 0.05
                elif metrics['alpha'] < -0.05:
                    score -= 0.1
            
            # 夏普比率
            if 'sharpe' in metrics:
                if metrics['sharpe'] > 1.0:
                    score += 0.1
                elif metrics['sharpe'] > 0.5:
                    score += 0.05
                elif metrics['sharpe'] < -0.5:
                    score -= 0.1
        
        # 通用评分标准
        # 最大回撤
        if 'max_drawdown' in metrics:
            if metrics['max_drawdown'] > -0.1:
                score += 0.1
            elif metrics['max_drawdown'] < -0.3:
                score -= 0.1
        
        # 胜率
        if 'win_rate' in metrics:
            if metrics['win_rate'] > 0.6:
                score += 0.1
            elif metrics['win_rate'] > 0.5:
                score += 0.05
            elif metrics['win_rate'] < 0.4:
                score -= 0.1
        
        # 限制在0-1范围内
        return max(0.0, min(1.0, score))


class AlphaValidatorFactory:
    """Alpha验证器工厂类"""
    
    @staticmethod
    def get_validator(validator_type: str, config: Dict[str, Any] = None) -> BaseAlphaValidator:
        """
        获取Alpha验证器
        
        参数:
            validator_type: 验证器类型，可选值: 'basic', 'backtest', 'ensemble'
            config: 验证器配置
            
        返回:
            Alpha验证器实例
        """
        config = config or {}
        
        if validator_type == 'basic':
            return BasicValidator(config)
        elif validator_type == 'backtest':
            return DataBacktestValidator(config)
        elif validator_type == 'ensemble':
            # TODO: 实现集成验证器
            logger.warning("集成验证器尚未实现，使用基本验证器替代")
            return BasicValidator(config)
        else:
            logger.warning(f"不支持的验证器类型: {validator_type}，使用基本验证器作为默认值")
            return BasicValidator(config)
