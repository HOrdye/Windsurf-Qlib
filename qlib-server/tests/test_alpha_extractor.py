#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Alpha信号提取器单元测试
"""
import os
import unittest
import tempfile
from unittest.mock import patch, MagicMock
import json
import pandas as pd
import numpy as np

# 修复导入路径
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from alpha.alpha_generation.alpha_extractor import (
    AlphaSignal,
    BaseAlphaExtractor,
    RuleBasedExtractor,
    LLMBasedExtractor,
    AlphaExtractorFactory
)

class TestAlphaSignal(unittest.TestCase):
    """Alpha信号测试"""
    
    def test_init(self):
        """测试初始化"""
        signal = AlphaSignal(
            name="测试信号",
            description="这是一个测试信号描述",
            source="test.pdf",
            signal_type="fundamental",
            factor_category="valuation",
            direction="positive",
            confidence=0.8,
            time_horizon="medium_term",
            stock_codes=["600000.SH", "000001.SZ"],
            industry="金融",
            metrics={"PE": 15.2, "ROE": 0.12}
        )
        
        self.assertEqual(signal.name, "测试信号")
        self.assertEqual(signal.description, "这是一个测试信号描述")
        self.assertEqual(signal.source, "test.pdf")
        self.assertEqual(signal.signal_type, "fundamental")
        self.assertEqual(signal.factor_category, "valuation")
        self.assertEqual(signal.direction, "positive")
        self.assertEqual(signal.confidence, 0.8)
        self.assertEqual(signal.time_horizon, "medium_term")
        self.assertEqual(signal.stock_codes, ["600000.SH", "000001.SZ"])
        self.assertEqual(signal.industry, "金融")
        self.assertEqual(signal.metrics, {"PE": 15.2, "ROE": 0.12})
    
    def test_validate_required_fields(self):
        """测试必填字段验证"""
        # 缺少必要字段
        with self.assertRaises(ValueError):
            AlphaSignal(
                name=None,
                description="测试描述",
                source="test.pdf"
            )
        
        with self.assertRaises(ValueError):
            AlphaSignal(
                name="测试信号",
                description=None,
                source="test.pdf"
            )
        
        with self.assertRaises(ValueError):
            AlphaSignal(
                name="测试信号",
                description="测试描述",
                source=None
            )
    
    def test_validate_confidence(self):
        """测试置信度验证"""
        # 置信度超出范围
        with self.assertRaises(ValueError):
            AlphaSignal(
                name="测试信号",
                description="测试描述",
                source="test.pdf",
                confidence=1.5
            )
        
        with self.assertRaises(ValueError):
            AlphaSignal(
                name="测试信号",
                description="测试描述",
                source="test.pdf",
                confidence=-0.5
            )
    
    def test_validate_direction(self):
        """测试方向验证"""
        # 无效的方向
        with self.assertRaises(ValueError):
            AlphaSignal(
                name="测试信号",
                description="测试描述",
                source="test.pdf",
                direction="invalid"
            )
    
    def test_validate_time_horizon(self):
        """测试时间范围验证"""
        # 无效的时间范围
        with self.assertRaises(ValueError):
            AlphaSignal(
                name="测试信号",
                description="测试描述",
                source="test.pdf",
                time_horizon="invalid"
            )
    
    def test_to_dict(self):
        """测试转换为字典"""
        signal = AlphaSignal(
            name="测试信号",
            description="这是一个测试信号描述",
            source="test.pdf",
            signal_type="fundamental",
            direction="positive",
            confidence=0.8
        )
        
        signal_dict = signal.to_dict()
        
        self.assertEqual(signal_dict["name"], "测试信号")
        self.assertEqual(signal_dict["description"], "这是一个测试信号描述")
        self.assertEqual(signal_dict["source"], "test.pdf")
        self.assertEqual(signal_dict["signal_type"], "fundamental")
        self.assertEqual(signal_dict["direction"], "positive")
        self.assertEqual(signal_dict["confidence"], 0.8)
    
    def test_to_json(self):
        """测试转换为JSON"""
        signal = AlphaSignal(
            name="测试信号",
            description="这是一个测试信号描述",
            source="test.pdf",
            signal_type="fundamental",
            direction="positive",
            confidence=0.8
        )
        
        signal_json = signal.to_json()
        signal_dict = json.loads(signal_json)
        
        self.assertEqual(signal_dict["name"], "测试信号")
        self.assertEqual(signal_dict["description"], "这是一个测试信号描述")
        self.assertEqual(signal_dict["source"], "test.pdf")
    
    def test_from_dict(self):
        """测试从字典创建"""
        signal_dict = {
            "name": "测试信号",
            "description": "这是一个测试信号描述",
            "source": "test.pdf",
            "signal_type": "fundamental",
            "direction": "positive",
            "confidence": 0.8,
            "time_horizon": "medium_term",
            "stock_codes": ["600000.SH", "000001.SZ"],
            "industry": "金融",
            "metrics": {"PE": 15.2, "ROE": 0.12}
        }
        
        signal = AlphaSignal.from_dict(signal_dict)
        
        self.assertEqual(signal.name, "测试信号")
        self.assertEqual(signal.description, "这是一个测试信号描述")
        self.assertEqual(signal.source, "test.pdf")
        self.assertEqual(signal.signal_type, "fundamental")
        self.assertEqual(signal.direction, "positive")
        self.assertEqual(signal.confidence, 0.8)
        self.assertEqual(signal.time_horizon, "medium_term")
        self.assertEqual(signal.stock_codes, ["600000.SH", "000001.SZ"])
        self.assertEqual(signal.industry, "金融")
        self.assertEqual(signal.metrics, {"PE": 15.2, "ROE": 0.12})


class TestBaseAlphaExtractor(unittest.TestCase):
    """基础Alpha提取器测试"""
    
    def setUp(self):
        """测试初始化"""
        self.config = {'test_key': 'test_value'}
        self.extractor = BaseAlphaExtractor(self.config)
    
    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.extractor.config, self.config)
        self.assertEqual(self.extractor.signals, [])
    
    def test_extract_not_implemented(self):
        """测试extract方法异常"""
        with self.assertRaises(NotImplementedError):
            self.extractor.extract({"content": "测试内容"})
    
    def test_validate_signals(self):
        """测试信号验证"""
        # 有效信号
        valid_signal = AlphaSignal(
            name="有效信号",
            description="这是一个有效信号描述",
            source="test.pdf",
            direction="positive"
        )
        
        # 无效信号 (置信度超出范围)
        invalid_signal_dict = {
            "name": "无效信号",
            "description": "这是一个无效信号描述",
            "source": "test.pdf",
            "confidence": 1.5
        }
        
        signals = [valid_signal, invalid_signal_dict]
        
        # 验证信号
        with patch('alpha.alpha_generation.alpha_extractor.AlphaSignal.from_dict', 
                 side_effect=lambda x: AlphaSignal(**x)):
            with patch('alpha.alpha_generation.alpha_extractor.logger.warning'):
                valid_signals = self.extractor.validate_signals(signals)
        
        # 只有有效信号被保留
        self.assertEqual(len(valid_signals), 1)
        self.assertEqual(valid_signals[0].name, "有效信号")
    
    def test_save_signals(self):
        """测试保存信号"""
        signals = [
            AlphaSignal(
                name="信号1",
                description="这是信号1描述",
                source="test.pdf",
                direction="positive"
            ),
            AlphaSignal(
                name="信号2",
                description="这是信号2描述",
                source="test.pdf",
                direction="negative"
            )
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "signals.json")
            result_path = self.extractor.save_signals(signals, output_path)
            
            self.assertEqual(result_path, output_path)
            self.assertTrue(os.path.exists(output_path))
            
            # 验证保存的内容
            with open(output_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                self.assertEqual(len(saved_data), 2)
                self.assertEqual(saved_data[0]["name"], "信号1")
                self.assertEqual(saved_data[1]["name"], "信号2")


class TestRuleBasedExtractor(unittest.TestCase):
    """规则提取器测试"""
    
    def setUp(self):
        """测试初始化"""
        self.config = {
            'keywords': {
                'positive': ['增长', '上升'],
                'negative': ['下降', '减少'],
                'technical': ['均线', '成交量'],
                'fundamental': ['利润', '营收'],
                'sentiment': ['情绪', '信心'],
                'short_term': ['短期'],
                'medium_term': ['中期'],
                'long_term': ['长期']
            },
            'stock_code_pattern': r'([0-9]{6}\.(?:SH|SZ))',
            'metrics_patterns': {
                'PE': r'PE(?:[\s值]*)(?:约|为)?(?:[\s:]*)([0-9]+\.?[0-9]*)',
                'ROE': r'ROE(?:[\s值]*)(?:约|为)?(?:[\s:]*)([0-9]+\.?[0-9]*)%?'
            },
            'minimum_confidence': 0.6
        }
        self.extractor = RuleBasedExtractor(self.config)
    
    def test_extract_from_text(self):
        """测试从文本提取信号"""
        # 测试文本内容
        text = """
        A股市场近期表现强劲，科技股持续上升。
        其中，600000.SH银行股PE值约为8.5，ROE为15%，预计将在中期内有良好表现。
        而000001.SZ近期成交量明显放大，短期内可能面临下跌压力。
        """
        
        # 测试提取
        signals = self.extractor._extract_from_text(text, "test.txt")
        
        # 验证结果
        self.assertGreater(len(signals), 0)
        
        # 验证第一个信号
        signal = signals[0]
        self.assertEqual(signal.source, "test.txt")
        self.assertEqual(signal.direction, "positive")  # 文本整体偏向积极
        
        # 验证是否提取到股票代码
        all_stock_codes = []
        for s in signals:
            all_stock_codes.extend(s.stock_codes)
        
        self.assertIn("600000.SH", all_stock_codes)
        self.assertIn("000001.SZ", all_stock_codes)
        
        # 验证是否提取到指标
        all_metrics = {}
        for s in signals:
            all_metrics.update(s.metrics)
        
        self.assertIn("PE", all_metrics.keys())
        self.assertIn("ROE", all_metrics.keys())
    
    def test_extract_from_tables(self):
        """测试从表格提取信号"""
        # 测试表格数据
        tables = [
            {
                "index": 1,
                "headers": ["股票代码", "股票名称", "行业", "PE", "评级"],
                "data": [
                    ["股票代码", "股票名称", "行业", "PE", "评级"],
                    ["600000.SH", "浦发银行", "银行", "7.5", "买入"],
                    ["000001.SZ", "平安银行", "银行", "8.2", "中性"],
                    ["601988.SH", "中国银行", "银行", "5.4", "增持"]
                ]
            }
        ]
        
        # 测试提取
        signals = self.extractor._extract_from_tables(tables, "test.xlsx")
        
        # 验证结果
        self.assertEqual(len(signals), 3)  # 3行数据
        
        # 验证第一个信号
        signal = signals[0]
        self.assertEqual(signal.source, "test.xlsx")
        self.assertEqual(signal.stock_codes, ["600000.SH"])
        self.assertEqual(signal.industry, "银行")
        self.assertEqual(signal.direction, "positive")  # 买入评级
        
        # 验证第二个信号
        signal = signals[1]
        self.assertEqual(signal.stock_codes, ["000001.SZ"])
        self.assertEqual(signal.direction, "neutral")  # 中性评级
    
    def test_determine_direction(self):
        """测试确定信号方向"""
        # 正向文本
        positive_text = "市场持续上升，企业盈利增长强劲"
        direction = self.extractor._determine_direction(positive_text)
        self.assertEqual(direction, "positive")
        
        # 负向文本
        negative_text = "市场持续下降，企业盈利减少明显"
        direction = self.extractor._determine_direction(negative_text)
        self.assertEqual(direction, "negative")
        
        # 中性文本
        neutral_text = "市场波动，企业盈利变化不大"
        direction = self.extractor._determine_direction(neutral_text)
        self.assertEqual(direction, "neutral")
    
    def test_determine_signal_type(self):
        """测试确定信号类型"""
        # 技术信号
        technical_text = "均线金叉，成交量明显放大"
        signal_type = self.extractor._determine_signal_type(technical_text)
        self.assertEqual(signal_type, "technical")
        
        # 基本面信号
        fundamental_text = "企业利润增长，营收超预期"
        signal_type = self.extractor._determine_signal_type(fundamental_text)
        self.assertEqual(signal_type, "fundamental")
        
        # 情绪信号
        sentiment_text = "市场情绪乐观，投资者信心增强"
        signal_type = self.extractor._determine_signal_type(sentiment_text)
        self.assertEqual(signal_type, "sentiment")
    
    def test_determine_time_horizon(self):
        """测试确定时间范围"""
        # 短期
        short_term_text = "短期内可能有较大波动"
        time_horizon = self.extractor._determine_time_horizon(short_term_text)
        self.assertEqual(time_horizon, "short_term")
        
        # 中期
        medium_term_text = "中期来看有望走强"
        time_horizon = self.extractor._determine_time_horizon(medium_term_text)
        self.assertEqual(time_horizon, "medium_term")
        
        # 长期
        long_term_text = "长期投资价值突出"
        time_horizon = self.extractor._determine_time_horizon(long_term_text)
        self.assertEqual(time_horizon, "long_term")
    
    def test_extract_stock_codes(self):
        """测试提取股票代码"""
        text = "600000.SH和000001.SZ都是银行股的代表"
        stock_codes = self.extractor._extract_stock_codes(text)
        self.assertEqual(len(stock_codes), 2)
        self.assertIn("600000.SH", stock_codes)
        self.assertIn("000001.SZ", stock_codes)
    
    def test_extract_metrics(self):
        """测试提取指标"""
        text = "该股PE值约为15.2，ROE为18.5%"
        metrics = self.extractor._extract_metrics(text)
        self.assertEqual(len(metrics), 2)
        self.assertEqual(metrics["PE"], 15.2)
        self.assertEqual(metrics["ROE"], 18.5)
    
    def test_calculate_confidence(self):
        """测试计算置信度"""
        # 高置信度文本：包含方向、股票代码、指标和足够长度
        high_confidence_text = "600000.SH近期表现强劲，PE值约为8.5，ROE为15%，中长期来看有望持续上升。" * 3
        confidence = self.extractor._calculate_confidence(
            high_confidence_text,
            "positive",
            "fundamental",
            ["600000.SH"],
            {"PE": 8.5, "ROE": 15.0}
        )
        self.assertGreater(confidence, 0.7)
        
        # 低置信度文本：信息不完整
        low_confidence_text = "市场波动较大，需要谨慎对待。"
        confidence = self.extractor._calculate_confidence(
            low_confidence_text,
            "neutral",
            "sentiment",
            [],
            {}
        )
        self.assertLess(confidence, 0.7)
    
    def test_deduplicate_signals(self):
        """测试去重信号"""
        # 创建重复信号
        signals = [
            AlphaSignal(
                name="信号1",
                description="这是一个关于600000.SH的信号",
                source="test.pdf",
                direction="positive",
                stock_codes=["600000.SH"]
            ),
            AlphaSignal(
                name="信号2",
                description="这是一个关于600000.SH的信号",  # 描述相同
                source="test.pdf",
                direction="positive",
                stock_codes=["600000.SH"]
            ),
            AlphaSignal(
                name="信号3",
                description="这是一个关于000001.SZ的信号",  # 描述不同
                source="test.pdf",
                direction="negative",
                stock_codes=["000001.SZ"]
            )
        ]
        
        # 去重
        unique_signals = self.extractor._deduplicate_signals(signals)
        
        # 验证结果
        self.assertEqual(len(unique_signals), 2)  # 两个不同的信号
        self.assertEqual(unique_signals[0].name, "信号1")
        self.assertEqual(unique_signals[1].name, "信号3")


class TestLLMBasedExtractor(unittest.TestCase):
    """LLM提取器测试"""
    
    def setUp(self):
        """测试初始化"""
        # 创建一个Mock版本的LLM提取器，不实际调用API
        with patch('alpha.alpha_generation.alpha_extractor.LLMBasedExtractor._init_llm_client'):
            self.config = {
                'model_name': 'gpt-3.5-turbo',
                'llm_provider': 'openai',
                'api_key': 'test_key',
                'prompt_template': "测试提示词模板 {content}",
                'max_tokens': 1000,
                'temperature': 0.2,
                'minimum_confidence': 0.6,
                'batch_size': 2
            }
            self.extractor = LLMBasedExtractor(self.config)
    
    def test_init(self):
        """测试初始化"""
        with patch('alpha.alpha_generation.alpha_extractor.LLMBasedExtractor._init_llm_client'):
            extractor = LLMBasedExtractor(self.config)
            
            self.assertEqual(extractor.model_name, 'gpt-3.5-turbo')
            self.assertEqual(extractor.llm_provider, 'openai')
            self.assertEqual(extractor.api_key, 'test_key')
            self.assertEqual(extractor.max_tokens, 1000)
            self.assertEqual(extractor.temperature, 0.2)
            self.assertEqual(extractor.minimum_confidence, 0.6)
            self.assertEqual(extractor.batch_size, 2)
    
    def test_split_into_paragraphs(self):
        """测试分割段落"""
        text = """
        这是第一段，内容较长。这是第一段的第二句话。
        
        这是第二段，内容也很长。这是第二段的第二句话。
        
        这是很短的内容。
        
        这是第三段，比较长的内容。这是第三段的第二句话。这是第三段的第三句话。
        """
        
        paragraphs = self.extractor._split_into_paragraphs(text)
        
        # 过滤掉短段落，应该剩下3个段落
        self.assertEqual(len(paragraphs), 3)
        self.assertIn("这是第一段", paragraphs[0])
        self.assertIn("这是第二段", paragraphs[1])
        self.assertIn("这是第三段", paragraphs[2])
    
    @patch('alpha.alpha_generation.alpha_extractor.LLMBasedExtractor._extract_with_llm')
    def test_extract(self, mock_extract_with_llm):
        """测试提取信号"""
        # 模拟LLM提取的信号
        mock_signals = [
            AlphaSignal(
                name="LLM信号1",
                description="这是LLM提取的信号1",
                source="test.pdf",
                signal_type="fundamental",
                direction="positive",
                confidence=0.85
            ),
            AlphaSignal(
                name="LLM信号2",
                description="这是LLM提取的信号2",
                source="test.pdf",
                signal_type="technical",
                direction="negative",
                confidence=0.78
            )
        ]
        mock_extract_with_llm.return_value = mock_signals
        
        # 测试文档内容
        content = {
            'content': "这是测试文档内容，包含多个段落。" * 5,
            'metadata': {'source': 'test.pdf'},
            'tables': [],
            'success': True
        }
        
        # 测试提取
        signals = self.extractor.extract(content)
        
        # 验证结果
        self.assertEqual(len(signals), 2)
        self.assertEqual(signals[0].name, "LLM信号1")
        self.assertEqual(signals[1].name, "LLM信号2")
    
    @patch('alpha.alpha_generation.alpha_extractor.json.loads')
    def test_extract_with_llm(self, mock_json_loads):
        """测试使用LLM提取信号"""
        # 模拟JSON解析结果
        mock_json_result = [
            {
                "name": "LLM信号1",
                "description": "这是LLM提取的信号1",
                "signal_type": "fundamental",
                "direction": "positive",
                "time_horizon": "medium_term",
                "stock_codes": ["600000.SH"],
                "industry": "银行",
                "metrics": {"PE": 8.5},
                "confidence": 0.85
            }
        ]
        mock_json_loads.return_value = mock_json_result
        
        # 模拟LLM调用
        self.extractor.llm_provider = 'openai'
        self.extractor.client = MagicMock()
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = '[{"name": "LLM信号1"}]'
        mock_response.choices = [MagicMock(message=mock_message)]
        self.extractor.client.ChatCompletion.create.return_value = mock_response
        
        # 测试文本
        text = "测试文本"
        source = "test.pdf"
        
        # 测试提取
        signals = self.extractor._extract_with_llm(text, source)
        
        # 验证结果
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].name, "LLM信号1")
        self.assertEqual(signals[0].source, source)
        self.assertEqual(signals[0].confidence, 0.85)
    
    def test_deduplicate_signals(self):
        """测试去重信号"""
        # 创建重复信号
        signals = [
            AlphaSignal(
                name="信号1",
                description="这是一个关于600000.SH的信号",
                source="test.pdf",
                direction="positive",
                stock_codes=["600000.SH"],
                confidence=0.9
            ),
            AlphaSignal(
                name="信号2",
                description="这是一个关于600000.SH的信号",  # 描述相同
                source="test.pdf",
                direction="positive",
                stock_codes=["600000.SH"],
                confidence=0.8
            ),
            AlphaSignal(
                name="信号3",
                description="这是一个关于000001.SZ的信号",  # 描述不同
                source="test.pdf",
                direction="negative",
                stock_codes=["000001.SZ"],
                confidence=0.7
            )
        ]
        
        # 去重
        unique_signals = self.extractor._deduplicate_signals(signals)
        
        # 验证结果
        self.assertEqual(len(unique_signals), 2)  # 两个不同的信号
        self.assertEqual(unique_signals[0].name, "信号1")  # 保留高置信度的信号
        self.assertEqual(unique_signals[1].name, "信号3")


class TestAlphaExtractorFactory(unittest.TestCase):
    """Alpha提取器工厂测试"""
    
    def test_get_extractor_rule(self):
        """测试获取规则提取器"""
        extractor = AlphaExtractorFactory.get_extractor("rule")
        self.assertIsInstance(extractor, RuleBasedExtractor)
    
    def test_get_extractor_llm(self):
        """测试获取LLM提取器"""
        with patch('alpha.alpha_generation.alpha_extractor.LLMBasedExtractor._init_llm_client'):
            extractor = AlphaExtractorFactory.get_extractor("llm")
            self.assertIsInstance(extractor, LLMBasedExtractor)
    
    def test_get_extractor_ensemble(self):
        """测试获取集成提取器"""
        with patch('alpha.alpha_generation.alpha_extractor.LLMBasedExtractor._init_llm_client'):
            extractor = AlphaExtractorFactory.get_extractor("ensemble")
            self.assertIsInstance(extractor, LLMBasedExtractor)  # 目前使用LLM作为替代
    
    def test_get_extractor_invalid(self):
        """测试获取无效提取器"""
        extractor = AlphaExtractorFactory.get_extractor("invalid")
        self.assertIsInstance(extractor, RuleBasedExtractor)  # 默认使用规则提取器


if __name__ == '__main__':
    unittest.main()
