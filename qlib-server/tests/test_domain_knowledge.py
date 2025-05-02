"""
领域知识增强模块的单元测试
测试金融知识图谱、术语理解和因子逻辑解释功能
"""

import os
import sys
import unittest
import logging
import json
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

# 设置日志级别
logging.basicConfig(level=logging.INFO)

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入被测试模块
try:
    from alpha.domain_knowledge import FinancialKnowledgeGraph, FinancialTerminology, FactorLogicExplainer
    HAS_MODULE = True
except ImportError as e:
    logging.warning(f"无法导入领域知识模块: {e}")
    HAS_MODULE = False


@unittest.skipIf(not HAS_MODULE, "领域知识模块不可用")
class TestFinancialKnowledgeGraph(unittest.TestCase):
    """测试金融知识图谱"""
    
    def setUp(self):
        """每个测试前的设置"""
        # 使用临时路径进行测试
        self.test_path = os.path.join(os.path.dirname(__file__), 'test_data', 'knowledge_graph')
        os.makedirs(self.test_path, exist_ok=True)
        
        # 初始化知识图谱
        self.config = {'data_path': self.test_path}
        self.knowledge_graph = FinancialKnowledgeGraph(self.config)
    
    def tearDown(self):
        """每个测试后的清理"""
        # 清理生成的测试文件
        try:
            for filename in ['financial_knowledge_graph.json', 'knowledge_embeddings.npz']:
                file_path = os.path.join(self.test_path, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
        except Exception as e:
            logging.warning(f"清理测试文件失败: {e}")
    
    def test_add_entity(self):
        """测试添加实体"""
        # 添加新实体
        result = self.knowledge_graph.add_entity(
            "test_entity", 
            "factor", 
            {"description": "测试因子"}
        )
        
        # 验证结果
        self.assertTrue(result, "添加实体失败")
        self.assertIn("test_entity", self.knowledge_graph.graph.nodes, "实体未被添加到图谱")
        self.assertEqual(
            self.knowledge_graph.graph.nodes["test_entity"]["type"], 
            "factor", 
            "实体类型不正确"
        )
    
    def test_add_relation(self):
        """测试添加关系"""
        # 添加实体
        self.knowledge_graph.add_entity("entity1", "factor")
        self.knowledge_graph.add_entity("entity2", "industry")
        
        # 添加关系
        result = self.knowledge_graph.add_relation(
            "entity1", 
            "entity2", 
            "correlates_with", 
            0.8
        )
        
        # 验证结果
        self.assertTrue(result, "添加关系失败")
        self.assertTrue(
            self.knowledge_graph.graph.has_edge("entity1", "entity2"),
            "关系未被添加到图谱"
        )
        edge_data = self.knowledge_graph.graph["entity1"]["entity2"]
        self.assertEqual(edge_data["type"], "correlates_with", "关系类型不正确")
        self.assertEqual(edge_data["weight"], 0.8, "关系权重不正确")
    
    def test_get_entity(self):
        """测试获取实体"""
        # 添加实体和关系
        self.knowledge_graph.add_entity("entity1", "factor", {"description": "测试因子"})
        self.knowledge_graph.add_entity("entity2", "industry")
        self.knowledge_graph.add_relation("entity1", "entity2", "correlates_with")
        
        # 获取实体
        entity_data = self.knowledge_graph.get_entity("entity1")
        
        # 验证结果
        self.assertIsNotNone(entity_data, "未能获取实体")
        self.assertEqual(entity_data["type"], "factor", "实体类型不正确")
        self.assertEqual(entity_data["description"], "测试因子", "实体描述不正确")
        self.assertGreaterEqual(len(entity_data["relations"]), 1, "关系列表为空")
    
    def test_search_entities(self):
        """测试搜索实体"""
        # 添加多个实体
        self.knowledge_graph.add_entity("momentum_factor", "factor", {"description": "动量因子"})
        self.knowledge_graph.add_entity("value_factor", "factor", {"description": "价值因子"})
        self.knowledge_graph.add_entity("tech_industry", "industry", {"description": "科技行业"})
        
        # 搜索实体 - 直接查找节点ID中包含的字符
        results = self.knowledge_graph.search_entities("momentum")
        
        # 验证结果
        self.assertGreaterEqual(len(results), 1, "搜索结果为空")
        self.assertEqual(results[0]["type"], "factor", "搜索结果类型不正确")
        
        # 带类型筛选的搜索
        results = self.knowledge_graph.search_entities("factor", entity_type="factor")
        self.assertGreaterEqual(len(results), 1, "按类型搜索结果为空")
    
    def test_export_graph_data(self):
        """测试导出图谱数据"""
        # 添加实体和关系
        self.knowledge_graph.add_entity("entity1", "factor")
        self.knowledge_graph.add_entity("entity2", "industry")
        self.knowledge_graph.add_relation("entity1", "entity2", "correlates_with")
        
        # 导出图谱数据
        graph_data = self.knowledge_graph.export_graph_data()
        
        # 验证结果
        self.assertIn("nodes", graph_data, "导出数据缺少节点信息")
        self.assertIn("links", graph_data, "导出数据缺少链接信息")
        self.assertGreaterEqual(len(graph_data["nodes"]), 2, "节点数量不正确")
        self.assertGreaterEqual(len(graph_data["links"]), 1, "链接数量不正确")
    
    def test_save_and_load(self):
        """测试保存和加载图谱"""
        # 添加实体和关系
        self.knowledge_graph.add_entity("test_entity1", "factor")
        self.knowledge_graph.add_entity("test_entity2", "industry")
        self.knowledge_graph.add_relation("test_entity1", "test_entity2", "correlates_with")
        
        # 保存图谱
        self.knowledge_graph.save_graph()
        
        # 验证文件存在
        graph_file = os.path.join(self.test_path, 'financial_knowledge_graph.json')
        embeddings_file = os.path.join(self.test_path, 'knowledge_embeddings.npz')
        self.assertTrue(os.path.exists(graph_file), "图谱文件未保存")
        self.assertTrue(os.path.exists(embeddings_file), "嵌入文件未保存")
        
        # 重新加载图谱
        new_graph = FinancialKnowledgeGraph(self.config)
        
        # 验证加载结果
        self.assertIn("test_entity1", new_graph.graph.nodes, "加载后实体丢失")
        self.assertTrue(
            new_graph.graph.has_edge("test_entity1", "test_entity2"),
            "加载后关系丢失"
        )


@unittest.skipIf(not HAS_MODULE, "领域知识模块不可用")
class TestFinancialTerminology(unittest.TestCase):
    """测试金融术语理解模块"""
    
    def setUp(self):
        """每个测试前的设置"""
        # 使用临时路径进行测试
        self.test_path = os.path.join(os.path.dirname(__file__), 'test_data', 'terminology')
        os.makedirs(self.test_path, exist_ok=True)
        
        # 初始化术语库
        self.config = {'data_path': self.test_path}
        self.terminology = FinancialTerminology(self.config)
    
    def tearDown(self):
        """每个测试后的清理"""
        # 清理生成的测试文件
        try:
            for filename in [f'financial_terms_zh.json', f'term_embeddings_zh.npz']:
                file_path = os.path.join(self.test_path, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
        except Exception as e:
            logging.warning(f"清理测试文件失败: {e}")
    
    def test_add_term(self):
        """测试添加术语"""
        # 添加新术语
        result = self.terminology.add_term(
            "test_term",
            "测试术语",
            "这是一个用于测试的术语",
            "测试类别",
            ["示例1", "示例2"],
            ["related_term1", "related_term2"]
        )
        
        # 验证结果
        self.assertTrue(result, "添加术语失败")
        self.assertIn("test_term", self.terminology.terms, "术语未被添加到术语库")
        term_data = self.terminology.terms["test_term"]
        self.assertEqual(term_data["term"], "测试术语", "术语名称不正确")
        self.assertEqual(term_data["category"], "测试类别", "术语类别不正确")
        self.assertGreaterEqual(len(term_data["examples"]), 2, "术语示例不完整")
    
    def test_get_term(self):
        """测试获取术语"""
        # 添加术语
        self.terminology.add_term(
            "test_term",
            "测试术语",
            "这是一个用于测试的术语",
            "测试类别"
        )
        
        # 获取术语
        term_data = self.terminology.get_term("test_term")
        
        # 验证结果
        self.assertIsNotNone(term_data, "未能获取术语")
        self.assertEqual(term_data["term"], "测试术语", "术语名称不正确")
        self.assertEqual(term_data["definition"], "这是一个用于测试的术语", "术语定义不正确")
    
    def test_search_terms(self):
        """测试搜索术语"""
        # 添加多个术语
        self.terminology.add_term(
            "pe_ratio",
            "市盈率",
            "股票价格与每股收益的比率",
            "估值指标"
        )
        self.terminology.add_term(
            "pb_ratio",
            "市净率",
            "股票价格与每股净资产的比率",
            "估值指标"
        )
        self.terminology.add_term(
            "momentum",
            "动量因子",
            "基于历史价格变化的趋势因子",
            "因子"
        )
        
        # 更新索引
        self.terminology._build_search_index()
        
        # 搜索术语
        results = self.terminology.search_terms("市盈")
        
        # 验证结果
        self.assertGreaterEqual(len(results), 1, "搜索结果为空")
        self.assertEqual(results[0]["term"], "市盈率", "搜索结果不正确")
        
        # 带类别筛选的搜索
        results = self.terminology.search_terms("率", category="估值指标")
        self.assertGreaterEqual(len(results), 1, "按类别搜索结果为空")
    
    def test_explain_text(self):
        """测试文本解释"""
        # 添加术语
        self.terminology.add_term(
            "pe_ratio",
            "市盈率",
            "股票价格与每股收益的比率",
            "估值指标"
        )
        self.terminology.add_term(
            "pb_ratio",
            "市净率",
            "股票价格与每股净资产的比率",
            "估值指标"
        )
        
        # 更新索引
        self.terminology._build_search_index()
        
        # 解释文本 - 使用完全匹配的术语词
        text = "市盈率是常用的估值指标。"
        result = self.terminology.explain_text(text)
        
        # 验证结果
        self.assertEqual(result["original_text"], text, "原始文本不匹配")
        self.assertGreaterEqual(len(result["explanations"]), 1, "解释列表为空")
        self.assertIsNotNone(result["highlighted_text"], "高亮文本为空")
        self.assertIn("<strong>", result["highlighted_text"], "高亮文本未包含标记")
    
    def test_get_categories(self):
        """测试获取类别"""
        # 添加不同类别的术语
        self.terminology.add_term("term1", "术语1", "定义1", "类别1")
        self.terminology.add_term("term2", "术语2", "定义2", "类别2")
        self.terminology.add_term("term3", "术语3", "定义3", "类别1")
        
        # 获取所有类别
        categories = self.terminology.get_categories()
        
        # 验证结果
        self.assertGreaterEqual(len(categories), 2, "类别数量不正确")
        self.assertIn("类别1", categories, "缺少类别1")
        self.assertIn("类别2", categories, "缺少类别2")
    
    def test_save_and_load(self):
        """测试保存和加载术语库"""
        # 添加术语
        self.terminology.add_term("test_term", "测试术语", "测试定义", "测试类别")
        
        # 保存术语库
        self.terminology.save_terminology()
        
        # 验证文件存在
        terms_file = os.path.join(self.test_path, f'financial_terms_zh.json')
        embeddings_file = os.path.join(self.test_path, f'term_embeddings_zh.npz')
        self.assertTrue(os.path.exists(terms_file), "术语库文件未保存")
        self.assertTrue(os.path.exists(embeddings_file), "嵌入文件未保存")
        
        # 重新加载术语库
        new_terminology = FinancialTerminology(self.config)
        
        # 验证加载结果
        self.assertIn("test_term", new_terminology.terms, "加载后术语丢失")
        self.assertEqual(
            new_terminology.terms["test_term"]["term"], 
            "测试术语", 
            "加载后术语数据不正确"
        )


@unittest.skipIf(not HAS_MODULE, "领域知识模块不可用")
class TestFactorLogicExplainer(unittest.TestCase):
    """测试因子逻辑解释生成器"""
    
    def setUp(self):
        """每个测试前的设置"""
        # 使用临时路径进行测试
        self.test_path = os.path.join(os.path.dirname(__file__), 'test_data', 'factors')
        os.makedirs(self.test_path, exist_ok=True)
        
        # 初始化因子库，禁用LLM以加速测试
        self.config = {
            'data_path': self.test_path,
            'use_llm': False
        }
        self.factor_explainer = FactorLogicExplainer(self.config)
    
    def tearDown(self):
        """每个测试后的清理"""
        # 清理生成的测试文件
        try:
            for filename in ['factors_library.json', 'factor_correlations.json']:
                file_path = os.path.join(self.test_path, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
        except Exception as e:
            logging.warning(f"清理测试文件失败: {e}")
    
    def test_add_factor(self):
        """测试添加因子"""
        # 添加新因子
        result = self.factor_explainer.add_factor(
            "test_factor",
            "测试因子",
            "这是一个用于测试的因子",
            "测试类别",
            formula="$TestFactor = X + Y$",
            code="def test_factor(df):\n    return df['X'] + df['Y']",
            interpretation="这个因子反映了X和Y的关系"
        )
        
        # 验证结果
        self.assertTrue(result, "添加因子失败")
        self.assertIn("test_factor", self.factor_explainer.factors, "因子未被添加到因子库")
        factor_data = self.factor_explainer.factors["test_factor"]
        self.assertEqual(factor_data["name"], "测试因子", "因子名称不正确")
        self.assertEqual(factor_data["category"], "测试类别", "因子类别不正确")
    
    def test_get_factor(self):
        """测试获取因子"""
        # 添加因子
        self.factor_explainer.add_factor(
            "test_factor",
            "测试因子",
            "这是一个用于测试的因子",
            "测试类别"
        )
        
        # 获取因子
        factor_data = self.factor_explainer.get_factor("test_factor")
        
        # 验证结果
        self.assertIsNotNone(factor_data, "未能获取因子")
        self.assertEqual(factor_data["name"], "测试因子", "因子名称不正确")
        self.assertEqual(factor_data["description"], "这是一个用于测试的因子", "因子描述不正确")
        self.assertIn("correlations", factor_data, "因子相关性信息缺失")
    
    def test_search_factors(self):
        """测试搜索因子"""
        # 添加多个因子
        self.factor_explainer.add_factor(
            "momentum_factor",
            "1个月价格动量",
            "基于历史价格变化的趋势因子",
            "动量类别"
        )
        self.factor_explainer.add_factor(
            "value_factor",
            "价值因子",
            "基于公司基本面价值的因子",
            "价值类别"
        )
        self.factor_explainer.add_factor(
            "vol_factor",
            "波动率因子",
            "基于价格波动性的因子",
            "波动率类别"
        )
        
        # 搜索因子
        results = self.factor_explainer.search_factors("动量")
        
        # 验证结果
        self.assertGreaterEqual(len(results), 1, "搜索结果为空")
        self.assertEqual(results[0]["name"], "1个月价格动量", "搜索结果不正确")
        
        # 带类别筛选的搜索
        results = self.factor_explainer.search_factors("因子", category="价值类别")
        self.assertGreaterEqual(len(results), 1, "按类别搜索结果为空")
        self.assertEqual(results[0]["category"], "价值类别", "搜索结果类别不正确")
    
    def test_factor_correlations(self):
        """测试因子相关性"""
        # 添加因子
        self.factor_explainer.add_factor("factor1", "因子1", "描述1", "类别1")
        self.factor_explainer.add_factor("factor2", "因子2", "描述2", "类别2")
        
        # 添加相关性
        result = self.factor_explainer.update_factor_correlation(
            "factor1",
            "factor2",
            0.75,
            "strong",
            "positive"
        )
        
        # 验证添加结果
        self.assertTrue(result, "添加相关性失败")
        
        # 获取相关性
        correlations = self.factor_explainer.get_factor_correlations("factor1")
        
        # 验证获取结果
        self.assertGreaterEqual(len(correlations), 1, "相关性列表为空")
        self.assertEqual(correlations[0]["factor"], "factor2", "相关因子ID不正确")
        self.assertEqual(correlations[0]["correlation"], 0.75, "相关系数不正确")
        self.assertEqual(correlations[0]["strength"], "strong", "相关强度不正确")
    
    def test_get_categories(self):
        """测试获取类别"""
        # 添加不同类别的因子
        self.factor_explainer.add_factor("factor1", "因子1", "描述1", "类别A")
        self.factor_explainer.add_factor("factor2", "因子2", "描述2", "类别B")
        self.factor_explainer.add_factor("factor3", "因子3", "描述3", "类别A")
        
        # 获取所有类别
        categories = self.factor_explainer.get_categories()
        
        # 验证结果
        self.assertGreaterEqual(len(categories), 2, "类别数量不正确")
        self.assertIn("类别A", categories, "缺少类别A")
        self.assertIn("类别B", categories, "缺少类别B")
    
    def test_save_and_load(self):
        """测试保存和加载因子库"""
        # 添加因子和相关性
        self.factor_explainer.add_factor("test_factor", "测试因子", "测试描述", "测试类别")
        self.factor_explainer.add_factor("related_factor", "相关因子", "相关描述", "相关类别")
        self.factor_explainer.update_factor_correlation("test_factor", "related_factor", 0.6)
        
        # 保存因子库
        self.factor_explainer.save_factors()
        
        # 验证文件存在
        factors_file = os.path.join(self.test_path, 'factors_library.json')
        correlations_file = os.path.join(self.test_path, 'factor_correlations.json')
        self.assertTrue(os.path.exists(factors_file), "因子库文件未保存")
        self.assertTrue(os.path.exists(correlations_file), "相关性文件未保存")
        
        # 重新加载因子库
        new_explainer = FactorLogicExplainer(self.config)
        
        # 验证加载结果
        self.assertIn("test_factor", new_explainer.factors, "加载后因子丢失")
        self.assertEqual(
            new_explainer.factors["test_factor"]["name"], 
            "测试因子", 
            "加载后因子数据不正确"
        )
        self.assertIn(
            "test_factor", 
            new_explainer.factor_correlations, 
            "加载后相关性数据丢失"
        )
    
    @patch('torch.cuda.is_available')
    @patch('alpha.domain_knowledge.factor_explainer.AutoTokenizer')
    @patch('alpha.domain_knowledge.factor_explainer.AutoModelForCausalLM')
    def test_generate_factor_logic_with_llm(self, mock_model_class, mock_tokenizer_class, mock_cuda):
        """测试使用LLM生成因子逻辑"""
        # 只有在HAS_LLM为True时才执行此测试
        if not hasattr(self.factor_explainer, 'HAS_LLM') or not self.factor_explainer.HAS_LLM:
            self.skipTest("LLM相关库不可用，跳过测试")
        
        # 设置模拟返回值
        mock_cuda.return_value = False
        
        # 模拟tokenizer
        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = MagicMock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        
        # 模拟模型
        mock_model = MagicMock()
        mock_model.generate.return_value = [0]  # 简单的token序列
        mock_tokenizer.decode.return_value = '''```json
{
    "name": "成交量价比率",
    "category": "成交量因子",
    "description": "衡量股票成交量与价格变化的比率",
    "formula": "$VPR = \\frac{Volume_t}{|Price_t - Price_{t-1}|}$",
    "code": "def volume_price_ratio(df):\\n    price_change = abs(df[\\'close\\'] - df[\\'close\\'].shift(1))\\n    return df[\\'volume\\'] / price_change",
    "explanation": "成交量价比率反映了价格变动所需的流动性，高VPR表示同等价格变动需要更多成交量，可能意味着市场吸收能力强。",
    "examples": [
        {
            "scenario": "股票价格小幅波动但成交量大增",
            "explanation": "VPR值较高，表明市场有较强的吸收能力",
            "result": "可能预示着行情即将启动"
        },
        {
            "scenario": "股票价格大幅波动但成交量增加有限",
            "explanation": "VPR值较低，表明市场流动性不足",
            "result": "可能是短期价格波动，不具可持续性"
        }
    ]
}
```'''
        mock_model_class.from_pretrained.return_value = mock_model
        
        # 使用启用LLM的配置
        config = {
            'data_path': self.test_path,
            'use_llm': True,
            'device': 'cpu'
        }
        explainer_with_llm = FactorLogicExplainer(config)
        
        # 生成因子逻辑
        result = explainer_with_llm.generate_factor_logic(
            "一个基于成交量与价格变化比率的因子，用于评估市场吸收能力",
            "未来收益率"
        )
        
        # 验证结果
        self.assertTrue(result['success'], "因子逻辑生成失败")
        self.assertIsNotNone(result['factor'], "生成的因子为空")
        self.assertEqual(result['factor']['name'], "成交量价比率", "因子名称不正确")
    
    def test_visualize_factor_performance(self):
        """测试可视化因子表现"""
        # 添加因子
        self.factor_explainer.add_factor(
            "test_factor",
            "测试因子",
            "测试描述",
            "测试类别"
        )
        
        # 准备测试数据
        np.random.seed(42)
        data = pd.DataFrame({
            'factor_value': np.random.randn(100),
            'returns': np.random.randn(100) * 0.01  # 1%标准差的收益率
        })
        
        # 添加相关性使factor_value和returns有一定相关性
        data['returns'] = data['returns'] + data['factor_value'] * 0.005
        
        # 可视化因子表现
        result = self.factor_explainer.visualize_factor_performance("test_factor", data)
        
        # 验证结果
        self.assertTrue(result['success'], "因子表现可视化失败")
        self.assertEqual(result['factor_id'], "test_factor", "因子ID不正确")
        self.assertIn('group_analysis', result, "缺少分组分析")
        self.assertIn('ic_analysis', result, "缺少IC分析")
        self.assertIn('regression_analysis', result, "缺少回归分析")
        self.assertGreater(result['ic_analysis']['ic'], 0, "IC值应为正")


# 判断是否直接运行
if __name__ == '__main__':
    unittest.main()
