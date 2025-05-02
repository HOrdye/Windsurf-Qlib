#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Alpha信号提取模块，负责从解析后的文档中提取结构化的Alpha信号
"""
import logging
import re
import json
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd
import numpy as np
from datetime import datetime

# 设置日志
logger = logging.getLogger(__name__)

class AlphaSignal:
    """Alpha信号类，表示从文档中提取的投资信号"""
    
    def __init__(self, 
                 name: str, 
                 description: str, 
                 source: str,
                 signal_type: str = "fundamental",
                 factor_category: str = None,
                 direction: str = None,
                 confidence: float = None,
                 time_horizon: str = None,
                 stock_codes: List[str] = None,
                 industry: str = None,
                 metrics: Dict[str, Any] = None,
                 extraction_date: str = None):
        """
        初始化Alpha信号
        
        参数:
            name: 信号名称
            description: 信号描述
            source: 信号来源(文档路径或URL)
            signal_type: 信号类型，如"fundamental", "technical", "sentiment"等
            factor_category: 因子分类，如"valuation", "growth", "momentum"等
            direction: 信号方向，"positive", "negative", "neutral"
            confidence: 信号置信度，0.0-1.0
            time_horizon: 时间范围，如"short_term", "medium_term", "long_term"
            stock_codes: 相关股票代码列表
            industry: 相关行业
            metrics: 相关指标，如{PE: 10.5, PB: 1.2}
            extraction_date: 提取日期，默认为当前日期
        """
        self.name = name
        self.description = description
        self.source = source
        self.signal_type = signal_type
        self.factor_category = factor_category
        self.direction = direction
        self.confidence = confidence
        self.time_horizon = time_horizon
        self.stock_codes = stock_codes or []
        self.industry = industry
        self.metrics = metrics or {}
        self.extraction_date = extraction_date or datetime.now().strftime("%Y-%m-%d")
        
        # 验证信号必要字段
        self._validate()
    
    def _validate(self) -> None:
        """验证Alpha信号的必要字段"""
        if not self.name or not self.description or not self.source:
            raise ValueError("信号必须包含名称、描述和来源")
        
        # 验证置信度范围
        if self.confidence is not None and (self.confidence < 0 or self.confidence > 1):
            raise ValueError("置信度必须在0到1之间")
        
        # 验证信号方向
        if self.direction and self.direction not in ["positive", "negative", "neutral"]:
            raise ValueError("信号方向必须是positive、negative或neutral")
        
        # 验证时间范围
        if self.time_horizon and self.time_horizon not in ["short_term", "medium_term", "long_term"]:
            raise ValueError("时间范围必须是short_term、medium_term或long_term")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将信号转换为字典格式
        
        返回:
            信号字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "signal_type": self.signal_type,
            "factor_category": self.factor_category,
            "direction": self.direction,
            "confidence": self.confidence,
            "time_horizon": self.time_horizon,
            "stock_codes": self.stock_codes,
            "industry": self.industry,
            "metrics": self.metrics,
            "extraction_date": self.extraction_date
        }
    
    def to_json(self) -> str:
        """
        将信号转换为JSON格式
        
        返回:
            JSON字符串
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlphaSignal':
        """
        从字典创建Alpha信号
        
        参数:
            data: 信号字典
            
        返回:
            Alpha信号实例
        """
        return cls(
            name=data.get("name"),
            description=data.get("description"),
            source=data.get("source"),
            signal_type=data.get("signal_type", "fundamental"),
            factor_category=data.get("factor_category"),
            direction=data.get("direction"),
            confidence=data.get("confidence"),
            time_horizon=data.get("time_horizon"),
            stock_codes=data.get("stock_codes"),
            industry=data.get("industry"),
            metrics=data.get("metrics"),
            extraction_date=data.get("extraction_date")
        )


class BaseAlphaExtractor:
    """Alpha信号提取器基类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化Alpha提取器
        
        参数:
            config: 配置参数
        """
        self.config = config or {}
        self.signals = []
    
    def extract(self, content: Dict[str, Any]) -> List[AlphaSignal]:
        """
        从文档内容中提取Alpha信号
        
        参数:
            content: 文档解析结果
            
        返回:
            提取的Alpha信号列表
        """
        raise NotImplementedError("子类必须实现extract方法")
    
    def validate_signals(self, signals: List[AlphaSignal]) -> List[AlphaSignal]:
        """
        验证提取的信号
        
        参数:
            signals: 提取的信号列表
            
        返回:
            验证后的信号列表
        """
        valid_signals = []
        for signal in signals:
            try:
                signal._validate()
                valid_signals.append(signal)
            except ValueError as e:
                logger.warning(f"信号验证失败: {e}")
        
        return valid_signals
    
    def save_signals(self, signals: List[AlphaSignal], output_path: str) -> str:
        """
        保存提取的信号
        
        参数:
            signals: 信号列表
            output_path: 输出路径
            
        返回:
            保存的文件路径
        """
        try:
            signals_data = [signal.to_dict() for signal in signals]
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(signals_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存 {len(signals)} 个信号到 {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"保存信号失败: {e}")
            return ""


class RuleBasedExtractor(BaseAlphaExtractor):
    """基于规则的Alpha信号提取器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化规则提取器
        
        参数:
            config: 配置参数，可包含:
                - keywords: 关键词字典，用于匹配不同类型的信号
                - stock_code_pattern: 股票代码正则表达式
                - metrics_patterns: 指标正则表达式字典
                - minimum_confidence: 最低置信度
        """
        super().__init__(config)
        
        # 加载关键词字典
        self.keywords = self.config.get('keywords', {
            'positive': ['增长', '上升', '超预期', '强劲', '利好', '提高', '提升', '领先'],
            'negative': ['下降', '减少', '低于预期', '疲软', '利空', '下滑', '减弱', '落后'],
            'technical': ['突破', '支撑', '压力', '趋势', '均线', '成交量', '振荡器', '背离'],
            'fundamental': ['盈利', '利润', '收入', '营收', '毛利率', '市盈率', '市净率', '股息率'],
            'sentiment': ['情绪', '信心', '乐观', '悲观', '预期', '担忧', '热情', '谨慎'],
            'short_term': ['短期', '日内', '周内', '近期'],
            'medium_term': ['中期', '月度', '季度'],
            'long_term': ['长期', '年度', '战略']
        })
        
        # 股票代码匹配模式
        self.stock_code_pattern = self.config.get(
            'stock_code_pattern', 
            r'([0-9]{6}\.(?:SH|SZ|BJ)|[0-9]{4}\.[HK])'
        )
        
        # 指标匹配模式
        self.metrics_patterns = self.config.get('metrics_patterns', {
            'PE': r'PE(?:[\s值]*)(?:约|为)?(?:[\s:]*)([0-9]+\.?[0-9]*)',
            'PB': r'PB(?:[\s值]*)(?:约|为)?(?:[\s:]*)([0-9]+\.?[0-9]*)',
            'ROE': r'ROE(?:[\s值]*)(?:约|为)?(?:[\s:]*)([0-9]+\.?[0-9]*)%?',
            'EPS': r'EPS(?:[\s值]*)(?:约|为)?(?:[\s:]*)([0-9]+\.?[0-9]*)',
            'Revenue': r'营收|收入(?:[\s]*)(?:约|为)?(?:[\s:]*)([0-9]+\.?[0-9]*)(?:亿|万|千万|百万)?',
            'Profit': r'利润|盈利(?:[\s]*)(?:约|为)?(?:[\s:]*)([0-9]+\.?[0-9]*)(?:亿|万|千万|百万)?',
            'Growth': r'增长(?:率)?(?:[\s]*)(?:约|为)?(?:[\s:]*)([0-9]+\.?[0-9]*)%'
        })
        
        # 最低置信度
        self.minimum_confidence = self.config.get('minimum_confidence', 0.6)
        
        # 行业分类字典
        self.industry_keywords = self.config.get('industry_keywords', {
            '科技': ['互联网', '软件', '硬件', '半导体', '人工智能', '云计算', '大数据'],
            '金融': ['银行', '保险', '证券', '信托', '金融服务', '资产管理'],
            '医药': ['制药', '生物技术', '医疗器械', '医疗服务', '医院', '药店'],
            '消费': ['零售', '食品饮料', '服装', '家电', '日用品', '电商'],
            '制造': ['机械', '汽车', '化工', '冶金', '建材', '军工'],
            '能源': ['石油', '天然气', '煤炭', '电力', '新能源', '风能', '太阳能'],
            '房地产': ['地产', '物业', '建筑', '装修', '家居'],
            '通信': ['通信', '电信', '移动', '5G', '物联网', '传媒']
        })
    
    def extract(self, content: Dict[str, Any]) -> List[AlphaSignal]:
        """
        从文档内容中提取Alpha信号
        
        参数:
            content: 文档解析结果，包含content, metadata, tables等
            
        返回:
            提取的Alpha信号列表
        """
        try:
            if not content or not content.get('success', False):
                logger.error("提取失败: 无效的文档内容")
                return []
            
            # 获取文本内容和元数据
            document_text = content.get('content', '')
            metadata = content.get('metadata', {})
            source = metadata.get('source', '')
            tables = content.get('tables', [])
            
            if not document_text:
                logger.warning("文档内容为空")
                return []
            
            # 从文本中提取信号
            text_signals = self._extract_from_text(document_text, source)
            
            # 从表格中提取信号
            table_signals = self._extract_from_tables(tables, source)
            
            # 合并信号
            all_signals = text_signals + table_signals
            
            # 对信号进行去重
            unique_signals = self._deduplicate_signals(all_signals)
            
            # 验证信号
            valid_signals = self.validate_signals(unique_signals)
            
            logger.info(f"从文档中提取出 {len(valid_signals)} 个有效Alpha信号")
            self.signals = valid_signals
            
            return valid_signals
        
        except Exception as e:
            logger.error(f"Alpha信号提取失败: {e}")
            return []
    
    def _extract_from_text(self, text: str, source: str) -> List[AlphaSignal]:
        """
        从文本中提取Alpha信号
        
        参数:
            text: 文本内容
            source: 信号来源
            
        返回:
            提取的信号列表
        """
        signals = []
        
        # 将文本分成段落
        paragraphs = text.split('\n')
        
        for para in paragraphs:
            if len(para.strip()) < 20:  # 忽略过短的段落
                continue
            
            # 判断段落中是否包含投资信号
            has_signal = self._contains_signal_keywords(para)
            
            if has_signal:
                # 提取信号方向
                direction = self._determine_direction(para)
                
                # 提取信号类型
                signal_type = self._determine_signal_type(para)
                
                # 提取时间范围
                time_horizon = self._determine_time_horizon(para)
                
                # 提取股票代码
                stock_codes = self._extract_stock_codes(para)
                
                # 提取行业
                industry = self._determine_industry(para)
                
                # 提取指标
                metrics = self._extract_metrics(para)
                
                # 计算置信度
                confidence = self._calculate_confidence(para, direction, signal_type, stock_codes, metrics)
                
                # 只保留置信度较高的信号
                if confidence >= self.minimum_confidence:
                    signal = AlphaSignal(
                        name=f"Signal-{len(signals)+1}",
                        description=para,
                        source=source,
                        signal_type=signal_type,
                        direction=direction,
                        confidence=confidence,
                        time_horizon=time_horizon,
                        stock_codes=stock_codes,
                        industry=industry,
                        metrics=metrics
                    )
                    signals.append(signal)
        
        return signals
    
    def _extract_from_tables(self, tables: List[Dict[str, Any]], source: str) -> List[AlphaSignal]:
        """
        从表格中提取Alpha信号
        
        参数:
            tables: 表格数据
            source: 信号来源
            
        返回:
            提取的信号列表
        """
        signals = []
        
        for table in tables:
            # 分析表格数据
            table_data = table.get('data', [])
            headers = table.get('headers', [])
            
            if not table_data or len(table_data) <= 1:
                continue
            
            # 判断表格是否包含投资因子信息
            is_factor_table = self._is_factor_table(headers)
            
            if is_factor_table:
                # 将表格转换为DataFrame便于处理
                df = pd.DataFrame(table_data[1:], columns=headers)
                
                # 处理每一行数据
                for _, row in df.iterrows():
                    signal = self._extract_signal_from_row(row, headers, source)
                    if signal:
                        signals.append(signal)
        
        return signals
    
    def _contains_signal_keywords(self, text: str) -> bool:
        """判断文本是否包含信号关键词"""
        all_keywords = []
        for category, keywords in self.keywords.items():
            all_keywords.extend(keywords)
        
        for keyword in all_keywords:
            if keyword in text:
                return True
        
        return False
    
    def _determine_direction(self, text: str) -> str:
        """确定信号方向"""
        positive_count = sum(1 for kw in self.keywords.get('positive', []) if kw in text)
        negative_count = sum(1 for kw in self.keywords.get('negative', []) if kw in text)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _determine_signal_type(self, text: str) -> str:
        """确定信号类型"""
        type_scores = {}
        
        for signal_type in ['technical', 'fundamental', 'sentiment']:
            keywords = self.keywords.get(signal_type, [])
            score = sum(1 for kw in keywords if kw in text)
            type_scores[signal_type] = score
        
        # 选择得分最高的类型
        max_type = max(type_scores.items(), key=lambda x: x[1])
        
        # 如果都没有匹配，默认为fundamental
        return max_type[0] if max_type[1] > 0 else "fundamental"
    
    def _determine_time_horizon(self, text: str) -> str:
        """确定时间范围"""
        horizon_scores = {}
        
        for horizon in ['short_term', 'medium_term', 'long_term']:
            keywords = self.keywords.get(horizon, [])
            score = sum(1 for kw in keywords if kw in text)
            horizon_scores[horizon] = score
        
        # 选择得分最高的时间范围
        max_horizon = max(horizon_scores.items(), key=lambda x: x[1])
        
        # 如果都没有匹配，默认为medium_term
        return max_horizon[0] if max_horizon[1] > 0 else "medium_term"
    
    def _extract_stock_codes(self, text: str) -> List[str]:
        """提取股票代码"""
        pattern = re.compile(self.stock_code_pattern)
        matches = pattern.findall(text)
        
        # 去重
        return list(set(matches))
    
    def _determine_industry(self, text: str) -> str:
        """确定行业"""
        industry_scores = {}
        
        for industry, keywords in self.industry_keywords.items():
            score = sum(1 for kw in keywords if kw in text)
            industry_scores[industry] = score
        
        # 选择得分最高的行业
        max_industry = max(industry_scores.items(), key=lambda x: x[1])
        
        # 如果都没有匹配，返回None
        return max_industry[0] if max_industry[1] > 0 else None
    
    def _extract_metrics(self, text: str) -> Dict[str, float]:
        """提取指标"""
        metrics = {}
        
        for metric_name, pattern in self.metrics_patterns.items():
            matches = re.search(pattern, text)
            if matches:
                try:
                    value = float(matches.group(1))
                    metrics[metric_name] = value
                except:
                    pass
        
        return metrics
    
    def _calculate_confidence(self, text: str, direction: str, signal_type: str, 
                             stock_codes: List[str], metrics: Dict[str, float]) -> float:
        """
        计算信号置信度
        
        根据信号的完整性和匹配程度计算置信度
        """
        confidence = 0.5  # 基础置信度
        
        # 方向明确加分
        if direction != "neutral":
            confidence += 0.1
        
        # 有具体股票代码加分
        if stock_codes:
            confidence += 0.1 * min(len(stock_codes), 3) / 3
        
        # 有具体指标加分
        if metrics:
            confidence += 0.1 * min(len(metrics), 3) / 3
        
        # 文本长度考虑
        if len(text) > 100:
            confidence += 0.1
        
        # 关键词密度考虑
        keywords_count = 0
        for category, keywords in self.keywords.items():
            keywords_count += sum(1 for kw in keywords if kw in text)
        
        keyword_density = keywords_count / max(len(text.split()), 1)
        if keyword_density > 0.1:
            confidence += 0.1
        
        # 确保置信度在0-1之间
        return min(max(confidence, 0), 1)
    
    def _is_factor_table(self, headers: List[str]) -> bool:
        """判断表格是否包含投资因子信息"""
        factor_related_headers = [
            "因子", "指标", "股票", "代码", "行业", "PE", "PB", "ROE", "EPS", 
            "增长率", "收益率", "回报率", "评级", "建议", "目标价", "信号"
        ]
        
        matched_count = sum(1 for header in headers if any(kw in header for kw in factor_related_headers))
        
        # 如果匹配的列数超过总列数的1/3，则认为是因子表格
        return matched_count >= len(headers) / 3
    
    def _extract_signal_from_row(self, row: pd.Series, headers: List[str], source: str) -> Optional[AlphaSignal]:
        """从表格行中提取信号"""
        try:
            # 寻找股票相关列
            stock_name = None
            stock_code = None
            
            for header in headers:
                if "名称" in header or "股票" in header:
                    stock_name = row[header]
                elif "代码" in header:
                    stock_code = row[header]
            
            # 提取指标
            metrics = {}
            for header in headers:
                for metric_name in self.metrics_patterns.keys():
                    if metric_name in header or any(kw in header for kw in self.metrics_patterns.keys()):
                        try:
                            value = float(row[header])
                            metrics[header] = value
                        except:
                            pass
            
            # 确定信号方向
            direction = "neutral"
            for header in headers:
                if "评级" in header or "建议" in header or "信号" in header:
                    value = str(row[header]).strip().lower()
                    if any(kw in value for kw in ["买入", "增持", "强烈推荐", "buy", "overweight"]):
                        direction = "positive"
                    elif any(kw in value for kw in ["卖出", "减持", "sell", "underweight"]):
                        direction = "negative"
            
            # 提取行业
            industry = None
            for header in headers:
                if "行业" in header or "板块" in header:
                    industry = row[header]
            
            # 构建描述
            description = f"表格提取信号: "
            if stock_name:
                description += f"股票名称: {stock_name}, "
            if stock_code:
                description += f"股票代码: {stock_code}, "
            if industry:
                description += f"行业: {industry}, "
            
            description += f"指标: {metrics}, 方向: {direction}"
            
            # 构建信号
            stock_codes = [stock_code] if stock_code else []
            
            signal = AlphaSignal(
                name=f"Table-Signal-{stock_name or '未知'}" if stock_name else f"Table-Signal-{len(self.signals)+1}",
                description=description,
                source=source,
                signal_type="fundamental",
                direction=direction,
                confidence=0.7,  # 表格数据通常更结构化，置信度较高
                stock_codes=stock_codes,
                industry=industry,
                metrics=metrics
            )
            
            return signal
        except Exception as e:
            logger.warning(f"从表格行提取信号失败: {e}")
            return None
    
    def _deduplicate_signals(self, signals: List[AlphaSignal]) -> List[AlphaSignal]:
        """去除重复信号"""
        # 简单方法：基于描述的相似度去重
        unique_signals = []
        descriptions = set()
        
        for signal in signals:
            # 使用描述的前100个字符作为判断依据
            desc_key = signal.description[:100]
            if desc_key not in descriptions:
                descriptions.add(desc_key)
                unique_signals.append(signal)
        
        return unique_signals

class LLMBasedExtractor(BaseAlphaExtractor):
    """基于语言模型的Alpha信号提取器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化LLM提取器
        
        参数:
            config: 配置参数，可包含:
                - model_name: 语言模型名称
                - llm_provider: 模型提供商
                - api_key: API密钥
                - prompt_template: 提示词模板
                - max_tokens: 最大tokens数
                - temperature: 生成温度
                - minimum_confidence: 最低置信度
                - batch_size: 每批处理的段落数量
        """
        super().__init__(config)
        self.config = config or {}
        
        # 初始化LLM参数 - 默认使用DeepSeek
        self.model_name = self.config.get('model_name', 'deepseek-chat')
        self.llm_provider = self.config.get('llm_provider', 'deepseek')
        self.api_key = self.config.get('api_key', os.environ.get('DEEPSEEK_API_KEY', ''))
        
        # 提示词模板
        self.prompt_template = self.config.get('prompt_template', """
        请分析以下文本，提取所有可能的投资Alpha信号。
        
        文本内容：
        {content}
        
        请以JSON数组格式返回提取的信号，每个信号包含以下字段：
        - name: 信号名称
        - description: 信号描述
        - signal_type: 信号类型 (fundamental, technical, sentiment, event)
        - factor_category: 因子类别 (valuation, growth, momentum, quality, etc.)
        - direction: 信号方向 (positive, negative, neutral)
        - confidence: 置信度 (0.0-1.0)
        - time_horizon: 时间范围 (short_term, medium_term, long_term)
        - stock_codes: 相关股票代码数组 (如有)
        - industry: 相关行业 (如有)
        - metrics: 相关指标 (如有)
            "industry": "行业名称",
            "metrics": {{"PE": 15.2, "ROE": 0.12}},
            "confidence": 0.85
        }}]
        
        如果没有检测到任何投资信号，请返回空JSON数组 []。
        请确保JSON格式正确无误，不要添加任何额外的说明文字。
        """)
        
        # 初始化客户端
        self._init_llm_client()
    
    def _init_llm_client(self) -> None:
        """初始化语言模型客户端"""
        try:
            if self.llm_provider == 'openai':
                import openai
                openai.api_key = self.api_key
                self.client = openai
                logger.info(f"成功初始化OpenAI客户端，使用模型: {self.model_name}")
            elif self.llm_provider == 'deepseek':
                try:
                    # 尝试导入deepseek_ai包
                    import deepseek_ai
                    deepseek_ai.api_key = self.api_key
                    self.client = deepseek_ai
                    logger.info(f"成功初始化DeepSeek客户端，使用模型: {self.model_name}")
                except ImportError:
                    try:
                        # 尝试导入deepseek包（旧版本）
                        import deepseek
                        deepseek.api_key = self.api_key
                        self.client = deepseek
                        logger.info(f"成功初始化DeepSeek客户端（旧版本），使用模型: {self.model_name}")
                    except ImportError:
                        # 如果没有deepseek库，尝试使用requests直接调用API
                        import requests
                        self.client = {
                            'api_url': 'https://api.deepseek.com/v1/chat/completions',
                            'api_key': self.api_key,
                            'session': requests.Session()
                        }
                        logger.info(f"使用requests初始化DeepSeek客户端，使用模型: {self.model_name}")
            elif self.llm_provider == 'local':
                # 使用本地模型客户端
                logger.info("使用本地模型客户端")
                pass
            else:
                logger.warning(f"不支持的LLM提供商: {self.llm_provider}，使用规则提取器作为后备")
                self.fallback_extractor = RuleBasedExtractor(self.config)
        except ImportError as e:
            logger.warning(f"导入LLM客户端库失败: {e}，使用规则提取器作为后备")
            self.fallback_extractor = RuleBasedExtractor(self.config)
    
    def extract(self, content: Dict[str, Any]) -> List[AlphaSignal]:
        """
        从文档内容中提取Alpha信号
        
        参数:
            content: 文档解析结果，包含content, metadata, tables等
            
        返回:
            提取的Alpha信号列表
        """
        try:
            if not content or not content.get('success', False):
                logger.error("提取失败: 无效的文档内容")
                return []
            
            # 获取文本内容和元数据
            document_text = content.get('content', '')
            metadata = content.get('metadata', {})
            source = metadata.get('source', '')
            tables = content.get('tables', [])
            
            if not document_text:
                logger.warning("文档内容为空")
                return []
            
            # 将文本分成段落
            paragraphs = self._split_into_paragraphs(document_text)
            
            # 按批次处理段落
            all_signals = []
            batch_size = self.batch_size
            
            for i in range(0, len(paragraphs), batch_size):
                batch = paragraphs[i:i+batch_size]
                batch_text = "\n\n".join(batch)
                
                # 使用LLM提取信号
                try:
                    batch_signals = self._extract_with_llm(batch_text, source)
                    all_signals.extend(batch_signals)
                except Exception as e:
                    logger.error(f"使用LLM提取信号失败: {e}")
                    # 如果LLM提取失败，尝试使用规则提取器作为后备
                    if hasattr(self, 'fallback_extractor'):
                        batch_content = {
                            'content': batch_text,
                            'metadata': metadata,
                            'tables': [],
                            'success': True
                        }
                        batch_signals = self.fallback_extractor.extract(batch_content)
                        all_signals.extend(batch_signals)
            
            # 从表格中提取信号
            if tables and hasattr(self, 'fallback_extractor'):
                table_content = {
                    'content': "",
                    'metadata': metadata,
                    'tables': tables,
                    'success': True
                }
                table_signals = self.fallback_extractor._extract_from_tables(tables, source)
                all_signals.extend(table_signals)
            
            # 对信号进行去重
            unique_signals = self._deduplicate_signals(all_signals)
            
            # 验证信号
            valid_signals = self.validate_signals(unique_signals)
            
            logger.info(f"从文档中提取出 {len(valid_signals)} 个有效Alpha信号")
            self.signals = valid_signals
            
            return valid_signals
            
        except Exception as e:
            logger.error(f"LLM Alpha信号提取失败: {e}")
            
            # 如果有后备提取器，使用规则提取器
            if hasattr(self, 'fallback_extractor'):
                logger.info("使用规则提取器作为后备方案")
                return self.fallback_extractor.extract(content)
            
            return []
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """将文本分成有意义的段落"""
        # 首先按换行符分割
        raw_paragraphs = text.split('\n')
        
        # 合并过短的段落
        paragraphs = []
        current_para = ""
        
        for para in raw_paragraphs:
            if len(para.strip()) < 20:  # 如果段落太短
                if current_para:
                    current_para += " " + para.strip()
                else:
                    current_para = para.strip()
            else:
                if current_para:
                    paragraphs.append(current_para)
                current_para = para.strip()
        
        # 添加最后一个段落
        if current_para:
            paragraphs.append(current_para)
        
        # 过滤掉太短的段落
        paragraphs = [p for p in paragraphs if len(p) >= 20]
        
        return paragraphs
    
    def _extract_with_llm(self, text: str, source: str) -> List[AlphaSignal]:
        """
        使用语言模型提取Alpha信号
        
        参数:
            text: 文本内容
            source: 信号来源
            
        返回:
            提取的Alpha信号列表
        """
        signals = []
        
        # 准备提示词
        prompt = self.prompt_template.format(content=text)
        
        try:
            # 调用不同的LLM提供商
            if self.llm_provider == 'openai':
                response = self.client.ChatCompletion.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "你是一名专业的金融分析师，擅长提取文本中的投资Alpha信号。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                
                # 提取结果
                result_text = response.choices[0].message.content.strip()
                logger.info("成功调用OpenAI API获取响应")
            elif self.llm_provider == 'deepseek':
                # 检查客户端类型
                if isinstance(self.client, dict):  # 使用requests直接调用API
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.client['api_key']}"
                    }
                    payload = {
                        "model": self.model_name,
                        "messages": [
                            {"role": "system", "content": "你是一名专业的金融分析师，擅长提取文本中的投资Alpha信号。"},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature
                    }
                    response = self.client['session'].post(
                        self.client['api_url'],
                        headers=headers,
                        json=payload
                    )
                    response_json = response.json()
                    result_text = response_json['choices'][0]['message']['content'].strip()
                else:  # 使用deepseek库
                    response = self.client.ChatCompletion.create(
                        model=self.model_name,
                        messages=[
                            {"role": "system", "content": "你是一名专业的金融分析师，擅长提取文本中的投资Alpha信号。"},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=self.max_tokens,
                        temperature=self.temperature
                    )
                    result_text = response.choices[0].message.content.strip()
                logger.info("成功调用DeepSeek API获取响应")
            elif self.llm_provider == 'local':
                # 本地模型调用逻辑
                pass
            else:
                return []
            
            # 解析JSON结果
            try:
                # 提取JSON部分
                json_start = result_text.find('[')
                json_end = result_text.rfind(']') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = result_text[json_start:json_end]
                    result_data = json.loads(json_str)
                else:
                    # 尝试直接解析
                    result_data = json.loads(result_text)
                
                # 确保结果是列表
                if not isinstance(result_data, list):
                    if isinstance(result_data, dict):
                        result_data = [result_data]
                    else:
                        result_data = []
                
                # 创建AlphaSignal对象
                for item in result_data:
                    # 确保置信度符合要求
                    if 'confidence' in item and item['confidence'] >= self.minimum_confidence:
                        signal = AlphaSignal(
                            name=item.get('name', f"LLM-Signal-{len(signals)+1}"),
                            description=item.get('description', text[:100]),
                            source=source,
                            signal_type=item.get('signal_type', 'fundamental'),
                            factor_category=item.get('factor_category'),
                            direction=item.get('direction', 'neutral'),
                            confidence=item.get('confidence', 0.7),
                            time_horizon=item.get('time_horizon', 'medium_term'),
                            stock_codes=item.get('stock_codes', []),
                            industry=item.get('industry'),
                            metrics=item.get('metrics', {})
                        )
                        signals.append(signal)
                        
                logger.info(f"成功从LLM响应中提取了 {len(signals)} 个信号")
            
            except json.JSONDecodeError as e:
                logger.error(f"解析LLM响应JSON失败: {e}")
                logger.debug(f"LLM原始响应: {result_text}")
        
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return signals
    
    def _deduplicate_signals(self, signals: List[AlphaSignal]) -> List[AlphaSignal]:
        """去除重复信号"""
        # 按置信度排序
        sorted_signals = sorted(signals, key=lambda x: x.confidence if x.confidence else 0, reverse=True)
        
        # 使用描述和股票代码作为去重依据
        unique_signals = []
        descriptions = set()
        code_dir_pairs = set()  # (股票代码, 方向)对
        
        for signal in sorted_signals:
            # 使用描述的指纹
            desc_key = signal.description[:100]
            
            # 使用(股票代码, 方向)对
            for code in signal.stock_codes:
                code_dir = (code, signal.direction)
                if code_dir in code_dir_pairs:
                    # 已存在相同的股票代码和方向，跳过
                    continue
                
            # 如果没有重复，添加到结果中
            if desc_key not in descriptions:
                descriptions.add(desc_key)
                for code in signal.stock_codes:
                    code_dir_pairs.add((code, signal.direction))
                unique_signals.append(signal)
        
        return unique_signals


class AlphaExtractorFactory:
    """Alpha信号提取器工厂类"""
    
    @staticmethod
    def create_extractor(extractor_type: str, config: Dict[str, Any] = None) -> BaseAlphaExtractor:
        """
        创建Alpha信号提取器实例
        
        参数:
            extractor_type: 提取器类型，可选值: 'rule', 'llm', 'ensemble'
            config: 提取器配置
            
        返回:
            Alpha信号提取器实例
        """
        return AlphaExtractorFactory.get_extractor(extractor_type, config)
    
    @staticmethod
    def get_extractor(extractor_type: str, config: Dict[str, Any] = None) -> BaseAlphaExtractor:
        """
        获取Alpha信号提取器
        
        参数:
            extractor_type: 提取器类型，可选值: 'rule', 'llm', 'ensemble'
            config: 提取器配置
            
        返回:
            Alpha信号提取器实例
        """
        config = config or {}
        
        if extractor_type == 'rule':
            return RuleBasedExtractor(config)
        elif extractor_type == 'llm':
            return LLMBasedExtractor(config)
        elif extractor_type == 'deepseek':
            # 使用DeepSeek作为LLM提供商
            deepseek_config = config.copy()
            deepseek_config['llm_provider'] = 'deepseek'
            deepseek_config['model_name'] = config.get('model_name', 'deepseek-chat')
            return LLMBasedExtractor(deepseek_config)
        elif extractor_type == 'ensemble':
            # 集成多种提取器的结果
            # TODO: 实现集成提取器
            logger.warning("集成提取器尚未实现，使用LLM提取器替代")
            return LLMBasedExtractor(config)
        else:
            logger.warning(f"不支持的提取器类型: {extractor_type}，使用DeepSeek提取器作为默认值")
            deepseek_config = config.copy()
            deepseek_config['llm_provider'] = 'deepseek'
            deepseek_config['model_name'] = 'deepseek-chat'
            return LLMBasedExtractor(deepseek_config)
