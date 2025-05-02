"""
市场实时数据流接入适配器实现
支持WebSocket、RESTful API和本地文件等多种数据源
"""
import os
import logging
import json
import time
import threading
import queue
import requests
import websocket
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Union, Optional, Any, Tuple, Callable, Generator
from pathlib import Path

from .base import BaseDataStreamAdapter

# 配置日志
logger = logging.getLogger(__name__)

class MarketDataStreamAdapter(BaseDataStreamAdapter):
    """
    市场数据流适配器
    支持多种数据源的统一接口
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化市场数据流适配器
        
        参数:
            config: 配置字典，包含以下字段:
                - data_source: 数据源类型，支持'websocket'、'restful'、'file'
                - connection_params: 连接参数
                - retry_params: 重试参数，可选
                - auth_params: 认证参数，可选
        """
        super().__init__(config)
        self.data_source = config["data_source"]
        self.connection_params = config["connection_params"]
        self.retry_params = config.get("retry_params", {
            "max_retries": 3,
            "retry_interval": 5,
            "exponential_backoff": True
        })
        self.auth_params = config.get("auth_params", {})
        
        # 创建适当的适配器
        if self.data_source == "websocket":
            self.adapter = WebSocketDataAdapter(config)
        elif self.data_source == "restful":
            self.adapter = RESTfulDataAdapter(config)
        elif self.data_source == "file":
            self.adapter = FileDataAdapter(config)
        else:
            raise ValueError(f"不支持的数据源类型: {self.data_source}")
    
    def connect(self) -> bool:
        """
        连接到数据源
        
        返回:
            连接是否成功
        """
        success = self.adapter.connect()
        self.connected = success
        return success
    
    def disconnect(self) -> bool:
        """
        断开与数据源的连接
        
        返回:
            断开连接是否成功
        """
        success = self.adapter.disconnect()
        self.connected = not success
        return success
    
    def subscribe(self, topics: List[str]) -> bool:
        """
        订阅数据主题
        
        参数:
            topics: 要订阅的主题列表
            
        返回:
            订阅是否成功
        """
        return self.adapter.subscribe(topics)
    
    def unsubscribe(self, topics: List[str]) -> bool:
        """
        取消订阅数据主题
        
        参数:
            topics: 要取消订阅的主题列表
            
        返回:
            取消订阅是否成功
        """
        return self.adapter.unsubscribe(topics)
    
    def _receive_data(self) -> Generator[Dict[str, Any], None, None]:
        """
        接收数据的内部方法
        
        返回:
            数据生成器
        """
        yield from self.adapter._receive_data()


class WebSocketDataAdapter(BaseDataStreamAdapter):
    """
    WebSocket数据适配器
    通过WebSocket协议接收实时数据
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化WebSocket数据适配器
        
        参数:
            config: 配置字典，包含以下字段:
                - connection_params: 连接参数，包含url等
                - auth_params: 认证参数，可选
                - heartbeat_interval: 心跳间隔，单位秒，可选
        """
        super().__init__(config)
        self.url = self.connection_params.get("url")
        self.headers = self.connection_params.get("headers", {})
        self.heartbeat_interval = self.config.get("heartbeat_interval", 30)
        self.ws = None
        self.message_queue = queue.Queue()
        self.reconnect_count = 0
        self.max_reconnect = self.config.get("max_reconnect", 10)
        self.reconnect_interval = self.config.get("reconnect_interval", 5)
        self.last_heartbeat_time = time.time()
    
    def _validate_config(self):
        """验证配置是否合法"""
        super()._validate_config()
        if "url" not in self.connection_params:
            raise ValueError("WebSocket连接参数必须包含url")
    
    def connect(self) -> bool:
        """
        连接到WebSocket服务器
        
        返回:
            连接是否成功
        """
        try:
            # 创建WebSocket连接
            self.ws = websocket.WebSocketApp(
                self.url,
                header=self.headers,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            
            # 启动WebSocket连接线程
            self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            self.ws_thread.start()
            
            # 等待连接建立
            timeout = self.config.get("connection_timeout", 10)
            start_time = time.time()
            while not self.connected and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            # 启动心跳线程
            if self.connected:
                self.heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
                self.heartbeat_thread.start()
                self.logger.info(f"已连接到WebSocket服务器: {self.url}")
            else:
                self.logger.error(f"连接WebSocket服务器超时: {self.url}")
            
            return self.connected
        except Exception as e:
            self.logger.error(f"连接WebSocket服务器失败: {e}")
            return False
    
    def disconnect(self) -> bool:
        """
        断开与WebSocket服务器的连接
        
        返回:
            断开连接是否成功
        """
        try:
            if self.ws:
                self.ws.close()
                # 等待关闭完成
                timeout = self.config.get("disconnection_timeout", 5)
                start_time = time.time()
                while self.connected and time.time() - start_time < timeout:
                    time.sleep(0.1)
                
                self.logger.info(f"已断开与WebSocket服务器的连接: {self.url}")
            
            return not self.connected
        except Exception as e:
            self.logger.error(f"断开WebSocket服务器连接失败: {e}")
            return False
    
    def subscribe(self, topics: List[str]) -> bool:
        """
        订阅数据主题
        
        参数:
            topics: 要订阅的主题列表
            
        返回:
            订阅是否成功
        """
        if not self.connected or not self.ws:
            self.logger.error("未连接到WebSocket服务器，无法订阅")
            return False
        
        try:
            # 构建订阅消息
            subscribe_msg = {
                "type": "subscribe",
                "topics": topics
            }
            
            # 添加认证信息
            if self.auth_params:
                subscribe_msg.update(self.auth_params)
            
            # 发送订阅消息
            self.ws.send(json.dumps(subscribe_msg))
            self.logger.info(f"已发送订阅请求: {topics}")
            return True
        except Exception as e:
            self.logger.error(f"订阅失败: {e}")
            return False
    
    def unsubscribe(self, topics: List[str]) -> bool:
        """
        取消订阅数据主题
        
        参数:
            topics: 要取消订阅的主题列表
            
        返回:
            取消订阅是否成功
        """
        if not self.connected or not self.ws:
            self.logger.error("未连接到WebSocket服务器，无法取消订阅")
            return False
        
        try:
            # 构建取消订阅消息
            unsubscribe_msg = {
                "type": "unsubscribe",
                "topics": topics
            }
            
            # 添加认证信息
            if self.auth_params:
                unsubscribe_msg.update(self.auth_params)
            
            # 发送取消订阅消息
            self.ws.send(json.dumps(unsubscribe_msg))
            self.logger.info(f"已发送取消订阅请求: {topics}")
            return True
        except Exception as e:
            self.logger.error(f"取消订阅失败: {e}")
            return False
    
    def _receive_data(self) -> Generator[Dict[str, Any], None, None]:
        """
        接收数据的内部方法
        
        返回:
            数据生成器
        """
        while not self.stop_event.is_set():
            try:
                # 从消息队列中获取数据
                message = self.message_queue.get(timeout=0.1)
                
                # 处理消息
                if isinstance(message, dict):
                    # 添加时间戳
                    if "timestamp" not in message:
                        message["timestamp"] = datetime.now().isoformat()
                    
                    yield message
                else:
                    try:
                        # 尝试解析JSON
                        data = json.loads(message)
                        
                        # 添加时间戳
                        if "timestamp" not in data:
                            data["timestamp"] = datetime.now().isoformat()
                        
                        yield data
                    except json.JSONDecodeError:
                        self.logger.warning(f"无法解析消息为JSON: {message}")
            except queue.Empty:
                # 队列为空，继续等待
                continue
            except Exception as e:
                self.logger.error(f"接收数据异常: {e}")
                # 短暂等待后继续
                time.sleep(0.1)
    
    def _on_message(self, ws, message):
        """WebSocket消息回调"""
        try:
            self.message_queue.put(message)
        except Exception as e:
            self.logger.error(f"处理WebSocket消息失败: {e}")
    
    def _on_error(self, ws, error):
        """WebSocket错误回调"""
        self.logger.error(f"WebSocket错误: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket关闭回调"""
        self.connected = False
        self.logger.info(f"WebSocket连接已关闭: {close_status_code} {close_msg}")
        
        # 尝试重连
        if not self.stop_event.is_set() and self.reconnect_count < self.max_reconnect:
            self.reconnect_count += 1
            reconnect_interval = self.reconnect_interval * (2 ** (self.reconnect_count - 1)) if self.config.get("exponential_backoff", True) else self.reconnect_interval
            self.logger.info(f"将在 {reconnect_interval} 秒后尝试重连 (尝试 {self.reconnect_count}/{self.max_reconnect})")
            
            def reconnect():
                time.sleep(reconnect_interval)
                if not self.stop_event.is_set():
                    self.logger.info("尝试重新连接WebSocket服务器")
                    self.connect()
            
            threading.Thread(target=reconnect, daemon=True).start()
    
    def _on_open(self, ws):
        """WebSocket打开回调"""
        self.connected = True
        self.reconnect_count = 0
        self.logger.info("WebSocket连接已建立")
        
        # 如果有初始订阅主题，则订阅
        initial_topics = self.config.get("initial_topics", [])
        if initial_topics:
            self.subscribe(initial_topics)
    
    def _heartbeat_worker(self):
        """心跳线程"""
        while self.connected and not self.stop_event.is_set():
            try:
                current_time = time.time()
                if current_time - self.last_heartbeat_time >= self.heartbeat_interval:
                    # 发送心跳
                    heartbeat_msg = {"type": "ping"}
                    self.ws.send(json.dumps(heartbeat_msg))
                    self.last_heartbeat_time = current_time
                
                # 短暂等待
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"发送心跳失败: {e}")


class RESTfulDataAdapter(BaseDataStreamAdapter):
    """
    RESTful API数据适配器
    通过定期轮询RESTful API获取数据
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化RESTful API数据适配器
        
        参数:
            config: 配置字典，包含以下字段:
                - connection_params: 连接参数，包含base_url等
                - auth_params: 认证参数，可选
                - polling_interval: 轮询间隔，单位秒，可选
        """
        super().__init__(config)
        self.base_url = self.connection_params.get("base_url")
        self.headers = self.connection_params.get("headers", {})
        self.polling_interval = self.config.get("polling_interval", 1.0)
        self.session = None
        self.subscribed_topics = []
        self.last_poll_time = {}
    
    def _validate_config(self):
        """验证配置是否合法"""
        super()._validate_config()
        if "base_url" not in self.connection_params:
            raise ValueError("RESTful连接参数必须包含base_url")
    
    def connect(self) -> bool:
        """
        创建HTTP会话
        
        返回:
            连接是否成功
        """
        try:
            self.session = requests.Session()
            
            # 设置通用头信息
            self.session.headers.update(self.headers)
            
            # 设置认证信息
            if self.auth_params:
                auth_type = self.auth_params.get("type", "basic")
                if auth_type == "basic":
                    username = self.auth_params.get("username", "")
                    password = self.auth_params.get("password", "")
                    self.session.auth = (username, password)
                elif auth_type == "token":
                    token = self.auth_params.get("token", "")
                    self.session.headers.update({"Authorization": f"Bearer {token}"})
                elif auth_type == "api_key":
                    api_key = self.auth_params.get("api_key", "")
                    key_name = self.auth_params.get("key_name", "X-API-Key")
                    self.session.headers.update({key_name: api_key})
            
            self.connected = True
            self.logger.info(f"已创建RESTful API会话: {self.base_url}")
            return True
        except Exception as e:
            self.logger.error(f"创建RESTful API会话失败: {e}")
            return False
    
    def disconnect(self) -> bool:
        """
        关闭HTTP会话
        
        返回:
            断开连接是否成功
        """
        try:
            if self.session:
                self.session.close()
                self.session = None
            
            self.connected = False
            self.logger.info(f"已关闭RESTful API会话: {self.base_url}")
            return True
        except Exception as e:
            self.logger.error(f"关闭RESTful API会话失败: {e}")
            return False
    
    def subscribe(self, topics: List[str]) -> bool:
        """
        订阅数据主题
        
        参数:
            topics: 要订阅的主题列表，对应API端点
            
        返回:
            订阅是否成功
        """
        # 添加新主题到订阅列表
        for topic in topics:
            if topic not in self.subscribed_topics:
                self.subscribed_topics.append(topic)
                self.last_poll_time[topic] = 0
        
        self.logger.info(f"已订阅RESTful API主题: {topics}")
        return True
    
    def unsubscribe(self, topics: List[str]) -> bool:
        """
        取消订阅数据主题
        
        参数:
            topics: 要取消订阅的主题列表
            
        返回:
            取消订阅是否成功
        """
        # 从订阅列表中移除主题
        for topic in topics:
            if topic in self.subscribed_topics:
                self.subscribed_topics.remove(topic)
                if topic in self.last_poll_time:
                    del self.last_poll_time[topic]
        
        self.logger.info(f"已取消订阅RESTful API主题: {topics}")
        return True
    
    def _receive_data(self) -> Generator[Dict[str, Any], None, None]:
        """
        接收数据的内部方法
        
        返回:
            数据生成器
        """
        while not self.stop_event.is_set():
            current_time = time.time()
            
            # 轮询所有订阅的主题
            for topic in self.subscribed_topics:
                # 检查是否到达轮询间隔
                if current_time - self.last_poll_time.get(topic, 0) >= self.polling_interval:
                    try:
                        # 构建请求URL
                        url = f"{self.base_url.rstrip('/')}/{topic.lstrip('/')}"
                        
                        # 发送请求
                        response = self.session.get(url, timeout=self.config.get("request_timeout", 5))
                        response.raise_for_status()
                        
                        # 更新最后轮询时间
                        self.last_poll_time[topic] = current_time
                        
                        # 解析响应
                        data = response.json()
                        
                        # 添加元数据
                        if isinstance(data, dict):
                            data["topic"] = topic
                            data["timestamp"] = datetime.now().isoformat()
                            data["source"] = "restful"
                            yield data
                        elif isinstance(data, list):
                            # 如果是列表，则为每个项目添加元数据
                            for item in data:
                                if isinstance(item, dict):
                                    item["topic"] = topic
                                    item["timestamp"] = datetime.now().isoformat()
                                    item["source"] = "restful"
                                    yield item
                    except requests.RequestException as e:
                        self.logger.error(f"轮询主题 {topic} 失败: {e}")
                    except json.JSONDecodeError as e:
                        self.logger.error(f"解析主题 {topic} 的响应失败: {e}")
                    except Exception as e:
                        self.logger.error(f"处理主题 {topic} 时发生异常: {e}")
            
            # 等待一小段时间
            time.sleep(0.01)


class FileDataAdapter(BaseDataStreamAdapter):
    """
    文件数据适配器
    从本地文件读取数据，用于回测或模拟实时数据流
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化文件数据适配器
        
        参数:
            config: 配置字典，包含以下字段:
                - connection_params: 连接参数，包含file_path等
                - replay_speed: 回放速度倍数，可选
                - loop: 是否循环回放，可选
        """
        super().__init__(config)
        self.file_path = self.config["connection_params"].get("file_path")
        self.replay_speed = self.config.get("replay_speed", 1.0)
        self.loop = self.config.get("loop", False)
        self.file_format = self.config["connection_params"].get("file_format", "auto")
        self.subscribed_topics = []
        self.data = None
        self.current_index = 0
    
    def _validate_config(self):
        """验证配置是否合法"""
        super()._validate_config()
        if "file_path" not in self.config["connection_params"]:
            raise ValueError("文件连接参数必须包含file_path")
    
    def connect(self) -> bool:
        """
        加载文件数据
        
        返回:
            连接是否成功
        """
        try:
            file_path = self.file_path
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                self.logger.error(f"文件不存在: {file_path}")
                return False
            
            # 根据文件格式加载数据
            file_format = self.file_format
            if file_format == "auto":
                # 根据文件扩展名自动判断格式
                ext = os.path.splitext(file_path)[1].lower()
                if ext == ".csv":
                    file_format = "csv"
                elif ext in [".json", ".jsonl"]:
                    file_format = "json"
                elif ext in [".parquet", ".pq"]:
                    file_format = "parquet"
                elif ext == ".feather":
                    file_format = "feather"
                else:
                    self.logger.warning(f"无法自动判断文件格式: {file_path}，默认使用CSV格式")
                    file_format = "csv"
            
            # 加载数据
            if file_format == "csv":
                self.data = pd.read_csv(file_path)
            elif file_format == "json":
                if os.path.getsize(file_path) > 10 * 1024 * 1024:  # 大于10MB的文件
                    # 对于大文件，逐行读取
                    self.data = []
                    with open(file_path, 'r') as f:
                        for line in f:
                            try:
                                self.data.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
                else:
                    # 对于小文件，一次性读取
                    with open(file_path, 'r') as f:
                        content = f.read()
                        try:
                            # 尝试作为单个JSON对象读取
                            self.data = json.loads(content)
                            if isinstance(self.data, dict):
                                self.data = [self.data]
                            elif not isinstance(self.data, list):
                                self.logger.error(f"JSON文件格式不正确: {file_path}")
                                return False
                        except json.JSONDecodeError:
                            # 尝试作为JSON Lines读取
                            self.data = []
                            for line in content.splitlines():
                                try:
                                    if line.strip():
                                        self.data.append(json.loads(line))
                                except json.JSONDecodeError:
                                    pass
            elif file_format == "parquet":
                self.data = pd.read_parquet(file_path)
            elif file_format == "feather":
                self.data = pd.read_feather(file_path)
            else:
                self.logger.error(f"不支持的文件格式: {file_format}")
                return False
            
            # 如果数据是DataFrame，转换为字典列表
            if isinstance(self.data, pd.DataFrame):
                self.data = self.data.to_dict('records')
            
            # 检查数据是否为空
            if not self.data:
                self.logger.error(f"文件中没有数据: {file_path}")
                return False
            
            self.connected = True
            self.current_index = 0
            self.logger.info(f"已加载文件数据: {file_path}, 数据条数: {len(self.data)}")
            return True
        except Exception as e:
            self.logger.error(f"加载文件数据失败: {e}")
            return False
    
    def disconnect(self) -> bool:
        """
        释放文件数据
        
        返回:
            断开连接是否成功
        """
        self.data = None
        self.connected = False
        self.logger.info("已释放文件数据")
        return True
    
    def subscribe(self, topics: List[str]) -> bool:
        """
        订阅数据主题
        
        参数:
            topics: 要订阅的主题列表，用于过滤数据
            
        返回:
            订阅是否成功
        """
        # 添加新主题到订阅列表
        for topic in topics:
            if topic not in self.subscribed_topics:
                self.subscribed_topics.append(topic)
        
        self.logger.info(f"已订阅文件数据主题: {topics}")
        return True
    
    def unsubscribe(self, topics: List[str]) -> bool:
        """
        取消订阅数据主题
        
        参数:
            topics: 要取消订阅的主题列表
            
        返回:
            取消订阅是否成功
        """
        # 从订阅列表中移除主题
        for topic in topics:
            if topic in self.subscribed_topics:
                self.subscribed_topics.remove(topic)
        
        self.logger.info(f"已取消订阅文件数据主题: {topics}")
        return True
    
    def _receive_data(self) -> Generator[Dict[str, Any], None, None]:
        """
        接收数据的内部方法
        
        返回:
            数据生成器
        """
        if not self.data:
            self.logger.error("未加载文件数据")
            return
        
        # 获取数据中的时间戳字段
        timestamp_field = self.config["connection_params"].get("timestamp_field", "timestamp")
        
        # 记录开始时间
        start_time = time.time()
        first_data_time = None
        
        while not self.stop_event.is_set():
            if self.current_index >= len(self.data):
                if self.loop:
                    # 循环回放
                    self.current_index = 0
                    self.logger.info("文件数据回放完成，重新开始")
                    # 重置开始时间
                    start_time = time.time()
                    first_data_time = None
                else:
                    # 播放完成
                    self.logger.info("文件数据回放完成")
                    break
            
            # 获取当前数据
            data_item = self.data[self.current_index]
            self.current_index += 1
            
            # 如果有订阅主题，则过滤数据
            if self.subscribed_topics:
                # 检查数据是否包含主题字段
                topic_field = self.config["connection_params"].get("topic_field", "topic")
                if topic_field in data_item:
                    topic = data_item[topic_field]
                    if topic not in self.subscribed_topics:
                        continue
            
            # 控制回放速度
            if self.replay_speed > 0:
                # 获取数据时间戳
                if timestamp_field in data_item:
                    try:
                        # 尝试解析时间戳
                        data_time = pd.to_datetime(data_item[timestamp_field])
                        data_time = data_time.timestamp()
                        
                        # 记录第一条数据的时间
                        if first_data_time is None:
                            first_data_time = data_time
                        
                        # 计算应该等待的时间
                        elapsed_data_time = data_time - first_data_time
                        elapsed_real_time = (time.time() - start_time) * self.replay_speed
                        
                        # 如果实际时间小于数据时间，则等待
                        if elapsed_real_time < elapsed_data_time:
                            wait_time = (elapsed_data_time - elapsed_real_time) / self.replay_speed
                            time.sleep(max(0, wait_time))
                    except (ValueError, TypeError):
                        # 时间戳解析失败，不等待
                        pass
            
            # 添加元数据
            data_item["source"] = "file"
            if "timestamp" not in data_item:
                data_item["timestamp"] = datetime.now().isoformat()
            
            yield data_item
