#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Alpha生成流水线集成测试
测试完整的Alpha生成流程，包括文档解析、信号提取和信号验证
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
from alpha.alpha_generation.document_parser import DocumentParser
from alpha.alpha_generation.alpha_extractor import AlphaExtractorFactory, AlphaSignal
from alpha.alpha_generation.alpha_validator import AlphaValidatorFactory, AlphaValidationResult


class AlphaGenerationPipelineTest(unittest.TestCase):
    """Alpha生成流水线集成测试"""
    
    def setUp(self):
        """测试初始化"""
        # 创建临时目录存放测试文件和结果
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = self.temp_dir.name
        
        # 设置测试文件路径
        self.test_pdf_path = os.path.join(self.output_dir, "test_document.pdf")
        self.signals_output_path = os.path.join(self.output_dir, "signals.json")
        self.validation_output_path = os.path.join(self.output_dir, "validation_results.json")
        
        # 创建测试配置
        self.parser_config = {
            'pdf': {'extract_tables': True, 'use_ocr': False},
            'docx': {'extract_tables': True},
            'webpage': {'remove_ads': True, 'extract_tables': True}
        }
        
        self.extractor_config = {
            'keywords': {
                'positive': ['增长', '上升', '利好'],
                'negative': ['下降', '减少', '利空'],
                'short_term': ['短期'],
                'medium_term': ['中期'],
                'long_term': ['长期']
            },
            'minimum_confidence': 0.6
        }
        
        self.validator_config = {
            'required_fields': ['name', 'description', 'source'],
            'minimum_confidence': 0.6,
            'minimum_description_length': 10  # 测试用较短长度
        }
        
        # 初始化Mock pdf文件内容
        self._create_mock_pdf()
    
    def tearDown(self):
        """测试清理"""
        self.temp_dir.cleanup()
    
    def _create_mock_pdf(self):
        """创建模拟的PDF文件"""
        # 在实际测试中，我们不会真正创建PDF文件，而是通过Mock解析过程
        with open(self.test_pdf_path, 'w', encoding='utf-8') as f:
            f.write("模拟PDF文件内容")
    
    @patch('alpha.alpha_generation.document_parser.pdfplumber.open')
    def test_complete_alpha_generation_pipeline(self, mock_pdf_open):
        """测试完整的Alpha生成流水线"""
        # 模拟PDF解析过程
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = """
        研究报告：A股市场投资策略分析
        
        一、市场概述
        近期A股市场持续上升，主要指数突破重要压力位，市场情绪明显转暖。
        
        二、板块分析
        科技板块：半导体行业景气度持续提升，产业链公司业绩普遍超预期。推荐关注600000.SH，ROE约15%，PE值8.5，中长期增长潜力显著。
        
        金融板块：银行股估值处于历史底部，随着经济复苏有望迎来修复行情。其中000001.SZ基本面稳健，短期内将受益于政策红利。
        
        三、风险提示
        需关注海外市场波动风险及国内政策调整可能带来的不确定性。
        """
        mock_page.extract_tables.return_value = [
            [
                ["股票代码", "股票名称", "所属行业", "PE", "评级"],
                ["600000.SH", "浦发银行", "银行", "8.5", "买入"],
                ["000001.SZ", "平安银行", "银行", "9.2", "中性"]
            ]
        ]
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        
        # 步骤1：文档解析
        print("\n--- 第一步：文档解析 ---")
        document_parser = DocumentParser(self.parser_config)
        parsed_result = document_parser.parse(self.test_pdf_path)
        
        # 验证解析结果
        self.assertTrue(parsed_result["success"])
        self.assertIn("A股市场投资策略分析", parsed_result["content"])
        self.assertEqual(parsed_result["metadata"]["type"], "pdf")
        self.assertGreaterEqual(len(parsed_result["tables"]), 1)
        print(f"文档解析完成，提取了{len(parsed_result['tables'])}个表格")
        
        # 步骤2：提取章节
        print("\n--- 提取文档章节 ---")
        sections = document_parser.extract_sections()
        self.assertIn("市场概述", sections.keys())
        self.assertIn("板块分析", sections.keys())
        self.assertIn("风险提示", sections.keys())
        print(f"成功提取{len(sections)}个章节")
        
        # 步骤3：Alpha信号提取
        print("\n--- 第二步：Alpha信号提取 ---")
        alpha_extractor = AlphaExtractorFactory.get_extractor("rule", self.extractor_config)
        signals = alpha_extractor.extract(parsed_result)
        
        # 验证提取结果
        self.assertGreaterEqual(len(signals), 2)  # 应该至少提取出两个信号
        print(f"成功提取{len(signals)}个Alpha信号")
        
        # 保存信号
        saved_path = alpha_extractor.save_signals(signals, self.signals_output_path)
        self.assertTrue(os.path.exists(saved_path))
        print(f"Alpha信号已保存到: {saved_path}")
        
        # 步骤4：信号验证
        print("\n--- 第三步：信号验证 ---")
        alpha_validator = AlphaValidatorFactory.get_validator("basic", self.validator_config)
        validation_results = alpha_validator.validate(signals)
        
        # 验证结果
        self.assertEqual(len(validation_results), len(signals))
        valid_count = sum(1 for result in validation_results if result.is_valid)
        print(f"验证完成: 总计{len(validation_results)}个信号, 其中{valid_count}个有效")
        
        # 保存验证结果
        saved_path = alpha_validator.save_results(validation_results, self.validation_output_path)
        self.assertTrue(os.path.exists(saved_path))
        print(f"验证结果已保存到: {saved_path}")
        
        # 输出示例信号和验证结果
        if signals:
            example_signal = signals[0]
            print("\n示例信号:")
            print(f"  名称: {example_signal.name}")
            print(f"  描述: {example_signal.description[:100]}...")
            print(f"  类型: {example_signal.signal_type}")
            print(f"  方向: {example_signal.direction}")
            print(f"  置信度: {example_signal.confidence}")
            if example_signal.stock_codes:
                print(f"  股票代码: {', '.join(example_signal.stock_codes)}")
            if example_signal.metrics:
                print(f"  指标: {example_signal.metrics}")
        
        if validation_results:
            example_result = validation_results[0]
            print("\n示例验证结果:")
            print(f"  信号名称: {example_result.signal_name}")
            print(f"  是否有效: {example_result.is_valid}")
            print(f"  验证得分: {example_result.validation_score}")
            if example_result.error_message:
                print(f"  错误信息: {example_result.error_message}")


class AlphaGenerationAPIUsageTest(unittest.TestCase):
    """Alpha生成API使用示例测试"""
    
    def test_api_usage_example(self):
        """测试API使用示例"""
        print("\n\n=== Alpha生成API使用示例 ===\n")
        
        # 这个测试不会真正运行，只是展示API的使用方式
        # 以下代码仅供参考，不会被实际执行
        
        print("# 1. 初始化文档解析器")
        print("from alpha.alpha_generation.document_parser import DocumentParser")
        print("parser = DocumentParser()")
        print("result = parser.parse('research_report.pdf')")
        print("# 可以提取文档章节")
        print("sections = parser.extract_sections()")
        
        print("\n# 2. 提取Alpha信号")
        print("from alpha.alpha_generation.alpha_extractor import AlphaExtractorFactory")
        print("# 使用规则提取器")
        print("rule_extractor = AlphaExtractorFactory.get_extractor('rule')")
        print("signals = rule_extractor.extract(result)")
        print("# 或使用LLM提取器")
        print("llm_extractor = AlphaExtractorFactory.get_extractor('llm', {'api_key': 'YOUR_API_KEY'})")
        print("signals = llm_extractor.extract(result)")
        
        print("\n# 3. 验证Alpha信号")
        print("from alpha.alpha_generation.alpha_validator import AlphaValidatorFactory")
        print("validator = AlphaValidatorFactory.get_validator('basic')")
        print("validation_results = validator.validate(signals)")
        print("# 输出验证结果")
        print("for result in validation_results:")
        print("    print(f'{result.signal_name}: 有效性={result.is_valid}, 得分={result.validation_score}')")
        
        print("\n# 完整流水线示例")
        print("def alpha_generation_pipeline(document_path):")
        print("    # 1. 解析文档")
        print("    parser = DocumentParser()")
        print("    result = parser.parse(document_path)")
        print("    ")
        print("    # 2. 提取信号")
        print("    extractor = AlphaExtractorFactory.get_extractor('rule')")
        print("    signals = extractor.extract(result)")
        print("    ")
        print("    # 3. 验证信号")
        print("    validator = AlphaValidatorFactory.get_validator('basic')")
        print("    validation_results = validator.validate(signals)")
        print("    ")
        print("    # 4. 返回结果")
        print("    return {")
        print("        'parsed_result': result,")
        print("        'signals': [s.to_dict() for s in signals],")
        print("        'validation_results': [r.to_dict() for r in validation_results]")
        print("    }")
        print("")
        print("# 调用流水线")
        print("results = alpha_generation_pipeline('research_report.pdf')")
        
        # 测试通过
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
