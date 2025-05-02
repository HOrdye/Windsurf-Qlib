"""
多模态数据加载器使用示例
展示如何加载和处理多模态数据
"""
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入多模态数据加载器
from data.multimodal_loader import MultiModalDataLoader

# 设置环境变量
os.environ["QLIB_DATA_ROOT"] = "/data/qlib"  # 根据实际情况修改

def create_mock_data(data_dir):
    """创建模拟数据用于测试"""
    # 确保目录存在
    os.makedirs(data_dir, exist_ok=True)
    
    # 创建数值数据
    instruments = ['000001.SZ', '000002.SZ', '000003.SZ']
    dates = pd.date_range(start='2022-01-01', end='2022-01-31')
    
    data = []
    for instrument in instruments:
        for date in dates:
            # 生成随机特征
            open_price = np.random.uniform(10, 100)
            high_price = open_price * (1 + np.random.uniform(0, 0.1))
            low_price = open_price * (1 - np.random.uniform(0, 0.1))
            close_price = np.random.uniform(low_price, high_price)
            volume = np.random.randint(1000000, 10000000)
            
            # 计算一些技术指标作为特征
            ma5 = np.random.uniform(open_price * 0.9, open_price * 1.1)
            ma10 = np.random.uniform(open_price * 0.9, open_price * 1.1)
            rsi = np.random.uniform(0, 100)
            
            # 生成目标变量（第二天收益率）
            next_return = np.random.normal(0, 0.02)
            
            data.append({
                'instrument': instrument,
                'datetime': date,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume,
                'ma5': ma5,
                'ma10': ma10,
                'rsi': rsi,
                'next_return': next_return
            })
    
    # 创建数据框并保存
    df = pd.DataFrame(data)
    numerical_path = os.path.join(data_dir, 'numerical_data.feather')
    df.to_feather(numerical_path)
    print(f"数值数据已保存到: {numerical_path}")
    
    # 创建文本数据目录
    text_dir = os.path.join(data_dir, 'text_data')
    os.makedirs(text_dir, exist_ok=True)
    
    # 为每个股票每天创建一个文本文件
    for instrument in instruments:
        for date in dates:
            date_str = date.strftime('%Y%m%d')
            file_path = os.path.join(text_dir, f"{instrument}_{date_str}.txt")
            
            # 生成随机新闻
            news_count = np.random.randint(1, 5)
            news = []
            for _ in range(news_count):
                sentiment = np.random.choice(['积极', '中性', '消极'])
                news.append(f"这是关于{instrument}的{sentiment}新闻。市场分析师认为该公司表现{sentiment}。")
            
            # 保存到文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(news))
    
    print(f"文本数据已保存到: {text_dir}")
    
    # 创建图像数据目录
    image_dir = os.path.join(data_dir, 'image_data')
    os.makedirs(image_dir, exist_ok=True)
    
    # 为每个股票创建一个目录
    for instrument in instruments:
        instrument_dir = os.path.join(image_dir, instrument)
        os.makedirs(instrument_dir, exist_ok=True)
        
        # 为每天创建一个目录
        for date in dates:
            date_str = date.strftime('%Y%m%d')
            date_dir = os.path.join(instrument_dir, date_str)
            os.makedirs(date_dir, exist_ok=True)
            
            # 创建K线图
            plt.figure(figsize=(10, 6))
            plt.plot(np.random.randn(100).cumsum())
            plt.title(f"{instrument} K线图 {date_str}")
            plt.savefig(os.path.join(date_dir, 'kline.png'))
            plt.close()
            
            # 创建成交量图
            plt.figure(figsize=(10, 6))
            plt.bar(range(30), np.random.randint(100, 1000, 30))
            plt.title(f"{instrument} 成交量 {date_str}")
            plt.savefig(os.path.join(date_dir, 'volume.png'))
            plt.close()
    
    print(f"图像数据已保存到: {image_dir}")
    
    return {
        'numerical_path': numerical_path,
        'text_dir': text_dir,
        'image_dir': image_dir
    }

def main():
    """主函数"""
    # 创建模拟数据
    mock_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mock_data')
    data_paths = create_mock_data(mock_data_dir)
    
    # 配置多模态数据加载器
    config = {
        'start_time': '2022-01-01',
        'end_time': '2022-01-31',
        'instruments': ['000001.SZ', '000002.SZ', '000003.SZ'],
        'features': ['open', 'high', 'low', 'close', 'volume', 'ma5', 'ma10', 'rsi'],
        'target': 'next_return',
        'numerical_data_path': data_paths['numerical_path'].replace('/data/qlib/', ''),
        'text_data_path': data_paths['text_dir'].replace('/data/qlib/', ''),
        'image_data_path': data_paths['image_dir'].replace('/data/qlib/', ''),
        'normalize': True,
        'fill_na_method': 'ffill',
        'cache_dir': 'example_cache'
    }
    
    # 创建数据加载器
    loader = MultiModalDataLoader(config)
    
    # 加载数据
    numerical_df, text_dict, image_dict = loader.load()
    
    # 显示数据信息
    print("\n数值数据信息:")
    print(f"形状: {numerical_df.shape}")
    print(f"列: {numerical_df.columns.tolist()}")
    print(f"样本:\n{numerical_df.head()}")
    
    print("\n文本数据信息:")
    print(f"样本数: {len(text_dict)}")
    if text_dict:
        sample_key = list(text_dict.keys())[0]
        print(f"样本 ({sample_key}): {text_dict[sample_key]}")
    
    print("\n图像数据信息:")
    print(f"样本数: {len(image_dict)}")
    if image_dict:
        sample_key = list(image_dict.keys())[0]
        print(f"样本 ({sample_key}): {image_dict[sample_key]}")
    
    # 尝试创建PyTorch数据加载器
    try:
        import torch
        train_loader, val_loader = loader.create_torch_dataloaders(batch_size=16)
        
        print("\nPyTorch数据加载器信息:")
        print(f"训练批次数: {len(train_loader)}")
        if val_loader:
            print(f"验证批次数: {len(val_loader)}")
        
        # 获取一个批次的数据
        batch = next(iter(train_loader))
        print(f"批次数据类型: {type(batch)}")
        print(f"批次数据键: {batch.keys()}")
        print(f"数值特征形状: {batch['numerical'].shape}")
        if 'target' in batch:
            print(f"目标变量形状: {batch['target'].shape}")
    except ImportError:
        print("\nPyTorch未安装，跳过数据加载器创建")

if __name__ == "__main__":
    main()
