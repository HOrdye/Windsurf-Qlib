#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
大模型(LLM)基础接口类
提供与各种大模型交互的统一接口
"""
import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Union, Optional, Any, Tuple

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BaseLLM(ABC):
    """
    大模型基础接口类
    所有特定大模型实现必须继承此类并实现其抽象方法
    """
    
    def __init__(self, 
                 model_name: str,
                 api_key: Optional[str] = None,
                 api_url: Optional[str] = None,
                 config: Optional[Dict] = None):
        """
        初始化大模型接口
        
        参数:
            model_name: 模型名称
            api_key: API密钥
            api_url: API地址
            config: 配置参数
        """
        self.model_name = model_name
        self.api_key = api_key or os.environ.get(f"{self.__class__.__name__.upper()}_API_KEY", "")
        self.api_url = api_url
        self.config = config or {}
        self.last_response = None
        self.history = []
        
        if not self.api_key:
            logger.warning(f"未提供API密钥，请确保在环境变量或初始化参数中设置API密钥")
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    def add_to_history(self, role: str, content: str) -> None:
        """
        添加对话历史
        
        参数:
            role: 角色 (user/assistant/system)
            content: 内容
        """
        self.history.append({"role": role, "content": content})
        
        # 保持历史记录在合理长度
        max_history = self.config.get("max_history", 10)
        if len(self.history) > max_history:
            # 保留system消息和最近的对话
            system_messages = [msg for msg in self.history if msg["role"] == "system"]
            recent_messages = self.history[-max_history:]
            
            # 合并，确保system消息在最前面
            self.history = system_messages + [msg for msg in recent_messages if msg["role"] != "system"]
    
    def clear_history(self) -> None:
        """
        清除对话历史
        """
        # 保留system消息
        self.history = [msg for msg in self.history if msg["role"] == "system"]
    
    def get_last_response(self) -> Optional[str]:
        """
        获取最后一次响应
        
        返回:
            最后一次响应内容
        """
        return self.last_response
    
    def _prepare_prompt(self, 
                       prompt: str, 
                       system_prompt: Optional[str] = None) -> str:
        """
        准备完整提示词
        
        参数:
            prompt: 用户提示词
            system_prompt: 系统提示词
            
        返回:
            完整提示词
        """
        if system_prompt:
            return f"{system_prompt}\n\n{prompt}"
        return prompt
