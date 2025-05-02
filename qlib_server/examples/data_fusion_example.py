"""
多源数据融合增强示例
演示如何使用跨市场数据对齐、多频率数据重采样和数据源可靠性评分机制
"""
import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入多源数据融合模块
from data.fusion import (
    CrossMarketDataAligner,
    TimeZoneAligner,
    AsynchronousDataAligner,
    MultiFrequencyResampler,
    UpSampler,
    DownSampler,
    AdaptiveResampler,
    DataSourceReliabilityScorer,
    LatencyScorer,
    AccuracyScorer,
    CompletenessScorer,
    ConsistencyScorer,
    DataFusionEngine,
    WeightedAverageFusion,
    KalmanFilterFusion,
    MachineLearningFusion
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_mock_data():
    """
    生成模拟数据
    
    返回:
        数据源字典，键为数据源名称，值为数据源DataFrame
    """
    # 生成时间索引
    # 使用不同的时区
    tz_shanghai = pytz.timezone('Asia/Shanghai')
    tz_newyork = pytz.timezone('America/New_York')
    tz_london = pytz.timezone('Europe/London')
    
    # 生成基准时间序列 - 使用UTC时区，然后转换到各个时区
    now = datetime.now(pytz.UTC)
    start_time = now - timedelta(days=5)
    
    # 生成不同频率的时间索引
    index_1min = pd.date_range(start=start_time, periods=24*60*5, freq='1min', tz='UTC')
    index_1min = index_1min.tz_convert(tz_shanghai)
    
    index_5min = pd.date_range(start=start_time, periods=24*12*5, freq='5min', tz='UTC')
    index_5min = index_5min.tz_convert(tz_newyork)
    
    index_15min = pd.date_range(start=start_time, periods=24*4*5, freq='15min', tz='UTC')
    index_15min = index_15min.tz_convert(tz_london)
    
    # 生成模拟数据
    data_sources = {}
    
    # 生成A股市场数据 - 1分钟频率
    np.random.seed(42)
    
    # 基础价格序列
    base_price = 100.0
    price_a = [base_price]
    for i in range(1, len(index_1min)):
        # 添加随机波动
        price_change = np.random.normal(0, 0.001)
        # 添加趋势
        trend = 0.0001 * np.sin(i / 1000 * np.pi)
        # 添加日内模式
        hour = index_1min[i].hour
        minute = index_1min[i].minute
        intraday = 0.0
        if 9 <= hour < 10 or (hour == 10 and minute < 30):
            # 早盘上涨
            intraday = 0.0002
        elif 13 <= hour < 14:
            # 午盘下跌
            intraday = -0.0001
        elif 14 <= hour < 15:
            # 尾盘上涨
            intraday = 0.0003
        
        # 新价格
        new_price = price_a[-1] * (1 + price_change + trend + intraday)
        price_a.append(new_price)
    
    # 创建A股数据
    df_a = pd.DataFrame({
        'price': price_a,
        'volume': np.random.poisson(1000, size=len(index_1min)),
        'bid': [p * 0.999 for p in price_a],
        'ask': [p * 1.001 for p in price_a]
    }, index=index_1min)
    
    # 只保留交易时间的数据
    trading_mask = ((df_a.index.hour >= 9) & (df_a.index.hour < 15)) & \
                   ~((df_a.index.hour == 12) | ((df_a.index.hour == 11) & (df_a.index.minute >= 30)))
    df_a = df_a[trading_mask]
    
    # 添加一些缺失值
    mask = np.random.random(size=len(df_a)) < 0.01
    df_a.loc[mask, 'price'] = np.nan
    
    # 添加一些异常值
    mask = np.random.random(size=len(df_a)) < 0.005
    df_a.loc[mask, 'price'] = df_a.loc[mask, 'price'] * (1 + np.random.uniform(-0.1, 0.1, size=mask.sum()))
    
    data_sources['china.stock'] = df_a
    
    # 生成美股市场数据 - 5分钟频率
    price_us = []
    for i in range(len(index_5min)):
        # 基于A股价格生成美股价格，但有一些差异
        idx = min(i * 5, len(price_a) - 1)
        base = price_a[idx] * 0.15  # 汇率差异
        noise = np.random.normal(0, 0.002)
        price_us.append(base * (1 + noise))
    
    # 创建美股数据
    df_us = pd.DataFrame({
        'price': price_us,
        'volume': np.random.poisson(500, size=len(index_5min)),
        'bid': [p * 0.998 for p in price_us],
        'ask': [p * 1.002 for p in price_us]
    }, index=index_5min)
    
    # 只保留交易时间的数据
    trading_mask = ((df_us.index.hour >= 9) & (df_us.index.hour < 16))
    df_us = df_us[trading_mask]
    
    # 添加一些缺失值
    mask = np.random.random(size=len(df_us)) < 0.02
    df_us.loc[mask, 'price'] = np.nan
    
    data_sources['us.stock'] = df_us
    
    # 生成港股市场数据 - 15分钟频率
    price_hk = []
    for i in range(len(index_15min)):
        # 基于A股价格生成港股价格，但有一些差异
        idx = min(i * 15, len(price_a) - 1)
        base = price_a[idx] * 1.15  # 汇率差异
        noise = np.random.normal(0, 0.003)
        price_hk.append(base * (1 + noise))
    
    # 创建港股数据
    df_hk = pd.DataFrame({
        'price': price_hk,
        'volume': np.random.poisson(300, size=len(index_15min)),
        'bid': [p * 0.997 for p in price_hk],
        'ask': [p * 1.003 for p in price_hk]
    }, index=index_15min)
    
    # 只保留交易时间的数据
    trading_mask = ((df_hk.index.hour >= 9) & (df_hk.index.hour < 16)) & \
                   ~((df_hk.index.hour == 12))
    df_hk = df_hk[trading_mask]
    
    # 添加一些缺失值和延迟
    mask = np.random.random(size=len(df_hk)) < 0.03
    df_hk.loc[mask, 'price'] = np.nan
    
    data_sources['hk.stock'] = df_hk
    
    return data_sources

def demo_cross_market_alignment():
    """
    演示跨市场数据对齐
    """
    logger.info("=== 演示跨市场数据对齐 ===")
    
    try:
        # 生成模拟数据
        data_sources = generate_mock_data()
        
        # 打印原始数据信息
        for source_name, df in data_sources.items():
            logger.info(f"数据源 {source_name}: 形状 {df.shape}, 时区 {df.index.tz}")
        
        # 配置跨市场数据对齐器
        aligner_config = {
            "reference_market": "china.stock",
            "alignment_method": "inner",
            "max_time_diff": 300,  # 5分钟
            "market_calendars": {
                "china.stock": [],  # 空列表表示使用所有日期
                "us.stock": [],
                "hk.stock": []
            },
            "market_hours": {
                "china.stock": {
                    "0": [["09:00", "11:30"], ["13:00", "15:00"]],  # 周一
                    "1": [["09:00", "11:30"], ["13:00", "15:00"]],  # 周二
                    "2": [["09:00", "11:30"], ["13:00", "15:00"]],  # 周三
                    "3": [["09:00", "11:30"], ["13:00", "15:00"]],  # 周四
                    "4": [["09:00", "11:30"], ["13:00", "15:00"]]   # 周五
                },
                "us.stock": {
                    "0": [["09:00", "16:00"]],  # 周一
                    "1": [["09:00", "16:00"]],  # 周二
                    "2": [["09:00", "16:00"]],  # 周三
                    "3": [["09:00", "16:00"]],  # 周四
                    "4": [["09:00", "16:00"]]   # 周五
                },
                "hk.stock": {
                    "0": [["09:00", "12:00"], ["13:00", "16:00"]],  # 周一
                    "1": [["09:00", "12:00"], ["13:00", "16:00"]],  # 周二
                    "2": [["09:00", "12:00"], ["13:00", "16:00"]],  # 周三
                    "3": [["09:00", "12:00"], ["13:00", "16:00"]],  # 周四
                    "4": [["09:00", "12:00"], ["13:00", "16:00"]]   # 周五
                }
            }
        }
        
        aligner = CrossMarketDataAligner(aligner_config)
        
        # 对齐数据
        aligned_data = aligner.align(data_sources)
        
        # 打印对齐后的数据信息
        for source_name, df in aligned_data.items():
            logger.info(f"对齐后数据源 {source_name}: 形状 {df.shape}, 时区 {df.index.tz}")
        
        # 验证对齐结果
        if len(aligned_data) > 1:
            # 获取第一个数据源的索引
            first_source = next(iter(aligned_data.values()))
            first_index = first_source.index
            
            # 检查其他数据源是否与第一个数据源有相同的索引
            all_aligned = True
            for source_name, df in aligned_data.items():
                if not df.index.equals(first_index):
                    all_aligned = False
                    logger.warning(f"数据源 {source_name} 的索引与第一个数据源不同")
            
            if all_aligned:
                logger.info("所有数据源已成功对齐")
        
        return aligned_data
    except Exception as e:
        logger.error(f"跨市场数据对齐演示出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {}

def demo_timezone_alignment():
    """
    演示时区对齐
    """
    logger.info("=== 演示时区对齐 ===")
    
    try:
        # 生成模拟数据
        data_sources = generate_mock_data()
        
        # 打印原始数据信息
        for source_name, df in data_sources.items():
            logger.info(f"数据源 {source_name}: 形状 {df.shape}, 时区 {df.index.tz}")
        
        # 配置时区对齐器
        aligner_config = {
            "source_timezones": {
                "china.stock": "Asia/Shanghai",
                "us.stock": "America/New_York",
                "hk.stock": "Europe/London"
            },
            "target_timezone": "Asia/Shanghai"  # 添加目标时区配置
        }
        
        aligner = TimeZoneAligner(aligner_config)
        
        # 对齐数据
        aligned_data = aligner.align(data_sources)
        
        # 打印对齐后的数据信息
        for source_name, df in aligned_data.items():
            logger.info(f"对齐后数据源 {source_name}: 形状 {df.shape}, 时区 {df.index.tz}")
        
        return aligned_data
    except Exception as e:
        logger.error(f"时区对齐演示出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {}

def demo_async_alignment():
    """
    演示异步数据对齐
    """
    logger.info("=== 演示异步数据对齐 ===")
    
    try:
        # 生成模拟数据
        data_sources = generate_mock_data()
        
        # 为美股数据添加延迟
        df_us = data_sources["us.stock"]
        df_us.index = df_us.index + pd.Timedelta(seconds=30)  # 添加30秒延迟
        data_sources["us.stock"] = df_us
        
        # 为港股数据添加延迟
        df_hk = data_sources["hk.stock"]
        df_hk.index = df_hk.index + pd.Timedelta(seconds=60)  # 添加60秒延迟
        data_sources["hk.stock"] = df_hk
        
        # 打印原始数据信息
        for source_name, df in data_sources.items():
            if not df.empty:
                logger.info(f"数据源 {source_name}: 形状 {df.shape}, 第一个时间戳 {df.index[0]}")
            else:
                logger.info(f"数据源 {source_name} 为空")
        
        # 配置异步数据对齐器
        aligner_config = {
            "max_delay": 120,  # 最大延迟2分钟
            "interpolation_method": "linear",
            "window_size": 20
        }
        
        aligner = AsynchronousDataAligner(aligner_config)
        
        # 对齐数据
        aligned_data = aligner.align(data_sources)
        
        # 打印对齐后的数据信息
        for source_name, df in aligned_data.items():
            if not df.empty:
                logger.info(f"对齐后数据源 {source_name}: 形状 {df.shape}, 第一个时间戳 {df.index[0]}")
            else:
                logger.info(f"对齐后数据源 {source_name} 为空")
        
        return aligned_data
    except Exception as e:
        logger.error(f"异步数据对齐演示出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {}

def demo_multi_frequency_resampling():
    """
    演示多频率数据重采样
    """
    logger.info("=== 演示多频率数据重采样 ===")
    
    try:
        # 生成模拟数据
        data_sources = generate_mock_data()
        
        # 打印原始数据信息
        for source_name, df in data_sources.items():
            if len(df) > 3:  # 确保有足够的数据点来推断频率
                try:
                    freq = pd.infer_freq(df.index)
                    logger.info(f"数据源 {source_name}: 形状 {df.shape}, 频率 {freq}")
                except Exception:
                    logger.info(f"数据源 {source_name}: 形状 {df.shape}, 频率无法推断")
            else:
                logger.info(f"数据源 {source_name}: 形状 {df.shape}, 数据点不足以推断频率")
        
        # 配置多频率数据重采样器 - 上采样
        upsampler_config = {
            "target_freq": "1min",
            "method": "upsample",
            "interpolation": "linear"
        }
        
        upsampler = UpSampler(upsampler_config)
        
        # 对美股数据进行上采样
        us_upsampled = upsampler.resample(data_sources["us.stock"])
        try:
            freq = pd.infer_freq(us_upsampled.index)
            logger.info(f"美股上采样后: 形状 {us_upsampled.shape}, 频率 {freq}")
        except Exception:
            logger.info(f"美股上采样后: 形状 {us_upsampled.shape}, 频率无法推断")
        
        # 配置多频率数据重采样器 - 下采样
        downsampler_config = {
            "target_freq": "15min",
            "method": "downsample",
            "aggregation": "mean"
        }
        
        downsampler = DownSampler(downsampler_config)
        
        # 对A股数据进行下采样
        china_downsampled = downsampler.resample(data_sources["china.stock"])
        try:
            freq = pd.infer_freq(china_downsampled.index)
            logger.info(f"A股下采样后: 形状 {china_downsampled.shape}, 频率 {freq}")
        except Exception:
            logger.info(f"A股下采样后: 形状 {china_downsampled.shape}, 频率无法推断")
        
        # 配置自适应重采样器
        adaptive_config = {
            "method": "entropy",
            "min_freq": "1min",
            "max_freq": "30min"
        }
        
        adaptive_resampler = AdaptiveResampler(adaptive_config)
        
        # 对A股数据进行自适应重采样
        china_adaptive = adaptive_resampler.resample(data_sources["china.stock"])
        try:
            freq = pd.infer_freq(china_adaptive.index)
            logger.info(f"A股自适应重采样后: 形状 {china_adaptive.shape}, 频率 {freq}")
        except Exception:
            logger.info(f"A股自适应重采样后: 形状 {china_adaptive.shape}, 频率无法推断")
        
        return {
            "us_upsampled": us_upsampled,
            "china_downsampled": china_downsampled,
            "china_adaptive": china_adaptive
        }
    except Exception as e:
        logger.error(f"多频率数据重采样演示出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {}

def demo_reliability_scoring():
    """
    演示数据源可靠性评分
    """
    logger.info("=== 演示数据源可靠性评分 ===")
    
    try:
        # 生成模拟数据
        data_sources = generate_mock_data()
        
        # 打印原始数据信息
        for source_name, df in data_sources.items():
            missing_rate = df['price'].isna().mean()
            logger.info(f"数据源 {source_name}: 形状 {df.shape}, 缺失率 {missing_rate:.4f}")
        
        # 配置数据源可靠性评分器
        scorer_config = {
            "reference_source": "china.stock",
            "scorers": ["latency", "accuracy", "completeness", "consistency"],
            "weights": {
                "latency": 0.2,
                "accuracy": 0.3,
                "completeness": 0.3,
                "consistency": 0.2
            },
            "accuracy_threshold": {
                "mape": 0.05,
                "rmse": 0.1,
                "correlation": 0.7
            },
            "missing_threshold": 0.05,
            "coverage_threshold": 0.8,
            "expected_frequency": "5min"
        }
        
        scorer = DataSourceReliabilityScorer(scorer_config)
        
        # 评估各数据源的可靠性
        reference_data = data_sources["china.stock"]
        
        for source_name, df in data_sources.items():
            if df.empty:
                logger.warning(f"数据源 {source_name} 为空，跳过评分")
                continue
                
            score = scorer.score(source_name, df, reference_data)
            logger.info(f"数据源 {source_name} 的可靠性评分: {score:.4f}")
            
            # 获取详细评分
            detailed_scores = scorer.get_detailed_scores(source_name, df, reference_data)
            for metric, metric_score in detailed_scores.items():
                logger.info(f"  {metric}: {metric_score:.4f}")
        
        return scorer
    except Exception as e:
        logger.error(f"数据源可靠性评分演示出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def demo_data_fusion():
    """
    演示数据融合
    """
    logger.info("=== 演示数据融合 ===")
    
    try:
        # 生成模拟数据
        data_sources = generate_mock_data()
        
        # 打印原始数据信息
        for source_name, df in data_sources.items():
            logger.info(f"数据源 {source_name}: 形状 {df.shape}, 价格均值 {df['price'].mean():.4f}")
        
        # 配置数据融合引擎
        fusion_config = {
            "aligner": {
                "type": "timezone",
                # 确保配置与TimeZoneAligner的__init__方法参数一致
                "source_timezones": {
                    "china.stock": "Asia/Shanghai",
                    "us.stock": "America/New_York",
                    "hk.stock": "Europe/London"
                },
                "target_timezone": "UTC"
            },
            "resampler": {
                "target_freq": "5min",
                "method": "downsample",  # 明确指定方法
                "interpolation": "linear",
                "aggregation": "mean"
            },
            "reliability_scorer": {
                "reference_source": "china.stock",
                "scorers": ["accuracy", "completeness"],
                "weights": {
                    "accuracy": 0.6,
                    "completeness": 0.4
                }
            },
            "fusion": {
                "type": "weighted_average",
                "min_weight": 0.1
            }
        }
        
        engine = DataFusionEngine(fusion_config)
        
        # 融合数据
        fused_data = engine.fuse(data_sources)
        
        # 打印融合结果
        logger.info(f"融合后数据: 形状 {fused_data.shape}, 价格均值 {fused_data['price'].mean():.4f}")
        
        # 获取可靠性评分
        reliability_scores = engine.get_reliability_scores(data_sources)
        for source_name, scores in reliability_scores.items():
            logger.info(f"数据源 {source_name} 的可靠性评分: {scores}")
        
        # 使用卡尔曼滤波融合
        kalman_config = {
            "aligner": fusion_config["aligner"],
            "resampler": fusion_config["resampler"],
            "reliability_scorer": fusion_config["reliability_scorer"],
            "fusion": {
                "type": "kalman_filter",
                "process_noise": 0.01
            }
        }
        
        kalman_engine = DataFusionEngine(kalman_config)
        kalman_fused = kalman_engine.fuse(data_sources)
        logger.info(f"卡尔曼滤波融合后数据: 形状 {kalman_fused.shape}, 价格均值 {kalman_fused['price'].mean():.4f}")
        
        # 使用机器学习融合
        ml_config = {
            "aligner": fusion_config["aligner"],
            "resampler": fusion_config["resampler"],
            "reliability_scorer": fusion_config["reliability_scorer"],
            "fusion": {
                "type": "machine_learning",
                "model_type": "random_forest",
                "reference_source": "china.stock",
                "model_params": {
                    "n_estimators": 50,
                    "max_depth": 5
                }
            }
        }
        
        ml_engine = DataFusionEngine(ml_config)
        ml_fused = ml_engine.fuse(data_sources)
        logger.info(f"机器学习融合后数据: 形状 {ml_fused.shape}, 价格均值 {ml_fused['price'].mean():.4f}")
        
        return {
            "weighted_average": fused_data,
            "kalman_filter": kalman_fused,
            "machine_learning": ml_fused
        }
    except Exception as e:
        logger.error(f"数据融合演示出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {}

def main():
    """主函数"""
    logger.info("开始多源数据融合增强示例")
    
    try:
        # 演示跨市场数据对齐
        logger.info("开始演示跨市场数据对齐")
        aligned_data = demo_cross_market_alignment()
        logger.info("跨市场数据对齐完成")
        
        # 演示时区对齐
        logger.info("开始演示时区对齐")
        tz_aligned_data = demo_timezone_alignment()
        logger.info("时区对齐完成")
        
        # 演示异步数据对齐
        logger.info("开始演示异步数据对齐")
        async_aligned_data = demo_async_alignment()
        logger.info("异步数据对齐完成")
        
        # 演示多频率数据重采样
        logger.info("开始演示多频率数据重采样")
        resampled_data = demo_multi_frequency_resampling()
        logger.info("多频率数据重采样完成")
        
        # 演示数据源可靠性评分
        logger.info("开始演示数据源可靠性评分")
        reliability_scorer = demo_reliability_scoring()
        logger.info("数据源可靠性评分完成")
        
        # 演示数据融合
        logger.info("开始演示数据融合")
        fused_data = demo_data_fusion()
        logger.info("数据融合完成")
        
    except Exception as e:
        logger.error(f"示例运行出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info("多源数据融合增强示例完成")

if __name__ == "__main__":
    main()
