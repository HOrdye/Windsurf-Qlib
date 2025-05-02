"""
数据流异常处理机制
实现数据流异常检测、处理和恢复，确保数据连续性
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

from .base import BaseStreamAnomalyHandler

# 配置日志
logger = logging.getLogger(__name__)

class StreamAnomalyHandler(BaseStreamAnomalyHandler):
    """
    数据流异常处理器
    检测和处理数据流中的异常，包括数据延迟、缺失和异常值
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据流异常处理器
        
        参数:
            config: 配置字典，包含以下字段:
                - anomaly_types: 要检测的异常类型列表，默认全部
                - thresholds: 异常阈值配置
                - time_field: 时间戳字段名，默认'timestamp'
                - instrument_field: 标的物字段名，默认'instrument'
        """
        super().__init__(config)
        self.anomaly_types = config.get("anomaly_types", [
            "delay", "missing", "duplicate", "outlier", "inconsistent"
        ])
        self.thresholds = config.get("thresholds", {
            "delay_ms": 1000,  # 延迟阈值，单位毫秒
            "missing_interval_ms": 2000,  # 缺失间隔阈值，单位毫秒
            "outlier_std": 3.0,  # 异常值标准差阈值
            "duplicate_window": 100  # 重复检测窗口大小
        })
        self.time_field = config.get("time_field", "timestamp")
        self.instrument_field = config.get("instrument_field", "instrument")
        
        # 每个标的物的最后数据时间
        self.last_data_time = {}
        
        # 每个标的物的历史数据窗口
        self.history_windows = defaultdict(lambda: deque(maxlen=self.thresholds.get("duplicate_window", 100)))
        
        # 每个标的物的统计信息
        self.statistics = defaultdict(lambda: {
            "values": [],
            "timestamps": [],
            "anomaly_counts": defaultdict(int)
        })
        
        # 注册默认处理函数
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认异常处理函数"""
        self.register_handler("delay", self._handle_delay)
        self.register_handler("missing", self._handle_missing)
        self.register_handler("duplicate", self._handle_duplicate)
        self.register_handler("outlier", self._handle_outlier)
        self.register_handler("inconsistent", self._handle_inconsistent)
    
    def detect_anomaly(self, data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        检测数据流异常
        
        参数:
            data: 数据字典
            
        返回:
            (是否异常, 异常类型, 异常详情)
        """
        # 获取标的物和时间戳
        instrument = data.get(self.instrument_field, "unknown")
        
        # 检查时间戳字段是否存在
        if self.time_field not in data:
            return True, "missing_timestamp", {"message": f"数据缺少时间戳字段: {self.time_field}"}
        
        # 解析时间戳
        try:
            timestamp = pd.to_datetime(data[self.time_field])
        except (ValueError, TypeError):
            return True, "invalid_timestamp", {"message": f"无效的时间戳格式: {data[self.time_field]}"}
        
        # 获取当前时间
        now = pd.Timestamp.now()
        
        # 检查数据延迟
        if "delay" in self.anomaly_types:
            delay_ms = (now - timestamp).total_seconds() * 1000
            if delay_ms > self.thresholds.get("delay_ms", 1000):
                return True, "delay", {
                    "delay_ms": delay_ms,
                    "threshold_ms": self.thresholds.get("delay_ms", 1000),
                    "timestamp": timestamp.isoformat(),
                    "current_time": now.isoformat()
                }
        
        # 检查数据缺失
        if "missing" in self.anomaly_types and instrument in self.last_data_time:
            last_time = self.last_data_time[instrument]
            time_diff = (timestamp - last_time).total_seconds() * 1000
            
            if time_diff > self.thresholds.get("missing_interval_ms", 2000):
                return True, "missing", {
                    "time_diff_ms": time_diff,
                    "threshold_ms": self.thresholds.get("missing_interval_ms", 2000),
                    "last_timestamp": last_time.isoformat(),
                    "current_timestamp": timestamp.isoformat()
                }
        
        # 检查数据重复
        if "duplicate" in self.anomaly_types:
            # 创建数据指纹
            data_copy = data.copy()
            if self.time_field in data_copy:
                del data_copy[self.time_field]  # 移除时间戳字段
            
            data_fingerprint = json.dumps(data_copy, sort_keys=True)
            
            # 检查是否在历史窗口中
            for historical_data in self.history_windows[instrument]:
                historical_copy = historical_data.copy()
                if self.time_field in historical_copy:
                    del historical_copy[self.time_field]
                
                historical_fingerprint = json.dumps(historical_copy, sort_keys=True)
                
                if data_fingerprint == historical_fingerprint:
                    return True, "duplicate", {
                        "original_data": historical_data,
                        "duplicate_data": data
                    }
        
        # 检查异常值
        if "outlier" in self.anomaly_types:
            # 获取数值字段
            numeric_fields = []
            for field, value in data.items():
                if isinstance(value, (int, float)) and field not in [self.time_field, self.instrument_field]:
                    numeric_fields.append(field)
            
            # 检查每个数值字段
            for field in numeric_fields:
                value = data[field]
                stats = self.statistics[instrument]
                
                # 如果历史数据不足，则添加当前值并跳过检测
                if len(stats["values"]) < 10:
                    stats["values"].append(value)
                    continue
                
                # 计算均值和标准差
                mean = np.mean(stats["values"])
                std = np.std(stats["values"])
                
                # 如果标准差为0，则跳过检测
                if std == 0:
                    continue
                
                # 计算Z分数
                z_score = abs(value - mean) / std
                
                # 检查是否超过阈值
                if z_score > self.thresholds.get("outlier_std", 3.0):
                    return True, "outlier", {
                        "field": field,
                        "value": value,
                        "mean": mean,
                        "std": std,
                        "z_score": z_score,
                        "threshold": self.thresholds.get("outlier_std", 3.0)
                    }
        
        # 检查数据一致性
        if "inconsistent" in self.anomaly_types:
            # 这里可以添加特定的一致性检查逻辑
            # 例如，检查价格和成交量是否符合特定关系
            pass
        
        # 更新历史数据
        self.history_windows[instrument].append(data)
        
        # 更新最后数据时间
        self.last_data_time[instrument] = timestamp
        
        # 更新统计信息
        stats = self.statistics[instrument]
        for field, value in data.items():
            if isinstance(value, (int, float)) and field not in [self.time_field, self.instrument_field]:
                if "values" not in stats:
                    stats["values"] = []
                stats["values"].append(value)
                # 只保留最近100个值
                if len(stats["values"]) > 100:
                    stats["values"] = stats["values"][-100:]
        
        stats["timestamps"].append(timestamp)
        # 只保留最近100个时间戳
        if len(stats["timestamps"]) > 100:
            stats["timestamps"] = stats["timestamps"][-100:]
        
        # 没有检测到异常
        return False, "", {}
    
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
        # 更新异常计数
        instrument = data.get(self.instrument_field, "unknown")
        self.statistics[instrument]["anomaly_counts"][anomaly_type] += 1
        
        # 使用注册的处理函数处理异常
        if anomaly_type in self.handlers:
            return self.handlers[anomaly_type](data, details)
        
        # 默认返回原始数据
        return data
    
    def _handle_delay(self, data: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据延迟"""
        # 对于延迟数据，我们通常只是记录并继续处理
        self.logger.warning(f"检测到数据延迟: {details['delay_ms']}ms > {details['threshold_ms']}ms")
        
        # 添加延迟标记
        data["_delayed"] = True
        data["_delay_ms"] = details["delay_ms"]
        
        return data
    
    def _handle_missing(self, data: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据缺失"""
        self.logger.warning(f"检测到数据缺失: {details['time_diff_ms']}ms > {details['threshold_ms']}ms")
        
        # 添加缺失标记
        data["_missing_gap"] = True
        data["_gap_ms"] = details["time_diff_ms"]
        
        return data
    
    def _handle_duplicate(self, data: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据重复"""
        self.logger.warning(f"检测到数据重复")
        
        # 对于重复数据，我们可以选择丢弃或标记
        data["_duplicate"] = True
        
        return data
    
    def _handle_outlier(self, data: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """处理异常值"""
        field = details["field"]
        value = details["value"]
        mean = details["mean"]
        
        self.logger.warning(f"检测到异常值: {field}={value}, Z分数={details['z_score']}")
        
        # 对于异常值，我们可以选择替换为均值或标记
        data["_outlier"] = True
        data["_outlier_field"] = field
        data["_outlier_original"] = value
        
        # 是否替换异常值取决于配置
        if self.config.get("replace_outliers", False):
            data[field] = mean
        
        return data
    
    def _handle_inconsistent(self, data: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据不一致"""
        self.logger.warning(f"检测到数据不一致: {details}")
        
        # 添加不一致标记
        data["_inconsistent"] = True
        
        return data
    
    def get_statistics(self, instrument: Optional[str] = None) -> Dict[str, Any]:
        """
        获取异常统计信息
        
        参数:
            instrument: 标的物，如果为None则返回所有标的物的统计信息
            
        返回:
            统计信息字典
        """
        if instrument is not None:
            if instrument in self.statistics:
                stats = self.statistics[instrument]
                return {
                    "instrument": instrument,
                    "anomaly_counts": dict(stats["anomaly_counts"]),
                    "total_anomalies": sum(stats["anomaly_counts"].values()),
                    "data_points": len(stats["timestamps"]),
                    "first_timestamp": stats["timestamps"][0].isoformat() if stats["timestamps"] else None,
                    "last_timestamp": stats["timestamps"][-1].isoformat() if stats["timestamps"] else None
                }
            else:
                return {"instrument": instrument, "message": "无统计信息"}
        else:
            # 返回所有标的物的统计信息
            result = {}
            for inst, stats in self.statistics.items():
                result[inst] = {
                    "anomaly_counts": dict(stats["anomaly_counts"]),
                    "total_anomalies": sum(stats["anomaly_counts"].values()),
                    "data_points": len(stats["timestamps"]),
                    "first_timestamp": stats["timestamps"][0].isoformat() if stats["timestamps"] else None,
                    "last_timestamp": stats["timestamps"][-1].isoformat() if stats["timestamps"] else None
                }
            return result


class DataContinuityHandler(BaseStreamAnomalyHandler):
    """
    数据连续性处理器
    确保数据流的连续性，处理数据缺失和时间戳不连续的情况
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据连续性处理器
        
        参数:
            config: 配置字典，包含以下字段:
                - time_field: 时间戳字段名，默认'timestamp'
                - instrument_field: 标的物字段名，默认'instrument'
                - expected_interval_ms: 预期数据间隔，单位毫秒，默认1000
                - max_gap_ms: 最大允许间隔，单位毫秒，默认5000
                - interpolation_method: 插值方法，默认'linear'
        """
        super().__init__(config)
        self.time_field = config.get("time_field", "timestamp")
        self.instrument_field = config.get("instrument_field", "instrument")
        self.expected_interval_ms = config.get("expected_interval_ms", 1000)
        self.max_gap_ms = config.get("max_gap_ms", 5000)
        self.interpolation_method = config.get("interpolation_method", "linear")
        
        # 每个标的物的最后数据时间
        self.last_data_time = {}
        
        # 每个标的物的数据缓存
        self.data_cache = defaultdict(list)
        
        # 每个标的物的缺失数据记录
        self.missing_records = defaultdict(list)
        
        # 注册处理函数
        self.register_handler("gap_detected", self._handle_gap)
    
    def detect_anomaly(self, data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        检测数据连续性异常
        
        参数:
            data: 数据字典
            
        返回:
            (是否异常, 异常类型, 异常详情)
        """
        # 获取标的物和时间戳
        instrument = data.get(self.instrument_field, "unknown")
        
        # 检查时间戳字段是否存在
        if self.time_field not in data:
            return True, "missing_timestamp", {"message": f"数据缺少时间戳字段: {self.time_field}"}
        
        # 解析时间戳
        try:
            timestamp = pd.to_datetime(data[self.time_field])
        except (ValueError, TypeError):
            return True, "invalid_timestamp", {"message": f"无效的时间戳格式: {data[self.time_field]}"}
        
        # 添加到数据缓存
        self.data_cache[instrument].append(data)
        # 限制缓存大小
        max_cache_size = self.config.get("max_cache_size", 1000)
        if len(self.data_cache[instrument]) > max_cache_size:
            self.data_cache[instrument] = self.data_cache[instrument][-max_cache_size:]
        
        # 检查是否有上一条数据
        if instrument in self.last_data_time:
            last_time = self.last_data_time[instrument]
            time_diff = (timestamp - last_time).total_seconds() * 1000
            
            # 如果时间差大于预期间隔的1.5倍，可能存在数据缺失
            if time_diff > self.expected_interval_ms * 1.5:
                # 计算缺失的数据点数量
                expected_points = int(time_diff / self.expected_interval_ms) - 1
                
                if expected_points > 0:
                    # 记录缺失数据
                    missing_record = {
                        "start_time": last_time.isoformat(),
                        "end_time": timestamp.isoformat(),
                        "time_diff_ms": time_diff,
                        "expected_points": expected_points,
                        "detected_at": datetime.now().isoformat()
                    }
                    self.missing_records[instrument].append(missing_record)
                    
                    # 限制记录大小
                    max_records = self.config.get("max_missing_records", 100)
                    if len(self.missing_records[instrument]) > max_records:
                        self.missing_records[instrument] = self.missing_records[instrument][-max_records:]
                    
                    return True, "gap_detected", missing_record
        
        # 更新最后数据时间
        self.last_data_time[instrument] = timestamp
        
        # 没有检测到异常
        return False, "", {}
    
    def handle_anomaly(self, anomaly_type: str, data: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理数据连续性异常
        
        参数:
            anomaly_type: 异常类型
            data: 原始数据
            details: 异常详情
            
        返回:
            处理后的数据
        """
        # 使用注册的处理函数处理异常
        if anomaly_type in self.handlers:
            return self.handlers[anomaly_type](data, details)
        
        # 默认返回原始数据
        return data
    
    def _handle_gap(self, data: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据间隔异常"""
        self.logger.warning(f"检测到数据间隔: {details['time_diff_ms']}ms, 预期缺失点: {details['expected_points']}")
        
        # 添加间隔标记
        data["_gap_detected"] = True
        data["_gap_ms"] = details["time_diff_ms"]
        data["_expected_points"] = details["expected_points"]
        
        # 如果配置了自动填充，则生成填充数据
        if self.config.get("auto_fill_gaps", False):
            instrument = data.get(self.instrument_field, "unknown")
            self._fill_data_gap(instrument, details)
        
        return data
    
    def _fill_data_gap(self, instrument: str, gap_details: Dict[str, Any]):
        """
        填充数据间隔
        
        参数:
            instrument: 标的物
            gap_details: 间隔详情
        """
        # 获取开始和结束时间
        try:
            start_time = pd.to_datetime(gap_details["start_time"])
            end_time = pd.to_datetime(gap_details["end_time"])
            expected_points = gap_details["expected_points"]
            
            # 如果缓存中数据不足，则无法填充
            if len(self.data_cache[instrument]) < 2:
                self.logger.warning(f"缓存数据不足，无法填充间隔: {instrument}")
                return
            
            # 获取间隔前后的数据
            before_data = None
            after_data = None
            
            for item in reversed(self.data_cache[instrument]):
                if self.time_field in item:
                    try:
                        item_time = pd.to_datetime(item[self.time_field])
                        if item_time <= start_time:
                            before_data = item
                            break
                    except (ValueError, TypeError):
                        pass
            
            for item in self.data_cache[instrument]:
                if self.time_field in item:
                    try:
                        item_time = pd.to_datetime(item[self.time_field])
                        if item_time >= end_time:
                            after_data = item
                            break
                    except (ValueError, TypeError):
                        pass
            
            if before_data is None or after_data is None:
                self.logger.warning(f"无法找到间隔前后的数据: {instrument}")
                return
            
            # 生成填充数据点
            filled_points = []
            time_interval = (end_time - start_time) / (expected_points + 1)
            
            for i in range(1, expected_points + 1):
                # 计算当前时间点
                current_time = start_time + time_interval * i
                
                # 创建新数据点
                new_point = before_data.copy()
                new_point[self.time_field] = current_time.isoformat()
                new_point["_filled"] = True
                new_point["_fill_method"] = self.interpolation_method
                
                # 对数值字段进行插值
                for field, value in before_data.items():
                    if isinstance(value, (int, float)) and field in after_data:
                        after_value = after_data[field]
                        if isinstance(after_value, (int, float)):
                            # 线性插值
                            if self.interpolation_method == "linear":
                                progress = i / (expected_points + 1)
                                interpolated = value + (after_value - value) * progress
                                new_point[field] = interpolated
                
                filled_points.append(new_point)
            
            # 发送填充的数据点
            self.logger.info(f"为 {instrument} 生成了 {len(filled_points)} 个填充数据点")
            
            # 如果配置了回调函数，则调用回调
            callback = self.config.get("fill_callback")
            if callback and callable(callback):
                callback(instrument, filled_points)
        except Exception as e:
            self.logger.error(f"填充数据间隔失败: {e}")
    
    def get_missing_records(self, instrument: Optional[str] = None) -> Dict[str, Any]:
        """
        获取缺失数据记录
        
        参数:
            instrument: 标的物，如果为None则返回所有标的物的记录
            
        返回:
            缺失数据记录
        """
        if instrument is not None:
            return {
                "instrument": instrument,
                "records": self.missing_records.get(instrument, []),
                "total_records": len(self.missing_records.get(instrument, [])),
                "total_missing_points": sum(record["expected_points"] for record in self.missing_records.get(instrument, []))
            }
        else:
            result = {}
            for inst, records in self.missing_records.items():
                result[inst] = {
                    "records": records,
                    "total_records": len(records),
                    "total_missing_points": sum(record["expected_points"] for record in records)
                }
            return result


class DataRecoveryHandler(BaseStreamAnomalyHandler):
    """
    数据恢复处理器
    在数据流中断后恢复数据，处理重连和数据回放
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据恢复处理器
        
        参数:
            config: 配置字典，包含以下字段:
                - time_field: 时间戳字段名，默认'timestamp'
                - instrument_field: 标的物字段名，默认'instrument'
                - recovery_window_ms: 恢复窗口，单位毫秒，默认60000 (1分钟)
                - max_recovery_points: 最大恢复点数，默认1000
        """
        super().__init__(config)
        self.time_field = config.get("time_field", "timestamp")
        self.instrument_field = config.get("instrument_field", "instrument")
        self.recovery_window_ms = config.get("recovery_window_ms", 60000)
        self.max_recovery_points = config.get("max_recovery_points", 1000)
        
        # 每个标的物的最后数据时间
        self.last_data_time = {}
        
        # 每个标的物的断连时间
        self.disconnect_time = {}
        
        # 每个标的物的恢复状态
        self.recovery_status = {}
        
        # 注册处理函数
        self.register_handler("reconnect", self._handle_reconnect)
        self.register_handler("out_of_sequence", self._handle_out_of_sequence)
    
    def detect_anomaly(self, data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        检测数据恢复异常
        
        参数:
            data: 数据字典
            
        返回:
            (是否异常, 异常类型, 异常详情)
        """
        # 获取标的物和时间戳
        instrument = data.get(self.instrument_field, "unknown")
        
        # 检查时间戳字段是否存在
        if self.time_field not in data:
            return True, "missing_timestamp", {"message": f"数据缺少时间戳字段: {self.time_field}"}
        
        # 解析时间戳
        try:
            timestamp = pd.to_datetime(data[self.time_field])
        except (ValueError, TypeError):
            return True, "invalid_timestamp", {"message": f"无效的时间戳格式: {data[self.time_field]}"}
        
        # 检查是否是重连后的数据
        if instrument in self.disconnect_time:
            disconnect_time = self.disconnect_time[instrument]
            reconnect_gap = (timestamp - disconnect_time).total_seconds() * 1000
            
            if reconnect_gap > self.recovery_window_ms:
                # 重连后的第一条数据
                recovery_details = {
                    "disconnect_time": disconnect_time.isoformat(),
                    "reconnect_time": timestamp.isoformat(),
                    "gap_ms": reconnect_gap,
                    "recovery_window_ms": self.recovery_window_ms
                }
                
                # 清除断连记录
                del self.disconnect_time[instrument]
                
                # 设置恢复状态
                self.recovery_status[instrument] = {
                    "recovering": True,
                    "start_time": timestamp,
                    "expected_end_time": timestamp + pd.Timedelta(milliseconds=self.recovery_window_ms),
                    "recovered_points": 0
                }
                
                return True, "reconnect", recovery_details
        
        # 检查是否在恢复过程中
        if instrument in self.recovery_status and self.recovery_status[instrument]["recovering"]:
            recovery_status = self.recovery_status[instrument]
            
            # 检查是否超过恢复窗口
            if timestamp > recovery_status["expected_end_time"]:
                # 恢复完成
                self.recovery_status[instrument]["recovering"] = False
                self.logger.info(f"数据恢复完成: {instrument}, 恢复了 {recovery_status['recovered_points']} 个数据点")
            else:
                # 恢复中，增加恢复点数
                self.recovery_status[instrument]["recovered_points"] += 1
                
                # 检查是否超过最大恢复点数
                if self.recovery_status[instrument]["recovered_points"] >= self.max_recovery_points:
                    self.recovery_status[instrument]["recovering"] = False
                    self.logger.info(f"数据恢复达到最大点数: {instrument}, 恢复了 {self.max_recovery_points} 个数据点")
                
                # 检查数据是否乱序
                if instrument in self.last_data_time:
                    last_time = self.last_data_time[instrument]
                    if timestamp < last_time:
                        return True, "out_of_sequence", {
                            "current_time": timestamp.isoformat(),
                            "last_time": last_time.isoformat(),
                            "time_diff_ms": (last_time - timestamp).total_seconds() * 1000
                        }
        
        # 更新最后数据时间
        self.last_data_time[instrument] = timestamp
        
        # 没有检测到异常
        return False, "", {}
    
    def handle_anomaly(self, anomaly_type: str, data: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理数据恢复异常
        
        参数:
            anomaly_type: 异常类型
            data: 原始数据
            details: 异常详情
            
        返回:
            处理后的数据
        """
        # 使用注册的处理函数处理异常
        if anomaly_type in self.handlers:
            return self.handlers[anomaly_type](data, details)
        
        # 默认返回原始数据
        return data
    
    def _handle_reconnect(self, data: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """处理重连"""
        self.logger.info(f"检测到数据流重连: 断连时间 {details['disconnect_time']}, 重连时间 {details['reconnect_time']}, 间隔 {details['gap_ms']}ms")
        
        # 添加重连标记
        data["_reconnect"] = True
        data["_reconnect_gap_ms"] = details["gap_ms"]
        
        return data
    
    def _handle_out_of_sequence(self, data: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """处理乱序数据"""
        self.logger.warning(f"检测到乱序数据: 当前时间 {details['current_time']}, 上一时间 {details['last_time']}, 时间差 {details['time_diff_ms']}ms")
        
        # 添加乱序标记
        data["_out_of_sequence"] = True
        data["_time_diff_ms"] = details["time_diff_ms"]
        
        return data
    
    def notify_disconnect(self, instrument: str):
        """
        通知断连
        
        参数:
            instrument: 标的物
        """
        self.disconnect_time[instrument] = datetime.now()
        self.logger.info(f"记录断连: {instrument}, 时间: {self.disconnect_time[instrument].isoformat()}")
    
    def get_recovery_status(self, instrument: Optional[str] = None) -> Dict[str, Any]:
        """
        获取恢复状态
        
        参数:
            instrument: 标的物，如果为None则返回所有标的物的状态
            
        返回:
            恢复状态
        """
        if instrument is not None:
            if instrument in self.recovery_status:
                status = self.recovery_status[instrument]
                return {
                    "instrument": instrument,
                    "recovering": status["recovering"],
                    "start_time": status["start_time"].isoformat() if "start_time" in status else None,
                    "expected_end_time": status["expected_end_time"].isoformat() if "expected_end_time" in status else None,
                    "recovered_points": status["recovered_points"] if "recovered_points" in status else 0
                }
            else:
                return {"instrument": instrument, "recovering": False}
        else:
            result = {}
            for inst, status in self.recovery_status.items():
                result[inst] = {
                    "recovering": status["recovering"],
                    "start_time": status["start_time"].isoformat() if "start_time" in status else None,
                    "expected_end_time": status["expected_end_time"].isoformat() if "expected_end_time" in status else None,
                    "recovered_points": status["recovered_points"] if "recovered_points" in status else 0
                }
            return result
