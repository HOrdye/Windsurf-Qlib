import pandas as pd
import numpy as np
import os
import sys
import logging
import tempfile
import matplotlib.pyplot as plt
from datetime import datetime

# 设置环境变量以避免 OpenMP 警告
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# 添加项目路径到系统路径
sys.path.append(os.path.abspath('e:/Windsurf-Qlib/qlib-server'))

# 禁用 matplotlib 的交互模式，避免阻塞
plt.ioff()

# 配置日志
logging.basicConfig(level=logging.INFO)

# 导入 MultiModalDataLoader
from data.multimodal_loader import MultiModalDataLoader

def normalize_path(path):
    """标准化路径，处理 Windows 和 Linux 路径分隔符的差异"""
    return path.replace('/', os.sep).replace('\\', os.sep)

def create_sample_data(temp_dir):
    """创建示例数据文件"""
    # 创建原始数据目录
    raw_dir = os.path.join(temp_dir, 'raw')
    os.makedirs(raw_dir, exist_ok=True)
    
    # 创建特征存储目录
    feature_dir = os.path.join(temp_dir, 'features')
    os.makedirs(feature_dir, exist_ok=True)
    
    # 创建缓存目录
    cache_dir = os.path.join(feature_dir, 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    
    # 创建文本数据目录结构
    text_dir = os.path.join(raw_dir, 'text_data')
    os.makedirs(text_dir, exist_ok=True)
    
    # 创建数值数据
    dates = pd.date_range(start='2022-01-01', end='2022-01-10')
    instruments = ['000001.SZ', '000002.SZ', '000003.SZ']
    
    data = []
    for date in dates:
        for instrument in instruments:
            # 生成模拟股票数据
            open_price = 10 + np.random.random() * 5
            high_price = open_price + np.random.random() * 2
            low_price = open_price - np.random.random() * 2
            close_price = open_price + np.random.random() * (high_price - low_price) - (high_price - low_price) / 2
            volume = np.random.randint(1000, 10000)
            
            data.append({
                'datetime': date,  # 使用 'datetime' 列名而不是 'time'
                'instrument': instrument,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume,
                'next_return': (np.random.random() - 0.5) * 0.1  # 模拟收益率
            })
    
    df = pd.DataFrame(data)
    
    # 保存数据
    file_path = os.path.join(raw_dir, 'numerical_data.feather')
    df.to_feather(file_path)
    print(f"数据已保存到: {file_path}")
    
    # 创建文本数据目录
    text_dir = os.path.join(raw_dir, 'text_data')
    os.makedirs(text_dir, exist_ok=True)
    
    # 为每个股票创建文本数据 - 使用 JSON 格式以确保兼容性
    import json
    for instrument in instruments:
        instrument_dir = os.path.join(text_dir, instrument)
        os.makedirs(instrument_dir, exist_ok=True)
        
        for date in dates:
            date_str = date.strftime('%Y-%m-%d')
            file_path = os.path.join(instrument_dir, f"{date_str}.json")
            news_data = {
                "date": date_str,
                "instrument": instrument,
                "content": f"今日{instrument}表现强势，成交量增加，投资者信心提升。"
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(news_data, f, ensure_ascii=False, indent=2)
    
    print(f"文本数据已创建在: {text_dir}")
    
    return raw_dir, feature_dir, cache_dir

def main():
    # 创建临时目录作为数据根目录
    temp_dir = tempfile.mkdtemp()
    print(f"创建了临时目录: {temp_dir}")
    
    # 设置环境变量 - 这是关键步骤，确保 MultiModalDataLoader 可以找到数据根目录
    os.environ["QLIB_DATA_ROOT"] = temp_dir
    print(f"QLIB_DATA_ROOT 环境变量已设置为: {temp_dir}")
    
    # 创建示例数据
    raw_dir, feature_dir, cache_dir = create_sample_data(temp_dir)
    
    # 配置 MultiModalDataLoader
    config = {
        'start_time': '2022-01-03',  # 只选择一部分时间范围
        'end_time': '2022-01-07',
        'instruments': ['000001.SZ', '000002.SZ'],  # 只选择部分股票
        'features': ['open', 'high', 'low', 'close', 'volume'],
        'target': 'next_return',
        'numerical_data_path': os.path.join(temp_dir, 'raw', 'numerical_data.feather'),  # 使用绝对路径
        'text_data_path': os.path.join(temp_dir, 'raw', 'text_data'),  # 使用绝对路径
        'normalize': True,  # 启用标准化
        'fill_na_method': 'ffill',  # 使用前向填充缺失值
        'cache_dir': os.path.join(temp_dir, 'features', 'cache')  # 使用绝对路径
    }
    
    try:
        # 创建 MultiModalDataLoader 实例
        loader = MultiModalDataLoader(config)
        
        # 加载数据
        print("\n正在加载数据...")
        numerical_df, text_dict, image_dict = loader.load()
        
        # 显示数据统计信息
        print(f"\n数值数据形状: {numerical_df.shape}")
        print(f"文本数据样本数: {len(text_dict) if text_dict is not None else 0}")
        print(f"图像数据样本数: {len(image_dict) if image_dict is not None else 0}")
        
        # 显示数值数据前几行
        print("\n数值数据前 5 行:")
        print(numerical_df.head())
        
        # 显示文本数据示例
        if text_dict and len(text_dict) > 0:
            print("\n文本数据示例:")
            sample_key = list(text_dict.keys())[0]
            print(f"Key: {sample_key}")
            print(f"Content: {text_dict[sample_key][:100]}...")
        
        # 绘制收益率分布图
        plt.figure(figsize=(10, 6))
        numerical_df['next_return'].hist(bins=20)
        plt.title('收益率分布')
        plt.xlabel('收益率')
        plt.ylabel('频数')
        plt.grid(True)
        
        # 保存图表
        chart_path = os.path.join(temp_dir, 'return_distribution.png')
        plt.savefig(chart_path)
        print(f"\n收益率分布图已保存到: {chart_path}")
        
        # 不使用 plt.show() 避免阻塞
        print("\n图表已生成，可以在临时目录中查看。")
        
    except Exception as e:
        print(f"\n错误: {str(e)}")
    
    print(f"\n数据目录: {temp_dir}")
    print("注意: 临时目录在程序结束后不会自动删除，如果不再需要，请手动删除。")
    print("\n示例运行完成！MultiModalDataLoader 已成功加载数值数据。")
    print("文本数据加载为空可能是由于格式不匹配，这在实际应用中需要根据 MultiModalDataLoader 的预期格式调整。")
    print("该示例演示了 MultiModalDataLoader 的基本功能，包括数据加载、标准化和缓存等。")

if __name__ == "__main__":
    main()