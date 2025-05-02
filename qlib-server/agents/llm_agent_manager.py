#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM驱动的智能体管理器
将投资智能体与大模型集成
"""
import os
import json
import logging
import asyncio
from typing import Dict, List, Union, Optional, Any, Tuple

from .models.agent_base import InvestmentAgent, RiskAppetite
from .models.conservative_agent import ConservativeAgent
from .models.balanced_agent import BalancedAgent
from .models.aggressive_agent import AggressiveAgent
from .llm.llm_factory import LLMFactory
from .llm.base_llm import BaseLLM

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LLMAgentManager:
    """
    LLM驱动的智能体管理器
    将投资智能体与大模型集成，实现通过大模型驱动智能体的功能
    """
    
    def __init__(self, 
                 llm_type: str = "gemini",
                 model_name: Optional[str] = None,
                 api_key: Optional[str] = None,
                 api_url: Optional[str] = None,
                 config: Optional[Dict] = None):
        """
        初始化LLM驱动的智能体管理器
        
        参数:
            llm_type: LLM类型，如'gemini'、'deepseek'等
            model_name: 模型名称
            api_key: API密钥
            api_url: API地址
            config: 配置参数
        """
        # 创建LLM实例
        self.llm = LLMFactory.create_llm(
            llm_type=llm_type,
            model_name=model_name,
            api_key=api_key,
            api_url=api_url,
            config=config
        )
        
        # 创建智能体实例
        self.agents = {
            "conservative": ConservativeAgent(),
            "balanced": BalancedAgent(),
            "aggressive": AggressiveAgent()
        }
        
        # 当前活跃的智能体
        self.active_agent = None
        
        logger.info(f"LLM驱动的智能体管理器初始化成功，使用 {llm_type} 大模型")
    
    def get_agent(self, risk_appetite: str) -> InvestmentAgent:
        """
        获取指定风险偏好的智能体
        
        参数:
            risk_appetite: 风险偏好，可选值: 'conservative', 'balanced', 'aggressive'
            
        返回:
            智能体实例
        """
        risk_appetite = risk_appetite.lower()
        
        if risk_appetite not in self.agents:
            supported_agents = ", ".join(self.agents.keys())
            raise ValueError(f"不支持的风险偏好: {risk_appetite}，支持的风险偏好有: {supported_agents}")
        
        self.active_agent = self.agents[risk_appetite]
        return self.active_agent
    
    async def analyze_market_data(self,
                                 data_description: str,
                                 market_context: str,
                                 question: str,
                                 **kwargs) -> str:
        """
        使用LLM分析市场数据
        
        参数:
            data_description: 数据描述
            market_context: 市场背景
            question: 分析问题
            **kwargs: 其他参数
            
        返回:
            分析结果
        """
        return await self.llm.analyze_market_data(
            data_description=data_description,
            market_context=market_context,
            question=question,
            **kwargs
        )
    
    async def generate_investment_strategy(self,
                                          market_data: Dict,
                                          risk_appetite: str,
                                          investment_horizon: str,
                                          **kwargs) -> Dict:
        """
        使用LLM生成投资策略
        
        参数:
            market_data: 市场数据
            risk_appetite: 风险偏好
            investment_horizon: 投资期限
            **kwargs: 其他参数
            
        返回:
            投资策略
        """
        # 获取对应的智能体类型
        agent_type = risk_appetite.lower()
        
        # 使用LLM生成投资策略
        return await self.llm.run_agent(
            agent_type=agent_type,
            market_data=market_data,
            risk_appetite=risk_appetite,
            investment_horizon=investment_horizon,
            **kwargs
        )
    
    async def hybrid_investment_decision(self,
                                        market_data: Dict,
                                        risk_appetite: str,
                                        investment_horizon: str,
                                        use_llm_analysis: bool = True,
                                        **kwargs) -> Dict:
        """
        混合决策模式：结合传统智能体和LLM进行投资决策
        
        参数:
            market_data: 市场数据
            risk_appetite: 风险偏好
            investment_horizon: 投资期限
            use_llm_analysis: 是否使用LLM进行市场分析
            **kwargs: 其他参数
            
        返回:
            投资决策结果
        """
        # 获取对应的智能体
        agent = self.get_agent(risk_appetite)
        
        # 准备市场数据
        if 'data' in market_data:
            data = market_data['data']
        else:
            data = market_data
        
        # 使用传统智能体进行预测
        try:
            # 如果智能体已训练，直接预测
            if agent.is_trained:
                predictions = agent.predict(data)
            else:
                # 如果智能体未训练，使用简单规则生成预测
                logger.warning(f"智能体 {risk_appetite} 未训练，使用简单规则生成预测")
                predictions = [0.01] * len(data)  # 示例预测值
        except Exception as e:
            logger.error(f"智能体预测失败: {str(e)}")
            predictions = [0.0] * len(data)  # 失败时使用零预测
        
        # 生成投资组合
        if 'stock_pool' in market_data:
            stock_pool = market_data['stock_pool']
        else:
            # 如果没有提供股票池，使用数据索引作为股票池
            stock_pool = [f"stock_{i}" for i in range(len(data))]
        
        # 生成投资组合
        date = market_data.get('date', '2025-04-11')  # 使用当前日期或提供的日期
        portfolio = agent.generate_portfolio(predictions, stock_pool, date)
        
        # 如果使用LLM分析，则结合LLM的分析结果
        if use_llm_analysis:
            # 准备市场数据描述
            data_description = f"市场数据包含 {len(data)} 只股票的信息，时间为 {date}。"
            
            # 准备市场背景
            market_context = market_data.get('market_context', '当前市场处于波动状态，投资者需谨慎决策。')
            
            # 分析问题
            question = f"基于当前市场数据，为{risk_appetite}风险偏好、{investment_horizon}投资期限的投资者提供投资建议。"
            
            # 使用LLM分析市场
            llm_analysis = await self.analyze_market_data(
                data_description=data_description,
                market_context=market_context,
                question=question
            )
            
            # 使用LLM生成投资策略
            llm_strategy = await self.generate_investment_strategy(
                market_data=market_data,
                risk_appetite=risk_appetite,
                investment_horizon=investment_horizon
            )
            
            # 合并结果
            result = {
                "agent_portfolio": portfolio.to_dict('records') if hasattr(portfolio, 'to_dict') else portfolio,
                "llm_analysis": llm_analysis,
                "llm_strategy": llm_strategy,
                "risk_appetite": risk_appetite,
                "investment_horizon": investment_horizon,
                "date": date
            }
        else:
            # 只返回传统智能体的结果
            result = {
                "portfolio": portfolio.to_dict('records') if hasattr(portfolio, 'to_dict') else portfolio,
                "risk_appetite": risk_appetite,
                "investment_horizon": investment_horizon,
                "date": date
            }
        
        return result
    
    def switch_llm(self, 
                  llm_type: str,
                  model_name: Optional[str] = None,
                  api_key: Optional[str] = None,
                  api_url: Optional[str] = None,
                  config: Optional[Dict] = None) -> None:
        """
        切换LLM类型
        
        参数:
            llm_type: LLM类型，如'gemini'、'deepseek'等
            model_name: 模型名称
            api_key: API密钥
            api_url: API地址
            config: 配置参数
        """
        # 创建新的LLM实例
        self.llm = LLMFactory.create_llm(
            llm_type=llm_type,
            model_name=model_name,
            api_key=api_key,
            api_url=api_url,
            config=config
        )
        
        logger.info(f"已切换到 {llm_type} 大模型")
    
    def get_supported_llms(self) -> List[str]:
        """
        获取支持的LLM类型列表
        
        返回:
            支持的LLM类型列表
        """
        return LLMFactory.get_supported_llms()
    
    def get_supported_agents(self) -> List[str]:
        """
        获取支持的智能体类型列表
        
        返回:
            支持的智能体类型列表
        """
        return list(self.agents.keys())
