"""
特征编码基础类
定义各种编码器和处理器的接口
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


class BaseFeatureEncoder(ABC):
    """
    特征编码器基类
    所有特征编码器的基类
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化特征编码器
        
        参数:
            config: 配置字典
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._validate_config()
        
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        pass
    
    @abstractmethod
    def encode(self, data: Any) -> np.ndarray:
        """
        编码数据
        
        参数:
            data: 输入数据
            
        返回:
            编码后的特征向量
        """
        pass
    
    @abstractmethod
    def get_output_dim(self) -> int:
        """
        获取输出维度
        
        返回:
            输出特征向量的维度
        """
        pass


class BaseTextEncoder(BaseFeatureEncoder):
    """
    文本编码器基类
    所有文本编码器的基类
    """
    
    @abstractmethod
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """
        批量编码文本
        
        参数:
            texts: 文本列表
            
        返回:
            编码后的特征向量，形状为 (batch_size, embedding_dim)
        """
        pass
    
    def encode(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        编码文本
        
        参数:
            text: 单个文本或文本列表
            
        返回:
            编码后的特征向量
        """
        if isinstance(text, str):
            return self.encode_batch([text])[0]
        else:
            return self.encode_batch(text)


class BaseImageEncoder(BaseFeatureEncoder):
    """
    图像编码器基类
    所有图像编码器的基类
    """
    
    @abstractmethod
    def encode_batch(self, images: List[np.ndarray]) -> np.ndarray:
        """
        批量编码图像
        
        参数:
            images: 图像列表，每个图像为numpy数组，形状为 (height, width, channels)
            
        返回:
            编码后的特征向量，形状为 (batch_size, embedding_dim)
        """
        pass
    
    def encode(self, image: Union[np.ndarray, List[np.ndarray]]) -> np.ndarray:
        """
        编码图像
        
        参数:
            image: 单个图像或图像列表
            
        返回:
            编码后的特征向量
        """
        if isinstance(image, np.ndarray) and len(image.shape) == 3:
            return self.encode_batch([image])[0]
        else:
            return self.encode_batch(image)


class BaseNumericalEncoder(BaseFeatureEncoder):
    """
    数值特征处理器基类
    所有数值特征处理器的基类
    """
    
    @abstractmethod
    def fit(self, data: pd.DataFrame) -> 'BaseNumericalEncoder':
        """
        拟合数值特征处理器
        
        参数:
            data: 数值特征DataFrame
            
        返回:
            拟合后的处理器
        """
        pass
    
    @abstractmethod
    def transform(self, data: pd.DataFrame) -> np.ndarray:
        """
        转换数值特征
        
        参数:
            data: 数值特征DataFrame
            
        返回:
            转换后的特征向量
        """
        pass
    
    def fit_transform(self, data: pd.DataFrame) -> np.ndarray:
        """
        拟合并转换数值特征
        
        参数:
            data: 数值特征DataFrame
            
        返回:
            转换后的特征向量
        """
        self.fit(data)
        return self.transform(data)
    
    def encode(self, data: pd.DataFrame) -> np.ndarray:
        """
        编码数值特征
        
        参数:
            data: 数值特征DataFrame
            
        返回:
            编码后的特征向量
        """
        return self.transform(data)


class BaseFeatureFusion(ABC):
    """
    特征融合器基类
    所有特征融合器的基类
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化特征融合器
        
        参数:
            config: 配置字典
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._validate_config()
        
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        pass
    
    @abstractmethod
    def fuse(self, features: Dict[str, np.ndarray]) -> np.ndarray:
        """
        融合特征
        
        参数:
            features: 特征字典，键为特征名称，值为特征向量
            
        返回:
            融合后的特征向量
        """
        pass
    
    @abstractmethod
    def get_output_dim(self) -> int:
        """
        获取输出维度
        
        返回:
            输出特征向量的维度
        """
        pass
