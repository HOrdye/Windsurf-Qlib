"""
推理缓存机制
减少重复计算的缓存策略实现
"""

import logging
import os
import gc
import time
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple, Union, Set
from collections import OrderedDict, defaultdict

import numpy as np
import torch

from .base import BaseCachingMechanism


class KVCachingMechanism(BaseCachingMechanism):
    """
    KV缓存机制
    实现键值对缓存，用于存储模型的中间计算结果
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化KV缓存机制
        
        参数:
            config: 配置字典，包含以下字段:
                - max_cache_size: 最大缓存大小（条目数），默认为1000
                - max_memory_mb: 最大内存占用（MB），默认为4000
                - eviction_policy: 缓存淘汰策略，可选值为'lru', 'lfu'，默认为'lru'
                - ttl: 缓存条目生存时间（秒），默认为3600
                - device: 缓存设备，可选值为'cpu', 'cuda'，默认为'cuda'
        """
        super().__init__(config)
        
        self.max_cache_size = self.config.get("max_cache_size", 1000)
        self.max_memory_mb = self.config.get("max_memory_mb", 4000)
        self.eviction_policy = self.config.get("eviction_policy", "lru")
        self.ttl = self.config.get("ttl", 3600)
        self.device = self.config.get("device", "cuda")
        
        # 初始化缓存
        self.cache = None
        self.cache_stats = None
        self.current_memory_usage = 0
        self.initialize()
        
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        super()._validate_config()
        
        # 检查缓存淘汰策略
        valid_eviction_policies = ["lru", "lfu"]
        if self.config.get("eviction_policy") not in [None, *valid_eviction_policies]:
            raise ValueError(f"缓存淘汰策略必须是以下之一: {valid_eviction_policies}")
        
        # 检查设备
        valid_devices = ["cpu", "cuda"]
        if self.config.get("device") not in [None, *valid_devices]:
            raise ValueError(f"设备必须是以下之一: {valid_devices}")
    
    def initialize(self) -> None:
        """初始化缓存"""
        if self.eviction_policy == "lru":
            # 使用OrderedDict实现LRU缓存
            self.cache = OrderedDict()
        else:
            # 使用字典实现LFU缓存
            self.cache = {}
        
        # 缓存统计信息
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "inserts": 0,
            "memory_usage": 0
        }
        
        # 对于LFU缓存，额外记录访问频率
        if self.eviction_policy == "lfu":
            self.access_frequency = {}
            self.access_time = {}
        
        self.current_memory_usage = 0
        self.logger.info(f"初始化{self.eviction_policy.upper()}缓存，最大大小={self.max_cache_size}，最大内存={self.max_memory_mb}MB")
    
    def _generate_key(self, key: Any) -> str:
        """
        生成缓存键
        
        参数:
            key: 原始键
            
        返回:
            缓存键
        """
        if isinstance(key, str):
            return key
        elif isinstance(key, (int, float, bool)):
            return str(key)
        elif isinstance(key, torch.Tensor):
            # 对于张量，使用其哈希值作为键
            tensor_bytes = key.cpu().numpy().tobytes()
            return hashlib.md5(tensor_bytes).hexdigest()
        elif isinstance(key, (list, tuple)):
            # 对于列表和元组，递归处理每个元素
            return str([self._generate_key(item) for item in key])
        elif isinstance(key, dict):
            # 对于字典，递归处理每个键值对
            sorted_items = sorted(key.items())
            return str({self._generate_key(k): self._generate_key(v) for k, v in sorted_items})
        else:
            # 对于其他类型，使用其字符串表示
            return str(key)
    
    def _get_tensor_size(self, tensor: torch.Tensor) -> float:
        """
        获取张量大小（MB）
        
        参数:
            tensor: 张量
            
        返回:
            张量大小（MB）
        """
        return tensor.nelement() * tensor.element_size() / (1024 * 1024)
    
    def _get_value_size(self, value: Any) -> float:
        """
        获取值大小（MB）
        
        参数:
            value: 值
            
        返回:
            值大小（MB）
        """
        if isinstance(value, torch.Tensor):
            return self._get_tensor_size(value)
        elif isinstance(value, (list, tuple)):
            # 对于列表和元组，递归计算每个元素的大小
            return sum(self._get_value_size(item) for item in value)
        elif isinstance(value, dict):
            # 对于字典，递归计算每个值的大小
            return sum(self._get_value_size(v) for v in value.values())
        else:
            # 对于其他类型，估计其大小
            try:
                return len(str(value)) / (1024 * 1024)
            except:
                return 0.001  # 默认大小为1KB
    
    def _evict_if_needed(self, new_value_size: float) -> None:
        """
        如果需要，淘汰缓存条目
        
        参数:
            new_value_size: 新值的大小（MB）
        """
        # 检查是否需要淘汰
        while (len(self.cache) > 0 and 
               (len(self.cache) >= self.max_cache_size or 
                self.current_memory_usage + new_value_size > self.max_memory_mb)):
            
            if self.eviction_policy == "lru":
                # LRU淘汰策略：淘汰最久未使用的条目
                key, (value, _) = self.cache.popitem(last=False)
            else:
                # LFU淘汰策略：淘汰使用频率最低的条目
                min_freq = min(self.access_frequency.values())
                min_freq_keys = [k for k, v in self.access_frequency.items() if v == min_freq]
                
                # 如果有多个最低频率的条目，选择最早访问的
                oldest_key = min(
                    min_freq_keys,
                    key=lambda k: self.access_time.get(k, 0)
                )
                
                # 删除条目
                key = oldest_key
                value, _ = self.cache.pop(key)
                self.access_frequency.pop(key)
                self.access_time.pop(key)
            
            # 更新内存使用
            value_size = self._get_value_size(value)
            self.current_memory_usage -= value_size
            
            # 更新统计信息
            self.cache_stats["evictions"] += 1
            
            self.logger.debug(f"淘汰缓存条目: {key}, 大小={value_size:.2f}MB")
    
    def get(self, key: Any) -> Optional[Any]:
        """
        获取缓存
        
        参数:
            key: 缓存键
            
        返回:
            缓存值，如果不存在则返回None
        """
        cache_key = self._generate_key(key)
        
        # 检查缓存是否存在
        if cache_key in self.cache:
            value, timestamp = self.cache[cache_key]
            
            # 检查是否过期
            if time.time() - timestamp > self.ttl:
                # 删除过期条目
                self.cache.pop(cache_key)
                if self.eviction_policy == "lfu":
                    self.access_frequency.pop(cache_key, None)
                    self.access_time.pop(cache_key, None)
                
                # 更新内存使用
                value_size = self._get_value_size(value)
                self.current_memory_usage -= value_size
                
                # 更新统计信息
                self.cache_stats["evictions"] += 1
                self.cache_stats["misses"] += 1
                
                self.logger.debug(f"缓存条目过期: {cache_key}")
                return None
            
            # 更新LRU顺序或LFU频率
            if self.eviction_policy == "lru":
                # 将条目移到队尾
                self.cache.move_to_end(cache_key)
            else:
                # 增加访问频率
                self.access_frequency[cache_key] = self.access_frequency.get(cache_key, 0) + 1
                self.access_time[cache_key] = time.time()
            
            # 更新统计信息
            self.cache_stats["hits"] += 1
            
            self.logger.debug(f"缓存命中: {cache_key}")
            return value
        else:
            # 更新统计信息
            self.cache_stats["misses"] += 1
            
            self.logger.debug(f"缓存未命中: {cache_key}")
            return None
    
    def put(self, key: Any, value: Any) -> None:
        """
        放入缓存
        
        参数:
            key: 缓存键
            value: 缓存值
        """
        cache_key = self._generate_key(key)
        
        # 计算值大小
        value_size = self._get_value_size(value)
        
        # 如果单个值超过最大内存限制，不缓存
        if value_size > self.max_memory_mb:
            self.logger.warning(f"值大小({value_size:.2f}MB)超过最大内存限制({self.max_memory_mb}MB)，不缓存")
            return
        
        # 如果需要，淘汰缓存条目
        self._evict_if_needed(value_size)
        
        # 将值移动到指定设备
        if isinstance(value, torch.Tensor) and self.device == "cuda" and torch.cuda.is_available():
            value = value.to(device="cuda")
        elif isinstance(value, torch.Tensor) and self.device == "cpu":
            value = value.to(device="cpu")
        
        # 添加到缓存
        timestamp = time.time()
        self.cache[cache_key] = (value, timestamp)
        
        # 对于LFU缓存，初始化访问频率
        if self.eviction_policy == "lfu":
            self.access_frequency[cache_key] = 1
            self.access_time[cache_key] = timestamp
        
        # 更新内存使用
        self.current_memory_usage += value_size
        
        # 更新统计信息
        self.cache_stats["inserts"] += 1
        self.cache_stats["memory_usage"] = self.current_memory_usage
        
        self.logger.debug(f"添加缓存条目: {cache_key}, 大小={value_size:.2f}MB")
    
    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        if self.eviction_policy == "lfu":
            self.access_frequency.clear()
            self.access_time.clear()
        
        self.current_memory_usage = 0
        
        # 重置统计信息
        for key in self.cache_stats:
            self.cache_stats[key] = 0
        
        self.logger.info("清空缓存")
    
    def get_cache_type(self) -> str:
        """
        获取缓存类型
        
        返回:
            缓存类型
        """
        return f"kv_{self.eviction_policy}"
    
    def get_cache_size(self) -> int:
        """
        获取缓存大小
        
        返回:
            缓存大小（条目数）
        """
        return len(self.cache)
    
    def get_memory_usage(self) -> float:
        """
        获取缓存内存占用
        
        返回:
            内存占用（MB）
        """
        return self.current_memory_usage
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        返回:
            缓存统计信息
        """
        stats = self.cache_stats.copy()
        stats["cache_size"] = self.get_cache_size()
        stats["memory_usage"] = self.get_memory_usage()
        
        # 计算命中率
        total_requests = stats["hits"] + stats["misses"]
        if total_requests > 0:
            stats["hit_ratio"] = stats["hits"] / total_requests
        else:
            stats["hit_ratio"] = 0.0
        
        return stats


class AttentionCachingMechanism(BaseCachingMechanism):
    """
    注意力缓存机制
    实现Transformer模型的注意力缓存，用于加速自回归生成
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化注意力缓存机制
        
        参数:
            config: 配置字典，包含以下字段:
                - max_cache_size: 最大缓存大小（序列数），默认为100
                - max_memory_mb: 最大内存占用（MB），默认为4000
                - max_seq_length: 最大序列长度，默认为2048
                - ttl: 缓存条目生存时间（秒），默认为3600（1小时）
                - device: 缓存设备，可选值为'cpu', 'cuda'，默认为'cuda'
                - dtype: 数据类型，可选值为'float32', 'float16', 'bfloat16'，默认为'float16'
        """
        super().__init__(config)
        
        self.max_cache_size = self.config.get("max_cache_size", 100)
        self.max_memory_mb = self.config.get("max_memory_mb", 4000)
        self.max_seq_length = self.config.get("max_seq_length", 2048)
        self.ttl = self.config.get("ttl", 3600)  # 默认1小时
        self.device = self.config.get("device", "cuda")
        self.dtype = self.config.get("dtype", "float16")
        
        # 初始化缓存
        self.key_cache = None
        self.value_cache = None
        self.seq_lengths = None
        self.last_access_time = None
        self.current_memory_usage = 0
        
        # 缓存统计信息
        self.cache_stats = None
        
        self.logger.info(f"初始化注意力缓存，最大大小={self.max_cache_size}，最大内存={self.max_memory_mb}MB")
        self.initialize()
    
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        super()._validate_config()
        
        # 检查设备
        valid_devices = ["cpu", "cuda"]
        if self.config.get("device") not in [None, *valid_devices]:
            raise ValueError(f"设备必须是以下之一: {valid_devices}")
        
        # 检查数据类型
        valid_dtypes = ["float32", "float16", "bfloat16"]
        if self.config.get("dtype") not in [None, *valid_dtypes]:
            raise ValueError(f"数据类型必须是以下之一: {valid_dtypes}")
    
    def initialize(self) -> None:
        """初始化缓存"""
        # 初始化缓存字典
        self.key_cache = {}  # 存储key缓存
        self.value_cache = {}  # 存储value缓存
        self.seq_lengths = {}  # 存储序列长度
        self.last_access_time = {}  # 存储最后访问时间
        
        # 缓存统计信息
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "inserts": 0,
            "memory_usage": 0
        }
        
        self.current_memory_usage = 0
        self.logger.info(f"初始化注意力缓存，最大大小={self.max_cache_size}，最大内存={self.max_memory_mb}MB，最大序列长度={self.max_seq_length}")
    
    def _get_dtype(self) -> torch.dtype:
        """
        获取数据类型
        
        返回:
            数据类型
        """
        if self.dtype == "float32":
            return torch.float32
        elif self.dtype == "float16":
            return torch.float16
        elif self.dtype == "bfloat16":
            return torch.bfloat16
        else:
            return torch.float16
    
    def _get_tensor_size(self, tensor: torch.Tensor) -> float:
        """
        获取张量大小（MB）
        
        参数:
            tensor: 张量
            
        返回:
            张量大小（MB）
        """
        return tensor.nelement() * tensor.element_size() / (1024 * 1024)
    
    def _evict_if_needed(self, new_value_size: float) -> None:
        """
        如果需要，淘汰缓存条目
        
        参数:
            new_value_size: 新值的大小（MB）
        """
        # 检查是否需要淘汰
        while (len(self.key_cache) > 0 and 
               (len(self.key_cache) >= self.max_cache_size or 
                self.current_memory_usage + new_value_size > self.max_memory_mb)):
            
            # 找到最久未使用的序列
            oldest_seq_id = min(self.last_access_time.items(), key=lambda x: x[1])[0]
            
            # 计算要释放的内存
            key_size = sum(self._get_tensor_size(tensor) for tensor in self.key_cache[oldest_seq_id].values())
            value_size = sum(self._get_tensor_size(tensor) for tensor in self.value_cache[oldest_seq_id].values())
            total_size = key_size + value_size
            
            # 删除缓存
            del self.key_cache[oldest_seq_id]
            del self.value_cache[oldest_seq_id]
            del self.seq_lengths[oldest_seq_id]
            del self.last_access_time[oldest_seq_id]
            
            # 更新内存使用
            self.current_memory_usage -= total_size
            
            # 更新统计信息
            self.cache_stats["evictions"] += 1
            
            self.logger.debug(f"淘汰注意力缓存: seq_id={oldest_seq_id}, 大小={total_size:.2f}MB")
    
    def get(self, seq_id: str) -> Optional[Tuple[Dict[int, torch.Tensor], Dict[int, torch.Tensor], int]]:
        """
        获取注意力缓存
        
        参数:
            seq_id: 序列ID
            
        返回:
            (key_cache, value_cache, seq_length)元组，如果不存在则返回None
        """
        # 检查序列ID是否存在
        if seq_id not in self.key_cache or seq_id not in self.value_cache:
            # 更新统计信息
            self.cache_stats["misses"] += 1
            
            self.logger.debug(f"注意力缓存未命中: {seq_id}")
            return None
        
        # 检查是否过期
        if time.time() - self.last_access_time.get(seq_id, 0) > self.ttl:
            # 删除过期条目
            self.remove(seq_id)
            
            # 更新统计信息
            self.cache_stats["misses"] += 1
            
            self.logger.debug(f"注意力缓存条目过期: {seq_id}")
            return None
        
        # 更新最后访问时间
        self.last_access_time[seq_id] = time.time()
        
        # 更新统计信息
        self.cache_stats["hits"] += 1
        
        self.logger.debug(f"注意力缓存命中: {seq_id}")
        return self.key_cache[seq_id], self.value_cache[seq_id], self.seq_lengths[seq_id]
    
    def put(self, seq_id: str, layer_idx: int, key: torch.Tensor, value: torch.Tensor, seq_length: int) -> None:
        """
        放入注意力缓存
        
        参数:
            seq_id: 序列ID
            layer_idx: 层索引
            key: 键张量
            value: 值张量
            seq_length: 序列长度
        """
        # 如果序列长度超过最大长度，不缓存
        if seq_length > self.max_seq_length:
            self.logger.warning(f"序列长度({seq_length})超过最大长度({self.max_seq_length})，不缓存")
            return
        
        # 将张量移动到指定设备并转换为指定数据类型
        key = key.to(device=self.device, dtype=self._get_dtype())
        value = value.to(device=self.device, dtype=self._get_dtype())
        
        # 计算张量大小
        key_size = self._get_tensor_size(key)
        value_size = self._get_tensor_size(value)
        total_size = key_size + value_size
        
        # 如果需要，淘汰缓存条目
        self._evict_if_needed(total_size)
        
        # 如果序列ID不存在，初始化
        if seq_id not in self.key_cache:
            self.key_cache[seq_id] = {}
            self.value_cache[seq_id] = {}
            self.seq_lengths[seq_id] = seq_length
        
        # 放入缓存
        self.key_cache[seq_id][layer_idx] = key
        self.value_cache[seq_id][layer_idx] = value
        
        # 更新序列长度
        self.seq_lengths[seq_id] = max(self.seq_lengths[seq_id], seq_length)
        
        # 更新最后访问时间
        self.last_access_time[seq_id] = time.time()
        
        # 更新内存使用
        self.current_memory_usage += total_size
        
        # 更新统计信息
        self.cache_stats["inserts"] += 1
        
        self.logger.debug(f"添加注意力缓存条目: {seq_id}, 层={layer_idx}, 大小={total_size:.2f}MB")
    
    def update(self, seq_id: str, layer_idx: int, key: torch.Tensor, value: torch.Tensor, seq_length: int) -> None:
        """
        更新缓存
        
        参数:
            seq_id: 序列ID
            layer_idx: 层索引
            key: 键张量
            value: 值张量
            seq_length: 序列长度
        """
        # 检查序列ID是否存在
        if seq_id not in self.key_cache or seq_id not in self.value_cache:
            # 如果不存在，直接放入缓存
            self.put(seq_id, layer_idx, key, value, seq_length)
            return
        
        # 如果序列长度超过最大长度，不更新
        if seq_length > self.max_seq_length:
            self.logger.warning(f"序列长度({seq_length})超过最大长度({self.max_seq_length})，不更新缓存")
            return
        
        # 将张量移动到指定设备并转换为指定数据类型
        key = key.to(device=self.device, dtype=self._get_dtype())
        value = value.to(device=self.device, dtype=self._get_dtype())
        
        # 计算张量大小
        key_size = self._get_tensor_size(key)
        value_size = self._get_tensor_size(value)
        total_size = key_size + value_size
        
        # 计算旧张量大小
        old_key_size = 0
        old_value_size = 0
        if layer_idx in self.key_cache[seq_id]:
            old_key_size = self._get_tensor_size(self.key_cache[seq_id][layer_idx])
        if layer_idx in self.value_cache[seq_id]:
            old_value_size = self._get_tensor_size(self.value_cache[seq_id][layer_idx])
        old_total_size = old_key_size + old_value_size
        
        # 计算内存变化
        memory_delta = total_size - old_total_size
        
        # 如果需要，淘汰缓存条目
        if memory_delta > 0:
            self._evict_if_needed(memory_delta)
        
        # 更新缓存
        self.key_cache[seq_id][layer_idx] = key
        self.value_cache[seq_id][layer_idx] = value
        
        # 更新序列长度
        self.seq_lengths[seq_id] = max(self.seq_lengths[seq_id], seq_length)
        
        # 更新最后访问时间
        self.last_access_time[seq_id] = time.time()
        
        # 更新内存使用
        self.current_memory_usage += memory_delta
        
        # 更新统计信息
        self.cache_stats["updates"] = self.cache_stats.get("updates", 0) + 1
        
        self.logger.debug(f"更新注意力缓存条目: {seq_id}, 层={layer_idx}, 大小变化={memory_delta:.2f}MB")
    
    def remove(self, seq_id: str) -> None:
        """
        从缓存中删除序列
        
        参数:
            seq_id: 序列ID
        """
        # 检查序列ID是否存在
        if seq_id not in self.key_cache or seq_id not in self.value_cache:
            return
        
        # 计算内存使用
        memory_usage = 0
        for layer_idx in self.key_cache[seq_id]:
            memory_usage += self._get_tensor_size(self.key_cache[seq_id][layer_idx])
        for layer_idx in self.value_cache[seq_id]:
            memory_usage += self._get_tensor_size(self.value_cache[seq_id][layer_idx])
        
        # 删除缓存条目
        del self.key_cache[seq_id]
        del self.value_cache[seq_id]
        del self.seq_lengths[seq_id]
        del self.last_access_time[seq_id]
        
        # 更新内存使用
        self.current_memory_usage -= memory_usage
        
        # 更新统计信息
        self.cache_stats["evictions"] += 1
        
        self.logger.debug(f"删除注意力缓存条目: {seq_id}, 释放内存={memory_usage:.2f}MB")
    
    def clear(self) -> None:
        """清空缓存"""
        self.key_cache.clear()
        self.value_cache.clear()
        self.seq_lengths.clear()
        self.last_access_time.clear()
        
        self.current_memory_usage = 0
        
        # 重置统计信息
        for key in self.cache_stats:
            self.cache_stats[key] = 0
        
        self.logger.info("清空注意力缓存")
    
    def get_cache_type(self) -> str:
        """
        获取缓存类型
        
        返回:
            缓存类型
        """
        return "attention"
    
    def get_cache_size(self) -> int:
        """
        获取缓存大小
        
        返回:
            缓存大小（序列数）
        """
        return len(self.key_cache)
    
    def get_memory_usage(self) -> float:
        """
        获取缓存内存占用
        
        返回:
            内存占用（MB）
        """
        return self.current_memory_usage
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        返回:
            缓存统计信息
        """
        stats = self.cache_stats.copy()
        stats["cache_size"] = self.get_cache_size()
        stats["memory_usage"] = self.get_memory_usage()
        
        # 计算命中率
        total_requests = stats["hits"] + stats["misses"]
        if total_requests > 0:
            stats["hit_ratio"] = stats["hits"] / total_requests
        else:
            stats["hit_ratio"] = 0.0
        
        return stats


class InferenceResultCachingMechanism(BaseCachingMechanism):
    """
    推理结果缓存机制
    缓存模型推理的最终结果，避免重复计算
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化推理结果缓存机制
        
        参数:
            config: 配置字典，包含以下字段:
                - max_cache_size: 最大缓存大小（条目数），默认为10000
                - max_memory_mb: 最大内存占用（MB），默认为8000
                - eviction_policy: 缓存淘汰策略，可选值为'lru', 'lfu'，默认为'lru'
                - ttl: 缓存条目生存时间（秒），默认为86400（1天）
                - device: 缓存设备，可选值为'cpu', 'cuda'，默认为'cpu'
                - use_disk_cache: 是否使用磁盘缓存，默认为False
                - disk_cache_dir: 磁盘缓存目录，默认为'./cache'
        """
        super().__init__(config)
        
        self.max_cache_size = self.config.get("max_cache_size", 10000)
        self.max_memory_mb = self.config.get("max_memory_mb", 8000)
        self.eviction_policy = self.config.get("eviction_policy", "lru")
        self.ttl = self.config.get("ttl", 86400)  # 默认1天
        self.device = self.config.get("device", "cpu")
        self.use_disk_cache = self.config.get("use_disk_cache", False)
        self.disk_cache_dir = self.config.get("disk_cache_dir", "./cache")
        
        # 初始化缓存
        self.memory_cache = None
        self.disk_cache = None
        self.cache_stats = None
        self.current_memory_usage = 0
        self.initialize()
        
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        super()._validate_config()
        
        # 检查缓存淘汰策略
        valid_eviction_policies = ["lru", "lfu"]
        if self.config.get("eviction_policy") not in [None, *valid_eviction_policies]:
            raise ValueError(f"缓存淘汰策略必须是以下之一: {valid_eviction_policies}")
        
        # 检查设备
        valid_devices = ["cpu", "cuda"]
        if self.config.get("device") not in [None, *valid_devices]:
            raise ValueError(f"设备必须是以下之一: {valid_devices}")
    
    def initialize(self) -> None:
        """初始化缓存"""
        if self.eviction_policy == "lru":
            # 使用OrderedDict实现LRU缓存
            self.memory_cache = OrderedDict()
        else:
            # 使用字典实现LFU缓存
            self.memory_cache = {}
        
        # 初始化磁盘缓存
        if self.use_disk_cache:
            try:
                os.makedirs(self.disk_cache_dir, exist_ok=True)
                self.logger.info(f"初始化磁盘缓存目录: {self.disk_cache_dir}")
            except Exception as e:
                self.logger.error(f"创建磁盘缓存目录失败: {str(e)}")
                # 禁用磁盘缓存
                self.use_disk_cache = False
        
        # 缓存统计信息
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "inserts": 0,
            "memory_usage": 0,
            "disk_hits": 0,
            "disk_misses": 0,
            "disk_writes": 0
        }
        
        # 对于LFU缓存，额外记录访问频率
        if self.eviction_policy == "lfu":
            self.access_frequency = {}
            self.access_time = {}
        
        self.current_memory_usage = 0
        self.logger.info(f"初始化推理结果缓存，最大大小={self.max_cache_size}，最大内存={self.max_memory_mb}MB，使用磁盘缓存={self.use_disk_cache}")
    
    def _generate_key(self, key: Any) -> str:
        """
        生成缓存键
        
        参数:
            key: 原始键
            
        返回:
            缓存键
        """
        if isinstance(key, str):
            return hashlib.md5(key.encode()).hexdigest()
        elif isinstance(key, (int, float, bool)):
            return hashlib.md5(str(key).encode()).hexdigest()
        elif isinstance(key, torch.Tensor):
            # 对于张量，使用其哈希值作为键
            tensor_bytes = key.cpu().numpy().tobytes()
            return hashlib.md5(tensor_bytes).hexdigest()
        elif isinstance(key, (list, tuple)):
            # 对于列表和元组，递归处理每个元素
            return hashlib.md5(str([self._generate_key(item) for item in key]).encode()).hexdigest()
        elif isinstance(key, dict):
            # 对于字典，递归处理每个键值对
            sorted_items = sorted(key.items())
            return hashlib.md5(str({self._generate_key(k): self._generate_key(v) for k, v in sorted_items}).encode()).hexdigest()
        else:
            # 对于其他类型，使用其字符串表示
            return hashlib.md5(str(key).encode()).hexdigest()
    
    def _get_value_size(self, value: Any) -> float:
        """
        获取值大小（MB）
        
        参数:
            value: 值
            
        返回:
            值大小（MB）
        """
        if isinstance(value, torch.Tensor):
            return value.nelement() * value.element_size() / (1024 * 1024)
        elif isinstance(value, (list, tuple)):
            # 对于列表和元组，递归计算每个元素的大小
            return sum(self._get_value_size(item) for item in value)
        elif isinstance(value, dict):
            # 对于字典，递归计算每个值的大小
            return sum(self._get_value_size(v) for v in value.values())
        elif isinstance(value, np.ndarray):
            # 对于NumPy数组，计算其大小
            return value.nbytes / (1024 * 1024)
        else:
            # 对于其他类型，估计其大小
            try:
                return len(str(value)) / (1024 * 1024)
            except:
                return 0.001  # 默认大小为1KB
    
    def _evict_if_needed(self, new_value_size: float) -> None:
        """
        如果需要，淘汰缓存条目
        
        参数:
            new_value_size: 新值的大小（MB）
        """
        # 检查是否需要淘汰
        while (len(self.memory_cache) > 0 and 
               (len(self.memory_cache) >= self.max_cache_size or 
                self.current_memory_usage + new_value_size > self.max_memory_mb)):
            
            if self.eviction_policy == "lru":
                # LRU淘汰策略：淘汰最久未使用的条目
                key, (value, timestamp, metadata) = self.memory_cache.popitem(last=False)
            else:
                # LFU淘汰策略：淘汰使用频率最低的条目
                min_freq = min(self.access_frequency.values())
                min_freq_keys = [k for k, v in self.access_frequency.items() if v == min_freq]
                
                # 如果有多个最低频率的条目，选择最早访问的
                oldest_key = min(
                    min_freq_keys,
                    key=lambda k: self.access_time.get(k, 0)
                )
                
                # 删除条目
                key = oldest_key
                value, timestamp, metadata = self.memory_cache.pop(key)
                self.access_frequency.pop(key)
                self.access_time.pop(key)
            
            # 如果使用磁盘缓存，将淘汰的条目写入磁盘
            if self.use_disk_cache:
                self._write_to_disk(key, value, timestamp, metadata)
            
            # 更新内存使用
            value_size = self._get_value_size(value)
            self.current_memory_usage -= value_size
            
            # 更新统计信息
            self.cache_stats["evictions"] += 1
            
            self.logger.debug(f"淘汰推理结果缓存: {key}, 大小={value_size:.2f}MB")
    
    def _write_to_disk(self, key: str, value: Any, timestamp: float, metadata: Dict[str, Any]) -> None:
        """
        将缓存条目写入磁盘
        
        参数:
            key: 缓存键
            value: 缓存值
            timestamp: 时间戳
            metadata: 元数据
        """
        if not self.use_disk_cache:
            return
        
        # 构造文件路径
        file_path = os.path.join(self.disk_cache_dir, f"{key}.cache")
        
        try:
            # 将值转换为可序列化的格式
            if isinstance(value, torch.Tensor):
                value_dict = {
                    "type": "tensor",
                    "data": value.cpu().numpy().tolist(),
                    "shape": value.shape,
                    "dtype": str(value.dtype)
                }
            elif isinstance(value, np.ndarray):
                value_dict = {
                    "type": "ndarray",
                    "data": value.tolist(),
                    "shape": value.shape,
                    "dtype": str(value.dtype)
                }
            else:
                value_dict = {
                    "type": "other",
                    "data": value
                }
            
            # 构造缓存条目
            cache_entry = {
                "value": value_dict,
                "timestamp": timestamp,
                "metadata": metadata
            }
            
            # 写入文件
            with open(file_path, "w") as f:
                json.dump(cache_entry, f)
            
            # 更新统计信息
            self.cache_stats["disk_writes"] += 1
            
            self.logger.debug(f"写入磁盘缓存: {key}")
        except Exception as e:
            self.logger.error(f"写入磁盘缓存失败: {key}, 错误: {str(e)}")
    
    def _read_from_disk(self, key: str) -> Optional[Tuple[Any, float, Dict[str, Any]]]:
        """
        从磁盘读取缓存条目
        
        参数:
            key: 缓存键
            
        返回:
            (value, timestamp, metadata)元组，如果不存在则返回None
        """
        if not self.use_disk_cache:
            return None
        
        # 构造文件路径
        file_path = os.path.join(self.disk_cache_dir, f"{key}.cache")
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            # 更新统计信息
            self.cache_stats["disk_misses"] += 1
            
            self.logger.debug(f"磁盘缓存未命中: {key}")
            return None
        
        try:
            # 读取文件
            with open(file_path, "r") as f:
                cache_entry = json.load(f)
            
            # 解析缓存条目
            value_dict = cache_entry["value"]
            timestamp = cache_entry["timestamp"]
            metadata = cache_entry["metadata"]
            
            # 将值转换回原始格式
            if value_dict["type"] == "tensor":
                data = np.array(value_dict["data"])
                value = torch.tensor(data)
                if self.device == "cuda" and torch.cuda.is_available():
                    value = value.cuda()
            elif value_dict["type"] == "ndarray":
                value = np.array(value_dict["data"])
            else:
                value = value_dict["data"]
            
            # 更新统计信息
            self.cache_stats["disk_hits"] += 1
            
            self.logger.debug(f"磁盘缓存命中: {key}")
            return value, timestamp, metadata
        except Exception as e:
            self.logger.error(f"读取磁盘缓存失败: {key}, 错误: {str(e)}")
            return None
    
    def get(self, key: Any) -> Optional[Any]:
        """
        获取缓存
        
        参数:
            key: 缓存键
            
        返回:
            缓存值，如果不存在则返回None
        """
        cache_key = self._generate_key(key)
        
        # 检查内存缓存是否存在
        if cache_key in self.memory_cache:
            value, timestamp, metadata = self.memory_cache[cache_key]
            
            # 检查是否过期
            if time.time() - timestamp > self.ttl:
                # 删除过期条目
                self.memory_cache.pop(cache_key)
                if self.eviction_policy == "lfu":
                    self.access_frequency.pop(cache_key, None)
                    self.access_time.pop(cache_key, None)
                
                # 更新内存使用
                value_size = self._get_value_size(value)
                self.current_memory_usage -= value_size
                
                # 更新统计信息
                self.cache_stats["evictions"] += 1
                self.cache_stats["misses"] += 1
                
                self.logger.debug(f"缓存条目过期: {cache_key}")
                
                # 尝试从磁盘缓存获取
                if self.use_disk_cache:
                    disk_result = self._read_from_disk(cache_key)
                    if disk_result is not None:
                        disk_value, disk_timestamp, disk_metadata = disk_result
                        
                        # 检查磁盘缓存是否过期
                        if time.time() - disk_timestamp > self.ttl:
                            self.logger.debug(f"磁盘缓存条目过期: {cache_key}")
                            return None
                        
                        # 将磁盘缓存加载到内存
                        self.put(key, disk_value, disk_metadata)
                        return disk_value
                
                return None
            
            # 更新LRU顺序或LFU频率
            if self.eviction_policy == "lru":
                # 将条目移到队尾
                self.memory_cache.move_to_end(cache_key)
            else:
                # 增加访问频率
                self.access_frequency[cache_key] = self.access_frequency.get(cache_key, 0) + 1
                self.access_time[cache_key] = time.time()
            
            # 更新统计信息
            self.cache_stats["hits"] += 1
            
            self.logger.debug(f"缓存命中: {cache_key}")
            return value
        else:
            # 尝试从磁盘缓存获取
            if self.use_disk_cache:
                disk_result = self._read_from_disk(cache_key)
                if disk_result is not None:
                    disk_value, disk_timestamp, disk_metadata = disk_result
                    
                    # 检查磁盘缓存是否过期
                    if time.time() - disk_timestamp > self.ttl:
                        self.logger.debug(f"磁盘缓存条目过期: {cache_key}")
                    else:
                        # 将磁盘缓存加载到内存
                        self.put(key, disk_value, disk_metadata)
                        return disk_value
            
            # 更新统计信息
            self.cache_stats["misses"] += 1
            
            self.logger.debug(f"缓存未命中: {cache_key}")
            return None
    
    def put(self, key: Any, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        放入缓存
        
        参数:
            key: 缓存键
            value: 缓存值
            metadata: 元数据，默认为空字典
        """
        if metadata is None:
            metadata = {}
        
        cache_key = self._generate_key(key)
        
        # 计算值大小
        value_size = self._get_value_size(value)
        
        # 如果单个值超过最大内存限制，不缓存到内存
        if value_size > self.max_memory_mb:
            self.logger.warning(f"值大小({value_size:.2f}MB)超过最大内存限制({self.max_memory_mb}MB)，不缓存到内存")
            
            # 如果使用磁盘缓存，直接写入磁盘
            if self.use_disk_cache:
                timestamp = time.time()
                self._write_to_disk(cache_key, value, timestamp, metadata)
            
            return
        
        # 如果需要，淘汰缓存条目
        self._evict_if_needed(value_size)
        
        # 将值移动到指定设备
        if isinstance(value, torch.Tensor):
            if self.device == "cuda" and torch.cuda.is_available():
                value = value.to(device="cuda")
            else:
                value = value.to(device="cpu")
        
        # 添加到缓存
        timestamp = time.time()
        self.memory_cache[cache_key] = (value, timestamp, metadata)
        
        # 对于LFU缓存，初始化访问频率
        if self.eviction_policy == "lfu":
            self.access_frequency[cache_key] = 1
            self.access_time[cache_key] = timestamp
        
        # 更新内存使用
        self.current_memory_usage += value_size
        
        # 更新统计信息
        self.cache_stats["inserts"] += 1
        self.cache_stats["memory_usage"] = self.current_memory_usage
        
        self.logger.debug(f"添加缓存条目: {cache_key}, 大小={value_size:.2f}MB")
    
    def clear(self) -> None:
        """清空缓存"""
        self.memory_cache.clear()
        if self.eviction_policy == "lfu":
            self.access_frequency.clear()
            self.access_time.clear()
        
        self.current_memory_usage = 0
        
        # 清空磁盘缓存
        if self.use_disk_cache:
            try:
                if os.path.exists(self.disk_cache_dir):
                    for file_name in os.listdir(self.disk_cache_dir):
                        if file_name.endswith(".cache") or file_name.endswith(".pt"):
                            os.remove(os.path.join(self.disk_cache_dir, file_name))
            except Exception as e:
                self.logger.error(f"清空磁盘缓存失败: {str(e)}")
        
        # 重置统计信息
        for key in self.cache_stats:
            self.cache_stats[key] = 0
        
        self.logger.info("清空推理结果缓存")
    
    def get_cache_type(self) -> str:
        """
        获取缓存类型
        
        返回:
            缓存类型
        """
        cache_type = f"inference_result_{self.eviction_policy}"
        if self.use_disk_cache:
            cache_type += "_disk"
        return cache_type
    
    def get_cache_size(self) -> int:
        """
        获取缓存大小
        
        返回:
            缓存大小（条目数）
        """
        return len(self.memory_cache)
    
    def get_memory_usage(self) -> float:
        """
        获取缓存内存占用
        
        返回:
            内存占用（MB）
        """
        return self.current_memory_usage
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        返回:
            缓存统计信息
        """
        stats = self.cache_stats.copy()
        stats["cache_size"] = self.get_cache_size()
        stats["memory_usage"] = self.get_memory_usage()
        
        # 计算命中率
        total_requests = stats["hits"] + stats["misses"]
        if total_requests > 0:
            stats["hit_ratio"] = stats["hits"] / total_requests
        else:
            stats["hit_ratio"] = 0.0
        
        # 计算磁盘命中率
        if self.use_disk_cache:
            total_disk_requests = stats["disk_hits"] + stats["disk_misses"]
            if total_disk_requests > 0:
                stats["disk_hit_ratio"] = stats["disk_hits"] / total_disk_requests
            else:
                stats["disk_hit_ratio"] = 0.0
        
        return stats


class PrefixCachingMechanism(BaseCachingMechanism):
    """
    前缀缓存机制
    缓存输入前缀的中间状态，加速相似前缀的推理
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化前缀缓存机制
        
        参数:
            config: 配置字典，包含以下字段:
                - max_cache_size: 最大缓存大小（条目数），默认为100
                - max_memory_mb: 最大内存占用（MB），默认为4000
                - max_prefix_length: 最大前缀长度，默认为128
                - device: 缓存设备，可选值为'cpu', 'cuda'，默认为'cuda'
                - dtype: 数据类型，可选值为'float32', 'float16', 'bfloat16'，默认为'float16'
        """
        super().__init__(config)
        
        self.max_cache_size = self.config.get("max_cache_size", 100)
        self.max_memory_mb = self.config.get("max_memory_mb", 4000)
        self.max_prefix_length = self.config.get("max_prefix_length", 128)
        self.device = self.config.get("device", "cuda")
        self.dtype = self.config.get("dtype", "float16")
        
        # 初始化缓存
        self.prefix_cache = OrderedDict()
        self.current_memory_usage = 0
        
        # 缓存统计信息
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "inserts": 0,
            "memory_usage": 0
        }
        
        self.logger.info(f"初始化前缀缓存，最大大小={self.max_cache_size}，最大内存={self.max_memory_mb}MB")
    
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        super()._validate_config()
        
        # 检查设备
        valid_devices = ["cpu", "cuda"]
        if self.config.get("device") not in [None, *valid_devices]:
            raise ValueError(f"设备必须是以下之一: {valid_devices}")
        
        # 检查数据类型
        valid_dtypes = ["float32", "float16", "bfloat16"]
        if self.config.get("dtype") not in [None, *valid_dtypes]:
            raise ValueError(f"数据类型必须是以下之一: {valid_dtypes}")
    
    def _get_dtype(self) -> torch.dtype:
        """
        获取数据类型
        
        返回:
            数据类型
        """
        if self.dtype == "float32":
            return torch.float32
        elif self.dtype == "float16":
            return torch.float16
        elif self.dtype == "bfloat16":
            return torch.bfloat16
        else:
            return torch.float16
    
    def _get_tensor_size(self, tensor: torch.Tensor) -> float:
        """
        获取张量大小（MB）
        
        参数:
            tensor: 张量
            
        返回:
            张量大小（MB）
        """
        return tensor.nelement() * tensor.element_size() / (1024 * 1024)
    
    def _get_prefix_size(self, prefix_states: Dict[str, torch.Tensor]) -> float:
        """
        获取前缀状态大小（MB）
        
        参数:
            prefix_states: 前缀状态
            
        返回:
            前缀状态大小（MB）
        """
        return sum(self._get_tensor_size(tensor) for tensor in prefix_states.values())
    
    def _evict_if_needed(self, new_value_size: float) -> None:
        """
        如果需要，淘汰缓存条目
        
        参数:
            new_value_size: 新值的大小（MB）
        """
        # 检查是否需要淘汰
        while (len(self.prefix_cache) > 0 and 
               (len(self.prefix_cache) >= self.max_cache_size or 
                self.current_memory_usage + new_value_size > self.max_memory_mb)):
            
            # LRU淘汰策略：淘汰最久未使用的条目
            prefix, (prefix_states, timestamp) = self.prefix_cache.popitem(last=False)
            
            # 更新内存使用
            prefix_size = self._get_prefix_size(prefix_states)
            self.current_memory_usage -= prefix_size
            
            # 更新统计信息
            self.cache_stats["evictions"] += 1
            
            self.logger.debug(f"淘汰前缀缓存: {prefix}, 大小={prefix_size:.2f}MB")
    
    def get(self, prefix: torch.Tensor) -> Optional[Dict[str, torch.Tensor]]:
        """
        获取前缀缓存
        
        参数:
            prefix: 前缀张量
            
        返回:
            前缀状态，如果不存在则返回None
        """
        # 将前缀转换为字符串
        prefix_str = str(prefix.cpu().numpy().tobytes())
        
        # 检查缓存是否存在
        if prefix_str in self.prefix_cache:
            prefix_states, timestamp = self.prefix_cache[prefix_str]
            
            # 更新LRU顺序
            self.prefix_cache.move_to_end(prefix_str)
            
            # 更新统计信息
            self.cache_stats["hits"] += 1
            
            self.logger.debug(f"前缀缓存命中: {prefix_str[:20]}...")
            return prefix_states
        else:
            # 更新统计信息
            self.cache_stats["misses"] += 1
            
            self.logger.debug(f"前缀缓存未命中: {prefix_str[:20]}...")
            return None
    
    def put(self, prefix: torch.Tensor, prefix_states: Dict[str, torch.Tensor]) -> None:
        """
        放入前缀缓存
        
        参数:
            prefix: 前缀张量
            prefix_states: 前缀状态
        """
        # 检查前缀长度
        if prefix.size(1) > self.max_prefix_length:
            self.logger.warning(f"前缀长度({prefix.size(1)})超过最大长度({self.max_prefix_length})，不缓存")
            return
        
        # 将前缀转换为字符串
        prefix_str = str(prefix.cpu().numpy().tobytes())
        
        # 计算前缀状态大小
        prefix_size = self._get_prefix_size(prefix_states)
        
        # 如果单个值超过最大内存限制，不缓存
        if prefix_size > self.max_memory_mb:
            self.logger.warning(f"前缀状态大小({prefix_size:.2f}MB)超过最大内存限制({self.max_memory_mb}MB)，不缓存")
            return
        
        # 如果需要，淘汰缓存条目
        self._evict_if_needed(prefix_size)
        
        # 将前缀状态移动到指定设备和数据类型
        dtype = self._get_dtype()
        processed_states = {}
        for key, tensor in prefix_states.items():
            if isinstance(tensor, torch.Tensor):
                if self.device == "cuda" and torch.cuda.is_available():
                    processed_states[key] = tensor.to(device="cuda", dtype=dtype)
                else:
                    processed_states[key] = tensor.to(device="cpu", dtype=dtype)
            else:
                processed_states[key] = tensor
        
        # 添加到缓存
        timestamp = time.time()
        self.prefix_cache[prefix_str] = (processed_states, timestamp)
        
        # 更新内存使用
        self.current_memory_usage += prefix_size
        
        # 更新统计信息
        self.cache_stats["inserts"] += 1
        self.cache_stats["memory_usage"] = self.current_memory_usage
        
        self.logger.debug(f"添加前缀缓存: {prefix_str[:20]}..., 大小={prefix_size:.2f}MB")
    
    def clear(self) -> None:
        """清空缓存"""
        self.prefix_cache.clear()
        self.current_memory_usage = 0
        
        # 重置统计信息
        for key in self.cache_stats:
            self.cache_stats[key] = 0
        
        self.logger.info("清空前缀缓存")
    
    def get_cache_type(self) -> str:
        """
        获取缓存类型
        
        返回:
            缓存类型
        """
        return "prefix"
    
    def get_cache_size(self) -> int:
        """
        获取缓存大小
        
        返回:
            缓存大小（条目数）
        """
        return len(self.prefix_cache)
    
    def get_memory_usage(self) -> float:
        """
        获取缓存内存占用
        
        返回:
            内存占用（MB）
        """
        return self.current_memory_usage
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        返回:
            缓存统计信息
        """
        stats = self.cache_stats.copy()
        stats["cache_size"] = self.get_cache_size()
        stats["memory_usage"] = self.get_memory_usage()
        
        # 计算命中率
        total_requests = stats["hits"] + stats["misses"]
        if total_requests > 0:
            stats["hit_ratio"] = stats["hits"] / total_requests
        else:
            stats["hit_ratio"] = 0.0
        
        return stats


class AdaptiveCachingStrategy(BaseCachingMechanism):
    """
    自适应缓存策略
    根据内存使用情况和缓存命中率动态调整缓存策略
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化自适应缓存策略
        
        参数:
            config: 配置字典，包含以下字段:
                - max_memory_mb: 最大内存占用（MB），默认为8000
                - target_hit_ratio: 目标命中率，默认为0.8
                - adjustment_interval: 调整间隔（秒），默认为60
                - cache_types: 缓存类型列表，可选值为'kv', 'attention', 'prefix', 'inference_result'，默认为全部
                - kv_cache_config: KV缓存配置
                - attention_cache_config: 注意力缓存配置
                - prefix_cache_config: 前缀缓存配置
                - inference_result_cache_config: 推理结果缓存配置
        """
        super().__init__(config)
        
        self.max_memory_mb = self.config.get("max_memory_mb", 8000)
        self.target_hit_ratio = self.config.get("target_hit_ratio", 0.8)
        self.adjustment_interval = self.config.get("adjustment_interval", 60)
        self.cache_types = self.config.get("cache_types", ["kv", "attention", "prefix", "inference_result"])
        
        # 初始化缓存
        self.caches = {}
        self.last_adjustment_time = time.time()
        self.initialize_caches()
        
        # 缓存统计信息
        self.cache_stats = {
            "total_hits": 0,
            "total_misses": 0,
            "total_memory_usage": 0,
            "cache_specific_stats": {}
        }
        
        self.logger.info(f"初始化自适应缓存策略，最大内存={self.max_memory_mb}MB，目标命中率={self.target_hit_ratio}")
    
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        super()._validate_config()
        
        # 检查缓存类型
        valid_cache_types = ["kv", "attention", "prefix", "inference_result"]
        for cache_type in self.cache_types:
            if cache_type not in valid_cache_types:
                raise ValueError(f"缓存类型必须是以下之一: {valid_cache_types}")
        
        # 检查目标命中率
        if not 0 <= self.target_hit_ratio <= 1:
            raise ValueError("目标命中率必须在0到1之间")
    
    def initialize_caches(self) -> None:
        """初始化缓存"""
        # 初始化KV缓存
        if "kv" in self.cache_types:
            kv_cache_config = self.config.get("kv_cache_config", {})
            self.caches["kv"] = KVCachingMechanism(kv_cache_config)
        
        # 初始化注意力缓存
        if "attention" in self.cache_types:
            attention_cache_config = self.config.get("attention_cache_config", {})
            self.caches["attention"] = AttentionCachingMechanism(attention_cache_config)
        
        # 初始化前缀缓存
        if "prefix" in self.cache_types:
            prefix_cache_config = self.config.get("prefix_cache_config", {})
            self.caches["prefix"] = PrefixCachingMechanism(prefix_cache_config)
        
        # 初始化推理结果缓存
        if "inference_result" in self.cache_types:
            inference_result_cache_config = self.config.get("inference_result_cache_config", {})
            self.caches["inference_result"] = InferenceResultCachingMechanism(inference_result_cache_config)
    
    def adjust_cache_sizes(self) -> None:
        """调整缓存大小"""
        current_time = time.time()
        
        # 检查是否需要调整
        if current_time - self.last_adjustment_time < self.adjustment_interval:
            return
        
        self.last_adjustment_time = current_time
        
        # 获取所有缓存的统计信息
        cache_stats = {}
        total_memory_usage = 0
        total_hit_ratio = 0
        cache_count = 0
        
        for cache_type, cache in self.caches.items():
            stats = cache.get_stats()
            cache_stats[cache_type] = stats
            total_memory_usage += stats.get("memory_usage", 0)
            
            # 计算命中率
            hits = stats.get("hits", 0)
            misses = stats.get("misses", 0)
            total_requests = hits + misses
            if total_requests > 0:
                hit_ratio = hits / total_requests
                total_hit_ratio += hit_ratio
                cache_count += 1
        
        # 计算平均命中率
        avg_hit_ratio = total_hit_ratio / cache_count if cache_count > 0 else 0
        
        # 检查是否需要调整
        if avg_hit_ratio < self.target_hit_ratio:
            # 命中率低于目标，增加缓存大小
            self.logger.info(f"平均命中率({avg_hit_ratio:.2%})低于目标({self.target_hit_ratio:.2%})，增加缓存大小")
            
            # 按命中率从低到高排序缓存
            sorted_caches = sorted(
                [(cache_type, cache) for cache_type, cache in self.caches.items()],
                key=lambda x: cache_stats[x[0]].get("hit_ratio", 0)
            )
            
            # 增加命中率最低的缓存的大小
            for cache_type, cache in sorted_caches:
                if cache_type == "kv":
                    # 增加KV缓存大小
                    current_size = cache.max_cache_size
                    new_size = int(current_size * 1.2)  # 增加20%
                    cache.max_cache_size = new_size
                    self.logger.info(f"增加KV缓存大小: {current_size} -> {new_size}")
                elif cache_type == "attention":
                    # 增加注意力缓存大小
                    current_size = cache.max_cache_size
                    new_size = int(current_size * 1.2)  # 增加20%
                    cache.max_cache_size = new_size
                    self.logger.info(f"增加注意力缓存大小: {current_size} -> {new_size}")
                elif cache_type == "prefix":
                    # 增加前缀缓存大小
                    current_size = cache.max_cache_size
                    new_size = int(current_size * 1.2)  # 增加20%
                    cache.max_cache_size = new_size
                    self.logger.info(f"增加前缀缓存大小: {current_size} -> {new_size}")
                elif cache_type == "inference_result":
                    # 增加推理结果缓存大小
                    current_size = cache.max_cache_size
                    new_size = int(current_size * 1.2)  # 增加20%
                    cache.max_cache_size = new_size
                    self.logger.info(f"增加推理结果缓存大小: {current_size} -> {new_size}")
                
                # 只调整一个缓存，然后等待下一次调整
                break
        elif total_memory_usage > self.max_memory_mb:
            # 内存使用超过限制，减少缓存大小
            self.logger.info(f"总内存使用({total_memory_usage:.2f}MB)超过限制({self.max_memory_mb}MB)，减少缓存大小")
            
            # 按命中率从低到高排序缓存
            sorted_caches = sorted(
                [(cache_type, cache) for cache_type, cache in self.caches.items()],
                key=lambda x: cache_stats[x[0]].get("hit_ratio", 0)
            )
            
            # 减少命中率最低的缓存的大小
            for cache_type, cache in sorted_caches:
                if cache_type == "kv":
                    # 减少KV缓存大小
                    current_size = cache.max_cache_size
                    new_size = int(current_size * 0.8)  # 减少20%
                    cache.max_cache_size = max(10, new_size)  # 确保至少有10个条目
                    self.logger.info(f"减少KV缓存大小: {current_size} -> {cache.max_cache_size}")
                elif cache_type == "attention":
                    # 减少注意力缓存大小
                    current_size = cache.max_cache_size
                    new_size = int(current_size * 0.8)  # 减少20%
                    cache.max_cache_size = max(10, new_size)  # 确保至少有10个条目
                    self.logger.info(f"减少注意力缓存大小: {current_size} -> {cache.max_cache_size}")
                elif cache_type == "prefix":
                    # 减少前缀缓存大小
                    current_size = cache.max_cache_size
                    new_size = int(current_size * 0.8)  # 减少20%
                    cache.max_cache_size = max(10, new_size)  # 确保至少有10个条目
                    self.logger.info(f"减少前缀缓存大小: {current_size} -> {cache.max_cache_size}")
                elif cache_type == "inference_result":
                    # 减少推理结果缓存大小
                    current_size = cache.max_cache_size
                    new_size = int(current_size * 0.8)  # 减少20%
                    cache.max_cache_size = max(10, new_size)  # 确保至少有10个条目
                    self.logger.info(f"减少推理结果缓存大小: {current_size} -> {cache.max_cache_size}")
                
                # 只调整一个缓存，然后等待下一次调整
                break
    
    def get(self, key: Any, cache_type: str = "kv") -> Optional[Any]:
        """
        获取缓存
        
        参数:
            key: 缓存键
            cache_type: 缓存类型，默认为'kv'
            
        返回:
            缓存值，如果不存在则返回None
        """
        # 检查缓存类型是否存在
        if cache_type not in self.caches:
            return None
        
        # 获取缓存
        value = self.caches[cache_type].get(key)
        
        # 更新统计信息
        if value is not None:
            self.cache_stats["total_hits"] += 1
        else:
            self.cache_stats["total_misses"] += 1
        
        # 调整缓存大小
        self.adjust_cache_sizes()
        
        return value
    
    def put(self, key: Any, value: Any, cache_type: str = "kv") -> None:
        """
        放入缓存
        
        参数:
            key: 缓存键
            value: 缓存值
            cache_type: 缓存类型，默认为'kv'
        """
        # 检查缓存类型是否存在
        if cache_type not in self.caches:
            return
        
        # 放入缓存
        self.caches[cache_type].put(key, value)
        
        # 调整缓存大小
        self.adjust_cache_sizes()
    
    def clear(self) -> None:
        """清空缓存"""
        for cache in self.caches.values():
            cache.clear()
        
        # 重置统计信息
        for key in self.cache_stats:
            if key != "cache_specific_stats":
                self.cache_stats[key] = 0
        self.cache_stats["cache_specific_stats"] = {}
        
        self.logger.info("清空所有缓存")
    
    def get_cache_type(self) -> str:
        """
        获取缓存类型
        
        返回:
            缓存类型
        """
        return "adaptive"
    
    def get_cache_size(self) -> int:
        """
        获取缓存大小
        
        返回:
            缓存大小（条目数）
        """
        return sum(cache.get_cache_size() for cache in self.caches.values())
    
    def get_memory_usage(self) -> float:
        """
        获取缓存内存占用
        
        返回:
            内存占用（MB）
        """
        return sum(cache.get_memory_usage() for cache in self.caches.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        返回:
            缓存统计信息
        """
        # 更新缓存特定统计信息
        cache_specific_stats = {}
        for cache_type, cache in self.caches.items():
            cache_specific_stats[cache_type] = cache.get_stats()
        
        # 更新总内存使用
        total_memory_usage = sum(stats.get("memory_usage", 0) for stats in cache_specific_stats.values())
        
        # 更新统计信息
        stats = self.cache_stats.copy()
        stats["cache_size"] = self.get_cache_size()
        stats["memory_usage"] = total_memory_usage
        stats["cache_specific_stats"] = cache_specific_stats
        
        # 计算命中率
        total_requests = stats["total_hits"] + stats["total_misses"]
        if total_requests > 0:
            stats["hit_ratio"] = stats["total_hits"] / total_requests
        else:
            stats["hit_ratio"] = 0.0
        
        return stats
