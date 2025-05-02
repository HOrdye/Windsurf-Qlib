#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM驱动智能体示例脚本
展示如何使用LLM驱动智能体框架
"""
import os
import sys
import json
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.llm_agent_manager import LLMAgentManager
from agents.models.agent_base import RiskAppetite

async def run_gemini_agent_example(api_key: str):
    """
    运行Gemini驱动的智能体示例
    
    参数:
        api_key: Gemini API密钥
    """
    print("=== 初始化Gemini驱动的智能体管理器 ===")
    agent_manager = LLMAgentManager(
        llm_type="gemini",
        api_key=api_key
    )
    
    # 创建示例市场数据
    market_data = create_sample_market_data()
    
    # 运行混合决策
    print("\n=== 运行混合决策模式（传统智能体 + Gemini分析）===")
    result = await agent_manager.hybrid_investment_decision(
        market_data=market_data,
        risk_appetite="balanced",
        investment_horizon="中期（1-5年）"
    )
    
    # 打印结果
    print("\n=== 投资决策结果 ===")
    print(f"风险偏好: {result['risk_appetite']}")
    print(f"投资期限: {result['investment_horizon']}")
    print(f"日期: {result['date']}")
    
    print("\n=== 智能体投资组合 ===")
    for item in result["agent_portfolio"]:
        print(f"股票: {item['stock_code']}, 权重: {item['weight']:.4f}")
    
    print("\n=== LLM市场分析 ===")
    print(result["llm_analysis"])
    
    print("\n=== LLM投资策略 ===")
    print(json.dumps(result["llm_strategy"], ensure_ascii=False, indent=2))

async def run_deepseek_agent_example(api_key: str):
    """
    运行DeepSeek驱动的智能体示例
    
    参数:
        api_key: DeepSeek API密钥
    """
    print("=== 初始化DeepSeek驱动的智能体管理器 ===")
    agent_manager = LLMAgentManager(
        llm_type="deepseek",
        api_key=api_key
    )
    
    # 创建示例市场数据
    market_data = create_sample_market_data()
    
    # 运行混合决策
    print("\n=== 运行混合决策模式（传统智能体 + DeepSeek分析）===")
    result = await agent_manager.hybrid_investment_decision(
        market_data=market_data,
        risk_appetite="aggressive",
        investment_horizon="长期（>5年）"
    )
    
    # 打印结果
    print("\n=== 投资决策结果 ===")
    print(f"风险偏好: {result['risk_appetite']}")
    print(f"投资期限: {result['investment_horizon']}")
    print(f"日期: {result['date']}")
    
    print("\n=== 智能体投资组合 ===")
    for item in result["agent_portfolio"]:
        print(f"股票: {item['stock_code']}, 权重: {item['weight']:.4f}")
    
    print("\n=== LLM市场分析 ===")
    print(result["llm_analysis"])
    
    print("\n=== LLM投资策略 ===")
    print(json.dumps(result["llm_strategy"], ensure_ascii=False, indent=2))

def create_sample_market_data() -> Dict:
    """
    创建示例市场数据
    
    返回:
        示例市场数据
    """
    # 创建示例股票池
    stock_pool = [
        "600000.SH", "600036.SH", "601318.SH", "000651.SZ", "000333.SZ",
        "600519.SH", "601888.SH", "600276.SH", "000858.SZ", "601899.SH",
        "600887.SH", "601688.SH", "600030.SH", "600031.SH", "600048.SH",
        "601166.SH", "600309.SH", "601988.SH", "600585.SH", "601398.SH"
    ]
    
    # 创建示例数据
    np.random.seed(42)
    data = []
    
    for stock in stock_pool:
        # 基本数据
        close = np.random.uniform(10, 100)
        open_price = close * (1 + np.random.uniform(-0.02, 0.02))
        high = max(close, open_price) * (1 + np.random.uniform(0, 0.03))
        low = min(close, open_price) * (1 - np.random.uniform(0, 0.03))
        volume = np.random.randint(1000000, 10000000)
        
        # 财务数据
        pe = np.random.uniform(10, 40)
        pb = np.random.uniform(1, 5)
        market_cap = np.random.uniform(1000000000, 1000000000000)
        
        # 技术指标
        ma5 = close * (1 + np.random.uniform(-0.05, 0.05))
        ma10 = close * (1 + np.random.uniform(-0.08, 0.08))
        ma20 = close * (1 + np.random.uniform(-0.1, 0.1))
        
        # 动量指标
        momentum_5d = np.random.uniform(-0.05, 0.05)
        momentum_10d = np.random.uniform(-0.08, 0.08)
        momentum_20d = np.random.uniform(-0.1, 0.1)
        
        # 波动率
        volatility_10d = np.random.uniform(0.01, 0.05)
        volatility_20d = np.random.uniform(0.01, 0.08)
        
        # 行业
        industries = ["金融", "科技", "消费", "医药", "能源", "地产", "材料"]
        industry = np.random.choice(industries)
        
        # 预测标签（用于智能体训练）
        label = np.random.uniform(-0.05, 0.1)
        
        # 添加到数据集
        data.append({
            "stock_id": stock,
            "date": "2025-04-11",
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "pe": pe,
            "pb": pb,
            "market_cap": market_cap,
            "ma_5": ma5,
            "ma_10": ma10,
            "ma_20": ma20,
            "momentum_5d": momentum_5d,
            "momentum_10d": momentum_10d,
            "momentum_20d": momentum_20d,
            "volatility_10d": volatility_10d,
            "volatility_20d": volatility_20d,
            "industry": industry,
            "label": label
        })
    
    # 创建DataFrame
    df = pd.DataFrame(data)
    
    # 构建市场数据字典
    market_data = {
        "data": df,
        "stock_pool": stock_pool,
        "date": "2025-04-11",
        "market_context": """
        当前市场处于震荡上行阶段，主要指数近期表现稳健。
        宏观经济数据显示经济增长稳定，通胀压力可控。
        央行货币政策保持中性，流动性充裕。
        科技、消费和医药板块表现较强，金融板块估值处于历史低位。
        市场风险包括地缘政治紧张局势和全球供应链不确定性。
        """
    }
    
    return market_data

async def main():
    """主函数"""
    print("欢迎使用LLM驱动智能体示例程序！")
    print("请选择要使用的LLM类型：")
    print("1. Gemini")
    print("2. DeepSeek")
    
    choice = input("请输入选项编号 (1/2): ")
    
    if choice == "1":
        api_key = input("请输入Gemini API密钥: ")
        await run_gemini_agent_example(api_key)
    elif choice == "2":
        api_key = input("请输入DeepSeek API密钥: ")
        await run_deepseek_agent_example(api_key)
    else:
        print("无效的选项，请重新运行程序并选择有效选项。")

if __name__ == "__main__":
    # 使用清华大学开源软件镜像站安装依赖
    # pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pandas numpy google-generativeai aiohttp
    
    # 运行主函数
    asyncio.run(main())
