"""
实时数据流接入系统基类定义
包含数据流适配器、高频数据处理器和数据流异常处理器的基类
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Union, Optional, Any, Tuple, Callable, Generator
import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime
import json
from pathlib import Path
import time
import threading
import queue

# 配置日志
logger = logging.getLogger(__name__)

class BaseDataStreamAdapter(ABC):
    """
    数据流适配器基类
    负责连接到数据源并接收实时数据流
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据流适配器
        
        参数:
            config: 配置字典，包含连接参数和数据源信息
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.connected = False
        self.data_queue = queue.Queue(maxsize=config.get("queue_size", 10000))
        self.stop_event = threading.Event()
        self._validate_config()
    
    def _validate_config(self):
        """验证配置是否合法"""
        required_keys = ["data_source", "connection_params"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"配置缺少必要参数: {key}")
    
    @abstractmethod
    def connect(self) -> bool:
        """
        连接到数据源
        
        返回:
            连接是否成功
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        断开与数据源的连接
        
        返回:
            断开连接是否成功
        """
        pass
    
    @abstractmethod
    def subscribe(self, topics: List[str]) -> bool:
        """
        订阅数据主题
        
        参数:
            topics: 要订阅的主题列表
            
        返回:
            订阅是否成功
        """
        pass
    
    @abstractmethod
    def unsubscribe(self, topics: List[str]) -> bool:
        """
        取消订阅数据主题
        
        参数:
            topics: 要取消订阅的主题列表
            
        返回:
            取消订阅是否成功
        """
        pass
    
    @abstractmethod
    def _receive_data(self) -> Generator[Dict[str, Any], None, None]:
        """
        接收数据的内部方法
        
        返回:
            数据生成器
        """
        pass
    
    def start_streaming(self):
        """启动数据流接收线程"""
        if not self.connected:
            success = self.connect()
            if not success:
                self.logger.error("无法连接到数据源，启动数据流失败")
                return False
        
        self.stop_event.clear()
        self.streaming_thread = threading.Thread(target=self._streaming_worker, daemon=True)
        self.streaming_thread.start()
        self.logger.info("数据流接收线程已启动")
        return True
    
    def stop_streaming(self):
        """停止数据流接收线程"""
        self.stop_event.set()
        if hasattr(self, 'streaming_thread') and self.streaming_thread.is_alive():
            self.streaming_thread.join(timeout=5.0)
            self.logger.info("数据流接收线程已停止")
        
        if self.connected:
            self.disconnect()
        
        return True
    
    def _streaming_worker(self):
        """数据流接收工作线程"""
        try:
            for data in self._receive_data():
                if self.stop_event.is_set():
                    break
                
                try:
                    # 将数据放入队列，如果队列已满则等待
                    self.data_queue.put(data, timeout=1.0)
                except queue.Full:
                    self.logger.warning("数据队列已满，丢弃数据")
        except Exception as e:
            self.logger.error(f"数据流接收异常: {e}")
        finally:
            self.logger.info("数据流接收线程结束")
    
    def get_data(self, timeout: float = 0.1) -> Optional[Dict[str, Any]]:
        """
        从队列中获取数据
        
        参数:
            timeout: 超时时间，单位秒
            
        返回:
            数据字典，如果队列为空则返回None
        """
        try:
            return self.data_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取适配器状态
        
        返回:
            状态字典
        """
        return {
            "connected": self.connected,
            "queue_size": self.data_queue.qsize(),
            "queue_full": self.data_queue.full(),
            "streaming_active": hasattr(self, 'streaming_thread') and self.streaming_thread.is_alive()
        }


class BaseHighFrequencyProcessor(ABC):
    """
    高频数据处理器基类
    负责处理毫秒级高频数据
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化高频数据处理器
        
        参数:
            config: 配置字典，包含处理参数
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.buffer = []
        self.buffer_size = config.get("buffer_size", 1000)
        self.processing_interval = config.get("processing_interval_ms", 100) / 1000.0  # 转换为秒
        self.last_process_time = time.time()
        self._validate_config()
    
    def _validate_config(self):
        """验证配置是否合法"""
        if "processing_interval_ms" in self.config and self.config["processing_interval_ms"] < 1:
            raise ValueError("处理间隔必须大于等于1毫秒")
    
    @abstractmethod
    def process(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        处理高频数据
        
        参数:
            data: 单条数据或数据列表
            
        返回:
            处理结果
        """
        pass
    
    def add_to_buffer(self, data: Dict[str, Any]):
        """
        将数据添加到缓冲区
        
        参数:
            data: 数据字典
        """
        self.buffer.append(data)
        
        # 如果缓冲区已满或达到处理间隔，则处理数据
        current_time = time.time()
        if (len(self.buffer) >= self.buffer_size or 
            (current_time - self.last_process_time) >= self.processing_interval):
            self.process_buffer()
    
    def process_buffer(self) -> Optional[Dict[str, Any]]:
        """
        处理缓冲区中的数据
        
        返回:
            处理结果，如果缓冲区为空则返回None
        """
        if not self.buffer:
            return None
        
        # 复制缓冲区数据并清空缓冲区
        buffer_copy = self.buffer.copy()
        self.buffer = []
        
        # 更新最后处理时间
        self.last_process_time = time.time()
        
        # 处理数据
        return self.process(buffer_copy)
    
    def get_buffer_status(self) -> Dict[str, Any]:
        """
        获取缓冲区状态
        
        返回:
            状态字典
        """
        return {
            "buffer_size": len(self.buffer),
            "buffer_capacity": self.buffer_size,
            "buffer_usage": len(self.buffer) / self.buffer_size if self.buffer_size > 0 else 0,
            "last_process_time": self.last_process_time,
            "time_since_last_process": time.time() - self.last_process_time
        }


class BaseStreamAnomalyHandler(ABC):
    """
    数据流异常处理器基类
    负责检测和处理数据流中的异常
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据流异常处理器
        
        参数:
            config: 配置字典，包含异常处理参数
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.handlers = {}
        self._validate_config()
    
    def _validate_config(self):
        """验证配置是否合法"""
        pass
    
    @abstractmethod
    def detect_anomaly(self, data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        检测数据流异常
        
        参数:
            data: 数据字典
            
        返回:
            (是否异常, 异常类型, 异常详情)
        """
        pass
    
    @abstractmethod
    def handle_anomaly(self, anomaly_type: str, data: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理数据流异常
        
        参数:
            anomaly_type: 异常类型
            data: 原始数据
            details: 异常详情
            
        返回:
            处理后的数据
        """
        pass
    
    def register_handler(self, anomaly_type: str, handler: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]):
        """
        注册异常处理函数
        
        参数:
            anomaly_type: 异常类型
            handler: 处理函数，接收(data, details)参数，返回处理后的数据
        """
        self.handlers[anomaly_type] = handler
        self.logger.info(f"注册异常处理函数: {anomaly_type}")
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理数据，检测并处理异常
        
        参数:
            data: 数据字典
            
        返回:
            处理后的数据
        """
        # 检测异常
        is_anomaly, anomaly_type, details = self.detect_anomaly(data)
        
        if is_anomaly:
            self.logger.warning(f"检测到异常: {anomaly_type}, 详情: {details}")
            
            # 使用注册的处理函数处理异常
            if anomaly_type in self.handlers:
                return self.handlers[anomaly_type](data, details)
            
            # 使用默认处理方法
            return self.handle_anomaly(anomaly_type, data, details)
        
        return data
