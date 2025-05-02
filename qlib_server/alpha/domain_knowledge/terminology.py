"""
金融术语理解模块
提供金融领域术语的存储、检索和解释功能
"""

import os
import json
import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Union, Any
from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 配置日志
logger = logging.getLogger(__name__)

class FinancialTerminology:
    """金融术语理解模块"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化金融术语理解模块
        
        参数:
            config: 配置参数，包含:
                - data_path: 术语库数据路径
                - preload: 是否预加载术语库
                - language: 语言，默认'zh'（中文）
        """
        self.config = config or {}
        self.data_path = self.config.get('data_path', os.path.join('/data/qlib', 'terminology'))
        self.preload = self.config.get('preload', True)
        self.language = self.config.get('language', 'zh')
        
        # 初始化术语库
        self.terms = {}
        self.term_embeddings = {}
        self.term_categories = set()
        self.term_index = defaultdict(list)  # 用于快速查找
        self.vectorizer = None
        
        if self.preload:
            self._load_terminology()
            self._build_search_index()
        
        logger.info(f"金融术语模块初始化完成，包含 {len(self.terms)} 个术语")
    
    def _load_terminology(self) -> None:
        """加载术语库数据"""
        try:
            # 检查术语库文件是否存在
            terms_file = os.path.join(self.data_path, f'financial_terms_{self.language}.json')
            embeddings_file = os.path.join(self.data_path, f'term_embeddings_{self.language}.npz')
            
            if os.path.exists(terms_file):
                with open(terms_file, 'r', encoding='utf-8') as f:
                    self.terms = json.load(f)
                logger.info(f"从 {terms_file} 加载术语库成功")
                
                # 提取所有类别
                self.term_categories = set(term['category'] for term in self.terms.values() if 'category' in term)
            else:
                logger.warning(f"术语库文件 {terms_file} 不存在，将初始化基础术语库")
                self._initialize_base_terminology()
            
            # 加载嵌入
            if os.path.exists(embeddings_file):
                embeddings = np.load(embeddings_file)
                self.term_embeddings = {term_id: embeddings['term_embeddings'][i] 
                                       for i, term_id in enumerate(embeddings['term_ids'])}
                logger.info(f"从 {embeddings_file} 加载术语嵌入成功")
            else:
                logger.warning(f"术语嵌入文件 {embeddings_file} 不存在，将使用文本特征")
                self._create_text_embeddings()
        
        except Exception as e:
            logger.error(f"加载术语库失败: {e}")
            # 如果加载失败，初始化基础术语库
            self._initialize_base_terminology()
            self._create_text_embeddings()
    
    def _initialize_base_terminology(self) -> None:
        """初始化基础术语库"""
        logger.info("初始化基础术语库")
        
        # 基础术语列表
        base_terms = [
            {
                'id': 'alpha',
                'term': 'Alpha',
                'definition': '超额收益，指投资组合相对于基准的额外回报率，通常用来衡量主动投资管理的能力。',
                'category': '投资指标',
                'examples': ['某基金的Alpha为2%，表示它比大盘表现好2个百分点。'],
                'related_terms': ['beta', 'sharp_ratio', 'active_return']
            },
            {
                'id': 'beta',
                'term': 'Beta',
                'definition': '市场风险系数，衡量证券或投资组合相对于整体市场的波动程度。Beta为1表示与市场同步波动，大于1表示波动更大，小于1表示波动更小。',
                'category': '风险指标',
                'examples': ['科技股的Beta通常大于1，表示它比整体市场更为波动。'],
                'related_terms': ['alpha', 'volatility', 'systematic_risk']
            },
            {
                'id': 'sharp_ratio',
                'term': '夏普比率',
                'definition': '风险调整后收益指标，计算超额收益与波动率的比值，用于衡量单位风险所获得的超额回报。',
                'category': '绩效指标',
                'examples': ['夏普比率为2.0的基金，意味着它的风险调整后收益非常优秀。'],
                'related_terms': ['alpha', 'information_ratio', 'sortino_ratio']
            },
            {
                'id': 'momentum',
                'term': '动量因子',
                'definition': '基于价格趋势的投资策略，认为价格运动趋势会在短期内持续，即"强者恒强，弱者恒弱"。',
                'category': '投资因子',
                'examples': ['过去3个月表现最好的股票在接下来的一个月继续表现良好。'],
                'related_terms': ['reversal', 'trend_following', 'price_momentum']
            },
            {
                'id': 'value',
                'term': '价值因子',
                'definition': '基于公司内在价值与市场价格比较的投资策略，寻找被低估的股票。常见指标包括市盈率(PE)、市净率(PB)等。',
                'category': '投资因子',
                'examples': ['低PE的股票长期来看可能获得超额收益。'],
                'related_terms': ['growth', 'pe_ratio', 'pb_ratio', 'intrinsic_value']
            },
            {
                'id': 'pe_ratio',
                'term': '市盈率',
                'definition': '股票价格与每股收益的比率，是最常用的估值指标之一。较低的PE可能意味着股票被低估，但也可能反映其增长前景不佳。',
                'category': '财务指标',
                'examples': ['科技股通常有较高的PE，因为投资者预期其未来有更高的增长。'],
                'related_terms': ['pb_ratio', 'value', 'earnings_yield']
            },
            {
                'id': 'volatility',
                'term': '波动率',
                'definition': '衡量证券价格变动幅度的指标，通常使用标准差或方差来计算。高波动率意味着价格变动更大，风险更高。',
                'category': '风险指标',
                'examples': ['VIX指数是衡量市场预期波动率的晴雨表。'],
                'related_terms': ['beta', 'risk', 'standard_deviation', 'vix']
            },
            {
                'id': 'backtest',
                'term': '回测',
                'definition': '使用历史数据来评估投资策略表现的过程。通过回测，可以模拟策略在过去市场条件下的表现，帮助评估其潜在效果和风险。',
                'category': '量化方法',
                'examples': ['策略回测显示过去10年的年化收益为12%，但最大回撤达到25%。'],
                'related_terms': ['performance_metrics', 'overfitting', 'forward_testing']
            },
            {
                'id': 'factor_exposure',
                'term': '因子暴露',
                'definition': '投资组合对特定因子的敏感程度。高因子暴露意味着投资组合的表现将更大程度地受到该因子变动的影响。',
                'category': '因子分析',
                'examples': ['该投资组合对动量因子的暴露度高，对价值因子的暴露度低。'],
                'related_terms': ['factor_loading', 'factor_model', 'risk_exposure']
            },
            {
                'id': 'factor_neutralization',
                'term': '因子中性化',
                'definition': '调整投资组合以减少或消除对特定因子的暴露，目的是隔离特定风险或专注于特定的阿尔法来源。',
                'category': '投资策略',
                'examples': ['通过做多低PE股票和做空高PE股票，可以构建对市场中性的价值因子投资组合。'],
                'related_terms': ['market_neutral', 'hedging', 'factor_exposure']
            }
        ]
        
        # 将基础术语添加到术语库
        for term_data in base_terms:
            term_id = term_data['id']
            self.terms[term_id] = term_data
        
        # 提取所有类别
        self.term_categories = set(term['category'] for term in self.terms.values() if 'category' in term)
        
        logger.info(f"基础术语库初始化完成，包含 {len(self.terms)} 个术语")
    
    def _create_text_embeddings(self) -> None:
        """创建术语的文本嵌入"""
        if not self.terms:
            logger.warning("术语库为空，无法创建文本嵌入")
            return
        
        try:
            # 准备文本数据
            texts = []
            term_ids = []
            
            for term_id, term_data in self.terms.items():
                # 合并术语相关文本
                term_text = f"{term_data['term']} {term_data['definition']}"
                if 'examples' in term_data:
                    term_text += ' ' + ' '.join(term_data['examples'])
                
                texts.append(term_text)
                term_ids.append(term_id)
            
            # 创建TF-IDF向量化器
            self.vectorizer = TfidfVectorizer(max_features=100)
            term_vectors = self.vectorizer.fit_transform(texts)
            
            # 保存嵌入
            for i, term_id in enumerate(term_ids):
                self.term_embeddings[term_id] = term_vectors[i].toarray()[0]
            
            logger.info(f"使用TF-IDF创建了 {len(term_ids)} 个术语的文本嵌入")
        
        except Exception as e:
            logger.error(f"创建文本嵌入失败: {e}")
    
    def _build_search_index(self) -> None:
        """构建术语搜索索引"""
        self.term_index = defaultdict(list)
        
        for term_id, term_data in self.terms.items():
            # 添加术语本身
            term = term_data['term'].lower()
            self.term_index[term].append(term_id)
            
            # 添加术语的各个部分（针对多词术语）
            for part in re.findall(r'\w+', term):
                if len(part) > 1:  # 忽略单个字符
                    self.term_index[part.lower()].append(term_id)
            
            # 添加相关术语
            if 'related_terms' in term_data:
                for related in term_data['related_terms']:
                    self.term_index[related.lower()].append(term_id)
        
        logger.info(f"构建了包含 {len(self.term_index)} 个索引项的术语搜索索引")
    
    def save_terminology(self) -> None:
        """保存术语库到文件"""
        try:
            # 确保目录存在
            os.makedirs(self.data_path, exist_ok=True)
            
            # 保存术语库
            terms_file = os.path.join(self.data_path, f'financial_terms_{self.language}.json')
            with open(terms_file, 'w', encoding='utf-8') as f:
                json.dump(self.terms, f, ensure_ascii=False, indent=2)
            
            # 保存嵌入
            embeddings_file = os.path.join(self.data_path, f'term_embeddings_{self.language}.npz')
            term_ids = list(self.term_embeddings.keys())
            term_embs = np.array([self.term_embeddings[tid] for tid in term_ids])
            
            np.savez(embeddings_file, term_ids=term_ids, term_embeddings=term_embs)
            
            logger.info(f"术语库和嵌入保存成功: {terms_file}, {embeddings_file}")
        
        except Exception as e:
            logger.error(f"保存术语库失败: {e}")
    
    def add_term(self, term_id: str, term: str, definition: str, category: str = None,
                examples: List[str] = None, related_terms: List[str] = None) -> bool:
        """
        添加新术语
        
        参数:
            term_id: 术语ID
            term: 术语名称
            definition: 术语定义
            category: 术语类别
            examples: 示例列表
            related_terms: 相关术语ID列表
        
        返回:
            添加是否成功
        """
        if term_id in self.terms:
            logger.warning(f"术语 {term_id} 已存在，将更新")
        
        # 准备术语数据
        term_data = {
            'id': term_id,
            'term': term,
            'definition': definition,
            'category': category or '未分类'
        }
        
        if examples:
            term_data['examples'] = examples
        
        if related_terms:
            term_data['related_terms'] = related_terms
        
        # 添加到术语库
        self.terms[term_id] = term_data
        
        # 更新类别集合
        if category:
            self.term_categories.add(category)
        
        # 创建文本嵌入
        if self.vectorizer is not None:
            term_text = f"{term} {definition}"
            if examples:
                term_text += ' ' + ' '.join(examples)
            
            term_vector = self.vectorizer.transform([term_text])
            self.term_embeddings[term_id] = term_vector.toarray()[0]
        
        # 更新搜索索引
        self._update_term_index(term_id, term_data)
        
        logger.info(f"添加术语: {term_id} - {term}")
        return True
    
    def _update_term_index(self, term_id: str, term_data: Dict[str, Any]) -> None:
        """
        更新特定术语的搜索索引
        
        参数:
            term_id: 术语ID
            term_data: 术语数据
        """
        # 添加术语本身
        term = term_data['term'].lower()
        self.term_index[term].append(term_id)
        
        # 添加术语的各个部分（针对多词术语）
        for part in re.findall(r'\w+', term):
            if len(part) > 1:  # 忽略单个字符
                self.term_index[part.lower()].append(term_id)
        
        # 添加相关术语
        if 'related_terms' in term_data:
            for related in term_data['related_terms']:
                self.term_index[related.lower()].append(term_id)
    
    def get_term(self, term_id: str) -> Optional[Dict[str, Any]]:
        """
        获取术语详情
        
        参数:
            term_id: 术语ID
        
        返回:
            术语详情字典
        """
        if term_id not in self.terms:
            logger.warning(f"术语 {term_id} 不存在")
            return None
        
        return self.terms[term_id]
    
    def search_terms(self, query: str, category: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索术语
        
        参数:
            query: 搜索关键词
            category: 可选的类别筛选
            limit: 结果数量限制
        
        返回:
            术语列表
        """
        query = query.lower()
        candidate_ids = set()
        
        # 首先尝试直接匹配
        for term_part in re.findall(r'\w+', query):
            if term_part in self.term_index:
                candidate_ids.update(self.term_index[term_part])
        
        # 如果没有直接匹配，尝试使用嵌入进行语义搜索
        if not candidate_ids and self.vectorizer is not None:
            try:
                query_vector = self.vectorizer.transform([query])
                
                # 计算与所有术语的相似度
                similarities = {}
                for term_id, embedding in self.term_embeddings.items():
                    sim = cosine_similarity(query_vector, embedding.reshape(1, -1))[0][0]
                    similarities[term_id] = sim
                
                # 获取最相似的术语
                sorted_terms = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
                candidate_ids.update([term_id for term_id, _ in sorted_terms[:limit]])
                
            except Exception as e:
                logger.error(f"语义搜索失败: {e}")
        
        # 筛选结果
        results = []
        for term_id in candidate_ids:
            term_data = self.terms[term_id]
            
            # 应用类别筛选
            if category and term_data.get('category') != category:
                continue
            
            results.append(term_data)
            
            if len(results) >= limit:
                break
        
        # 计算匹配分数并排序
        for result in results:
            term = result['term'].lower()
            definition = result['definition'].lower()
            
            # 简单的相关性分数
            score = 0
            if query in term:
                score += 5  # 术语名称中包含查询词
            elif any(query in part.lower() for part in re.findall(r'\w+', term)):
                score += 3  # 术语名称的部分匹配查询词
            
            if query in definition:
                score += 2  # 定义中包含查询词
            
            result['relevance_score'] = score
        
        # 按相关性分数排序
        results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        return results
    
    def get_similar_terms(self, term_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        获取语义相似的术语
        
        参数:
            term_id: 术语ID
            limit: 结果数量限制
        
        返回:
            相似术语列表
        """
        if term_id not in self.terms:
            logger.warning(f"术语 {term_id} 不存在")
            return []
        
        if term_id not in self.term_embeddings:
            logger.warning(f"术语 {term_id} 的嵌入不存在")
            return []
        
        # 获取当前术语的嵌入
        query_embedding = self.term_embeddings[term_id]
        
        # 计算与所有其他术语的相似度
        similarities = {}
        for other_id, embedding in self.term_embeddings.items():
            if other_id != term_id:  # 排除自身
                sim = cosine_similarity(query_embedding.reshape(1, -1), embedding.reshape(1, -1))[0][0]
                similarities[other_id] = sim
        
        # 获取最相似的术语
        similar_ids = sorted(similarities.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        # 提取详细信息
        results = []
        for similar_id, similarity in similar_ids:
            term_data = self.terms[similar_id].copy()
            term_data['similarity'] = float(similarity)
            results.append(term_data)
        
        return results
    
    def get_terms_by_category(self, category: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取特定类别的术语
        
        参数:
            category: 术语类别
            limit: 结果数量限制
        
        返回:
            术语列表
        """
        if category not in self.term_categories:
            logger.warning(f"类别 {category} 不存在")
            return []
        
        results = [term for term in self.terms.values() if term.get('category') == category]
        
        # 按字母顺序排序
        results.sort(key=lambda x: x['term'])
        
        return results[:limit]
    
    def get_popular_terms(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取热门术语
        
        参数:
            limit: 结果数量限制
        
        返回:
            热门术语列表
        """
        # 在没有使用统计的情况下，可以返回有最多相关术语的术语
        terms_with_relations = []
        for term_id, term_data in self.terms.items():
            num_relations = len(term_data.get('related_terms', []))
            terms_with_relations.append((term_id, num_relations))
        
        # 按关联术语数量排序
        terms_with_relations.sort(key=lambda x: x[1], reverse=True)
        popular_ids = [term_id for term_id, _ in terms_with_relations[:limit]]
        
        return [self.terms[term_id] for term_id in popular_ids]
    
    def get_categories(self) -> List[str]:
        """
        获取所有术语类别
        
        返回:
            类别列表
        """
        return sorted(list(self.term_categories))
    
    def explain_text(self, text: str, highlight: bool = True) -> Dict[str, Any]:
        """
        解释文本中的金融术语
        
        参数:
            text: 要解释的文本
            highlight: 是否高亮显示找到的术语
        
        返回:
            解释结果，包含原文和解释列表
        """
        result = {
            'original_text': text,
            'explanations': [],
            'highlighted_text': text if highlight else None
        }
        
        # 打印调试信息
        logger.info(f"开始解释文本: {text}")
        logger.info(f"当前术语索引包含 {len(self.term_index)} 个项")
        
        found_terms = {}
        
        # 直接检查每个术语是否在文本中
        for term_id, term_data in self.terms.items():
            term_text = term_data['term'].lower()
            # 检查术语是否在文本中
            if term_text in text.lower():
                logger.info(f"在文本中找到术语: {term_text}")
                found_terms[term_id] = term_data
        
        # 整理解释
        for term_id, term_data in found_terms.items():
            explanation = {
                'id': term_id,
                'term': term_data['term'],
                'definition': term_data['definition'],
                'category': term_data.get('category', '未分类')
            }
            result['explanations'].append(explanation)
        
        # 生成高亮文本
        if highlight and found_terms:
            highlighted = text
            for term_data in found_terms.values():
                term_text = term_data['term']
                pattern = f"(?i){re.escape(term_text)}"
                replacement = f"<strong>{term_text}</strong>"
                highlighted = re.sub(pattern, replacement, highlighted)
            
            result['highlighted_text'] = highlighted
        
        logger.info(f"解释完成，找到 {len(result['explanations'])} 个术语")
        return result
