"""
Qlib多模态数据加载器简单验证工具
使用matplotlib直接生成图表，不依赖Streamlit
"""
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import json
import time

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# 设置环境变量
data_dir = os.path.join(project_root, "mock_data")
os.environ["QLIB_DATA_ROOT"] = data_dir

# 导入多模态数据加载器
from data.multimodal_loader import MultiModalDataLoader

def create_mock_data():
    """创建模拟数据用于测试"""
    # 确保目录存在
    os.makedirs(data_dir, exist_ok=True)
    
    # 创建数值数据
    instruments = ['000001.SZ', '000002.SZ', '000003.SZ']
    dates = pd.date_range(start='2022-01-01', end='2022-01-31')
    
    data = []
    for instrument in instruments:
        # 为每只股票创建一个基础价格和趋势
        base_price = np.random.uniform(10, 100)
        trend = np.random.choice([-1, 1]) * np.random.uniform(0.001, 0.005)
        volatility = np.random.uniform(0.01, 0.03)
        
        for i, date in enumerate(dates):
            # 生成价格走势，加入一些随机性但保持趋势
            price_change = trend + np.random.normal(0, volatility)
            if i == 0:
                open_price = base_price
            else:
                open_price = data[-1]['close'] * (1 + price_change)
            
            # 生成当天的高低开收价格
            high_price = open_price * (1 + np.random.uniform(0, 0.02))
            low_price = open_price * (1 - np.random.uniform(0, 0.02))
            close_price = np.random.uniform(low_price, high_price)
            
            # 生成成交量，与价格变化正相关
            volume = np.random.randint(1000000, 10000000) * (1 + abs(price_change) * 10)
            
            # 计算一些技术指标作为特征
            if i >= 5:
                ma5 = np.mean([data[j]['close'] for j in range(len(data)-5, len(data))])
            else:
                ma5 = close_price
                
            if i >= 10:
                ma10 = np.mean([data[j]['close'] for j in range(len(data)-10, len(data))])
            else:
                ma10 = close_price
            
            # 生成RSI指标（简化版）
            rsi = np.random.uniform(30, 70)
            
            # 生成目标变量（第二天收益率）
            next_return = np.random.normal(trend, volatility)
            
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
            plt.plot(range(30), np.random.randn(30).cumsum())
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
        'image_dir': image_dir,
        'instruments': instruments,
        'date_range': (dates[0].strftime('%Y-%m-%d'), dates[-1].strftime('%Y-%m-%d'))
    }

def test_data_loader():
    """测试数据加载器并生成可视化结果"""
    # 检查模拟数据是否存在
    numerical_path = os.path.join(data_dir, 'numerical_data.feather')
    
    if not os.path.exists(numerical_path):
        print("未检测到模拟数据，正在创建...")
        data_info = create_mock_data()
    else:
        print("检测到现有模拟数据")
    
    # 配置数据加载器
    config = {
        'start_time': '2022-01-01',
        'end_time': '2022-01-31',
        'instruments': ['000001.SZ', '000002.SZ'],
        'features': ['open', 'high', 'low', 'close', 'volume', 'ma5', 'ma10', 'rsi'],
        'target': 'next_return',
        'numerical_data_path': os.path.relpath(numerical_path, data_dir),
        'text_data_path': os.path.relpath(os.path.join(data_dir, 'text_data'), data_dir),
        'image_data_path': os.path.relpath(os.path.join(data_dir, 'image_data'), data_dir),
        'normalize': True,
        'fill_na_method': 'ffill'
    }
    
    print("\n数据加载配置:")
    print(json.dumps(config, indent=2))
    
    # 加载数据
    try:
        print("\n正在加载数据...")
        start_time = time.time()
        loader = MultiModalDataLoader(config)
        numerical_df, text_dict, image_dict = loader.load()
        end_time = time.time()
        
        print(f"数据加载成功！耗时: {end_time - start_time:.2f}秒")
        
        # 显示数据信息
        print(f"\n数值数据样本数: {len(numerical_df) if numerical_df is not None else 0}")
        print(f"文本数据样本数: {len(text_dict) if text_dict is not None else 0}")
        print(f"图像数据样本数: {len(image_dict) if image_dict is not None else 0}")
        
        # 数值数据预览
        if numerical_df is not None and not numerical_df.empty:
            print("\n数值数据预览:")
            print(numerical_df.head())
            
            print("\n数值数据统计:")
            print(numerical_df.describe())
            
            # 创建可视化目录
            viz_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
            os.makedirs(viz_dir, exist_ok=True)
            
            # 生成可视化图表
            print("\n生成可视化图表...")
            
            # 1. 价格走势图
            plt.figure(figsize=(12, 6))
            plot_df = numerical_df.reset_index()
            for instrument in plot_df['instrument'].unique():
                inst_data = plot_df[plot_df['instrument'] == instrument]
                plt.plot(inst_data['datetime'], inst_data['close'], label=instrument)
            
            plt.title("股票价格走势")
            plt.xlabel("日期")
            plt.ylabel("收盘价")
            plt.legend()
            plt.grid(True)
            plt.savefig(os.path.join(viz_dir, "price_trend.png"))
            plt.close()
            
            # 2. 成交量图
            plt.figure(figsize=(12, 6))
            instrument = plot_df['instrument'].unique()[0]
            inst_data = plot_df[plot_df['instrument'] == instrument]
            plt.bar(inst_data['datetime'], inst_data['volume'])
            
            plt.title(f"{instrument} 成交量")
            plt.xlabel("日期")
            plt.ylabel("成交量")
            plt.grid(True)
            plt.savefig(os.path.join(viz_dir, "volume.png"))
            plt.close()
            
            # 3. 相关性矩阵
            plt.figure(figsize=(10, 8))
            corr = numerical_df.corr()
            im = plt.imshow(corr, cmap='coolwarm')
            
            # 添加刻度和标签
            plt.xticks(np.arange(len(corr.columns)), corr.columns, rotation=45)
            plt.yticks(np.arange(len(corr.columns)), corr.columns)
            
            # 添加颜色条
            plt.colorbar(im)
            
            plt.title("特征相关性矩阵")
            plt.tight_layout()
            plt.savefig(os.path.join(viz_dir, "correlation.png"))
            plt.close()
            
            # 4. 特征分布图
            feature = 'close'
            plt.figure(figsize=(10, 6))
            plt.hist(numerical_df[feature], bins=30)
            
            plt.title(f"{feature} 分布")
            plt.xlabel(feature)
            plt.ylabel("频率")
            plt.grid(True)
            plt.savefig(os.path.join(viz_dir, "feature_distribution.png"))
            plt.close()
            
            print(f"可视化图表已保存到: {viz_dir}")
            
            # 文本数据预览
            if text_dict:
                print("\n文本数据预览:")
                sample_keys = list(text_dict.keys())[:2]
                for key in sample_keys:
                    print(f"{key}:")
                    for text in text_dict[key]:
                        print(f"  - {text}")
            
            # 图像数据预览
            if image_dict:
                print("\n图像数据预览:")
                sample_keys = list(image_dict.keys())[:2]
                for key in sample_keys:
                    print(f"{key}: {len(image_dict[key])}张图像")
                    for path in image_dict[key]:
                        print(f"  - {path}")
            
            print("\n数据加载器验证完成！")
            
            # 返回可视化目录路径
            return viz_dir
        else:
            print("未加载数值数据，无法生成可视化图表")
            return None
    
    except Exception as e:
        print(f"数据加载失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("开始验证Qlib多模态数据加载器...")
    viz_dir = test_data_loader()
    
    if viz_dir:
        print(f"\n验证成功！可视化结果已保存到: {viz_dir}")
        print("请打开该目录查看生成的图表")
    else:
        print("\n验证失败！请检查错误信息")
    
    input("\n按Enter键退出...")
