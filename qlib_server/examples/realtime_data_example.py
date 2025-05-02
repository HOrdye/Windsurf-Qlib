"""
实时数据流接入示例
演示如何使用市场实时数据流适配器、高频数据处理和数据流异常处理
"""
import os
import sys
import time
import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入实时数据流模块
from data.realtime import (
    MarketDataStreamAdapter,
    HighFrequencyDataProcessor,
    TickDataProcessor,
    OrderBookProcessor,
    StreamAnomalyHandler,
    DataContinuityHandler,
    DataRecoveryHandler,
    DataStreamMonitor
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def on_data_callback(data):
    """数据回调函数"""
    logger.debug(f"收到数据: {data.get('timestamp')}, {data.get('instrument')}")

def on_processed_callback(result):
    """处理结果回调函数"""
    logger.info(f"处理结果: {result.get('status')}, 总数: {result.get('total_count')}")
    
    # 打印每个标的物的处理结果
    for instrument, info in result.get('results', {}).items():
        logger.info(f"  {instrument}: {info}")

def on_anomaly_callback(anomaly_type, data, details):
    """异常回调函数"""
    logger.warning(f"检测到异常: {anomaly_type}, 详情: {details}")

def main():
    """主函数"""
    logger.info("开始实时数据流接入示例")
    
    # 创建示例数据目录
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../mock_data")
    os.makedirs(data_dir, exist_ok=True)
    
    # 生成示例数据文件
    csv_file = os.path.join(data_dir, "market_data.csv")
    if not os.path.exists(csv_file):
        logger.info("生成示例数据文件")
        generate_sample_data(csv_file)
    
    # 配置数据流适配器
    adapter_config = {
        "type": "market",
        "data_source": "file",
        "connection_params": {
            "file_path": csv_file,
            "file_format": "csv",
            "timestamp_field": "timestamp",
            "topic_field": "instrument"
        },
        "replay_speed": 10.0,  # 10倍速回放
        "loop": True  # 循环回放
    }
    
    # 配置高频数据处理器
    processor_config = {
        "type": "tick",
        "buffer_size": 1000,
        "processing_interval_ms": 100,
        "time_field": "timestamp",
        "instrument_field": "instrument",
        "price_field": "price",
        "volume_field": "volume",
        "window_size": 100
    }
    
    # 配置数据流异常处理器
    handler_config = {
        "type": "continuity",
        "time_field": "timestamp",
        "instrument_field": "instrument",
        "expected_interval_ms": 1000,
        "max_gap_ms": 5000,
        "interpolation_method": "linear",
        "auto_fill_gaps": True
    }
    
    # 配置数据流监控器
    monitor_config = {
        "adapter": adapter_config,
        "processor": processor_config,
        "handler": handler_config,
        "monitor": {
            "processing_interval_ms": 500,
            "max_batch_size": 100,
            "auto_reconnect": True,
            "reconnect_interval": 5.0,
            "max_reconnect_attempts": 3
        }
    }
    
    # 创建数据流监控器
    monitor = DataStreamMonitor(monitor_config)
    
    # 注册回调函数
    monitor.register_callback("on_data", on_data_callback)
    monitor.register_callback("on_processed", on_processed_callback)
    monitor.register_callback("on_anomaly", on_anomaly_callback)
    
    # 启动监控
    success = monitor.start()
    if not success:
        logger.error("启动数据流监控失败")
        return
    
    # 订阅数据主题
    monitor.subscribe(["AAPL", "MSFT", "GOOGL"])
    
    try:
        # 运行一段时间
        logger.info("数据流监控已启动，按Ctrl+C停止")
        
        # 每隔5秒打印统计信息
        for i in range(12):  # 运行60秒
            time.sleep(5)
            stats = monitor.get_statistics()
            logger.info(f"统计信息: 接收 {stats['received_count']}, 处理 {stats['processed_count']}, 异常 {stats['anomaly_count']}")
            
            # 打印处理器状态
            processor_status = stats.get('processor_status', {})
            logger.info(f"处理器状态: 缓冲区使用率 {processor_status.get('buffer_usage', 0):.2%}")
            
            # 每20秒模拟一次断连
            if i > 0 and i % 4 == 0:
                logger.info("模拟断连...")
                # 获取恢复处理器
                if isinstance(monitor.get_handler(), DataRecoveryHandler):
                    recovery_handler = monitor.get_handler()
                    recovery_handler.notify_disconnect("AAPL")
    except KeyboardInterrupt:
        logger.info("用户中断")
    finally:
        # 停止监控
        monitor.stop()
        logger.info("数据流监控已停止")
    
    logger.info("示例完成")

def generate_sample_data(file_path):
    """生成示例数据"""
    # 生成时间序列
    start_time = datetime.now()
    timestamps = [start_time + timedelta(seconds=i) for i in range(3600)]  # 1小时数据，每秒一条
    
    # 生成标的物列表
    instruments = ["AAPL", "MSFT", "GOOGL", "AMZN", "FB"]
    
    # 生成价格和成交量
    data = []
    for instrument in instruments:
        # 基础价格
        base_price = np.random.uniform(100, 500)
        
        # 价格序列
        prices = [base_price]
        for i in range(1, len(timestamps)):
            # 添加随机波动
            price_change = np.random.normal(0, 0.1)
            # 添加趋势
            trend = 0.01 * np.sin(i / 1800 * np.pi)
            # 新价格
            new_price = max(0.01, prices[-1] * (1 + price_change + trend))
            prices.append(new_price)
        
        # 成交量序列
        volumes = []
        for i in range(len(timestamps)):
            # 基础成交量
            base_volume = np.random.poisson(100)
            # 添加时间模式（开盘和收盘成交量较大）
            hour = (start_time.hour + i // 3600) % 24
            minute = (start_time.minute + (i % 3600) // 60) % 60
            time_factor = 1.0
            if (hour == 9 and minute >= 30) or (hour == 15 and minute >= 30):
                time_factor = 2.0
            # 最终成交量
            volume = int(base_volume * time_factor)
            volumes.append(volume)
        
        # 添加到数据集
        for i in range(len(timestamps)):
            data.append({
                "timestamp": timestamps[i].isoformat(),
                "instrument": instrument,
                "price": prices[i],
                "volume": volumes[i],
                "bid": prices[i] * 0.999,
                "ask": prices[i] * 1.001,
                "bid_size": int(volumes[i] * 0.6),
                "ask_size": int(volumes[i] * 0.4)
            })
    
    # 转换为DataFrame并按时间排序
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")
    
    # 保存到CSV文件
    df.to_csv(file_path, index=False)
    logger.info(f"生成示例数据文件: {file_path}, 数据条数: {len(df)}")

if __name__ == "__main__":
    main()
