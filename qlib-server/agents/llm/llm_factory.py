#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM工厂类，用于创建和管理不同的大模型实例
"""
import os
import logging
from typing import Dict, List, Union, Optional, Any, Tuple

from .base_llm import BaseLLM
from .gemini_llm import GeminiLLM
from .deepseek_llm import DeepSeekLLM

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LLMFactory:
    """
    LLM工厂类，用于创建和管理不同的大模型实例
    """
    
    # 支持的LLM类型
    SUPPORTED_LLMS = {
        "gemini": GeminiLLM,
        "deepseek": DeepSeekLLM,
    }
    
    @staticmethod
    def create_llm(llm_type: str, 
                  model_name: Optional[str] = None, 
                  api_key: Optional[str] = None,
                  api_url: Optional[str] = None,
                  config: Optional[Dict] = None) -> BaseLLM:
        """
        创建LLM实例
        
        参数:
            llm_type: LLM类型，如'gemini'、'deepseek'等
            model_name: 模型名称
            api_key: API密钥
            api_url: API地址
            config: 配置参数
            
        返回:
            LLM实例
        """
        llm_type = llm_type.lower()
        
        if llm_type not in LLMFactory.SUPPORTED_LLMS:
            supported_llms = ", ".join(LLMFactory.SUPPORTED_LLMS.keys())
            raise ValueError(f"不支持的LLM类型: {llm_type}，支持的类型有: {supported_llms}")
        
        # 获取LLM类
        llm_class = LLMFactory.SUPPORTED_LLMS[llm_type]
        
        # 创建LLM实例
        try:
            # 设置默认模型名称
            if model_name is None:
                if llm_type == "gemini":
                    model_name = "gemini-pro"
                elif llm_type == "deepseek":
                    model_name = "deepseek-chat"
            
            # 创建实例
            llm_instance = llm_class(
                model_name=model_name,
                api_key=api_key,
                api_url=api_url,
                config=config
            )
            
            logger.info(f"成功创建 {llm_type} LLM实例: {model_name}")
            return llm_instance
        
        except Exception as e:
            logger.error(f"创建 {llm_type} LLM实例失败: {str(e)}")
            raise
    
    @staticmethod
    def register_llm(llm_type: str, llm_class: type) -> None:
        """
        注册新的LLM类型
        
        参数:
            llm_type: LLM类型名称
            llm_class: LLM类
        """
        # 检查是否继承自BaseLLM
        if not issubclass(llm_class, BaseLLM):
            raise TypeError(f"LLM类 {llm_class.__name__} 必须继承自 BaseLLM")
        
        # 注册LLM类型
        LLMFactory.SUPPORTED_LLMS[llm_type.lower()] = llm_class
        logger.info(f"成功注册LLM类型: {llm_type}")
    
    @staticmethod
    def get_supported_llms() -> List[str]:
        """
        获取支持的LLM类型列表
        
        返回:
            支持的LLM类型列表
        """
        return list(LLMFactory.SUPPORTED_LLMS.keys())
