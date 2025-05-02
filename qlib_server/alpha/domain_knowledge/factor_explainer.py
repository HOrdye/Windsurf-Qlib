"""
因子逻辑解释生成器
提供量化投资因子的解释、可视化和生成功能
"""

import os
import json
import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Union, Any
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

# 可选的LLM导入
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    HAS_LLM = True
except ImportError:
    HAS_LLM = False

# 配置日志
logger = logging.getLogger(__name__)

class FactorLogicExplainer:
    """因子逻辑解释生成器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化因子逻辑解释生成器
        
        参数:
            config: 配置参数，包含:
                - data_path: 因子库数据路径
                - use_llm: 是否使用LLM生成解释
                - llm_model: LLM模型名称
                - device: 设备，'cpu'或'cuda'
        """
        self.config = config or {}
        self.data_path = self.config.get('data_path', os.path.join('/data/qlib', 'factors'))
        self.use_llm = self.config.get('use_llm', HAS_LLM)
        self.llm_model = self.config.get('llm_model', 'THUDM/chatglm-6b')
        self.device = self.config.get('device', 'cuda' if torch.cuda.is_available() else 'cpu') if HAS_LLM else 'cpu'
        
        # 初始化因子库
        self.factors = {}
        self.factor_categories = set()
        self.factor_correlations = {}
        
        # 加载因子库
        self._load_factors()
        
        # 初始化LLM（如果启用）
        self.tokenizer = None
        self.model = None
        if self.use_llm and HAS_LLM:
            self._init_llm()
        
        logger.info(f"因子逻辑解释生成器初始化完成，包含 {len(self.factors)} 个因子")
    
    def _load_factors(self) -> None:
        """加载因子库数据"""
        try:
            # 检查因子库文件是否存在
            factors_file = os.path.join(self.data_path, 'factors_library.json')
            correlations_file = os.path.join(self.data_path, 'factor_correlations.json')
            
            if os.path.exists(factors_file):
                with open(factors_file, 'r', encoding='utf-8') as f:
                    self.factors = json.load(f)
                logger.info(f"从 {factors_file} 加载因子库成功")
                
                # 提取所有类别
                self.factor_categories = set(factor['category'] for factor in self.factors.values() if 'category' in factor)
            else:
                logger.warning(f"因子库文件 {factors_file} 不存在，将初始化基础因子库")
                self._initialize_base_factors()
            
            # 加载因子相关性
            if os.path.exists(correlations_file):
                with open(correlations_file, 'r', encoding='utf-8') as f:
                    self.factor_correlations = json.load(f)
                logger.info(f"从 {correlations_file} 加载因子相关性成功")
        
        except Exception as e:
            logger.error(f"加载因子库失败: {e}")
            # 如果加载失败，初始化基础因子库
            self._initialize_base_factors()
    
    def _initialize_base_factors(self) -> None:
        """初始化基础因子库"""
        logger.info("初始化基础因子库")
        
        # 基础因子列表
        base_factors = [
            {
                'id': 'price_momentum_1m',
                'name': '1个月价格动量',
                'category': '动量因子',
                'description': '计算股票过去1个月的价格变化率，衡量短期价格趋势。',
                'formula': r'$PriceMomentum_{1M} = \frac{Price_t}{Price_{t-21}} - 1$',
                'code': '''
def price_momentum_1m(df):
    """计算1个月价格动量"""
    close_price = df['close']
    return close_price / close_price.shift(21) - 1
''',
                'interpretation': '价格动量因子捕捉了市场的趋势延续特性，背后的逻辑是价格的惯性效应。研究表明，短期内表现强势的股票在接下来的一段时间内可能继续保持强势，而弱势股票可能继续走弱。这种现象可能源于投资者的行为偏差，如处置效应和羊群效应。',
                'examples': [
                    {
                        'scenario': '股票在过去一个月上涨了10%',
                        'explanation': '该股票的1个月价格动量为0.1，表明有较强的上升趋势。',
                        'result': '按照动量投资策略，可能会考虑买入该股票。'
                    },
                    {
                        'scenario': '股票在过去一个月下跌了5%',
                        'explanation': '该股票的1个月价格动量为-0.05，表明有下跌趋势。',
                        'result': '按照动量投资策略，可能会考虑卖出或做空该股票。'
                    }
                ]
            },
            {
                'id': 'pe_ratio',
                'name': '市盈率',
                'category': '价值因子',
                'description': '股票价格与每股收益的比率，是最常用的估值指标之一。较低的PE可能意味着股票被低估。',
                'formula': r'$PE = \frac{Price}{EPS}$',
                'code': '''
def pe_ratio(df):
    """计算市盈率"""
    price = df['close']
    eps = df['eps']
    return price / eps
''',
                'interpretation': '市盈率(PE)是价值投资的核心指标之一，它反映了投资者愿意为每元收益支付的价格。低PE通常意味着股票相对便宜，可能被低估；高PE则可能意味着股票估值较高，投资者预期其未来有强劲增长。不同行业和不同增长阶段的公司有不同的合理PE范围。',
                'examples': [
                    {
                        'scenario': '成熟行业股票PE为8',
                        'explanation': '该股票的市盈率较低，可能被市场低估。',
                        'result': '价值投资者可能会考虑买入该股票。'
                    },
                    {
                        'scenario': '高增长科技股PE为50',
                        'explanation': '虽然PE较高，但如果公司有强劲的增长前景，这可能是合理的。',
                        'result': '需要结合公司增长率、行业平均PE等进一步评估。'
                    }
                ]
            },
            {
                'id': 'vol_20d',
                'name': '20日波动率',
                'category': '波动率因子',
                'description': '计算股票过去20个交易日收益率的标准差，衡量股票价格波动的剧烈程度。',
                'formula': r'$Volatility_{20d} = \sqrt{\frac{\sum_{i=1}^{20}(r_i - \bar{r})^2}{19}}$',
                'code': '''
def vol_20d(df):
    """计算20日波动率"""
    returns = df['close'].pct_change().dropna()
    return returns.rolling(20).std()
''',
                'interpretation': '波动率是衡量风险的重要指标，高波动率通常意味着高风险。波动率因子可以用来构建低波动率策略，这种策略发现低波动率股票在风险调整后往往有更好的表现，挑战了传统的"高风险高回报"理念。',
                'examples': [
                    {
                        'scenario': '股票的20日波动率为0.01（1%）',
                        'explanation': '该股票波动性较低，价格相对稳定。',
                        'result': '可能适合风险厌恶型投资者，或用于构建低波动策略。'
                    },
                    {
                        'scenario': '股票的20日波动率为0.03（3%）',
                        'explanation': '该股票波动性较高，价格波动较大。',
                        'result': '风险较高，可能需要更高的预期回报才能吸引投资者。'
                    }
                ]
            },
            {
                'id': 'rsi_14d',
                'name': '14日相对强弱指标',
                'category': '技术指标',
                'description': '衡量价格变动的速度和变化，判断市场是否超买或超卖。RSI值介于0到100之间，通常RSI>70视为超买，RSI<30视为超卖。',
                'formula': r'$RSI = 100 - \frac{100}{1 + \frac{\sum_{i=1}^{n}U_i}{\sum_{i=1}^{n}D_i}}$',
                'code': '''
def rsi_14d(df):
    """计算14日RSI"""
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))
''',
                'interpretation': 'RSI是一种动量振荡指标，用于识别超买或超卖状态。当RSI高于70时，表明资产可能被超买，价格可能回落；当RSI低于30时，表明资产可能被超卖，价格可能反弹。RSI也可以用来识别看涨或看跌的背离，当价格创新高而RSI未能创新高时，可能是看跌信号。',
                'examples': [
                    {
                        'scenario': '股票的RSI为75',
                        'explanation': '该股票可能处于超买状态，有回调风险。',
                        'result': '技术分析师可能会考虑减持或卖出该股票。'
                    },
                    {
                        'scenario': '股票的RSI为25',
                        'explanation': '该股票可能处于超卖状态，有反弹机会。',
                        'result': '技术分析师可能会考虑买入该股票。'
                    }
                ]
            },
            {
                'id': 'pb_ratio',
                'name': '市净率',
                'category': '价值因子',
                'description': '股票价格与每股净资产的比率，衡量公司股价相对于账面价值的溢价程度。',
                'formula': r'$PB = \frac{Price}{BookValuePerShare}$',
                'code': '''
def pb_ratio(df):
    """计算市净率"""
    price = df['close']
    bvps = df['bvps']
    return price / bvps
''',
                'interpretation': '市净率(PB)是评估公司估值的重要指标，特别适用于有大量有形资产的公司，如银行、房地产等。低PB可能意味着股票被低估，但也可能反映公司资产质量差或盈利能力弱。高PB公司通常具有强大的品牌、专利等无形资产或有高资产回报率。',
                'examples': [
                    {
                        'scenario': '银行股PB为0.8',
                        'explanation': '该银行股的市值低于其净资产，可能被低估。',
                        'result': '价值投资者可能会考虑买入，但需要评估资产质量和未来盈利能力。'
                    },
                    {
                        'scenario': '科技股PB为10',
                        'explanation': '该科技股的市值是其净资产的10倍，估值较高。',
                        'result': '需要结合公司的ROE、成长性等进一步评估是否合理。'
                    }
                ]
            }
        ]
        
        # 将基础因子添加到因子库
        for factor_data in base_factors:
            factor_id = factor_data['id']
            self.factors[factor_id] = factor_data
        
        # 添加简单的相关性数据
        self.factor_correlations = {
            'price_momentum_1m': [
                {'factor': 'vol_20d', 'correlation': 0.35, 'strength': 'moderate', 'direction': 'positive'},
                {'factor': 'rsi_14d', 'correlation': 0.75, 'strength': 'strong', 'direction': 'positive'}
            ],
            'pe_ratio': [
                {'factor': 'pb_ratio', 'correlation': 0.65, 'strength': 'strong', 'direction': 'positive'},
                {'factor': 'price_momentum_1m', 'correlation': -0.15, 'strength': 'weak', 'direction': 'negative'}
            ],
            'vol_20d': [
                {'factor': 'price_momentum_1m', 'correlation': 0.35, 'strength': 'moderate', 'direction': 'positive'},
                {'factor': 'rsi_14d', 'correlation': 0.25, 'strength': 'weak', 'direction': 'positive'}
            ],
            'rsi_14d': [
                {'factor': 'price_momentum_1m', 'correlation': 0.75, 'strength': 'strong', 'direction': 'positive'},
                {'factor': 'vol_20d', 'correlation': 0.25, 'strength': 'weak', 'direction': 'positive'}
            ],
            'pb_ratio': [
                {'factor': 'pe_ratio', 'correlation': 0.65, 'strength': 'strong', 'direction': 'positive'},
                {'factor': 'price_momentum_1m', 'correlation': -0.10, 'strength': 'weak', 'direction': 'negative'}
            ]
        }
        
        # 提取所有类别
        self.factor_categories = set(factor['category'] for factor in self.factors.values() if 'category' in factor)
        
        logger.info(f"基础因子库初始化完成，包含 {len(self.factors)} 个因子")
    
    def _init_llm(self) -> None:
        """初始化语言模型"""
        try:
            logger.info(f"正在加载语言模型: {self.llm_model}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.llm_model, trust_remote_code=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.llm_model, 
                trust_remote_code=True,
                device_map='auto' if self.device == 'cuda' else None
            )
            
            if self.device == 'cpu':
                self.model = self.model.float()
            
            logger.info(f"语言模型加载成功，设备: {self.device}")
        except Exception as e:
            logger.error(f"加载语言模型失败: {e}")
            self.use_llm = False
    
    def save_factors(self) -> None:
        """保存因子库到文件"""
        try:
            # 确保目录存在
            os.makedirs(self.data_path, exist_ok=True)
            
            # 保存因子库
            factors_file = os.path.join(self.data_path, 'factors_library.json')
            with open(factors_file, 'w', encoding='utf-8') as f:
                json.dump(self.factors, f, ensure_ascii=False, indent=2)
            
            # 保存因子相关性
            correlations_file = os.path.join(self.data_path, 'factor_correlations.json')
            with open(correlations_file, 'w', encoding='utf-8') as f:
                json.dump(self.factor_correlations, f, ensure_ascii=False, indent=2)
            
            logger.info(f"因子库和相关性保存成功: {factors_file}, {correlations_file}")
        
        except Exception as e:
            logger.error(f"保存因子库失败: {e}")
            
    def add_factor(self, factor_id: str, name: str, description: str, category: str,
                  formula: str = None, code: str = None, interpretation: str = None,
                  examples: List[Dict[str, str]] = None) -> bool:
        """
        添加新因子
        
        参数:
            factor_id: 因子ID
            name: 因子名称
            description: 因子描述
            category: 因子类别
            formula: 因子公式（支持LaTeX格式）
            code: 因子实现代码
            interpretation: 因子解释
            examples: 示例列表
        
        返回:
            添加是否成功
        """
        if factor_id in self.factors:
            logger.warning(f"因子 {factor_id} 已存在，将更新")
        
        # 准备因子数据
        factor_data = {
            'id': factor_id,
            'name': name,
            'category': category,
            'description': description
        }
        
        if formula:
            factor_data['formula'] = formula
        
        if code:
            factor_data['code'] = code
        
        if interpretation:
            factor_data['interpretation'] = interpretation
        
        if examples:
            factor_data['examples'] = examples
        
        # 添加到因子库
        self.factors[factor_id] = factor_data
        
        # 更新类别集合
        if category:
            self.factor_categories.add(category)
        
        logger.info(f"添加因子: {factor_id} - {name}")
        return True
    
    def get_factor(self, factor_id: str) -> Optional[Dict[str, Any]]:
        """
        获取因子详情
        
        参数:
            factor_id: 因子ID
        
        返回:
            因子详情字典
        """
        if factor_id not in self.factors:
            logger.warning(f"因子 {factor_id} 不存在")
            return None
        
        # 获取基本信息
        factor_data = self.factors[factor_id].copy()
        
        # 添加相关性信息
        if factor_id in self.factor_correlations:
            factor_data['correlations'] = self.factor_correlations[factor_id]
        else:
            factor_data['correlations'] = []
        
        return factor_data
    
    def search_factors(self, query: str, category: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索因子
        
        参数:
            query: 搜索关键词
            category: 可选的类别筛选
            limit: 结果数量限制
        
        返回:
            因子列表
        """
        query = query.lower()
        results = []
        
        for factor_id, factor_data in self.factors.items():
            # 检查名称或描述是否包含查询词
            name_match = query in factor_data['name'].lower()
            desc_match = 'description' in factor_data and query in factor_data['description'].lower()
            
            # 检查类别是否匹配
            category_match = category is None or factor_data.get('category') == category
            
            if (name_match or desc_match) and category_match:
                results.append(factor_data.copy())
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_factor_correlations(self, factor_id: str) -> List[Dict[str, Any]]:
        """
        获取因子相关性
        
        参数:
            factor_id: 因子ID
        
        返回:
            相关性列表
        """
        if factor_id not in self.factors:
            logger.warning(f"因子 {factor_id} 不存在")
            return []
        
        # 获取相关性数据
        if factor_id in self.factor_correlations:
            correlations = self.factor_correlations[factor_id]
            
            # 添加相关因子的详细信息
            for corr in correlations:
                related_id = corr['factor']
                if related_id in self.factors:
                    corr['factor_name'] = self.factors[related_id]['name']
                    corr['factor_category'] = self.factors[related_id].get('category', '未分类')
        else:
            correlations = []
        
        return correlations

    def generate_factor_logic(self, description: str, target_variable: str, 
                            constraints: Optional[str] = None) -> Dict[str, Any]:
        """
        使用LLM生成因子逻辑
        
        参数:
            description: 因子描述
            target_variable: 目标变量
            constraints: 约束条件
        
        返回:
            生成的因子逻辑字典
        """
        if not self.use_llm or not HAS_LLM:
            logger.warning("LLM未启用或不可用，无法生成因子逻辑")
            return {
                'success': False,
                'error': 'LLM未启用或不可用，无法生成因子逻辑',
                'factor': None
            }
        
        try:
            # 构建提示词
            prompt = f"""作为金融量化因子专家，请根据以下描述创建一个投资因子：

描述：{description}
目标变量：{target_variable}
"""
            
            if constraints:
                prompt += f"约束条件：{constraints}\n"
            
            prompt += """
请提供以下信息：
1. 因子名称
2. 因子类别（如动量因子、价值因子、技术指标等）
3. 因子详细描述
4. 数学公式（使用LaTeX格式）
5. Python实现代码
6. 因子逻辑解释（原理、经济学原理、行为金融学解释等）
7. 应用示例（至少两个）
8. 可能的优缺点

请以JSON格式输出，不要有额外的解释。
"""
            
            # 调用LLM生成
            logger.info("开始使用LLM生成因子逻辑")
            
            with torch.no_grad():
                inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
                response = self.model.generate(
                    inputs.input_ids,
                    max_length=2048,
                    temperature=0.7,
                    top_p=0.9,
                    repetition_penalty=1.1
                )
                output = self.tokenizer.decode(response[0], skip_special_tokens=True)
            
            # 提取JSON部分
            json_match = re.search(r'```json\s*(.*?)\s*```', output, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试找到整个JSON块
                json_start = output.find('{')
                json_end = output.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = output[json_start:json_end]
                else:
                    raise ValueError("无法从LLM输出中提取JSON数据")
            
            # 解析JSON
            factor_data = json.loads(json_str)
            
            # 格式化因子数据
            formatted_factor = {
                'id': factor_data.get('name', '').lower().replace(' ', '_'),
                'name': factor_data.get('name', '未命名因子'),
                'category': factor_data.get('category', '未分类'),
                'description': factor_data.get('description', ''),
                'formula': factor_data.get('formula', ''),
                'code': factor_data.get('code', ''),
                'interpretation': factor_data.get('explanation', factor_data.get('interpretation', '')),
                'examples': []
            }
            
            # 处理示例
            if 'examples' in factor_data and isinstance(factor_data['examples'], list):
                for example in factor_data['examples']:
                    if isinstance(example, dict):
                        formatted_example = {
                            'scenario': example.get('scenario', ''),
                            'explanation': example.get('explanation', ''),
                            'result': example.get('result', '')
                        }
                        formatted_factor['examples'].append(formatted_example)
            
            logger.info(f"成功生成因子逻辑: {formatted_factor['name']}")
            
            return {
                'success': True,
                'factor': formatted_factor,
                'raw_output': output
            }
        
        except Exception as e:
            logger.error(f"生成因子逻辑失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'factor': None
            }
    
    def update_factor_correlation(self, factor_id: str, related_factor_id: str, 
                                correlation: float, strength: str = None, 
                                direction: str = None) -> bool:
        """
        更新因子相关性
        
        参数:
            factor_id: 因子ID
            related_factor_id: 相关因子ID
            correlation: 相关系数，范围[-1, 1]
            strength: 相关强度描述，'strong', 'moderate', 'weak'
            direction: 相关方向，'positive', 'negative'
        
        返回:
            更新是否成功
        """
        if factor_id not in self.factors:
            logger.warning(f"因子 {factor_id} 不存在")
            return False
        
        if related_factor_id not in self.factors:
            logger.warning(f"相关因子 {related_factor_id} 不存在")
            return False
        
        # 确保相关性在[-1, 1]范围内
        correlation = max(-1.0, min(1.0, correlation))
        
        # 如果未提供强度，根据相关系数计算
        if strength is None:
            abs_corr = abs(correlation)
            if abs_corr >= 0.5:
                strength = 'strong'
            elif abs_corr >= 0.3:
                strength = 'moderate'
            else:
                strength = 'weak'
        
        # 如果未提供方向，根据相关系数确定
        if direction is None:
            direction = 'positive' if correlation >= 0 else 'negative'
        
        # 准备相关性数据
        correlation_data = {
            'factor': related_factor_id,
            'correlation': correlation,
            'strength': strength,
            'direction': direction
        }
        
        # 更新相关性
        if factor_id not in self.factor_correlations:
            self.factor_correlations[factor_id] = []
        
        # 检查是否已存在相关性
        for i, existing in enumerate(self.factor_correlations[factor_id]):
            if existing['factor'] == related_factor_id:
                # 更新现有相关性
                self.factor_correlations[factor_id][i] = correlation_data
                logger.info(f"更新因子相关性: {factor_id} - {related_factor_id}")
                return True
        
        # 添加新相关性
        self.factor_correlations[factor_id].append(correlation_data)
        logger.info(f"添加因子相关性: {factor_id} - {related_factor_id}")
        
        return True
    
    def visualize_factor_performance(self, factor_id: str, return_data: pd.DataFrame) -> Dict[str, Any]:
        """
        可视化因子表现
        
        参数:
            factor_id: 因子ID
            return_data: 包含因子值和收益率的DataFrame
            
        返回:
            可视化结果字典
        """
        if factor_id not in self.factors:
            logger.warning(f"因子 {factor_id} 不存在")
            return {'success': False, 'error': f"因子 {factor_id} 不存在"}
        
        try:
            # 确保DataFrame包含必要的列
            required_cols = ['factor_value', 'returns']
            if not all(col in return_data.columns for col in required_cols):
                return {
                    'success': False, 
                    'error': f"DataFrame必须包含列: {required_cols}"
                }
            
            # 1. 因子分组收益分析
            group_analysis = self._analyze_factor_groups(return_data)
            
            # 2. 因子IC分析
            ic_analysis = self._analyze_factor_ic(return_data)
            
            # 3. 因子回归分析
            regression_analysis = self._analyze_factor_regression(return_data)
            
            # 整合分析结果
            results = {
                'factor_id': factor_id,
                'factor_name': self.factors[factor_id]['name'],
                'group_analysis': group_analysis,
                'ic_analysis': ic_analysis,
                'regression_analysis': regression_analysis,
                'success': True
            }
            
            return results
        
        except Exception as e:
            logger.error(f"可视化因子表现失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _analyze_factor_groups(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析因子分组收益"""
        # 按因子值分组
        data['group'] = pd.qcut(data['factor_value'], 5, labels=False)
        
        # 计算每组平均收益
        group_returns = data.groupby('group')['returns'].mean().reset_index()
        
        # 计算多空组合收益
        long_short_return = group_returns.iloc[-1]['returns'] - group_returns.iloc[0]['returns']
        
        return {
            'group_returns': group_returns.to_dict(orient='records'),
            'long_short_return': float(long_short_return)
        }
    
    def _analyze_factor_ic(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析因子IC"""
        # 计算相关系数
        ic = data['factor_value'].corr(data['returns'])
        
        # 计算T统计量
        n = len(data)
        t_stat = ic * np.sqrt(n - 2) / np.sqrt(1 - ic ** 2)
        
        # 计算p值
        from scipy import stats
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))
        
        return {
            'ic': float(ic),
            't_statistic': float(t_stat),
            'p_value': float(p_value),
            'significant': p_value < 0.05
        }
    
    def _analyze_factor_regression(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析因子回归"""
        # 准备数据
        X = data['factor_value'].values.reshape(-1, 1)
        y = data['returns'].values
        
        # 训练线性回归
        model = LinearRegression()
        model.fit(X, y)
        
        # 预测和评估
        y_pred = model.predict(X)
        r2 = r2_score(y, y_pred)
        
        return {
            'coefficient': float(model.coef_[0]),
            'intercept': float(model.intercept_),
            'r_squared': float(r2)
        }
    
    def get_categories(self) -> List[str]:
        """
        获取所有因子类别
        
        返回:
            类别列表
        """
        return sorted(list(self.factor_categories))
    
    def get_factors_by_category(self, category: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取特定类别的因子
        
        参数:
            category: 因子类别
            limit: 结果数量限制
        
        返回:
            因子列表
        """
        if category not in self.factor_categories:
            logger.warning(f"类别 {category} 不存在")
            return []
        
        results = [factor for factor in self.factors.values() if factor.get('category') == category]
        
        # 按名称排序
        results.sort(key=lambda x: x['name'])
        
        return results[:limit]
