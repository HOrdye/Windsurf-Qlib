"""
数据加载基类定义
包含数据加载器的基本接口和通用方法
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Union, Optional, Any
import os
import pandas as pd
import numpy as np
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局配置
DATA_ROOT = os.environ.get("QLIB_DATA_ROOT", "/data/qlib")
RAW_DATA_DIR = os.path.join(DATA_ROOT, "raw")
FEATURE_STORE_DIR = os.path.join(DATA_ROOT, "features")


class BaseDataLoader(ABC):
    """
    数据加载器基类，定义了数据加载的基本接口
    所有数据加载器必须继承此类并实现相应方法
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据加载器
        
        参数:
            config: 配置字典，包含数据加载器的参数
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._validate_config()
        
    def _validate_config(self):
        """验证配置是否合法"""
        required_keys = ["start_time", "end_time", "instruments"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"配置缺少必要参数: {key}")
    
    @abstractmethod
    def load(self, *args, **kwargs) -> Any:
        """
        加载数据的抽象方法，所有子类必须实现
        
        返回:
            加载的数据，格式由具体实现决定
        """
        pass
    
    def check_data_leakage(self, df: pd.DataFrame, time_col: str = "datetime") -> bool:
        """
        检查数据是否存在泄露
        
        参数:
            df: 待检查的数据框
            time_col: 时间列名
            
        返回:
            是否存在数据泄露
        """
        # 检查是否有未来数据
        if time_col in df.columns:
            current_time = pd.Timestamp.now()
            future_data = df[df[time_col] > current_time]
            if not future_data.empty:
                self.logger.warning(f"检测到未来数据: {len(future_data)}行")
                return True
        return False
    
    def save_feature_snapshot(self, df: pd.DataFrame, name: str) -> str:
        """
        保存特征快照
        
        参数:
            df: 特征数据框
            name: 特征名称
            
        返回:
            保存的文件路径
        """
        # 确保目录存在
        os.makedirs(FEATURE_STORE_DIR, exist_ok=True)
        
        # 生成时间戳文件名
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.feather"
        filepath = os.path.join(FEATURE_STORE_DIR, filename)
        
        # 保存为feather格式
        df.to_feather(filepath)
        self.logger.info(f"特征快照已保存: {filepath}")
        
        return filepath


class BaseModel(ABC):
    """
    模型基类，定义了模型训练和预测的基本接口
    所有量化模型必须继承此类并实现相应方法
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化模型
        
        参数:
            config: 配置字典，包含模型参数
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.model = None
        
    @abstractmethod
    def train(self, train_data: Any, valid_data: Optional[Any] = None) -> None:
        """
        训练模型的抽象方法
        
        参数:
            train_data: 训练数据
            valid_data: 验证数据，可选
        """
        pass
    
    @abstractmethod
    def predict(self, data: Any) -> Any:
        """
        模型预测的抽象方法
        
        参数:
            data: 预测数据
            
        返回:
            预测结果
        """
        pass
    
    def feature_importance(self) -> Optional[pd.DataFrame]:
        """
        获取特征重要性
        
        返回:
            特征重要性数据框，如果模型不支持则返回None
        """
        return None
    
    def save(self, path: str) -> None:
        """
        保存模型
        
        参数:
            path: 保存路径
        """
        import pickle
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump(self.model, f)
        self.logger.info(f"模型已保存: {path}")
    
    def load(self, path: str) -> None:
        """
        加载模型
        
        参数:
            path: 模型路径
        """
        import pickle
        with open(path, 'rb') as f:
            self.model = pickle.load(f)
        self.logger.info(f"模型已加载: {path}")
