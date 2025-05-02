"""
缓存管理器
统一管理不同类型的缓存机制
"""

import logging
import os
import gc
import time
from typing import Any, Dict, List, Optional, Tuple, Union, Type

import torch

from .base import BaseCachingMechanism
from .caching import KVCachingMechanism, AttentionCachingMechanism, InferenceResultCachingMechanism


class CacheManager:
    """
    缓存管理器
    统一管理不同类型的缓存机制
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化缓存管理器
        
        参数:
            config: 配置字典，包含以下字段:
                - cache_types: 要启用的缓存类型列表，可选值为'kv', 'attention', 'inference_result'，默认为全部
                - kv_cache_config: KV缓存配置
                - attention_cache_config: 注意力缓存配置
                - inference_result_cache_config: 推理结果缓存配置
                - global_ttl: 全局缓存生存时间（秒），默认为3600
                - global_max_memory_mb: 全局最大内存占用（MB），默认为16000
                - enable_stats: 是否启用统计信息，默认为True
                - stats_interval: 统计信息收集间隔（秒），默认为60
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.cache_types = self.config.get("cache_types", ["kv", "attention", "inference_result"])
        self.global_ttl = self.config.get("global_ttl", 3600)
        self.global_max_memory_mb = self.config.get("global_max_memory_mb", 16000)
        self.enable_stats = self.config.get("enable_stats", True)
        self.stats_interval = self.config.get("stats_interval", 60)
        
        # 初始化缓存
        self.caches = {}
        self.initialize()
        
        # 统计信息
        self.stats = {
            "total_hits": 0,
            "total_misses": 0,
            "total_memory_usage": 0,
            "cache_specific_stats": {}
        }
        self.last_stats_time = time.time()
    
    def initialize(self) -> None:
        """初始化缓存"""
        # 初始化KV缓存
        if "kv" in self.cache_types:
            kv_cache_config = self.config.get("kv_cache_config", {})
            # 应用全局配置
            if "ttl" not in kv_cache_config:
                kv_cache_config["ttl"] = self.global_ttl
            
            self.caches["kv"] = KVCachingMechanism(kv_cache_config)
            self.logger.info("初始化KV缓存")
        
        # 初始化注意力缓存
        if "attention" in self.cache_types:
            attention_cache_config = self.config.get("attention_cache_config", {})
            # 应用全局配置
            if "ttl" not in attention_cache_config:
                attention_cache_config["ttl"] = self.global_ttl
            
            self.caches["attention"] = AttentionCachingMechanism(attention_cache_config)
            self.logger.info("初始化注意力缓存")
        
        # 初始化推理结果缓存
        if "inference_result" in self.cache_types:
            inference_result_cache_config = self.config.get("inference_result_cache_config", {})
            # 应用全局配置
            if "ttl" not in inference_result_cache_config:
                inference_result_cache_config["ttl"] = self.global_ttl
            
            self.caches["inference_result"] = InferenceResultCachingMechanism(inference_result_cache_config)
            self.logger.info("初始化推理结果缓存")
        
        self.logger.info(f"缓存管理器初始化完成，启用的缓存类型: {self.cache_types}")
    
    def get_cache(self, cache_type: str) -> Optional[BaseCachingMechanism]:
        """
        获取指定类型的缓存
        
        参数:
            cache_type: 缓存类型
            
        返回:
            缓存实例，如果不存在则返回None
        """
        return self.caches.get(cache_type)
    
    def get_from_kv_cache(self, key: Any) -> Optional[Any]:
        """
        从KV缓存获取值
        
        参数:
            key: 缓存键
            
        返回:
            缓存值，如果不存在则返回None
        """
        # 检查KV缓存是否启用
        if "kv" not in self.caches:
            self.logger.warning("KV缓存未启用")
            return None
        
        # 获取缓存
        value = self.caches["kv"].get(key)
        
        # 更新统计信息
        if value is not None:
            self.stats["total_hits"] += 1
        else:
            self.stats["total_misses"] += 1
        
        return value
    
    def put_to_kv_cache(self, key: Any, value: Any) -> None:
        """
        放入KV缓存
        
        参数:
            key: 缓存键
            value: 缓存值
        """
        if "kv" not in self.caches:
            return
        
        self.caches["kv"].put(key, value)
    
    def get_from_attention_cache(self, seq_id: str) -> Optional[Tuple[Dict[int, torch.Tensor], Dict[int, torch.Tensor], int]]:
        """
        从注意力缓存获取值
        
        参数:
            seq_id: 序列ID
            
        返回:
            (key_cache, value_cache, seq_length)元组，如果不存在则返回None
        """
        # 检查注意力缓存是否启用
        if "attention" not in self.caches:
            self.logger.warning("注意力缓存未启用")
            return None
        
        # 获取缓存
        result = self.caches["attention"].get(seq_id)
        
        # 更新统计信息
        if result is not None:
            self.stats["total_hits"] += 1
        else:
            self.stats["total_misses"] += 1
        
        return result
    
    def put_to_attention_cache(self, seq_id: str, layer_idx: int, key: torch.Tensor, value: torch.Tensor, seq_length: int) -> None:
        """
        放入注意力缓存
        
        参数:
            seq_id: 序列ID
            layer_idx: 层索引
            key: 键张量
            value: 值张量
            seq_length: 序列长度
        """
        # 检查注意力缓存是否启用
        if "attention" not in self.caches:
            self.logger.warning("注意力缓存未启用")
            return
        
        # 放入缓存
        self.caches["attention"].put(seq_id, layer_idx, key, value, seq_length)
    
    def update_attention_cache(self, seq_id: str, layer_idx: int, key: torch.Tensor, value: torch.Tensor, seq_length: int) -> None:
        """
        更新注意力缓存
        
        参数:
            seq_id: 序列ID
            layer_idx: 层索引
            key: 键张量
            value: 值张量
            seq_length: 序列长度
        """
        # 检查注意力缓存是否启用
        if "attention" not in self.caches:
            self.logger.warning("注意力缓存未启用")
            return
        
        # 更新缓存
        self.caches["attention"].update(seq_id, layer_idx, key, value, seq_length)
    
    def remove_from_attention_cache(self, seq_id: str) -> None:
        """
        从注意力缓存删除序列
        
        参数:
            seq_id: 序列ID
        """
        # 检查注意力缓存是否启用
        if "attention" not in self.caches:
            self.logger.warning("注意力缓存未启用")
            return
        
        # 删除缓存
        self.caches["attention"].remove(seq_id)
    
    def get_from_inference_result_cache(self, key: Any) -> Optional[Any]:
        """
        从推理结果缓存获取值
        
        参数:
            key: 缓存键
            
        返回:
            缓存值，如果不存在则返回None
        """
        # 检查推理结果缓存是否启用
        if "inference_result" not in self.caches:
            self.logger.warning("推理结果缓存未启用")
            return None
        
        # 获取缓存
        value = self.caches["inference_result"].get(key)
        
        # 更新统计信息
        if value is not None:
            self.stats["total_hits"] += 1
        else:
            self.stats["total_misses"] += 1
        
        return value
    
    def put_to_inference_result_cache(self, key: Any, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        放入推理结果缓存
        
        参数:
            key: 缓存键
            value: 缓存值
            metadata: 元数据，默认为None
        """
        # 检查推理结果缓存是否启用
        if "inference_result" not in self.caches:
            self.logger.warning("推理结果缓存未启用")
            return
        
        # 放入缓存
        self.caches["inference_result"].put(key, value, metadata)
    
    def clear_all_caches(self) -> None:
        """清空所有缓存"""
        for cache in self.caches.values():
            cache.clear()
        
        # 强制执行垃圾回收
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self.logger.info("清空所有缓存")
    
    def clear_cache(self, cache_type: str) -> None:
        """
        清空指定类型的缓存
        
        参数:
            cache_type: 缓存类型
        """
        if cache_type in self.caches:
            self.caches[cache_type].clear()
            
            # 强制执行垃圾回收
            gc.collect()
            if torch.cuda.is_available() and cache_type in ["attention", "kv"]:
                torch.cuda.empty_cache()
            
            self.logger.info(f"清空{cache_type}缓存")
    
    def update_stats(self) -> None:
        """更新统计信息"""
        if not self.enable_stats:
            return
        
        # 检查是否需要更新统计信息
        current_time = time.time()
        if current_time - self.last_stats_time < self.stats_interval:
            return
        
        # 更新总内存使用
        total_memory_usage = 0
        cache_specific_stats = {}
        
        for cache_type, cache in self.caches.items():
            # 获取缓存统计信息
            cache_stats = cache.get_stats()
            cache_specific_stats[cache_type] = cache_stats
            
            # 更新总内存使用
            total_memory_usage += cache_stats.get("memory_usage", 0)
        
        # 更新统计信息
        self.stats["total_memory_usage"] = total_memory_usage
        self.stats["cache_specific_stats"] = cache_specific_stats
        
        # 更新最后统计时间
        self.last_stats_time = current_time
        
        # 检查是否超过全局内存限制
        if total_memory_usage > self.global_max_memory_mb:
            self.logger.warning(f"总内存使用({total_memory_usage:.2f}MB)超过全局限制({self.global_max_memory_mb}MB)，考虑清空部分缓存")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        返回:
            统计信息
        """
        # 更新统计信息
        self.update_stats()
        
        # 计算命中率
        total_requests = self.stats["total_hits"] + self.stats["total_misses"]
        if total_requests > 0:
            hit_ratio = self.stats["total_hits"] / total_requests
        else:
            hit_ratio = 0.0
        
        # 构造统计信息
        stats = {
            "total_hits": self.stats["total_hits"],
            "total_misses": self.stats["total_misses"],
            "total_requests": total_requests,
            "hit_ratio": hit_ratio,
            "total_memory_usage": self.stats["total_memory_usage"],
            "cache_specific_stats": self.stats["cache_specific_stats"]
        }
        
        return stats
    
    def print_stats(self) -> None:
        """打印统计信息"""
        stats = self.get_stats()
        
        self.logger.info("缓存统计信息:")
        self.logger.info(f"总命中: {stats['total_hits']}")
        self.logger.info(f"总未命中: {stats['total_misses']}")
        self.logger.info(f"总请求: {stats['total_requests']}")
        self.logger.info(f"命中率: {stats['hit_ratio']:.2%}")
        self.logger.info(f"总内存使用: {stats['total_memory_usage']:.2f}MB")
        
        for cache_type, cache_stats in stats["cache_specific_stats"].items():
            self.logger.info(f"{cache_type}缓存统计信息:")
            self.logger.info(f"  缓存大小: {cache_stats.get('cache_size', 0)}")
            self.logger.info(f"  内存使用: {cache_stats.get('memory_usage', 0):.2f}MB")
            self.logger.info(f"  命中率: {cache_stats.get('hit_ratio', 0):.2%}")
            self.logger.info(f"  命中: {cache_stats.get('hits', 0)}")
            self.logger.info(f"  未命中: {cache_stats.get('misses', 0)}")
            self.logger.info(f"  淘汰: {cache_stats.get('evictions', 0)}")
            
            # 打印磁盘缓存统计信息
            if "disk_hit_ratio" in cache_stats:
                self.logger.info(f"  磁盘命中率: {cache_stats.get('disk_hit_ratio', 0):.2%}")
                self.logger.info(f"  磁盘命中: {cache_stats.get('disk_hits', 0)}")
                self.logger.info(f"  磁盘未命中: {cache_stats.get('disk_misses', 0)}")
                self.logger.info(f"  磁盘写入: {cache_stats.get('disk_writes', 0)}")
    
    def __del__(self) -> None:
        """析构函数"""
        # 清空所有缓存
        try:
            self.clear_all_caches()
        except:
            pass
