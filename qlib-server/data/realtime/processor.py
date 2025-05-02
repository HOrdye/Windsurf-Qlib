"""
高频数据处理模块
支持毫秒级数据处理、行情数据聚合和订单簿重建
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
import heapq

from .base import BaseHighFrequencyProcessor

# 配置日志
logger = logging.getLogger(__name__)

class HighFrequencyDataProcessor(BaseHighFrequencyProcessor):
    """
    高频数据处理器
    处理毫秒级高频数据，支持数据聚合和异常检测
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化高频数据处理器
        
        参数:
            config: 配置字典，包含以下字段:
                - buffer_size: 缓冲区大小，默认1000
                - processing_interval_ms: 处理间隔，单位毫秒，默认100
                - time_field: 时间戳字段名，默认'timestamp'
                - instrument_field: 标的物字段名，默认'instrument'
                - aggregation: 聚合配置，可选
        """
        super().__init__(config)
        self.time_field = config.get("time_field", "timestamp")
        self.instrument_field = config.get("instrument_field", "instrument")
        self.aggregation = config.get("aggregation", {
            "enabled": False,
            "interval_ms": 1000,  # 1秒
            "fields": []
        })
        self.last_data_time = {}  # 记录每个标的物的最后数据时间
        self.statistics = {
            "processed_count": 0,
            "anomaly_count": 0,
            "latency_ms": []
        }
    
    def process(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        处理高频数据
        
        参数:
            data: 单条数据或数据列表
            
        返回:
            处理结果
        """
        # 确保数据是列表形式
        if not isinstance(data, list):
            data = [data]
        
        if not data:
            return {"status": "empty", "message": "没有数据需要处理"}
        
        # 更新统计信息
        self.statistics["processed_count"] += len(data)
        
        # 按标的物分组数据
        grouped_data = defaultdict(list)
        for item in data:
            # 获取标的物
            instrument = item.get(self.instrument_field, "unknown")
            grouped_data[instrument].append(item)
        
        # 处理每个标的物的数据
        results = {}
        for instrument, items in grouped_data.items():
            # 按时间排序
            if self.time_field in items[0]:
                try:
                    items.sort(key=lambda x: pd.to_datetime(x[self.time_field]))
                except (ValueError, TypeError):
                    self.logger.warning(f"无法解析时间戳: {items[0][self.time_field]}")
            
            # 计算处理延迟
            if self.time_field in items[-1]:
                try:
                    data_time = pd.to_datetime(items[-1][self.time_field])
                    now = pd.Timestamp.now()
                    latency_ms = (now - data_time).total_seconds() * 1000
                    self.statistics["latency_ms"].append(latency_ms)
                    # 只保留最近100个延迟记录
                    if len(self.statistics["latency_ms"]) > 100:
                        self.statistics["latency_ms"] = self.statistics["latency_ms"][-100:]
                except (ValueError, TypeError):
                    pass
            
            # 检查数据连续性
            if instrument in self.last_data_time and self.time_field in items[0]:
                try:
                    current_time = pd.to_datetime(items[0][self.time_field])
                    last_time = self.last_data_time[instrument]
                    time_diff = (current_time - last_time).total_seconds() * 1000
                    
                    # 如果时间差大于处理间隔的2倍，可能存在数据缺失
                    if time_diff > self.processing_interval * 2000:
                        self.logger.warning(f"检测到数据缺失: {instrument}, 时间差: {time_diff}ms")
                        self.statistics["anomaly_count"] += 1
                except (ValueError, TypeError):
                    pass
            
            # 更新最后数据时间
            if self.time_field in items[-1]:
                try:
                    self.last_data_time[instrument] = pd.to_datetime(items[-1][self.time_field])
                except (ValueError, TypeError):
                    pass
            
            # 执行数据聚合
            if self.aggregation["enabled"]:
                aggregated = self._aggregate_data(items, instrument)
                results[instrument] = {
                    "raw_count": len(items),
                    "aggregated": aggregated
                }
            else:
                results[instrument] = {
                    "count": len(items),
                    "first_time": items[0].get(self.time_field),
                    "last_time": items[-1].get(self.time_field)
                }
        
        # 返回处理结果
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "instruments": list(grouped_data.keys()),
            "total_count": len(data),
            "results": results,
            "statistics": {
                "processed_count": self.statistics["processed_count"],
                "anomaly_count": self.statistics["anomaly_count"],
                "avg_latency_ms": np.mean(self.statistics["latency_ms"]) if self.statistics["latency_ms"] else 0
            }
        }
    
    def _aggregate_data(self, data: List[Dict[str, Any]], instrument: str) -> List[Dict[str, Any]]:
        """
        聚合数据
        
        参数:
            data: 数据列表
            instrument: 标的物
            
        返回:
            聚合后的数据列表
        """
        if not data:
            return []
        
        # 获取聚合间隔
        interval_ms = self.aggregation.get("interval_ms", 1000)
        
        # 获取需要聚合的字段
        agg_fields = self.aggregation.get("fields", [])
        if not agg_fields:
            # 如果未指定字段，则尝试自动检测数值字段
            sample = data[0]
            agg_fields = [field for field, value in sample.items() 
                         if isinstance(value, (int, float)) and field not in [self.time_field, self.instrument_field]]
        
        # 转换为DataFrame
        df = pd.DataFrame(data)
        
        # 确保时间戳字段存在
        if self.time_field not in df.columns:
            self.logger.warning(f"数据中缺少时间戳字段: {self.time_field}")
            return []
        
        try:
            # 转换时间戳
            df[self.time_field] = pd.to_datetime(df[self.time_field])
            
            # 创建时间分组
            df["time_group"] = df[self.time_field].dt.floor(f"{interval_ms}ms")
            
            # 定义聚合函数
            agg_funcs = {}
            for field in agg_fields:
                if field in df.columns:
                    agg_funcs[field] = {
                        "open": "first",
                        "high": "max",
                        "low": "min",
                        "close": "last",
                        "mean": "mean",
                        "sum": "sum",
                        "count": "count"
                    }
            
            # 执行聚合
            if agg_funcs:
                agg_df = df.groupby("time_group").agg(agg_funcs)
                
                # 重置索引
                agg_df = agg_df.reset_index()
                
                # 重命名列
                new_columns = []
                for col in agg_df.columns:
                    if isinstance(col, tuple):
                        new_columns.append(f"{col[0]}_{col[1]}")
                    else:
                        new_columns.append(col)
                agg_df.columns = new_columns
                
                # 添加标的物字段
                agg_df[self.instrument_field] = instrument
                
                # 重命名时间分组字段
                agg_df = agg_df.rename(columns={"time_group": self.time_field})
                
                # 转换回字典列表
                return agg_df.to_dict("records")
            else:
                self.logger.warning(f"没有可聚合的字段")
                return []
        except Exception as e:
            self.logger.error(f"聚合数据失败: {e}")
            return []


class TickDataProcessor(BaseHighFrequencyProcessor):
    """
    Tick数据处理器
    处理逐笔成交数据，计算成交量分布和价格变动
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Tick数据处理器
        
        参数:
            config: 配置字典，包含以下字段:
                - buffer_size: 缓冲区大小，默认1000
                - processing_interval_ms: 处理间隔，单位毫秒，默认100
                - time_field: 时间戳字段名，默认'timestamp'
                - instrument_field: 标的物字段名，默认'instrument'
                - price_field: 价格字段名，默认'price'
                - volume_field: 成交量字段名，默认'volume'
                - window_size: 窗口大小，默认100
        """
        super().__init__(config)
        self.time_field = config.get("time_field", "timestamp")
        self.instrument_field = config.get("instrument_field", "instrument")
        self.price_field = config.get("price_field", "price")
        self.volume_field = config.get("volume_field", "volume")
        self.window_size = config.get("window_size", 100)
        
        # 每个标的物的历史数据窗口
        self.history_windows = defaultdict(lambda: deque(maxlen=self.window_size))
        
        # 统计信息
        self.statistics = defaultdict(lambda: {
            "tick_count": 0,
            "volume_sum": 0,
            "price_changes": [],
            "last_price": None,
            "max_price": float('-inf'),
            "min_price": float('inf'),
            "last_update": None
        })
    
    def process(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        处理Tick数据
        
        参数:
            data: 单条数据或数据列表
            
        返回:
            处理结果
        """
        # 确保数据是列表形式
        if not isinstance(data, list):
            data = [data]
        
        if not data:
            return {"status": "empty", "message": "没有数据需要处理"}
        
        # 按标的物分组数据
        grouped_data = defaultdict(list)
        for item in data:
            # 获取标的物
            instrument = item.get(self.instrument_field, "unknown")
            grouped_data[instrument].append(item)
        
        # 处理每个标的物的数据
        results = {}
        for instrument, items in grouped_data.items():
            # 按时间排序
            if self.time_field in items[0]:
                try:
                    items.sort(key=lambda x: pd.to_datetime(x[self.time_field]))
                except (ValueError, TypeError):
                    self.logger.warning(f"无法解析时间戳: {items[0][self.time_field]}")
            
            # 处理每个Tick
            for item in items:
                # 添加到历史窗口
                self.history_windows[instrument].append(item)
                
                # 更新统计信息
                stats = self.statistics[instrument]
                stats["tick_count"] += 1
                
                # 更新成交量
                if self.volume_field in item:
                    volume = item.get(self.volume_field, 0)
                    if isinstance(volume, (int, float)):
                        stats["volume_sum"] += volume
                
                # 更新价格
                if self.price_field in item:
                    price = item.get(self.price_field)
                    if isinstance(price, (int, float)):
                        # 记录价格变动
                        if stats["last_price"] is not None:
                            price_change = price - stats["last_price"]
                            stats["price_changes"].append(price_change)
                            # 只保留最近100个价格变动
                            if len(stats["price_changes"]) > 100:
                                stats["price_changes"] = stats["price_changes"][-100:]
                        
                        # 更新最高最低价格
                        stats["last_price"] = price
                        stats["max_price"] = max(stats["max_price"], price)
                        stats["min_price"] = min(stats["min_price"], price)
                
                # 更新最后更新时间
                if self.time_field in item:
                    try:
                        stats["last_update"] = pd.to_datetime(item[self.time_field])
                    except (ValueError, TypeError):
                        pass
            
            # 计算统计指标
            window_data = list(self.history_windows[instrument])
            stats = self.statistics[instrument]
            
            # 提取价格序列
            prices = [item.get(self.price_field) for item in window_data if self.price_field in item]
            prices = [p for p in prices if isinstance(p, (int, float))]
            
            # 提取成交量序列
            volumes = [item.get(self.volume_field) for item in window_data if self.volume_field in item]
            volumes = [v for v in volumes if isinstance(v, (int, float))]
            
            # 计算价格波动率
            price_volatility = np.std(prices) if prices else 0
            
            # 计算成交量分布
            volume_mean = np.mean(volumes) if volumes else 0
            volume_std = np.std(volumes) if volumes else 0
            
            # 计算价格变动趋势
            price_changes = stats["price_changes"]
            price_trend = np.mean(price_changes) if price_changes else 0
            
            # 汇总结果
            results[instrument] = {
                "tick_count": stats["tick_count"],
                "volume_sum": stats["volume_sum"],
                "last_price": stats["last_price"],
                "price_range": {
                    "max": stats["max_price"] if stats["max_price"] != float('-inf') else None,
                    "min": stats["min_price"] if stats["min_price"] != float('inf') else None,
                    "range": stats["max_price"] - stats["min_price"] if stats["max_price"] != float('-inf') and stats["min_price"] != float('inf') else 0
                },
                "window_statistics": {
                    "size": len(window_data),
                    "price_volatility": price_volatility,
                    "volume_mean": volume_mean,
                    "volume_std": volume_std,
                    "price_trend": price_trend
                },
                "last_update": stats["last_update"].isoformat() if stats["last_update"] else None
            }
        
        # 返回处理结果
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "instruments": list(grouped_data.keys()),
            "total_count": len(data),
            "results": results
        }


class OrderBookProcessor(BaseHighFrequencyProcessor):
    """
    订单簿处理器
    处理订单簿数据，维护最新订单簿状态和计算市场深度指标
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化订单簿处理器
        
        参数:
            config: 配置字典，包含以下字段:
                - buffer_size: 缓冲区大小，默认1000
                - processing_interval_ms: 处理间隔，单位毫秒，默认100
                - time_field: 时间戳字段名，默认'timestamp'
                - instrument_field: 标的物字段名，默认'instrument'
                - book_depth: 订单簿深度，默认10
                - snapshot_interval: 快照间隔，单位毫秒，默认1000
        """
        super().__init__(config)
        self.time_field = config.get("time_field", "timestamp")
        self.instrument_field = config.get("instrument_field", "instrument")
        self.book_depth = config.get("book_depth", 10)
        self.snapshot_interval = config.get("snapshot_interval", 1000) / 1000.0  # 转换为秒
        
        # 每个标的物的订单簿状态
        self.order_books = {}
        
        # 每个标的物的最后快照时间
        self.last_snapshot_time = {}
        
        # 订单簿快照历史
        self.book_snapshots = defaultdict(lambda: deque(maxlen=100))
    
    def process(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        处理订单簿数据
        
        参数:
            data: 单条数据或数据列表
            
        返回:
            处理结果
        """
        # 确保数据是列表形式
        if not isinstance(data, list):
            data = [data]
        
        if not data:
            return {"status": "empty", "message": "没有数据需要处理"}
        
        # 按标的物分组数据
        grouped_data = defaultdict(list)
        for item in data:
            # 获取标的物
            instrument = item.get(self.instrument_field, "unknown")
            grouped_data[instrument].append(item)
        
        # 处理每个标的物的数据
        results = {}
        current_time = time.time()
        
        for instrument, items in grouped_data.items():
            # 按时间排序
            if self.time_field in items[0]:
                try:
                    items.sort(key=lambda x: pd.to_datetime(x[self.time_field]))
                except (ValueError, TypeError):
                    self.logger.warning(f"无法解析时间戳: {items[0][self.time_field]}")
            
            # 初始化订单簿
            if instrument not in self.order_books:
                self.order_books[instrument] = {
                    "bids": {},  # 买单 {price: {size, orders}}
                    "asks": {},  # 卖单 {price: {size, orders}}
                    "last_update": None
                }
            
            # 处理每个订单簿更新
            for item in items:
                self._update_order_book(instrument, item)
            
            # 检查是否需要生成快照
            if (instrument not in self.last_snapshot_time or 
                current_time - self.last_snapshot_time.get(instrument, 0) >= self.snapshot_interval):
                # 生成订单簿快照
                snapshot = self._create_book_snapshot(instrument)
                self.book_snapshots[instrument].append(snapshot)
                self.last_snapshot_time[instrument] = current_time
            
            # 计算市场深度指标
            market_depth = self._calculate_market_depth(instrument)
            
            # 汇总结果
            results[instrument] = {
                "book_status": {
                    "bid_levels": len(self.order_books[instrument]["bids"]),
                    "ask_levels": len(self.order_books[instrument]["asks"]),
                    "last_update": self.order_books[instrument]["last_update"].isoformat() if self.order_books[instrument]["last_update"] else None
                },
                "market_depth": market_depth,
                "snapshot_count": len(self.book_snapshots[instrument])
            }
        
        # 返回处理结果
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "instruments": list(grouped_data.keys()),
            "total_count": len(data),
            "results": results
        }
    
    def _update_order_book(self, instrument: str, data: Dict[str, Any]):
        """
        更新订单簿
        
        参数:
            instrument: 标的物
            data: 订单簿更新数据
        """
        # 获取订单簿
        book = self.order_books[instrument]
        
        # 检查数据类型
        data_type = data.get("type", "")
        
        if data_type == "snapshot":
            # 完整订单簿快照
            if "bids" in data:
                book["bids"] = {}
                for bid in data["bids"]:
                    if isinstance(bid, list) and len(bid) >= 2:
                        price, size = bid[0], bid[1]
                        book["bids"][price] = {"size": size, "orders": 1}
                    elif isinstance(bid, dict) and "price" in bid and "size" in bid:
                        price, size = bid["price"], bid["size"]
                        book["bids"][price] = {"size": size, "orders": bid.get("orders", 1)}
            
            if "asks" in data:
                book["asks"] = {}
                for ask in data["asks"]:
                    if isinstance(ask, list) and len(ask) >= 2:
                        price, size = ask[0], ask[1]
                        book["asks"][price] = {"size": size, "orders": 1}
                    elif isinstance(ask, dict) and "price" in ask and "size" in ask:
                        price, size = ask["price"], ask["size"]
                        book["asks"][price] = {"size": size, "orders": ask.get("orders", 1)}
        
        elif data_type == "update":
            # 增量更新
            if "bids" in data:
                for bid in data["bids"]:
                    if isinstance(bid, list) and len(bid) >= 2:
                        price, size = bid[0], bid[1]
                        if size > 0:
                            book["bids"][price] = {"size": size, "orders": 1}
                        else:
                            book["bids"].pop(price, None)
                    elif isinstance(bid, dict) and "price" in bid and "size" in bid:
                        price, size = bid["price"], bid["size"]
                        if size > 0:
                            book["bids"][price] = {"size": size, "orders": bid.get("orders", 1)}
                        else:
                            book["bids"].pop(price, None)
            
            if "asks" in data:
                for ask in data["asks"]:
                    if isinstance(ask, list) and len(ask) >= 2:
                        price, size = ask[0], ask[1]
                        if size > 0:
                            book["asks"][price] = {"size": size, "orders": 1}
                        else:
                            book["asks"].pop(price, None)
                    elif isinstance(ask, dict) and "price" in ask and "size" in ask:
                        price, size = ask["price"], ask["size"]
                        if size > 0:
                            book["asks"][price] = {"size": size, "orders": ask.get("orders", 1)}
                        else:
                            book["asks"].pop(price, None)
        
        # 更新最后更新时间
        if self.time_field in data:
            try:
                book["last_update"] = pd.to_datetime(data[self.time_field])
            except (ValueError, TypeError):
                book["last_update"] = datetime.now()
        else:
            book["last_update"] = datetime.now()
    
    def _create_book_snapshot(self, instrument: str) -> Dict[str, Any]:
        """
        创建订单簿快照
        
        参数:
            instrument: 标的物
            
        返回:
            订单簿快照
        """
        book = self.order_books[instrument]
        
        # 获取最优买卖价
        bids = sorted(book["bids"].items(), key=lambda x: float(x[0]), reverse=True)
        asks = sorted(book["asks"].items(), key=lambda x: float(x[0]))
        
        # 截取指定深度
        bids = bids[:self.book_depth]
        asks = asks[:self.book_depth]
        
        # 计算中间价
        mid_price = None
        if bids and asks:
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            mid_price = (best_bid + best_ask) / 2
        
        # 创建快照
        snapshot = {
            "instrument": instrument,
            "timestamp": datetime.now().isoformat(),
            "bids": [{"price": price, "size": info["size"], "orders": info["orders"]} for price, info in bids],
            "asks": [{"price": price, "size": info["size"], "orders": info["orders"]} for price, info in asks],
            "mid_price": mid_price,
            "spread": float(asks[0][0]) - float(bids[0][0]) if bids and asks else None
        }
        
        return snapshot
    
    def _calculate_market_depth(self, instrument: str) -> Dict[str, Any]:
        """
        计算市场深度指标
        
        参数:
            instrument: 标的物
            
        返回:
            市场深度指标
        """
        book = self.order_books[instrument]
        
        # 获取买卖单
        bids = sorted(book["bids"].items(), key=lambda x: float(x[0]), reverse=True)
        asks = sorted(book["asks"].items(), key=lambda x: float(x[0]))
        
        # 计算总量和加权平均价格
        bid_volume = sum(info["size"] for _, info in bids)
        ask_volume = sum(info["size"] for _, info in asks)
        
        bid_value = sum(float(price) * info["size"] for price, info in bids)
        ask_value = sum(float(price) * info["size"] for price, info in asks)
        
        bid_wavp = bid_value / bid_volume if bid_volume > 0 else 0
        ask_wavp = ask_value / ask_volume if ask_volume > 0 else 0
        
        # 计算买卖比率
        bid_ask_ratio = bid_volume / ask_volume if ask_volume > 0 else float('inf')
        
        # 计算订单簿不平衡度
        imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume) if (bid_volume + ask_volume) > 0 else 0
        
        # 计算市场深度
        depth = {
            "bid_volume": bid_volume,
            "ask_volume": ask_volume,
            "bid_wavp": bid_wavp,
            "ask_wavp": ask_wavp,
            "bid_ask_ratio": bid_ask_ratio,
            "imbalance": imbalance,
            "best_bid": float(bids[0][0]) if bids else None,
            "best_ask": float(asks[0][0]) if asks else None,
            "spread": float(asks[0][0]) - float(bids[0][0]) if bids and asks else None,
            "spread_pct": (float(asks[0][0]) - float(bids[0][0])) / float(bids[0][0]) * 100 if bids and asks else None
        }
        
        return depth
    
    def get_order_book(self, instrument: str) -> Optional[Dict[str, Any]]:
        """
        获取指定标的物的最新订单簿
        
        参数:
            instrument: 标的物
            
        返回:
            订单簿快照
        """
        if instrument not in self.order_books:
            return None
        
        return self._create_book_snapshot(instrument)
    
    def get_order_book_history(self, instrument: str) -> List[Dict[str, Any]]:
        """
        获取指定标的物的订单簿历史
        
        参数:
            instrument: 标的物
            
        返回:
            订单簿快照列表
        """
        if instrument not in self.book_snapshots:
            return []
        
        return list(self.book_snapshots[instrument])
