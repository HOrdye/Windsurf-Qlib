"""
Qlib多模态数据加载器可视化验证工具
使用Streamlit构建简单的Web界面，展示数据加载和可视化过程
"""
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import time

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入多模态数据加载器
from data.multimodal_loader import MultiModalDataLoader

# 设置页面配置
st.set_page_config(
    page_title="Qlib多模态数据加载器验证",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 设置环境变量
os.environ["QLIB_DATA_ROOT"] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mock_data")

# 创建模拟数据
def create_mock_data():
    """创建模拟数据用于测试"""
    data_dir = os.environ["QLIB_DATA_ROOT"]
    
    # 确保目录存在
    os.makedirs(data_dir, exist_ok=True)
    
    # 创建数值数据
    instruments = ['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ', '000005.SZ']
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
            
            # 生成与股票表现相关的新闻
            instrument_data = df[(df['instrument'] == instrument) & (df['datetime'] == date)]
            if not instrument_data.empty:
                price_change = instrument_data['close'].values[0] / instrument_data['open'].values[0] - 1
                if price_change > 0.01:
                    sentiment = "积极"
                    news_templates = [
                        f"{instrument}今日大涨，分析师看好后市表现。",
                        f"{instrument}发布利好消息，股价应声上涨。",
                        f"机构投资者增持{instrument}，看好公司发展前景。"
                    ]
                elif price_change < -0.01:
                    sentiment = "消极"
                    news_templates = [
                        f"{instrument}今日下跌，市场对业绩表现存疑。",
                        f"{instrument}面临行业竞争加剧，投资者担忧盈利能力。",
                        f"分析师下调{instrument}评级，建议投资者谨慎。"
                    ]
                else:
                    sentiment = "中性"
                    news_templates = [
                        f"{instrument}今日表现平稳，市场观望态度明显。",
                        f"{instrument}发布季度报告，业绩符合预期。",
                        f"分析师维持{instrument}评级，认为估值合理。"
                    ]
                
                for _ in range(news_count):
                    news.append(np.random.choice(news_templates))
            
            # 保存到文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(news))
    
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
            
            # 获取该股票该日期的数据
            day_data = df[(df['instrument'] == instrument) & (df['datetime'] == date)]
            if day_data.empty:
                continue
                
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
    
    return {
        'numerical_path': numerical_path,
        'text_dir': text_dir,
        'image_dir': image_dir,
        'instruments': instruments,
        'date_range': (dates[0].strftime('%Y-%m-%d'), dates[-1].strftime('%Y-%m-%d'))
    }

# 主界面
def main():
    st.title("Qlib多模态数据加载器验证工具")
    
    # 侧边栏
    st.sidebar.title("配置选项")
    
    # 检查模拟数据是否存在
    data_dir = os.environ["QLIB_DATA_ROOT"]
    numerical_path = os.path.join(data_dir, 'numerical_data.feather')
    
    if not os.path.exists(numerical_path):
        st.sidebar.warning("未检测到模拟数据，请先创建")
        if st.sidebar.button("创建模拟数据"):
            with st.spinner("正在创建模拟数据..."):
                data_info = create_mock_data()
                st.sidebar.success("模拟数据创建成功！")
                st.experimental_rerun()
        return
    
    # 加载模拟数据信息
    instruments = []
    date_range = ('2022-01-01', '2022-01-31')  # 默认值
    
    try:
        df = pd.read_feather(numerical_path)
        instruments = df['instrument'].unique().tolist()
        start_date = df['datetime'].min().strftime('%Y-%m-%d')
        end_date = df['datetime'].max().strftime('%Y-%m-%d')
        date_range = (start_date, end_date)
    except Exception as e:
        st.sidebar.error(f"加载数据信息失败: {e}")
    
    # 数据加载配置
    st.sidebar.subheader("数据加载配置")
    
    selected_instruments = st.sidebar.multiselect(
        "选择股票代码",
        instruments,
        default=instruments[:2] if len(instruments) >= 2 else instruments
    )
    
    start_date = st.sidebar.date_input(
        "开始日期",
        pd.to_datetime(date_range[0])
    )
    
    end_date = st.sidebar.date_input(
        "结束日期",
        pd.to_datetime(date_range[1])
    )
    
    features = ['open', 'high', 'low', 'close', 'volume', 'ma5', 'ma10', 'rsi']
    selected_features = st.sidebar.multiselect(
        "选择特征",
        features,
        default=['open', 'close', 'volume']
    )
    
    target = st.sidebar.selectbox(
        "目标变量",
        ['next_return'],
        index=0
    )
    
    # 数据处理选项
    st.sidebar.subheader("数据处理选项")
    
    normalize = st.sidebar.checkbox("标准化特征", value=True)
    
    fill_na_method = st.sidebar.selectbox(
        "缺失值填充方法",
        ['ffill', 'bfill', 'mean', 'zero'],
        index=0
    )
    
    # 数据模态选择
    st.sidebar.subheader("数据模态")
    
    load_numerical = st.sidebar.checkbox("加载数值数据", value=True)
    load_text = st.sidebar.checkbox("加载文本数据", value=True)
    load_image = st.sidebar.checkbox("加载图像数据", value=True)
    
    # 加载数据按钮
    if st.sidebar.button("加载数据"):
        # 构建配置
        config = {
            'start_time': start_date.strftime('%Y-%m-%d'),
            'end_time': end_date.strftime('%Y-%m-%d'),
            'instruments': selected_instruments,
            'features': selected_features,
            'target': target,
            'normalize': normalize,
            'fill_na_method': fill_na_method
        }
        
        # 添加数据路径
        if load_numerical:
            config['numerical_data_path'] = os.path.relpath(numerical_path, data_dir)
        
        if load_text:
            text_dir = os.path.join(data_dir, 'text_data')
            if os.path.exists(text_dir):
                config['text_data_path'] = os.path.relpath(text_dir, data_dir)
        
        if load_image:
            image_dir = os.path.join(data_dir, 'image_data')
            if os.path.exists(image_dir):
                config['image_data_path'] = os.path.relpath(image_dir, data_dir)
        
        # 显示配置
        st.subheader("数据加载配置")
        st.json(config)
        
        # 加载数据
        try:
            with st.spinner("正在加载数据..."):
                start_time = time.time()
                loader = MultiModalDataLoader(config)
                numerical_df, text_dict, image_dict = loader.load()
                end_time = time.time()
                
                st.success(f"数据加载成功！耗时: {end_time - start_time:.2f}秒")
                
                # 显示数据信息
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("数值数据样本数", len(numerical_df) if numerical_df is not None else 0)
                
                with col2:
                    st.metric("文本数据样本数", len(text_dict) if text_dict is not None else 0)
                
                with col3:
                    st.metric("图像数据样本数", len(image_dict) if image_dict is not None else 0)
                
                # 展示数据
                tabs = st.tabs(["数值数据", "文本数据", "图像数据", "数据可视化"])
                
                with tabs[0]:
                    if numerical_df is not None and not numerical_df.empty:
                        st.subheader("数值数据预览")
                        st.dataframe(numerical_df.head(10))
                        
                        st.subheader("数值数据统计")
                        st.dataframe(numerical_df.describe())
                    else:
                        st.info("未加载数值数据")
                
                with tabs[1]:
                    if text_dict is not None and text_dict:
                        st.subheader("文本数据预览")
                        sample_keys = list(text_dict.keys())[:5]
                        for key in sample_keys:
                            st.write(f"**{key}**")
                            for text in text_dict[key]:
                                st.text(text)
                            st.markdown("---")
                    else:
                        st.info("未加载文本数据")
                
                with tabs[2]:
                    if image_dict is not None and image_dict:
                        st.subheader("图像数据预览")
                        sample_keys = list(image_dict.keys())[:3]
                        for key in sample_keys:
                            st.write(f"**{key}**")
                            image_paths = image_dict[key]
                            if image_paths:
                                cols = st.columns(min(len(image_paths), 3))
                                for i, img_path in enumerate(image_paths[:3]):
                                    try:
                                        cols[i].image(img_path, caption=os.path.basename(img_path))
                                    except Exception as e:
                                        cols[i].error(f"无法加载图像: {e}")
                            st.markdown("---")
                    else:
                        st.info("未加载图像数据")
                
                with tabs[3]:
                    if numerical_df is not None and not numerical_df.empty:
                        st.subheader("数据可视化")
                        
                        # 选择可视化类型
                        viz_type = st.selectbox(
                            "选择可视化类型",
                            ["价格走势", "成交量", "相关性矩阵", "特征分布"],
                            index=0
                        )
                        
                        if viz_type == "价格走势":
                            # 重置索引以便绘图
                            plot_df = numerical_df.reset_index()
                            
                            # 选择要显示的股票
                            plot_instruments = st.multiselect(
                                "选择要显示的股票",
                                plot_df['instrument'].unique(),
                                default=plot_df['instrument'].unique()[0]
                            )
                            
                            if plot_instruments:
                                fig, ax = plt.subplots(figsize=(12, 6))
                                for instrument in plot_instruments:
                                    inst_data = plot_df[plot_df['instrument'] == instrument]
                                    ax.plot(inst_data['datetime'], inst_data['close'], label=instrument)
                                
                                ax.set_title("股票价格走势")
                                ax.set_xlabel("日期")
                                ax.set_ylabel("收盘价")
                                ax.legend()
                                ax.grid(True)
                                
                                st.pyplot(fig)
                        
                        elif viz_type == "成交量":
                            # 重置索引以便绘图
                            plot_df = numerical_df.reset_index()
                            
                            # 选择要显示的股票
                            plot_instrument = st.selectbox(
                                "选择股票",
                                plot_df['instrument'].unique()
                            )
                            
                            if plot_instrument:
                                inst_data = plot_df[plot_df['instrument'] == plot_instrument]
                                
                                fig, ax = plt.subplots(figsize=(12, 6))
                                ax.bar(inst_data['datetime'], inst_data['volume'])
                                
                                ax.set_title(f"{plot_instrument} 成交量")
                                ax.set_xlabel("日期")
                                ax.set_ylabel("成交量")
                                ax.grid(True)
                                
                                st.pyplot(fig)
                        
                        elif viz_type == "相关性矩阵":
                            # 计算相关性矩阵
                            corr = numerical_df.corr()
                            
                            fig, ax = plt.subplots(figsize=(10, 8))
                            im = ax.imshow(corr, cmap='coolwarm')
                            
                            # 添加刻度和标签
                            ax.set_xticks(np.arange(len(corr.columns)))
                            ax.set_yticks(np.arange(len(corr.columns)))
                            ax.set_xticklabels(corr.columns)
                            ax.set_yticklabels(corr.columns)
                            
                            # 旋转x轴标签
                            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
                            
                            # 添加颜色条
                            plt.colorbar(im)
                            
                            # 在每个单元格中添加文本
                            for i in range(len(corr.columns)):
                                for j in range(len(corr.columns)):
                                    text = ax.text(j, i, f"{corr.iloc[i, j]:.2f}",
                                                ha="center", va="center", color="black")
                            
                            ax.set_title("特征相关性矩阵")
                            fig.tight_layout()
                            
                            st.pyplot(fig)
                        
                        elif viz_type == "特征分布":
                            # 选择要显示的特征
                            plot_feature = st.selectbox(
                                "选择特征",
                                selected_features
                            )
                            
                            if plot_feature:
                                fig, ax = plt.subplots(figsize=(10, 6))
                                ax.hist(numerical_df[plot_feature], bins=30)
                                
                                ax.set_title(f"{plot_feature} 分布")
                                ax.set_xlabel(plot_feature)
                                ax.set_ylabel("频率")
                                ax.grid(True)
                                
                                st.pyplot(fig)
                                
                                # 显示描述性统计
                                st.write(f"**{plot_feature} 统计信息**")
                                st.dataframe(numerical_df[plot_feature].describe())
                    else:
                        st.info("未加载数值数据，无法进行可视化")
                
        except Exception as e:
            st.error(f"数据加载失败: {e}")
            st.exception(e)

if __name__ == "__main__":
    main()
