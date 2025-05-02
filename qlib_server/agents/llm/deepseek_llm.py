#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DeepSeek大模型API实现
"""
import os
import json
import logging
import aiohttp
from typing import Dict, List, Union, Optional, Any, Tuple

from .base_llm import BaseLLM

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DeepSeekLLM(BaseLLM):
    """
    DeepSeek大模型API实现
    """
    
    def __init__(self, 
                 model_name: str = "deepseek-chat",
                 api_key: Optional[str] = None,
                 api_url: Optional[str] = None,
                 config: Optional[Dict] = None):
        """
        初始化DeepSeek API
        
        参数:
            model_name: 模型名称，默认为deepseek-chat
            api_key: API密钥
            api_url: API地址，默认为官方API地址
            config: 配置参数
        """
        # 设置默认API URL
        default_api_url = "https://api.deepseek.com/v1/chat/completions"
        
        super().__init__(model_name, api_key, api_url or default_api_url, config)
        
        # 设置默认生成配置
        self.generation_config = {
            "temperature": self.config.get("temperature", 0.7),
            "top_p": self.config.get("top_p", 0.95),
            "max_tokens": self.config.get("max_tokens", 1024),
        }
        
        logger.info(f"DeepSeek模型 '{self.model_name}' 初始化成功")
    
    async def generate(self, 
                      prompt: str, 
                      system_prompt: Optional[str] = None,
                      temperature: float = 0.7,
                      max_tokens: int = 1024,
                      stop_sequences: Optional[List[str]] = None,
                      **kwargs) -> str:
        """
        生成文本
        
        参数:
            prompt: 提示词
            system_prompt: 系统提示词
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            stop_sequences: 停止序列
            **kwargs: 其他参数
            
        返回:
            生成的文本
        """
        # 准备消息
        messages = []
        
        # 添加系统提示词
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 添加历史消息
        for msg in self.history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # 添加当前提示词
        messages.append({"role": "user", "content": prompt})
        
        # 准备请求参数
        request_data = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # 添加停止序列
        if stop_sequences:
            request_data["stop"] = stop_sequences
        
        # 添加其他参数
        for key, value in kwargs.items():
            if key not in request_data:
                request_data[key] = value
        
        # 发送请求
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=request_data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ValueError(f"DeepSeek API请求失败: 状态码 {response.status}, 错误信息: {error_text}")
                    
                    response_data = await response.json()
                    
                    # 提取响应文本
                    response_text = response_data["choices"][0]["message"]["content"]
                    
                    # 保存响应
                    self.last_response = response_text
                    
                    # 更新对话历史
                    self.add_to_history("user", prompt)
                    self.add_to_history("assistant", response_text)
                    
                    return response_text
        
        except Exception as e:
            logger.error(f"DeepSeek生成文本失败: {str(e)}")
            raise
    
    async def generate_with_json_output(self,
                                       prompt: str,
                                       json_schema: Dict,
                                       system_prompt: Optional[str] = None,
                                       temperature: float = 0.1,
                                       **kwargs) -> Dict:
        """
        生成JSON格式的输出
        
        参数:
            prompt: 提示词
            json_schema: JSON模式定义
            system_prompt: 系统提示词
            temperature: 温度参数，控制随机性
            **kwargs: 其他参数
            
        返回:
            JSON格式的输出
        """
        # 构建提示词，包含JSON模式要求
        schema_str = json.dumps(json_schema, ensure_ascii=False, indent=2)
        json_prompt = f"{prompt}\n\n请严格按照以下JSON模式返回结果：\n```json\n{schema_str}\n```\n请确保返回的是有效的JSON格式，不要包含额外的文本。"
        
        # 如果没有系统提示词，添加一个强调JSON输出的系统提示词
        if not system_prompt:
            system_prompt = "你是一个专业的数据分析助手，请以JSON格式返回结果，确保输出符合指定的JSON模式。"
        else:
            system_prompt = f"{system_prompt}\n请以JSON格式返回结果，确保输出符合指定的JSON模式。"
        
        # 生成响应
        response_text = await self.generate(
            json_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            **kwargs
        )
        
        # 提取JSON部分
        try:
            # 尝试直接解析
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # 尝试从文本中提取JSON部分
            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_text = response_text[json_start:json_end]
                    result = json.loads(json_text)
                else:
                    # 尝试提取代码块中的JSON
                    import re
                    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
                    if json_match:
                        result = json.loads(json_match.group(1))
                    else:
                        raise ValueError("无法从响应中提取有效的JSON")
            except Exception as e:
                logger.error(f"从响应中提取JSON失败: {str(e)}")
                raise ValueError(f"无法从响应中提取有效的JSON: {response_text}")
        
        return result
    
    async def analyze_market_data(self,
                                 data_description: str,
                                 market_context: str,
                                 question: str,
                                 **kwargs) -> str:
        """
        分析市场数据
        
        参数:
            data_description: 数据描述
            market_context: 市场背景
            question: 分析问题
            **kwargs: 其他参数
            
        返回:
            分析结果
        """
        # 构建提示词
        prompt = f"""
# 市场数据分析任务

## 数据描述
{data_description}

## 市场背景
{market_context}

## 分析问题
{question}

请基于以上信息进行深入分析，提供详细的见解和建议。分析应包括：
1. 对数据的关键发现
2. 市场趋势判断
3. 潜在投资机会
4. 风险评估
5. 具体的投资建议
"""
        
        system_prompt = """
你是一位专业的量化投资分析师，擅长分析金融市场数据并提供投资建议。
你的分析应该基于数据和市场背景，提供客观、理性的见解。
请确保你的建议考虑了风险因素，并适合不同风险偏好的投资者。
"""
        
        # 生成分析结果
        response = await self.generate(
            prompt,
            system_prompt=system_prompt,
            temperature=kwargs.get("temperature", 0.3),
            max_tokens=kwargs.get("max_tokens", 2048),
            **kwargs
        )
        
        return response
    
    async def run_agent(self,
                       agent_type: str,
                       market_data: Dict,
                       risk_appetite: str,
                       investment_horizon: str,
                       **kwargs) -> Dict:
        """
        使用DeepSeek运行投资智能体
        
        参数:
            agent_type: 智能体类型
            market_data: 市场数据
            risk_appetite: 风险偏好
            investment_horizon: 投资期限
            **kwargs: 其他参数
            
        返回:
            投资决策结果
        """
        # 构建JSON模式
        json_schema = {
            "type": "object",
            "properties": {
                "analysis": {
                    "type": "object",
                    "properties": {
                        "market_trend": {"type": "string"},
                        "key_factors": {"type": "array", "items": {"type": "string"}},
                        "risk_assessment": {"type": "string"}
                    }
                },
                "portfolio": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "asset": {"type": "string"},
                            "weight": {"type": "number"},
                            "rationale": {"type": "string"}
                        }
                    }
                },
                "strategy": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "expected_return": {"type": "number"},
                        "risk_level": {"type": "string"},
                        "rebalance_frequency": {"type": "string"}
                    }
                }
            }
        }
        
        # 构建市场数据描述
        market_data_str = json.dumps(market_data, ensure_ascii=False, indent=2)
        
        # 构建提示词
        prompt = f"""
# 投资智能体任务

## 智能体类型
{agent_type}

## 风险偏好
{risk_appetite}

## 投资期限
{investment_horizon}

## 市场数据
```json
{market_data_str}
```

请基于以上信息，作为一个{agent_type}投资智能体，生成投资组合建议。
你的决策应该符合{risk_appetite}的风险偏好和{investment_horizon}的投资期限。
"""
        
        system_prompt = f"""
你是一个专业的投资智能体，根据不同的风险偏好和投资期限提供投资建议。

对于不同的风险偏好，你应该遵循以下原则：
- 保守型：追求资本保全，偏好低风险资产，最大仓位不超过70%，单一资产不超过5%
- 平衡型：平衡风险与收益，适度配置成长资产，最大仓位不超过90%，单一资产不超过8%
- 激进型：追求高收益，偏好高增长资产，最大仓位可达100%，单一资产不超过12%

对于不同的投资期限，你应该考虑：
- 短期（<1年）：更注重流动性和短期市场趋势
- 中期（1-5年）：平衡短期波动和中期增长
- 长期（>5年）：更注重长期增长潜力，可以容忍短期波动

请基于市场数据和投资参数生成详细的投资组合建议。
"""
        
        # 生成投资决策
        result = await self.generate_with_json_output(
            prompt,
            json_schema,
            system_prompt=system_prompt,
            temperature=kwargs.get("temperature", 0.2),
            **kwargs
        )
        
        return result
