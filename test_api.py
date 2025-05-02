#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试API服务器的Alpha信号提取功能
"""
import requests
import json
import sys
import os

# 设置API基础URL
BASE_URL = "http://localhost:8080"

def test_parse_url():
    """测试网页解析API"""
    url = "https://finance.sina.com.cn/stock/"
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/alpha/documents/parse-url",
            json={"url": url}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("网页解析成功:")
            print(f"文档ID: {result.get('document_id')}")
            print(f"内容长度: {len(result.get('content', ''))}")
            return result.get('document_id'), result.get('content')
        else:
            print(f"网页解析失败: {response.status_code}")
            print(response.text)
            return None, None
    except Exception as e:
        print(f"请求异常: {e}")
        return None, None

def test_extract_signals(document_id, extractor_type="deepseek"):
    """测试信号提取API"""
    if not document_id:
        print("错误: 缺少文档ID")
        return None
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/alpha/extract",
            json={
                "document_id": document_id,
                "extractor_type": extractor_type
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            signals = result.get('signals', [])
            print(f"\n成功提取 {len(signals)} 个Alpha信号:")
            
            for i, signal in enumerate(signals):
                print(f"\n信号 {i+1}:")
                print(f"  名称: {signal.get('name')}")
                print(f"  描述: {signal.get('description')[:100]}...")
                print(f"  方向: {signal.get('direction')}")
                print(f"  置信度: {signal.get('confidence')}")
                print(f"  股票代码: {signal.get('stock_codes')}")
            
            return signals
        else:
            print(f"\n信号提取失败: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"\n请求异常: {e}")
        return None

def main():
    """主函数"""
    print("=== 测试Alpha信号提取API ===\n")
    
    # 测试网页解析
    print("1. 测试网页解析API...")
    document_id, content = test_parse_url()
    
    if not document_id:
        print("网页解析失败，测试终止")
        return
    
    # 测试DeepSeek提取器
    print("\n2. 测试DeepSeek提取器...")
    signals = test_extract_signals(document_id, "deepseek")
    
    if not signals:
        print("DeepSeek提取器测试失败")
    
    # 测试规则提取器
    print("\n3. 测试规则提取器...")
    signals = test_extract_signals(document_id, "rule")
    
    if not signals:
        print("规则提取器测试失败")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    main()
