"""
数据版本控制系统实现
用于跟踪和管理数据集的版本历史
"""
from typing import Dict, List, Union, Optional, Any, Tuple
import pandas as pd
import numpy as np
import os
import logging
import json
import hashlib
import shutil
from datetime import datetime
import pickle
import warnings
import re

from .base import BaseVersionControl

# 配置日志
logger = logging.getLogger(__name__)


class DataVersionControl(BaseVersionControl):
    """
    数据版本控制系统
    用于跟踪和管理数据集的版本历史
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据版本控制系统
        
        参数:
            config: 配置字典，包含以下字段:
                - storage_path: 版本存储路径，默认为'/data/qlib/versions'
                - metadata_format: 元数据格式，支持'json'、'pickle'，默认为'json'
                - snapshot_format: 快照格式，支持'feather'、'parquet'、'csv'，默认为'feather'
                - max_versions: 最大版本数量，默认为10
                - compression: 压缩方式，支持'zstd'、'gzip'、'none'，默认为'zstd'
                - hash_algorithm: 哈希算法，支持'md5'、'sha256'，默认为'md5'
        """
        super().__init__(config)
        
        # 设置默认配置
        self.storage_path = self.config.get("storage_path", "/data/qlib/versions")
        self.metadata_format = self.config.get("metadata_format", "json")
        self.snapshot_format = self.config.get("snapshot_format", "feather")
        self.max_versions = self.config.get("max_versions", 10)
        self.compression = self.config.get("compression", "zstd")
        self.hash_algorithm = self.config.get("hash_algorithm", "md5")
        
        # 检查存储路径
        os.makedirs(self.storage_path, exist_ok=True)
        
        # 检查压缩方式
        if self.compression == "zstd":
            try:
                import zstandard
                self._zstd_available = True
            except ImportError:
                self._zstd_available = False
                warnings.warn("zstandard未安装，将使用gzip压缩")
                self.compression = "gzip"
        
        # 初始化版本索引
        self._init_version_index()
    
    def _init_version_index(self):
        """初始化版本索引"""
        self.index_path = os.path.join(self.storage_path, "version_index.json")
        
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, "r") as f:
                    self.version_index = json.load(f)
            except Exception as e:
                logger.error(f"加载版本索引失败: {e}")
                self.version_index = {"datasets": {}}
        else:
            self.version_index = {"datasets": {}}
    
    def _save_version_index(self):
        """保存版本索引"""
        try:
            with open(self.index_path, "w") as f:
                json.dump(self.version_index, f, indent=2)
        except Exception as e:
            logger.error(f"保存版本索引失败: {e}")
    
    def _compute_hash(self, data: pd.DataFrame) -> str:
        """
        计算数据的哈希值
        
        参数:
            data: 数据框
            
        返回:
            哈希值
        """
        # 将数据转换为字节
        data_bytes = data.to_csv(index=True).encode()
        
        # 计算哈希值
        if self.hash_algorithm == "md5":
            return hashlib.md5(data_bytes).hexdigest()
        elif self.hash_algorithm == "sha256":
            return hashlib.sha256(data_bytes).hexdigest()
        else:
            return hashlib.md5(data_bytes).hexdigest()
    
    def _get_dataset_path(self, dataset_name: str) -> str:
        """
        获取数据集路径
        
        参数:
            dataset_name: 数据集名称
            
        返回:
            数据集路径
        """
        # 规范化数据集名称
        dataset_name = re.sub(r'[^\w\-\.]', '_', dataset_name)
        return os.path.join(self.storage_path, dataset_name)
    
    def _save_metadata(self, path: str, metadata: Dict[str, Any]) -> None:
        """
        保存元数据
        
        参数:
            path: 保存路径
            metadata: 元数据
        """
        if self.metadata_format == "json":
            with open(path, "w") as f:
                json.dump(metadata, f, indent=2)
        elif self.metadata_format == "pickle":
            with open(path, "wb") as f:
                pickle.dump(metadata, f)
        else:
            with open(path, "w") as f:
                json.dump(metadata, f, indent=2)
    
    def _load_metadata(self, path: str) -> Dict[str, Any]:
        """
        加载元数据
        
        参数:
            path: 元数据路径
            
        返回:
            元数据
        """
        if not os.path.exists(path):
            return {}
        
        if self.metadata_format == "json":
            with open(path, "r") as f:
                return json.load(f)
        elif self.metadata_format == "pickle":
            with open(path, "rb") as f:
                return pickle.load(f)
        else:
            with open(path, "r") as f:
                return json.load(f)
    
    def _save_snapshot(self, path: str, data: pd.DataFrame) -> None:
        """
        保存数据快照
        
        参数:
            path: 保存路径
            data: 数据框
        """
        if self.snapshot_format == "feather":
            try:
                # 检查是否有pyarrow
                import pyarrow
                if self.compression == "zstd" and self._zstd_available:
                    data.to_feather(path, compression="zstd")
                else:
                    data.to_feather(path)
            except ImportError:
                logger.warning("pyarrow未安装，将使用parquet格式")
                if self.compression == "zstd" and self._zstd_available:
                    data.to_parquet(path, compression="zstd")
                else:
                    data.to_parquet(path, compression="gzip")
        
        elif self.snapshot_format == "parquet":
            if self.compression == "zstd" and self._zstd_available:
                data.to_parquet(path, compression="zstd")
            else:
                data.to_parquet(path, compression="gzip")
        
        elif self.snapshot_format == "csv":
            if self.compression == "gzip":
                data.to_csv(path + ".gz", index=True, compression="gzip")
            elif self.compression == "zstd" and self._zstd_available:
                # 使用zstandard手动压缩
                import zstandard as zstd
                csv_data = data.to_csv(index=True).encode()
                compressor = zstd.ZstdCompressor(level=3)
                compressed = compressor.compress(csv_data)
                with open(path + ".zst", "wb") as f:
                    f.write(compressed)
            else:
                data.to_csv(path, index=True)
        
        else:
            logger.warning(f"不支持的快照格式: {self.snapshot_format}，使用feather格式")
            try:
                data.to_feather(path)
            except Exception:
                data.to_csv(path, index=True)
    
    def _load_snapshot(self, path: str) -> pd.DataFrame:
        """
        加载数据快照
        
        参数:
            path: 快照路径
            
        返回:
            数据框
        """
        if not os.path.exists(path):
            # 检查是否有压缩文件
            if os.path.exists(path + ".gz"):
                path = path + ".gz"
                compression = "gzip"
            elif os.path.exists(path + ".zst"):
                path = path + ".zst"
                compression = "zstd"
            else:
                logger.error(f"快照文件不存在: {path}")
                return pd.DataFrame()
        else:
            compression = None
        
        try:
            if self.snapshot_format == "feather":
                return pd.read_feather(path)
            
            elif self.snapshot_format == "parquet":
                return pd.read_parquet(path)
            
            elif self.snapshot_format == "csv":
                if compression == "gzip":
                    return pd.read_csv(path, index_col=0, compression="gzip")
                elif compression == "zstd":
                    # 使用zstandard手动解压
                    import zstandard as zstd
                    with open(path, "rb") as f:
                        compressed_data = f.read()
                    decompressor = zstd.ZstdDecompressor()
                    decompressed_data = decompressor.decompress(compressed_data)
                    return pd.read_csv(pd.io.common.StringIO(decompressed_data.decode()), index_col=0)
                else:
                    return pd.read_csv(path, index_col=0)
            
            else:
                logger.warning(f"不支持的快照格式: {self.snapshot_format}，尝试使用feather格式")
                try:
                    return pd.read_feather(path)
                except Exception:
                    return pd.read_csv(path, index_col=0)
        
        except Exception as e:
            logger.error(f"加载快照失败: {e}")
            return pd.DataFrame()
    
    def save_version(self, dataset_name: str, data: pd.DataFrame, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        保存数据版本
        
        参数:
            dataset_name: 数据集名称
            data: 数据框
            metadata: 元数据，可选
            
        返回:
            版本ID
        """
        # 检查数据
        if not isinstance(data, pd.DataFrame):
            raise TypeError("数据必须是pandas DataFrame类型")
        
        # 获取数据集路径
        dataset_path = self._get_dataset_path(dataset_name)
        os.makedirs(dataset_path, exist_ok=True)
        
        # 计算数据哈希值
        data_hash = self._compute_hash(data)
        
        # 生成版本ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_id = f"{timestamp}_{data_hash[:8]}"
        
        # 创建版本目录
        version_path = os.path.join(dataset_path, version_id)
        os.makedirs(version_path, exist_ok=True)
        
        # 准备元数据
        if metadata is None:
            metadata = {}
        
        metadata.update({
            "version_id": version_id,
            "timestamp": timestamp,
            "data_hash": data_hash,
            "rows": data.shape[0],
            "columns": data.shape[1],
            "column_names": data.columns.tolist(),
            "dtypes": {col: str(dtype) for col, dtype in data.dtypes.items()},
            "has_missing": data.isna().any().any(),
            "missing_count": data.isna().sum().sum(),
            "created_at": datetime.now().isoformat()
        })
        
        # 保存元数据
        metadata_path = os.path.join(version_path, f"metadata.{self.metadata_format}")
        self._save_metadata(metadata_path, metadata)
        
        # 保存快照
        snapshot_path = os.path.join(version_path, f"data.{self.snapshot_format}")
        self._save_snapshot(snapshot_path, data)
        
        # 更新版本索引
        if dataset_name not in self.version_index["datasets"]:
            self.version_index["datasets"][dataset_name] = {
                "versions": [],
                "latest_version": None
            }
        
        # 添加新版本
        self.version_index["datasets"][dataset_name]["versions"].append({
            "version_id": version_id,
            "timestamp": timestamp,
            "data_hash": data_hash,
            "metadata_path": metadata_path,
            "snapshot_path": snapshot_path
        })
        
        # 更新最新版本
        self.version_index["datasets"][dataset_name]["latest_version"] = version_id
        
        # 限制版本数量
        versions = self.version_index["datasets"][dataset_name]["versions"]
        if len(versions) > self.max_versions:
            # 按时间戳排序
            versions.sort(key=lambda v: v["timestamp"])
            
            # 删除最旧的版本
            old_version = versions.pop(0)
            old_version_path = os.path.join(dataset_path, old_version["version_id"])
            try:
                shutil.rmtree(old_version_path)
                logger.info(f"删除旧版本: {old_version['version_id']}")
            except Exception as e:
                logger.error(f"删除旧版本失败: {e}")
        
        # 保存版本索引
        self._save_version_index()
        
        logger.info(f"保存数据版本成功: {dataset_name} - {version_id}")
        return version_id
    
    def load_version(self, dataset_name: str, version_id: Optional[str] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        加载数据版本
        
        参数:
            dataset_name: 数据集名称
            version_id: 版本ID，如果为None则加载最新版本
            
        返回:
            (数据框, 元数据)
        """
        # 检查数据集是否存在
        if dataset_name not in self.version_index["datasets"]:
            logger.error(f"数据集不存在: {dataset_name}")
            return pd.DataFrame(), {}
        
        # 获取版本ID
        if version_id is None:
            version_id = self.version_index["datasets"][dataset_name]["latest_version"]
            if version_id is None:
                logger.error(f"数据集没有版本: {dataset_name}")
                return pd.DataFrame(), {}
        
        # 检查版本是否存在
        versions = self.version_index["datasets"][dataset_name]["versions"]
        version_info = None
        for v in versions:
            if v["version_id"] == version_id:
                version_info = v
                break
        
        if version_info is None:
            logger.error(f"版本不存在: {dataset_name} - {version_id}")
            return pd.DataFrame(), {}
        
        # 加载元数据
        metadata_path = version_info["metadata_path"]
        metadata = self._load_metadata(metadata_path)
        
        # 加载快照
        snapshot_path = version_info["snapshot_path"]
        data = self._load_snapshot(snapshot_path)
        
        logger.info(f"加载数据版本成功: {dataset_name} - {version_id}")
        return data, metadata
    
    def list_versions(self, dataset_name: str) -> List[Dict[str, Any]]:
        """
        列出数据集的所有版本
        
        参数:
            dataset_name: 数据集名称
            
        返回:
            版本列表
        """
        # 检查数据集是否存在
        if dataset_name not in self.version_index["datasets"]:
            logger.warning(f"数据集不存在: {dataset_name}")
            return []
        
        # 获取版本列表
        versions = self.version_index["datasets"][dataset_name]["versions"]
        
        # 按时间戳排序（从新到旧）
        versions.sort(key=lambda v: v["timestamp"], reverse=True)
        
        # 获取详细信息
        result = []
        for v in versions:
            # 加载元数据
            metadata = self._load_metadata(v["metadata_path"])
            
            # 添加到结果
            result.append({
                "version_id": v["version_id"],
                "timestamp": v["timestamp"],
                "data_hash": v["data_hash"],
                "rows": metadata.get("rows", 0),
                "columns": metadata.get("columns", 0),
                "has_missing": metadata.get("has_missing", False),
                "missing_count": metadata.get("missing_count", 0),
                "created_at": metadata.get("created_at", "")
            })
        
        return result
    
    def list_datasets(self) -> List[str]:
        """
        列出所有数据集
        
        返回:
            数据集列表
        """
        return list(self.version_index["datasets"].keys())
    
    def delete_version(self, dataset_name: str, version_id: str) -> bool:
        """
        删除数据版本
        
        参数:
            dataset_name: 数据集名称
            version_id: 版本ID
            
        返回:
            是否成功
        """
        # 检查数据集是否存在
        if dataset_name not in self.version_index["datasets"]:
            logger.error(f"数据集不存在: {dataset_name}")
            return False
        
        # 获取版本列表
        versions = self.version_index["datasets"][dataset_name]["versions"]
        
        # 查找版本
        version_index = None
        for i, v in enumerate(versions):
            if v["version_id"] == version_id:
                version_index = i
                break
        
        if version_index is None:
            logger.error(f"版本不存在: {dataset_name} - {version_id}")
            return False
        
        # 检查是否为最新版本
        if self.version_index["datasets"][dataset_name]["latest_version"] == version_id:
            # 如果还有其他版本，更新最新版本
            if len(versions) > 1:
                # 找到时间戳最大的版本
                remaining_versions = [v for v in versions if v["version_id"] != version_id]
                remaining_versions.sort(key=lambda v: v["timestamp"], reverse=True)
                self.version_index["datasets"][dataset_name]["latest_version"] = remaining_versions[0]["version_id"]
            else:
                # 如果没有其他版本，设置为None
                self.version_index["datasets"][dataset_name]["latest_version"] = None
        
        # 获取版本路径
        version_path = os.path.join(self._get_dataset_path(dataset_name), version_id)
        
        # 删除版本目录
        try:
            shutil.rmtree(version_path)
        except Exception as e:
            logger.error(f"删除版本目录失败: {e}")
            return False
        
        # 更新版本索引
        versions.pop(version_index)
        
        # 保存版本索引
        self._save_version_index()
        
        logger.info(f"删除数据版本成功: {dataset_name} - {version_id}")
        return True
    
    def delete_dataset(self, dataset_name: str) -> bool:
        """
        删除数据集
        
        参数:
            dataset_name: 数据集名称
            
        返回:
            是否成功
        """
        # 检查数据集是否存在
        if dataset_name not in self.version_index["datasets"]:
            logger.error(f"数据集不存在: {dataset_name}")
            return False
        
        # 获取数据集路径
        dataset_path = self._get_dataset_path(dataset_name)
        
        # 删除数据集目录
        try:
            shutil.rmtree(dataset_path)
        except Exception as e:
            logger.error(f"删除数据集目录失败: {e}")
            return False
        
        # 更新版本索引
        del self.version_index["datasets"][dataset_name]
        
        # 保存版本索引
        self._save_version_index()
        
        logger.info(f"删除数据集成功: {dataset_name}")
        return True
    
    def compare_versions(self, dataset_name: str, version_id1: str, version_id2: str) -> Dict[str, Any]:
        """
        比较两个数据版本
        
        参数:
            dataset_name: 数据集名称
            version_id1: 版本ID1
            version_id2: 版本ID2
            
        返回:
            比较结果
        """
        # 加载两个版本
        data1, metadata1 = self.load_version(dataset_name, version_id1)
        data2, metadata2 = self.load_version(dataset_name, version_id2)
        
        if data1.empty or data2.empty:
            logger.error("加载版本失败")
            return {"error": "加载版本失败"}
        
        # 比较基本信息
        result = {
            "version1": version_id1,
            "version2": version_id2,
            "timestamp1": metadata1.get("timestamp", ""),
            "timestamp2": metadata2.get("timestamp", ""),
            "rows1": metadata1.get("rows", 0),
            "rows2": metadata2.get("rows", 0),
            "columns1": metadata1.get("columns", 0),
            "columns2": metadata2.get("columns", 0),
            "missing_count1": metadata1.get("missing_count", 0),
            "missing_count2": metadata2.get("missing_count", 0)
        }
        
        # 比较列
        columns1 = set(data1.columns)
        columns2 = set(data2.columns)
        
        result["common_columns"] = list(columns1.intersection(columns2))
        result["only_in_version1"] = list(columns1 - columns2)
        result["only_in_version2"] = list(columns2 - columns1)
        
        # 比较共同列的统计信息
        common_stats = {}
        for col in result["common_columns"]:
            if pd.api.types.is_numeric_dtype(data1[col]) and pd.api.types.is_numeric_dtype(data2[col]):
                # 数值列比较统计信息
                stats1 = {
                    "mean": data1[col].mean(),
                    "std": data1[col].std(),
                    "min": data1[col].min(),
                    "max": data1[col].max(),
                    "missing": data1[col].isna().sum()
                }
                
                stats2 = {
                    "mean": data2[col].mean(),
                    "std": data2[col].std(),
                    "min": data2[col].min(),
                    "max": data2[col].max(),
                    "missing": data2[col].isna().sum()
                }
                
                # 计算差异
                diff = {
                    "mean_diff": stats2["mean"] - stats1["mean"],
                    "std_diff": stats2["std"] - stats1["std"],
                    "min_diff": stats2["min"] - stats1["min"],
                    "max_diff": stats2["max"] - stats1["max"],
                    "missing_diff": stats2["missing"] - stats1["missing"]
                }
                
                common_stats[col] = {
                    "version1": stats1,
                    "version2": stats2,
                    "diff": diff
                }
            else:
                # 非数值列只比较缺失值
                missing1 = data1[col].isna().sum()
                missing2 = data2[col].isna().sum()
                
                common_stats[col] = {
                    "version1": {"missing": missing1},
                    "version2": {"missing": missing2},
                    "diff": {"missing_diff": missing2 - missing1}
                }
        
        result["common_stats"] = common_stats
        
        # 计算整体相似度
        if result["common_columns"]:
            # 使用共同列计算相关性
            common_data1 = data1[result["common_columns"]]
            common_data2 = data2[result["common_columns"]]
            
            # 只保留数值列
            numeric_cols = [col for col in result["common_columns"] 
                           if pd.api.types.is_numeric_dtype(common_data1[col]) and 
                              pd.api.types.is_numeric_dtype(common_data2[col])]
            
            if numeric_cols:
                # 计算相关性
                try:
                    corr = np.corrcoef(common_data1[numeric_cols].values.flatten(), 
                                      common_data2[numeric_cols].values.flatten())[0, 1]
                    result["correlation"] = corr
                except Exception as e:
                    logger.warning(f"计算相关性失败: {e}")
                    result["correlation"] = None
            else:
                result["correlation"] = None
        else:
            result["correlation"] = None
        
        return result
    
    def get_version_metadata(self, dataset_name: str, version_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取版本元数据
        
        参数:
            dataset_name: 数据集名称
            version_id: 版本ID，如果为None则获取最新版本
            
        返回:
            元数据
        """
        # 检查数据集是否存在
        if dataset_name not in self.version_index["datasets"]:
            logger.error(f"数据集不存在: {dataset_name}")
            return {}
        
        # 获取版本ID
        if version_id is None:
            version_id = self.version_index["datasets"][dataset_name]["latest_version"]
            if version_id is None:
                logger.error(f"数据集没有版本: {dataset_name}")
                return {}
        
        # 检查版本是否存在
        versions = self.version_index["datasets"][dataset_name]["versions"]
        version_info = None
        for v in versions:
            if v["version_id"] == version_id:
                version_info = v
                break
        
        if version_info is None:
            logger.error(f"版本不存在: {dataset_name} - {version_id}")
            return {}
        
        # 加载元数据
        metadata_path = version_info["metadata_path"]
        metadata = self._load_metadata(metadata_path)
        
        return metadata
