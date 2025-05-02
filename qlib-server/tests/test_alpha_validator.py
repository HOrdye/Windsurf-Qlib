#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Alpha验证器单元测试
"""
import os
import unittest
import tempfile
from unittest.mock import patch, MagicMock
import json
import pandas as pd
import numpy as np
import datetime

# 修复导入路径
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from alpha.alpha_generation.alpha_validator import (
    AlphaValidationResult,
    BaseAlphaValidator,
    BasicValidator,
    DataBacktestValidator,
    AlphaValidatorFactory
)
from alpha.alpha_generation.alpha_extractor import AlphaSignal

class TestAlphaValidationResult(unittest.TestCase):
    """Alpha验证结果测试"""
    
    def test_init(self):
        """测试初始化"""
        validation_date = "2025-04-10"
        result = AlphaValidationResult(
            signal_id="test-id",
            signal_name="测试信号",
            validation_date=validation_date,
            is_valid=True,
            validation_score=0.85,
            metrics={"confidence": 0.8, "has_stock_codes": True},
            error_message=None,
            details={"missing_fields": []}
        )
        
        self.assertEqual(result.signal_id, "test-id")
        self.assertEqual(result.signal_name, "测试信号")
        self.assertEqual(result.validation_date, validation_date)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.validation_score, 0.85)
        self.assertEqual(result.metrics, {"confidence": 0.8, "has_stock_codes": True})
        self.assertIsNone(result.error_message)
        self.assertEqual(result.details, {"missing_fields": []})
    
    def test_init_default_date(self):
        """测试默认验证日期"""
        result = AlphaValidationResult(
            signal_id="test-id",
            signal_name="测试信号"
        )
        
        # 验证日期是否为当天
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        self.assertEqual(result.validation_date, today)
    
    def test_to_dict(self):
        """测试转换为字典"""
        validation_date = "2025-04-10"
        result = AlphaValidationResult(
            signal_id="test-id",
            signal_name="测试信号",
            validation_date=validation_date,
            is_valid=True,
            validation_score=0.85
        )
        
        result_dict = result.to_dict()
        
        self.assertEqual(result_dict["signal_id"], "test-id")
        self.assertEqual(result_dict["signal_name"], "测试信号")
        self.assertEqual(result_dict["validation_date"], validation_date)
        self.assertTrue(result_dict["is_valid"])
        self.assertEqual(result_dict["validation_score"], 0.85)
    
    def test_to_json(self):
        """测试转换为JSON"""
        validation_date = "2025-04-10"
        result = AlphaValidationResult(
            signal_id="test-id",
            signal_name="测试信号",
            validation_date=validation_date,
            is_valid=True,
            validation_score=0.85
        )
        
        result_json = result.to_json()
        result_dict = json.loads(result_json)
        
        self.assertEqual(result_dict["signal_id"], "test-id")
        self.assertEqual(result_dict["signal_name"], "测试信号")
        self.assertEqual(result_dict["validation_date"], validation_date)
    
    def test_from_dict(self):
        """测试从字典创建"""
        result_dict = {
            "signal_id": "test-id",
            "signal_name": "测试信号",
            "validation_date": "2025-04-10",
            "is_valid": True,
            "validation_score": 0.85,
            "metrics": {"confidence": 0.8, "has_stock_codes": True},
            "error_message": None,
            "details": {"missing_fields": []}
        }
        
        result = AlphaValidationResult.from_dict(result_dict)
        
        self.assertEqual(result.signal_id, "test-id")
        self.assertEqual(result.signal_name, "测试信号")
        self.assertEqual(result.validation_date, "2025-04-10")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.validation_score, 0.85)
        self.assertEqual(result.metrics, {"confidence": 0.8, "has_stock_codes": True})
        self.assertIsNone(result.error_message)
        self.assertEqual(result.details, {"missing_fields": []})


class TestBaseAlphaValidator(unittest.TestCase):
    """基础Alpha验证器测试"""
    
    def setUp(self):
        """测试初始化"""
        self.config = {'test_key': 'test_value'}
        self.validator = BaseAlphaValidator(self.config)
    
    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.validator.config, self.config)
        self.assertEqual(self.validator.results, [])
    
    def test_validate_not_implemented(self):
        """测试validate方法异常"""
        with self.assertRaises(NotImplementedError):
            self.validator.validate([])
    
    def test_save_results(self):
        """测试保存验证结果"""
        validation_date = "2025-04-10"
        results = [
            AlphaValidationResult(
                signal_id="id-1",
                signal_name="信号1",
                validation_date=validation_date,
                is_valid=True,
                validation_score=0.85
            ),
            AlphaValidationResult(
                signal_id="id-2",
                signal_name="信号2",
                validation_date=validation_date,
                is_valid=False,
                validation_score=0.45,
                error_message="验证失败原因"
            )
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "validation_results.json")
            result_path = self.validator.save_results(results, output_path)
            
            self.assertEqual(result_path, output_path)
            self.assertTrue(os.path.exists(output_path))
            
            # 验证保存的内容
            with open(output_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                self.assertEqual(len(saved_data), 2)
                self.assertEqual(saved_data[0]["signal_name"], "信号1")
                self.assertTrue(saved_data[0]["is_valid"])
                self.assertEqual(saved_data[1]["signal_name"], "信号2")
                self.assertFalse(saved_data[1]["is_valid"])
                self.assertEqual(saved_data[1]["error_message"], "验证失败原因")


class TestBasicValidator(unittest.TestCase):
    """基本验证器测试"""
    
    def setUp(self):
        """测试初始化"""
        self.config = {
            'required_fields': ['name', 'description', 'source', 'signal_type', 'direction'],
            'minimum_confidence': 0.6,
            'minimum_description_length': 30,
            'valid_signal_types': ['fundamental', 'technical', 'sentiment'],
            'valid_directions': ['positive', 'negative', 'neutral'],
            'valid_time_horizons': ['short_term', 'medium_term', 'long_term']
        }
        self.validator = BasicValidator(self.config)
    
    def test_validate_valid_signal(self):
        """测试验证有效信号"""
        # 创建有效信号
        valid_signal = AlphaSignal(
            name="有效信号",
            description="这是一个有效信号描述，长度超过最小要求" * 2,
            source="test.pdf",
            signal_type="fundamental",
            direction="positive",
            confidence=0.8,
            time_horizon="medium_term",
            stock_codes=["600000.SH"],
            industry="银行",
            metrics={"PE": 8.5}
        )
        
        # 验证信号
        results = self.validator.validate([valid_signal])
        
        # 验证结果
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].is_valid)
        self.assertGreater(results[0].validation_score, 0.7)  # 得分应该较高
        self.assertIsNone(results[0].error_message)
    
    def test_validate_invalid_signal_missing_fields(self):
        """测试验证缺少必需字段的信号"""
        # 创建缺少必需字段的信号
        invalid_signal = AlphaSignal(
            name="无效信号",
            description="这是一个无效信号描述，长度超过最小要求" * 2,
            source="test.pdf",
            signal_type=None,  # 缺少信号类型
            direction=None,    # 缺少方向
            confidence=0.8
        )
        
        # 验证信号
        results = self.validator.validate([invalid_signal])
        
        # 验证结果
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].is_valid)  # 应该无效
        self.assertLess(results[0].validation_score, 0.7)  # 得分应该较低
        self.assertIsNotNone(results[0].error_message)
        self.assertIn("缺少必需字段", results[0].error_message)
    
    def test_validate_invalid_signal_low_confidence(self):
        """测试验证低置信度的信号"""
        # 创建低置信度的信号
        invalid_signal = AlphaSignal(
            name="低置信度信号",
            description="这是一个低置信度信号描述，长度超过最小要求" * 2,
            source="test.pdf",
            signal_type="fundamental",
            direction="positive",
            confidence=0.5  # 低于最低要求
        )
        
        # 验证信号
        results = self.validator.validate([invalid_signal])
        
        # 验证结果
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].is_valid)  # 应该无效
        self.assertIn("置信度低于最低要求", results[0].error_message)
    
    def test_validate_invalid_signal_short_description(self):
        """测试验证描述太短的信号"""
        # 创建描述太短的信号
        invalid_signal = AlphaSignal(
            name="短描述信号",
            description="这是一个短描述",  # 描述太短
            source="test.pdf",
            signal_type="fundamental",
            direction="positive",
            confidence=0.8
        )
        
        # 验证信号
        results = self.validator.validate([invalid_signal])
        
        # 验证结果
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].is_valid)  # 应该无效
        self.assertIn("描述长度不足", results[0].error_message)
    
    def test_validate_invalid_signal_type(self):
        """测试验证无效信号类型"""
        # 创建无效信号类型的信号
        with patch('alpha.alpha_generation.alpha_extractor.AlphaSignal._validate'):  # 绕过初始验证
            invalid_signal = AlphaSignal(
                name="无效类型信号",
                description="这是一个无效类型信号描述，长度超过最小要求" * 2,
                source="test.pdf",
                signal_type="invalid_type",  # 无效类型
                direction="positive",
                confidence=0.8
            )
            
            # 验证信号
            results = self.validator.validate([invalid_signal])
            
            # 验证结果
            self.assertEqual(len(results), 1)
            self.assertFalse(results[0].is_valid)  # 应该无效
            self.assertIn("无效的信号类型", results[0].error_message)
    
    def test_validate_invalid_direction(self):
        """测试验证无效方向"""
        # 创建无效方向的信号
        with patch('alpha.alpha_generation.alpha_extractor.AlphaSignal._validate'):  # 绕过初始验证
            invalid_signal = AlphaSignal(
                name="无效方向信号",
                description="这是一个无效方向信号描述，长度超过最小要求" * 2,
                source="test.pdf",
                signal_type="fundamental",
                direction="invalid_direction",  # 无效方向
                confidence=0.8
            )
            
            # 验证信号
            results = self.validator.validate([invalid_signal])
            
            # 验证结果
            self.assertEqual(len(results), 1)
            self.assertFalse(results[0].is_valid)  # 应该无效
            self.assertIn("无效的方向", results[0].error_message)
    
    def test_validate_invalid_time_horizon(self):
        """测试验证无效时间范围"""
        # 创建无效时间范围的信号
        with patch('alpha.alpha_generation.alpha_extractor.AlphaSignal._validate'):  # 绕过初始验证
            invalid_signal = AlphaSignal(
                name="无效时间信号",
                description="这是一个无效时间信号描述，长度超过最小要求" * 2,
                source="test.pdf",
                signal_type="fundamental",
                direction="positive",
                confidence=0.8,
                time_horizon="invalid_horizon"  # 无效时间范围
            )
            
            # 验证信号
            results = self.validator.validate([invalid_signal])
            
            # 验证结果
            self.assertEqual(len(results), 1)
            self.assertFalse(results[0].is_valid)  # 应该无效
            self.assertIn("无效的时间范围", results[0].error_message)
    
    def test_calculate_validation_score(self):
        """测试计算验证得分"""
        # 创建有效信号
        signal = AlphaSignal(
            name="测试信号",
            description="这是一个测试信号描述，长度超过最小要求" * 2,
            source="test.pdf",
            signal_type="fundamental",
            direction="positive",
            confidence=0.8,
            time_horizon="medium_term",
            stock_codes=["600000.SH"],
            industry="银行",
            metrics={"PE": 8.5, "ROE": 15.0}
        )
        
        # 计算得分
        score = self.validator._calculate_validation_score(
            signal,
            [],  # 无缺失字段
            True,  # 置信度有效
            True,  # 描述长度有效
            True,  # 信号类型有效
            True,  # 方向有效
            True   # 时间范围有效
        )
        
        # 验证得分
        self.assertGreater(score, 0.7)  # 完整信号得分应该较高


class TestDataBacktestValidator(unittest.TestCase):
    """数据回测验证器测试"""
    
    def setUp(self):
        """测试初始化"""
        # 创建Mock数据提供者
        self.data_provider = MagicMock()
        
        self.config = {
            'data_provider': self.data_provider,
            'benchmark': '000300.SH',
            'lookback_days': 60,
            'metrics_to_calculate': ['return', 'alpha', 'beta', 'sharpe', 'max_drawdown', 'win_rate'],
            'minimum_data_points': 20,
            'validation_thresholds': {
                'positive': {'return': 0.0, 'alpha': 0.0, 'sharpe': 0.0},
                'negative': {'return': 0.0, 'alpha': 0.0, 'sharpe': 0.0},
                'neutral': {'max_drawdown': -0.3, 'win_rate': 0.45}
            }
        }
        self.validator = DataBacktestValidator(self.config)
    
    def test_validate_no_stock_codes(self):
        """测试验证没有股票代码的信号"""
        # 创建无股票代码的信号
        signal = AlphaSignal(
            name="无股票代码信号",
            description="这是一个没有股票代码的信号",
            source="test.pdf",
            signal_type="fundamental",
            direction="positive",
            confidence=0.8
        )
        
        # 验证信号
        results = self.validator.validate([signal])
        
        # 验证结果
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].is_valid)  # 没有股票代码无法回测
        self.assertIn("无法进行回测: 缺少股票代码", results[0].error_message)
    
    def test_validate_insufficient_data(self):
        """测试验证数据点不足的情况"""
        # 创建股票代码的信号
        signal = AlphaSignal(
            name="有股票代码信号",
            description="这是一个有股票代码的信号",
            source="test.pdf",
            signal_type="fundamental",
            direction="positive",
            confidence=0.8,
            stock_codes=["600000.SH"]
        )
        
        # 设置Mock数据提供者返回空数据
        self.data_provider.get_data.return_value = pd.DataFrame()
        
        # 验证信号
        results = self.validator.validate([signal])
        
        # 验证结果
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].is_valid)  # 数据点不足
        self.assertIn("数据点数不足", results[0].error_message)
    
    def test_validate_positive_signal(self):
        """测试验证正向信号"""
        # 创建正向信号
        signal = AlphaSignal(
            name="正向信号",
            description="这是一个正向信号",
            source="test.pdf",
            signal_type="fundamental",
            direction="positive",
            confidence=0.8,
            stock_codes=["600000.SH"]
        )
        
        # 创建模拟历史数据
        dates = pd.date_range(end=datetime.datetime.now(), periods=30)
        mock_data = pd.DataFrame({
            'close': [100 + i for i in range(30)]  # 持续上涨的价格
        }, index=dates)
        self.data_provider.get_data.return_value = mock_data
        
        # 验证信号
        with patch.object(self.validator, '_calculate_alpha_beta', return_value=(0.05, 1.0)):
            results = self.validator.validate([signal])
        
        # 验证结果
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].is_valid)  # 应该有效
        self.assertGreater(results[0].validation_score, 0.5)
        self.assertIn('return', results[0].metrics)
        self.assertIn('sharpe', results[0].metrics)
        self.assertIn('max_drawdown', results[0].metrics)
    
    def test_calculate_backtest_metrics(self):
        """测试计算回测指标"""
        # 创建模拟历史数据
        dates = pd.date_range(end=datetime.datetime.now(), periods=30)
        mock_data = pd.DataFrame({
            'close': [100 + i for i in range(30)]  # 持续上涨的价格
        }, index=dates)
        
        # 计算指标 - 正向信号
        with patch.object(self.validator, '_calculate_alpha_beta', return_value=(0.05, 1.0)):
            metrics = self.validator._calculate_backtest_metrics(mock_data, "positive")
        
        # 验证指标
        self.assertIn('return', metrics)
        self.assertIn('alpha', metrics)
        self.assertIn('beta', metrics)
        self.assertIn('sharpe', metrics)
        self.assertIn('max_drawdown', metrics)
        self.assertIn('win_rate', metrics)
        
        # 正向信号应该有正收益
        self.assertGreater(metrics['return'], 0)
        
        # 计算指标 - 负向信号
        with patch.object(self.validator, '_calculate_alpha_beta', return_value=(-0.05, 1.0)):
            metrics = self.validator._calculate_backtest_metrics(mock_data, "negative")
        
        # 负向信号应该与正向信号相反
        self.assertLess(metrics['return'], 0)
    
    def test_calculate_max_drawdown(self):
        """测试计算最大回撤"""
        # 创建累计收益序列
        cum_returns = pd.Series([0.0, 0.1, 0.05, 0.15, 0.05, 0.0, 0.1])
        
        # 计算最大回撤
        max_drawdown = self.validator._calculate_max_drawdown(cum_returns)
        
        # 验证结果
        self.assertLess(max_drawdown, 0)  # 回撤应该是负数
        self.assertEqual(max_drawdown, -0.1)  # 最大回撤应该是从0.15降到0.05，即-0.1
    
    def test_evaluate_backtest_results(self):
        """测试评估回测结果"""
        # 创建模拟指标
        positive_metrics = {
            'return': 0.1,
            'alpha': 0.05,
            'sharpe': 1.5,
            'max_drawdown': -0.05,
            'win_rate': 0.6
        }
        
        # 评估正向信号的回测结果
        is_valid, score, details = self.validator._evaluate_backtest_results(positive_metrics, "positive")
        
        # 验证结果
        self.assertTrue(is_valid)  # 应该有效
        self.assertGreater(score, 0.5)  # 得分应该较高
        
        # 创建不合格的指标
        negative_metrics = {
            'return': -0.1,
            'alpha': -0.05,
            'sharpe': -0.5,
            'max_drawdown': -0.2,
            'win_rate': 0.4
        }
        
        # 评估不合格的回测结果
        is_valid, score, details = self.validator._evaluate_backtest_results(negative_metrics, "positive")
        
        # 验证结果
        self.assertFalse(is_valid)  # 应该无效
        self.assertLess(score, 0.5)  # 得分应该较低


class TestAlphaValidatorFactory(unittest.TestCase):
    """Alpha验证器工厂测试"""
    
    def test_get_validator_basic(self):
        """测试获取基本验证器"""
        validator = AlphaValidatorFactory.get_validator("basic")
        self.assertIsInstance(validator, BasicValidator)
    
    def test_get_validator_backtest(self):
        """测试获取回测验证器"""
        validator = AlphaValidatorFactory.get_validator("backtest")
        self.assertIsInstance(validator, DataBacktestValidator)
    
    def test_get_validator_ensemble(self):
        """测试获取集成验证器"""
        validator = AlphaValidatorFactory.get_validator("ensemble")
        self.assertIsInstance(validator, BasicValidator)  # 目前使用基本验证器作为替代
    
    def test_get_validator_invalid(self):
        """测试获取无效验证器"""
        validator = AlphaValidatorFactory.get_validator("invalid")
        self.assertIsInstance(validator, BasicValidator)  # 默认使用基本验证器


if __name__ == '__main__':
    unittest.main()
