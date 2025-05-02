"""
数据质量监控系统使用示例
展示如何使用数据质量监控系统的各个组件
"""
import os
import sys
import pandas as pd
import numpy as np
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import warnings

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入数据质量监控组件
from data.quality.monitor import DataQualityMonitor
from data.quality.anomaly_detector import StatisticalAnomalyDetector
from data.quality.text_image_detector import TextAnomalyDetector, ImageAnomalyDetector
from data.quality.missing_value_handler import BasicMissingValueHandler, InterpolationMissingValueHandler
from data.quality.multimodal_handler import MultiModalMissingValueHandler
from data.quality.version_control import DataVersionControl
from data.quality.report_generator import DataQualityReportGenerator

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_sample_data(rows=1000, missing_ratio=0.05, anomaly_ratio=0.02):
    """
    创建示例数据
    
    参数:
        rows: 行数
        missing_ratio: 缺失值比例
        anomaly_ratio: 异常值比例
        
    返回:
        示例数据框
    """
    # 设置随机种子
    np.random.seed(42)
    
    # 创建日期索引
    dates = pd.date_range(start='2022-01-01', periods=rows, freq='D')
    
    # 创建股票代码
    stocks = ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'META']
    
    # 创建多级索引
    index = pd.MultiIndex.from_product([stocks, dates], names=['instrument', 'datetime'])
    
    # 创建数据框
    data = pd.DataFrame(index=index)
    
    # 添加特征
    # 价格特征
    data['open'] = np.random.normal(100, 10, len(data))
    data['high'] = data['open'] * (1 + np.random.uniform(0, 0.05, len(data)))
    data['low'] = data['open'] * (1 - np.random.uniform(0, 0.05, len(data)))
    data['close'] = data['open'] * (1 + np.random.normal(0, 0.02, len(data)))
    data['volume'] = np.random.randint(1000000, 10000000, len(data))
    
    # 技术指标
    data['ma5'] = data.groupby(level=0)['close'].transform(lambda x: x.rolling(5).mean())
    data['ma10'] = data.groupby(level=0)['close'].transform(lambda x: x.rolling(10).mean())
    data['ma20'] = data.groupby(level=0)['close'].transform(lambda x: x.rolling(20).mean())
    data['rsi'] = np.random.uniform(0, 100, len(data))
    data['volatility'] = np.random.uniform(0, 0.05, len(data))
    
    # 基本面指标
    data['pe_ratio'] = np.random.uniform(10, 30, len(data))
    data['pb_ratio'] = np.random.uniform(1, 5, len(data))
    data['dividend_yield'] = np.random.uniform(0, 0.05, len(data))
    data['market_cap'] = np.random.uniform(1e9, 1e12, len(data))
    data['sector'] = np.random.choice(['Technology', 'Finance', 'Healthcare', 'Consumer', 'Energy'], len(data))
    
    # 添加缺失值
    for col in data.columns:
        if col != 'sector':  # 不在类别列中添加缺失值
            mask = np.random.random(len(data)) < missing_ratio
            data.loc[mask, col] = np.nan
    
    # 添加异常值
    for col in ['open', 'high', 'low', 'close', 'volume', 'pe_ratio', 'pb_ratio']:
        mask = np.random.random(len(data)) < anomaly_ratio
        if col == 'volume':
            data.loc[mask, col] = data.loc[mask, col] * 10  # 成交量异常
        else:
            data.loc[mask, col] = data.loc[mask, col] * (1 + np.random.choice([-1, 1]) * np.random.uniform(0.5, 1))  # 价格异常
    
    return data


def create_sample_text_data(data):
    """
    创建示例文本数据
    
    参数:
        data: 数据框
        
    返回:
        文本数据字典
    """
    # 创建文本数据字典
    text_data = {}
    
    # 新闻标题模板
    news_templates = [
        "{company} 宣布 Q{quarter} 财报，{performance}预期",
        "{company} 推出新产品，分析师{opinion}",
        "{company} {action}并购交易，市场反应{reaction}",
        "{company} CEO {statement}公司未来发展",
        "{company} 股价{movement}，{reason}"
    ]
    
    # 填充模板的词汇
    companies = {
        'AAPL': '苹果',
        'MSFT': '微软',
        'GOOG': '谷歌',
        'AMZN': '亚马逊',
        'META': 'Meta'
    }
    
    quarters = ['1', '2', '3', '4']
    performances = ['超出', '符合', '低于']
    opinions = ['看好', '持中立态度', '表示担忧']
    actions = ['完成', '取消', '推进']
    reactions = ['积极', '谨慎', '消极']
    statements = ['乐观评价', '谨慎展望', '详细分析']
    movements = ['上涨', '下跌', '震荡']
    reasons = ['因市场情绪改善', '受行业政策影响', '由于竞争加剧']
    
    # 为每个股票的每一天生成1-3条新闻
    for idx in data.index:
        instrument, dt = idx
        if isinstance(dt, pd.Timestamp):
            dt = dt.strftime("%Y%m%d")
        
        key = f"{instrument}_{dt}"
        
        # 随机生成1-3条新闻
        num_news = np.random.randint(1, 4)
        news_list = []
        
        for _ in range(num_news):
            template = np.random.choice(news_templates)
            company = companies.get(instrument, instrument)
            quarter = np.random.choice(quarters)
            performance = np.random.choice(performances)
            opinion = np.random.choice(opinions)
            action = np.random.choice(actions)
            reaction = np.random.choice(reactions)
            statement = np.random.choice(statements)
            movement = np.random.choice(movements)
            reason = np.random.choice(reasons)
            
            news = template.format(
                company=company,
                quarter=quarter,
                performance=performance,
                opinion=opinion,
                action=action,
                reaction=reaction,
                statement=statement,
                movement=movement,
                reason=reason
            )
            
            news_list.append(news)
        
        text_data[key] = news_list
    
    return text_data


def main():
    """主函数"""
    logger.info("开始数据质量监控示例")
    
    # 创建示例数据
    logger.info("创建示例数据")
    data = create_sample_data(rows=100)
    text_data = create_sample_text_data(data)
    
    # 创建数据质量监控器
    logger.info("创建数据质量监控器")
    
    monitor_config = {
        "name": "stock_data_monitor",
        "description": "股票数据质量监控",
        "data_path": os.path.join(os.path.dirname(__file__), "../data"),
        "output_dir": "reports",
        # 配置异常检测器
        "anomaly_detectors": [
            {
                "type": "statistical",
                "method": "z_score",
                "threshold": 3.0,
                "target_columns": ["open", "high", "low", "close", "volume", "pe_ratio", "pb_ratio"]
            },
            {
                "type": "text",
                "method": "length",
                "threshold": 2.0
            }
        ],
        # 配置缺失值处理器
        "missing_value_handlers": [
            {
                "type": "interpolation",
                "method": "interpolate",
                "interpolation_method": "linear",
                "target_columns": ["open", "high", "low", "close", "volume", "ma5", "ma10", "ma20"]
            },
            {
                "type": "multimodal",
                "method": "correlation",
                "target_columns": ["rsi", "volatility", "pe_ratio", "pb_ratio", "dividend_yield", "market_cap"],
                "auxiliary_columns": ["open", "high", "low", "close", "volume", "ma5", "ma10", "ma20"]
            }
        ],
        # 配置版本控制系统
        "version_control": {
            "type": "basic",
            "storage_path": os.path.join(os.path.dirname(__file__), "../data/versions"),
            "max_versions": 5
        },
        # 配置报告生成器
        "report_generators": [
            {
                "type": "quality",
                "report_type": "html",
                "output_path": os.path.join(os.path.dirname(__file__), "../data/reports"),
                "include_plots": True
            }
        ]
    }
    
    # 创建数据质量监控器
    monitor = DataQualityMonitor(config=monitor_config)
    
    # 运行数据质量监控
    logger.info("运行数据质量监控")
    result = monitor.monitor_data(data, {"text_data": text_data})
    
    # 输出结果
    logger.info(f"数据质量监控完成，报告路径: {result['report_path']}")
    logger.info(f"检测到的异常数量: {len(result.get('anomalies', {}).get('anomalies', []))}")
    logger.info(f"处理的缺失值数量: {result.get('missing_values_filled', 0)}")
    logger.info(f"数据版本ID: {result.get('version_id', '')}")
    
    # 加载保存的版本
    logger.info("加载保存的版本")
    try:
        loaded_data, metadata = monitor.version_control.load_version("stock_data")
        logger.info(f"加载的数据形状: {loaded_data.shape}")
        logger.info(f"版本元数据: {metadata.get('version_id')}")
        
        # 列出所有版本
        logger.info("列出所有版本")
        versions = monitor.version_control.list_versions("stock_data")
        for v in versions:
            logger.info(f"版本: {v['version_id']}, 时间: {v['timestamp']}, 行数: {v['rows']}")
    except Exception as e:
        logger.error(f"版本操作失败: {e}")
    
    logger.info("示例完成")


if __name__ == "__main__":
    main()
