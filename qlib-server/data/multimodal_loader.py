"""
多模态数据加载器
支持数值、文本、图像数据的统一加载和处理
"""
import os
import pandas as pd
import numpy as np
from typing import Dict, List, Union, Optional, Any, Tuple
import logging
import datetime
import json
from pathlib import Path
import warnings
import re

# 尝试导入可选依赖
TORCH_AVAILABLE = False
try:
    import torch
    from torch.utils.data import Dataset
    TORCH_AVAILABLE = True
except ImportError:
    warnings.warn("PyTorch未安装，部分功能将不可用")
    # 创建一个简单的Dataset基类，用于在没有PyTorch时提供基本功能
    class Dataset:
        def __init__(self):
            pass
        def __len__(self):
            return 0
        def __getitem__(self, idx):
            return None

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    warnings.warn("PIL未安装，图像处理功能将不可用")

try:
    import transformers
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    warnings.warn("Transformers未安装，文本处理功能将受限")

from .base import BaseDataLoader, DATA_ROOT, RAW_DATA_DIR, FEATURE_STORE_DIR


class MultiModalDataset(Dataset):
    """
    多模态数据集，用于PyTorch数据加载
    支持数值特征、文本和图像数据
    """
    
    def __init__(
        self, 
        numerical_data: pd.DataFrame,
        text_data: Optional[Dict[str, List[str]]] = None,
        image_data: Optional[Dict[str, List[str]]] = None,
        target_col: Optional[str] = None
    ):
        """
        初始化多模态数据集
        
        参数:
            numerical_data: 数值特征数据框，索引为instrument和datetime
            text_data: 文本数据字典，键为instrument_datetime，值为文本列表
            image_data: 图像数据字典，键为instrument_datetime，值为图像路径列表
            target_col: 目标列名，如果为None则不加载标签
        """
        if not TORCH_AVAILABLE:
            raise ImportError("需要PyTorch支持多模态数据集功能")
            
        self.numerical_data = numerical_data
        self.text_data = text_data or {}
        self.image_data = image_data or {}
        self.target_col = target_col
        
        # 构建索引
        self.index = numerical_data.index.tolist()
        
        # 检查数据一致性
        self._validate_data()
        
    def _validate_data(self):
        """验证数据一致性"""
        if self.text_data:
            missing_text = 0
            for idx in self.index:
                key = self._get_key_from_index(idx)
                if key not in self.text_data:
                    missing_text += 1
            
            if missing_text > 0:
                warnings.warn(f"有{missing_text}/{len(self.index)}个样本缺少文本数据")
                
        if self.image_data:
            missing_image = 0
            for idx in self.index:
                key = self._get_key_from_index(idx)
                if key not in self.image_data:
                    missing_image += 1
            
            if missing_image > 0:
                warnings.warn(f"有{missing_image}/{len(self.index)}个样本缺少图像数据")
    
    def _get_key_from_index(self, idx: Tuple) -> str:
        """从索引元组生成键"""
        instrument, dt = idx
        if isinstance(dt, pd.Timestamp):
            dt = dt.strftime("%Y%m%d")
        return f"{instrument}_{dt}"
        
    def __len__(self) -> int:
        """返回数据集长度"""
        return len(self.index)
    
    def __getitem__(self, idx: int) -> Dict[str, Any]:
        """
        获取指定索引的数据项
        
        参数:
            idx: 索引
            
        返回:
            包含数值特征、文本、图像和标签的字典
        """
        index_tuple = self.index[idx]
        key = self._get_key_from_index(index_tuple)
        
        # 获取数值特征
        numerical_features = self.numerical_data.loc[index_tuple].values
        if self.target_col and self.target_col in self.numerical_data.columns:
            # 从特征中分离标签
            target_idx = self.numerical_data.columns.get_loc(self.target_col)
            target = numerical_features[target_idx]
            # 移除标签列
            numerical_features = np.delete(numerical_features, target_idx)
        else:
            target = None
        
        # 获取文本数据
        texts = self.text_data.get(key, [])
        
        # 获取图像数据
        image_paths = self.image_data.get(key, [])
        images = []
        if PIL_AVAILABLE and image_paths:
            for img_path in image_paths:
                try:
                    img = Image.open(img_path)
                    images.append(img)
                except Exception as e:
                    warnings.warn(f"无法加载图像 {img_path}: {e}")
        
        result = {
            "numerical": torch.tensor(numerical_features, dtype=torch.float32),
            "text": texts,
            "images": images,
            "key": key
        }
        
        if target is not None:
            result["target"] = torch.tensor(target, dtype=torch.float32)
            
        return result


class MultiModalDataLoader(BaseDataLoader):
    """
    多模态数据加载器
    支持加载和处理数值、文本和图像数据
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化多模态数据加载器
        
        参数:
            config: 配置字典，包含以下字段:
                - start_time: 开始时间
                - end_time: 结束时间
                - instruments: 股票代码列表
                - features: 特征列表
                - target: 目标列名
                - numerical_data_path: 数值数据路径，相对于DATA_ROOT
                - text_data_path: 文本数据路径，相对于DATA_ROOT，可选
                - image_data_path: 图像数据路径，相对于DATA_ROOT，可选
                - cache_dir: 缓存目录，相对于FEATURE_STORE_DIR，可选
        """
        super().__init__(config)
        
        # 设置数据路径
        self.numerical_data_path = os.path.join(DATA_ROOT, config.get("numerical_data_path", ""))
        
        # 文本和图像数据路径是可选的
        self.text_data_path = None
        if "text_data_path" in config:
            self.text_data_path = os.path.join(DATA_ROOT, config["text_data_path"])
            
        self.image_data_path = None
        if "image_data_path" in config:
            self.image_data_path = os.path.join(DATA_ROOT, config["image_data_path"])
        
        # 缓存目录
        self.cache_dir = None
        if "cache_dir" in config:
            self.cache_dir = os.path.join(FEATURE_STORE_DIR, config["cache_dir"])
            os.makedirs(self.cache_dir, exist_ok=True)
        
        # 特征和目标
        self.features = config.get("features", [])
        self.target = config.get("target")
        
        # 数据预处理配置
        self.normalize = config.get("normalize", False)
        self.fill_na_method = config.get("fill_na_method", "ffill")
        
        # 文本处理配置
        self.text_max_length = config.get("text_max_length", 512)
        self.text_model_name = config.get("text_model_name", "bert-base-uncased")
        
        # 图像处理配置
        self.image_size = config.get("image_size", (224, 224))
        self.image_model_name = config.get("image_model_name", "resnet18")
        
    def load(self, return_dataset: bool = False) -> Union[Tuple[pd.DataFrame, Optional[Dict], Optional[Dict]], MultiModalDataset]:
        """
        加载多模态数据
        
        参数:
            return_dataset: 是否返回MultiModalDataset对象，默认为False
            
        返回:
            如果return_dataset为True，返回MultiModalDataset对象
            否则返回(numerical_df, text_dict, image_dict)元组
        """
        # 加载数值数据
        numerical_df = self._load_numerical_data()
        
        # 加载文本数据
        text_dict = None
        if self.text_data_path:
            text_dict = self._load_text_data()
        
        # 加载图像数据
        image_dict = None
        if self.image_data_path:
            image_dict = self._load_image_data()
        
        # 检查数据泄露
        if self.check_data_leakage(numerical_df):
            self.logger.warning("检测到数据泄露风险，请检查数据")
        
        # 保存特征快照
        if self.cache_dir:
            snapshot_name = f"multimodal_features_{len(self.features)}"
            self.save_feature_snapshot(numerical_df, snapshot_name)
        
        if return_dataset and TORCH_AVAILABLE:
            return MultiModalDataset(
                numerical_data=numerical_df,
                text_data=text_dict,
                image_data=image_dict,
                target_col=self.target
            )
        else:
            return numerical_df, text_dict, image_dict
    
    def _load_numerical_data(self) -> pd.DataFrame:
        """
        加载数值特征数据
        
        返回:
            数值特征数据框
        """
        self.logger.info(f"加载数值数据: {self.numerical_data_path}")
        
        # 检查路径是否存在
        if not os.path.exists(self.numerical_data_path):
            raise FileNotFoundError(f"数值数据路径不存在: {self.numerical_data_path}")
        
        # 根据文件类型加载数据
        if self.numerical_data_path.endswith('.csv'):
            df = pd.read_csv(self.numerical_data_path)
        elif self.numerical_data_path.endswith('.feather'):
            df = pd.read_feather(self.numerical_data_path)
        elif self.numerical_data_path.endswith('.parquet'):
            df = pd.read_parquet(self.numerical_data_path)
        else:
            raise ValueError(f"不支持的数值数据文件格式: {self.numerical_data_path}")
        
        # 确保datetime列是日期时间类型
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        
        # 筛选时间范围
        if 'datetime' in df.columns:
            start_time = pd.to_datetime(self.config['start_time'])
            end_time = pd.to_datetime(self.config['end_time'])
            df = df[(df['datetime'] >= start_time) & (df['datetime'] <= end_time)]
        
        # 筛选股票
        if 'instrument' in df.columns and self.config.get('instruments'):
            df = df[df['instrument'].isin(self.config['instruments'])]
        
        # 筛选特征
        if self.features:
            # 确保包含必要的列
            required_cols = ['instrument', 'datetime']
            if self.target:
                required_cols.append(self.target)
            
            # 合并所有需要的列
            all_cols = list(set(required_cols + self.features))
            df = df[all_cols]
        
        # 处理缺失值
        if self.fill_na_method == 'ffill':
            # 使用更兼容的方式处理缺失值
            # 首先按照股票分组
            grouped = df.groupby('instrument')
            # 然后对每个组应用 ffill
            result_dfs = []
            for name, group in grouped:
                # 对每个组使用 ffill
                result_dfs.append(group.ffill())
            # 合并结果
            df = pd.concat(result_dfs)
        elif self.fill_na_method == 'bfill':
            # 使用相同的方式处理 bfill
            grouped = df.groupby('instrument')
            result_dfs = []
            for name, group in grouped:
                result_dfs.append(group.bfill())
            df = pd.concat(result_dfs)
        elif self.fill_na_method == 'mean':
            df = df.fillna(df.mean())
        elif self.fill_na_method == 'zero':
            
            df = df.fillna(0)
        
        # 标准化
        if self.normalize:
            for col in self.features:
                if col in df.columns and col != self.target:
                    mean = df[col].mean()
                    std = df[col].std()
                    if std > 0:
                        df[col] = (df[col] - mean) / std
        
        # 设置索引
        if 'instrument' in df.columns and 'datetime' in df.columns:
            df = df.set_index(['instrument', 'datetime'])
        
        self.logger.info(f"数值数据加载完成，形状: {df.shape}")
        return df
    
    def _load_text_data(self) -> Dict[str, List[str]]:
        """
        加载文本数据
        
        返回:
            文本数据字典，键为instrument_date，值为文本列表
        """
        self.logger.info(f"加载文本数据: {self.text_data_path}")
        
        # 检查路径是否存在
        if not os.path.exists(self.text_data_path):
            raise FileNotFoundError(f"文本数据路径不存在: {self.text_data_path}")
        
        text_dict = {}
        
        # 支持不同的文本数据格式
        if os.path.isdir(self.text_data_path):
            # 目录格式: instrument_YYYYMMDD.txt 或 instrument_YYYYMMDD.json
            for file in os.listdir(self.text_data_path):
                match = re.match(r'([A-Za-z0-9]+)_(\d{8})\.(txt|json)', file)
                if match:
                    instrument, date, ext = match.groups()
                    
                    # 检查是否在目标股票列表中
                    if self.config.get('instruments') and instrument not in self.config['instruments']:
                        continue
                    
                    # 检查是否在目标时间范围内
                    file_date = pd.to_datetime(date)
                    start_time = pd.to_datetime(self.config['start_time'])
                    end_time = pd.to_datetime(self.config['end_time'])
                    if file_date < start_time or file_date > end_time:
                        continue
                    
                    # 读取文本数据
                    file_path = os.path.join(self.text_data_path, file)
                    key = f"{instrument}_{date}"
                    
                    if ext == 'txt':
                        with open(file_path, 'r', encoding='utf-8') as f:
                            text_dict[key] = [line.strip() for line in f if line.strip()]
                    elif ext == 'json':
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                text_dict[key] = data
                            elif isinstance(data, dict) and 'texts' in data:
                                text_dict[key] = data['texts']
        
        elif self.text_data_path.endswith('.json'):
            # 单一JSON文件格式
            with open(self.text_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 检查JSON格式
                if isinstance(data, dict):
                    for key, texts in data.items():
                        # 解析键
                        match = re.match(r'([A-Za-z0-9]+)_(\d{8})', key)
                        if match:
                            instrument, date = match.groups()
                            
                            # 检查是否在目标股票列表中
                            if self.config.get('instruments') and instrument not in self.config['instruments']:
                                continue
                            
                            # 检查是否在目标时间范围内
                            file_date = pd.to_datetime(date)
                            start_time = pd.to_datetime(self.config['start_time'])
                            end_time = pd.to_datetime(self.config['end_time'])
                            if file_date < start_time or file_date > end_time:
                                continue
                            
                            text_dict[key] = texts if isinstance(texts, list) else [texts]
        
        self.logger.info(f"文本数据加载完成，样本数: {len(text_dict)}")
        return text_dict
    
    def _load_image_data(self) -> Dict[str, List[str]]:
        """
        加载图像数据
        
        返回:
            图像数据字典，键为instrument_date，值为图像路径列表
        """
        self.logger.info(f"加载图像数据: {self.image_data_path}")
        
        # 检查路径是否存在
        if not os.path.exists(self.image_data_path):
            raise FileNotFoundError(f"图像数据路径不存在: {self.image_data_path}")
        
        image_dict = {}
        
        # 支持不同的图像数据组织方式
        if os.path.isdir(self.image_data_path):
            # 目录格式: instrument/YYYYMMDD/*.jpg 或 instrument_YYYYMMDD/*.jpg
            
            # 情况1: instrument/YYYYMMDD/*.jpg
            for instrument_dir in os.listdir(self.image_data_path):
                instrument_path = os.path.join(self.image_data_path, instrument_dir)
                
                # 检查是否是目录
                if not os.path.isdir(instrument_path):
                    continue
                
                # 检查是否在目标股票列表中
                if self.config.get('instruments') and instrument_dir not in self.config['instruments']:
                    continue
                
                # 遍历日期目录
                for date_dir in os.listdir(instrument_path):
                    # 检查日期格式
                    if not re.match(r'\d{8}', date_dir):
                        continue
                    
                    # 检查是否在目标时间范围内
                    try:
                        date = pd.to_datetime(date_dir)
                        start_time = pd.to_datetime(self.config['start_time'])
                        end_time = pd.to_datetime(self.config['end_time'])
                        if date < start_time or date > end_time:
                            continue
                    except:
                        continue
                    
                    # 获取该日期下的所有图像
                    date_path = os.path.join(instrument_path, date_dir)
                    if os.path.isdir(date_path):
                        key = f"{instrument_dir}_{date_dir}"
                        image_dict[key] = []
                        
                        for img_file in os.listdir(date_path):
                            if img_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                                img_path = os.path.join(date_path, img_file)
                                image_dict[key].append(img_path)
            
            # 情况2: instrument_YYYYMMDD/*.jpg
            for item in os.listdir(self.image_data_path):
                match = re.match(r'([A-Za-z0-9]+)_(\d{8})', item)
                if match and os.path.isdir(os.path.join(self.image_data_path, item)):
                    instrument, date = match.groups()
                    
                    # 检查是否在目标股票列表中
                    if self.config.get('instruments') and instrument not in self.config['instruments']:
                        continue
                    
                    # 检查是否在目标时间范围内
                    try:
                        file_date = pd.to_datetime(date)
                        start_time = pd.to_datetime(self.config['start_time'])
                        end_time = pd.to_datetime(self.config['end_time'])
                        if file_date < start_time or file_date > end_time:
                            continue
                    except:
                        continue
                    
                    # 获取该目录下的所有图像
                    dir_path = os.path.join(self.image_data_path, item)
                    key = f"{instrument}_{date}"
                    image_dict[key] = []
                    
                    for img_file in os.listdir(dir_path):
                        if img_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                            img_path = os.path.join(dir_path, img_file)
                            image_dict[key].append(img_path)
        
        elif self.image_data_path.endswith('.json'):
            # 图像路径索引文件
            with open(self.image_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 检查JSON格式
                if isinstance(data, dict):
                    for key, img_paths in data.items():
                        # 解析键
                        match = re.match(r'([A-Za-z0-9]+)_(\d{8})', key)
                        if match:
                            instrument, date = match.groups()
                            
                            # 检查是否在目标股票列表中
                            if self.config.get('instruments') and instrument not in self.config['instruments']:
                                continue
                            
                            # 检查是否在目标时间范围内
                            try:
                                file_date = pd.to_datetime(date)
                                start_time = pd.to_datetime(self.config['start_time'])
                                end_time = pd.to_datetime(self.config['end_time'])
                                if file_date < start_time or file_date > end_time:
                                    continue
                            except:
                                continue
                            
                            # 验证图像路径
                            valid_paths = []
                            for img_path in img_paths if isinstance(img_paths, list) else [img_paths]:
                                # 如果是相对路径，转换为绝对路径
                                if not os.path.isabs(img_path):
                                    img_path = os.path.join(os.path.dirname(self.image_data_path), img_path)
                                
                                if os.path.exists(img_path):
                                    valid_paths.append(img_path)
                            
                            if valid_paths:
                                image_dict[key] = valid_paths
        
        self.logger.info(f"图像数据加载完成，样本数: {len(image_dict)}")
        return image_dict
    
    def create_torch_dataloaders(
        self, 
        batch_size: int = 32,
        val_ratio: float = 0.2,
        shuffle: bool = True,
        num_workers: int = 4
    ) -> Tuple[Any, Any]:
        """
        创建PyTorch数据加载器
        
        参数:
            batch_size: 批次大小
            val_ratio: 验证集比例
            shuffle: 是否打乱数据
            num_workers: 数据加载线程数
            
        返回:
            (train_loader, val_loader)元组
        """
        if not TORCH_AVAILABLE:
            raise ImportError("需要PyTorch支持数据加载器功能")
        
        from torch.utils.data import DataLoader, random_split
        
        # 加载数据集
        dataset = self.load(return_dataset=True)
        
        # 分割训练集和验证集
        val_size = int(len(dataset) * val_ratio)
        train_size = len(dataset) - val_size
        
        if val_size > 0:
            train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
            
            train_loader = DataLoader(
                train_dataset,
                batch_size=batch_size,
                shuffle=shuffle,
                num_workers=num_workers
            )
            
            val_loader = DataLoader(
                val_dataset,
                batch_size=batch_size,
                shuffle=False,
                num_workers=num_workers
            )
            
            return train_loader, val_loader
        else:
            train_loader = DataLoader(
                dataset,
                batch_size=batch_size,
                shuffle=shuffle,
                num_workers=num_workers
            )
            
            return train_loader, None
