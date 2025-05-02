"""
数据流监控器
整合数据流适配器、处理器和异常处理器，提供统一的API
"""
import os
import logging
import json
import time
import threading
import queue
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Union, Optional, Any, Tuple, Callable, Generator, Set
from collections import defaultdict, deque

from .base import BaseDataStreamAdapter, BaseHighFrequencyProcessor, BaseStreamAnomalyHandler
from .adapter import MarketDataStreamAdapter
from .processor import HighFrequencyDataProcessor, TickDataProcessor, OrderBookProcessor
from .handler import StreamAnomalyHandler, DataContinuityHandler, DataRecoveryHandler

# 配置日志
logger = logging.getLogger(__name__)

class DataStreamMonitor:
    """
    数据流监控器
    整合数据流适配器、处理器和异常处理器，提供统一的API
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据流监控器
        
        参数:
            config: 配置字典，包含以下字段:
                - adapter: 适配器配置
                - processor: 处理器配置
                - handler: 异常处理器配置
                - monitor: 监控器配置
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.DataStreamMonitor")
        
        # 创建适配器
        adapter_config = config.get("adapter", {})
        self.adapter = self._create_adapter(adapter_config)
        
        # 创建处理器
        processor_config = config.get("processor", {})
        self.processor = self._create_processor(processor_config)
        
        # 创建异常处理器
        handler_config = config.get("handler", {})
        self.handler = self._create_handler(handler_config)
        
        # 监控器配置
        monitor_config = config.get("monitor", {})
        self.processing_interval = monitor_config.get("processing_interval_ms", 100) / 1000.0  # 转换为秒
        self.max_batch_size = monitor_config.get("max_batch_size", 100)
        self.auto_reconnect = monitor_config.get("auto_reconnect", True)
        self.reconnect_interval = monitor_config.get("reconnect_interval", 5.0)
        self.max_reconnect_attempts = monitor_config.get("max_reconnect_attempts", 10)
        
        # 监控状态
        self.running = False
        self.stop_event = threading.Event()
        self.reconnect_count = 0
        self.last_reconnect_time = 0
        
        # 统计信息
        self.statistics = {
            "received_count": 0,
            "processed_count": 0,
            "anomaly_count": 0,
            "start_time": None,
            "last_data_time": None,
            "reconnect_count": 0
        }
        
        # 回调函数
        self.callbacks = {
            "on_data": [],
            "on_processed": [],
            "on_anomaly": [],
            "on_reconnect": [],
            "on_error": []
        }
    
    def _create_adapter(self, config: Dict[str, Any]) -> BaseDataStreamAdapter:
        """
        创建数据流适配器
        
        参数:
            config: 适配器配置
            
        返回:
            数据流适配器
        """
        adapter_type = config.get("type", "market")
        
        if adapter_type == "market":
            return MarketDataStreamAdapter(config)
        elif adapter_type == "custom" and "class" in config:
            # 动态导入自定义适配器类
            try:
                module_path, class_name = config["class"].rsplit(".", 1)
                module = __import__(module_path, fromlist=[class_name])
                adapter_class = getattr(module, class_name)
                return adapter_class(config)
            except (ImportError, AttributeError) as e:
                self.logger.error(f"导入自定义适配器类失败: {e}")
                return MarketDataStreamAdapter(config)
        else:
            self.logger.warning(f"不支持的适配器类型: {adapter_type}，使用默认市场数据适配器")
            return MarketDataStreamAdapter(config)
    
    def _create_processor(self, config: Dict[str, Any]) -> BaseHighFrequencyProcessor:
        """
        创建高频数据处理器
        
        参数:
            config: 处理器配置
            
        返回:
            高频数据处理器
        """
        processor_type = config.get("type", "default")
        
        if processor_type == "default":
            return HighFrequencyDataProcessor(config)
        elif processor_type == "tick":
            return TickDataProcessor(config)
        elif processor_type == "orderbook":
            return OrderBookProcessor(config)
        elif processor_type == "custom" and "class" in config:
            # 动态导入自定义处理器类
            try:
                module_path, class_name = config["class"].rsplit(".", 1)
                module = __import__(module_path, fromlist=[class_name])
                processor_class = getattr(module, class_name)
                return processor_class(config)
            except (ImportError, AttributeError) as e:
                self.logger.error(f"导入自定义处理器类失败: {e}")
                return HighFrequencyDataProcessor(config)
        else:
            self.logger.warning(f"不支持的处理器类型: {processor_type}，使用默认高频数据处理器")
            return HighFrequencyDataProcessor(config)
    
    def _create_handler(self, config: Dict[str, Any]) -> BaseStreamAnomalyHandler:
        """
        创建数据流异常处理器
        
        参数:
            config: 异常处理器配置
            
        返回:
            数据流异常处理器
        """
        handler_type = config.get("type", "default")
        
        if handler_type == "default":
            return StreamAnomalyHandler(config)
        elif handler_type == "continuity":
            return DataContinuityHandler(config)
        elif handler_type == "recovery":
            return DataRecoveryHandler(config)
        elif handler_type == "custom" and "class" in config:
            # 动态导入自定义处理器类
            try:
                module_path, class_name = config["class"].rsplit(".", 1)
                module = __import__(module_path, fromlist=[class_name])
                handler_class = getattr(module, class_name)
                return handler_class(config)
            except (ImportError, AttributeError) as e:
                self.logger.error(f"导入自定义异常处理器类失败: {e}")
                return StreamAnomalyHandler(config)
        else:
            self.logger.warning(f"不支持的异常处理器类型: {handler_type}，使用默认数据流异常处理器")
            return StreamAnomalyHandler(config)
    
    def start(self) -> bool:
        """
        启动数据流监控
        
        返回:
            是否成功启动
        """
        if self.running:
            self.logger.warning("数据流监控器已经在运行")
            return True
        
        # 连接数据源
        if not self.adapter.connected:
            success = self.adapter.connect()
            if not success:
                self.logger.error("连接数据源失败")
                return False
        
        # 启动数据流
        success = self.adapter.start_streaming()
        if not success:
            self.logger.error("启动数据流失败")
            return False
        
        # 更新状态
        self.running = True
        self.stop_event.clear()
        self.statistics["start_time"] = datetime.now()
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_worker, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("数据流监控器已启动")
        return True
    
    def stop(self) -> bool:
        """
        停止数据流监控
        
        返回:
            是否成功停止
        """
        if not self.running:
            self.logger.warning("数据流监控器未在运行")
            return True
        
        # 停止数据流
        self.stop_event.set()
        success = self.adapter.stop_streaming()
        
        # 等待监控线程结束
        if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        # 更新状态
        self.running = False
        
        self.logger.info("数据流监控器已停止")
        return success
    
    def subscribe(self, topics: List[str]) -> bool:
        """
        订阅数据主题
        
        参数:
            topics: 要订阅的主题列表
            
        返回:
            订阅是否成功
        """
        if not self.adapter.connected:
            self.logger.warning("未连接到数据源，无法订阅")
            return False
        
        return self.adapter.subscribe(topics)
    
    def unsubscribe(self, topics: List[str]) -> bool:
        """
        取消订阅数据主题
        
        参数:
            topics: 要取消订阅的主题列表
            
        返回:
            取消订阅是否成功
        """
        if not self.adapter.connected:
            self.logger.warning("未连接到数据源，无法取消订阅")
            return False
        
        return self.adapter.unsubscribe(topics)
    
    def _monitor_worker(self):
        """监控工作线程"""
        batch = []
        last_process_time = time.time()
        
        while not self.stop_event.is_set():
            try:
                # 获取数据
                data = self.adapter.get_data(timeout=0.01)
                
                if data:
                    # 更新统计信息
                    self.statistics["received_count"] += 1
                    self.statistics["last_data_time"] = datetime.now()
                    
                    # 检测异常
                    is_anomaly, anomaly_type, details = self.handler.detect_anomaly(data)
                    
                    if is_anomaly:
                        # 更新统计信息
                        self.statistics["anomaly_count"] += 1
                        
                        # 处理异常
                        data = self.handler.handle_anomaly(anomaly_type, data, details)
                        
                        # 调用异常回调
                        for callback in self.callbacks["on_anomaly"]:
                            try:
                                callback(anomaly_type, data, details)
                            except Exception as e:
                                self.logger.error(f"异常回调函数执行失败: {e}")
                    
                    # 添加到批处理
                    batch.append(data)
                    
                    # 调用数据回调
                    for callback in self.callbacks["on_data"]:
                        try:
                            callback(data)
                        except Exception as e:
                            self.logger.error(f"数据回调函数执行失败: {e}")
                
                # 检查是否需要处理批次
                current_time = time.time()
                if (len(batch) >= self.max_batch_size or 
                    (current_time - last_process_time) >= self.processing_interval):
                    if batch:
                        # 处理批次
                        result = self.processor.process(batch)
                        
                        # 更新统计信息
                        self.statistics["processed_count"] += len(batch)
                        
                        # 调用处理回调
                        for callback in self.callbacks["on_processed"]:
                            try:
                                callback(result)
                            except Exception as e:
                                self.logger.error(f"处理回调函数执行失败: {e}")
                        
                        # 清空批次
                        batch = []
                    
                    # 更新最后处理时间
                    last_process_time = current_time
                
                # 检查连接状态
                if self.auto_reconnect and not self.adapter.connected:
                    current_time = time.time()
                    if (current_time - self.last_reconnect_time) >= self.reconnect_interval:
                        self.reconnect_count += 1
                        
                        if self.reconnect_count <= self.max_reconnect_attempts:
                            self.logger.info(f"尝试重新连接 (尝试 {self.reconnect_count}/{self.max_reconnect_attempts})")
                            
                            # 尝试重连
                            success = self.adapter.connect()
                            if success:
                                success = self.adapter.start_streaming()
                                
                                if success:
                                    self.logger.info("重新连接成功")
                                    self.statistics["reconnect_count"] += 1
                                    self.reconnect_count = 0
                                    
                                    # 调用重连回调
                                    for callback in self.callbacks["on_reconnect"]:
                                        try:
                                            callback()
                                        except Exception as e:
                                            self.logger.error(f"重连回调函数执行失败: {e}")
                            
                            self.last_reconnect_time = current_time
                        else:
                            self.logger.error(f"重连失败次数超过最大限制 ({self.max_reconnect_attempts})，停止重连")
                            self.stop_event.set()
            except Exception as e:
                self.logger.error(f"监控线程异常: {e}")
                
                # 调用错误回调
                for callback in self.callbacks["on_error"]:
                    try:
                        callback(e)
                    except Exception as e:
                        self.logger.error(f"错误回调函数执行失败: {e}")
                
                # 短暂等待后继续
                time.sleep(0.1)
        
        self.logger.info("监控线程结束")
    
    def register_callback(self, event_type: str, callback: Callable):
        """
        注册回调函数
        
        参数:
            event_type: 事件类型，支持'on_data'、'on_processed'、'on_anomaly'、'on_reconnect'、'on_error'
            callback: 回调函数
        """
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
            self.logger.info(f"注册 {event_type} 回调函数")
        else:
            self.logger.warning(f"不支持的事件类型: {event_type}")
    
    def unregister_callback(self, event_type: str, callback: Callable) -> bool:
        """
        取消注册回调函数
        
        参数:
            event_type: 事件类型
            callback: 回调函数
            
        返回:
            是否成功取消注册
        """
        if event_type in self.callbacks and callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)
            self.logger.info(f"取消注册 {event_type} 回调函数")
            return True
        else:
            self.logger.warning(f"未找到要取消注册的回调函数: {event_type}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        返回:
            统计信息字典
        """
        stats = self.statistics.copy()
        
        # 添加运行时间
        if stats["start_time"]:
            stats["running_time_seconds"] = (datetime.now() - stats["start_time"]).total_seconds()
        
        # 添加适配器状态
        stats["adapter_status"] = self.adapter.get_status()
        
        # 添加处理器状态
        stats["processor_status"] = self.processor.get_buffer_status()
        
        # 添加异常处理器统计
        if hasattr(self.handler, 'get_statistics'):
            stats["handler_statistics"] = self.handler.get_statistics()
        
        return stats
    
    def get_adapter(self) -> BaseDataStreamAdapter:
        """获取数据流适配器"""
        return self.adapter
    
    def get_processor(self) -> BaseHighFrequencyProcessor:
        """获取高频数据处理器"""
        return self.processor
    
    def get_handler(self) -> BaseStreamAnomalyHandler:
        """获取数据流异常处理器"""
        return self.handler
