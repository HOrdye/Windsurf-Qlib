"""
特征融合模块
包含多模态特征融合和特征编码Pipeline实现
"""

import logging
from typing import Any, Dict, List, Optional, Union, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from .base import BaseFeatureFusion, BaseFeatureEncoder
from .text_encoder import BERTTextEncoder
from .image_encoder import ResNetImageEncoder
from .numerical_encoder import NumericalFeatureProcessor


class MultiModalFeatureFusion(BaseFeatureFusion):
    """
    多模态特征融合器
    融合文本、图像和数值特征
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化多模态特征融合器
        
        参数:
            config: 配置字典，包含以下字段:
                - fusion_method: 融合方法，可选值为'concat', 'weighted_sum', 'attention', 'mlp'，默认为'concat'
                - weights: 各模态的权重，默认为均等权重
                - output_dim: 输出维度，当fusion_method为'mlp'或'attention'时使用，默认为128
                - dropout: Dropout比例，当fusion_method为'mlp'或'attention'时使用，默认为0.1
                - device: 设备，可选值为'cpu', 'cuda'，默认为'cpu'
        """
        super().__init__(config)
        
        self.fusion_method = self.config.get("fusion_method", "concat")
        self.weights = self.config.get("weights", {})
        self.output_dim = self.config.get("output_dim", 128)
        self.dropout = self.config.get("dropout", 0.1)
        self.device = self.config.get("device", "cpu")
        
        # 初始化融合模型
        self._init_fusion_model()
        
        # 存储输入维度
        self.input_dims = {}
        
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        super()._validate_config()
        
        # 检查融合方法
        valid_fusion_methods = ["concat", "weighted_sum", "attention", "mlp"]
        if self.config.get("fusion_method") not in [None, *valid_fusion_methods]:
            raise ValueError(f"融合方法必须是以下之一: {valid_fusion_methods}")
        
        # 检查设备
        valid_devices = ["cpu", "cuda"]
        if self.config.get("device") not in [None, *valid_devices]:
            raise ValueError(f"设备必须是以下之一: {valid_devices}")
    
    def _init_fusion_model(self) -> None:
        """初始化融合模型"""
        self.fusion_model = None
        
        # 如果使用MLP或注意力机制，需要初始化模型
        if self.fusion_method in ["mlp", "attention"]:
            self.fusion_model = nn.Module()
            # 具体的模型结构将在设置输入维度后初始化
    
    def set_input_dims(self, input_dims: Dict[str, int]) -> None:
        """
        设置输入维度
        
        参数:
            input_dims: 输入维度字典，键为特征名称，值为维度
        """
        self.input_dims = input_dims
        
        # 如果使用MLP或注意力机制，初始化模型
        if self.fusion_method == "mlp":
            self._init_mlp_model()
        elif self.fusion_method == "attention":
            self._init_attention_model()
    
    def _init_mlp_model(self) -> None:
        """初始化MLP模型"""
        # 计算输入总维度
        total_dim = sum(self.input_dims.values())
        
        # 创建MLP模型
        self.fusion_model = nn.Sequential(
            nn.Linear(total_dim, total_dim // 2),
            nn.ReLU(),
            nn.Dropout(self.dropout),
            nn.Linear(total_dim // 2, self.output_dim)
        ).to(self.device)
    
    def _init_attention_model(self) -> None:
        """初始化注意力模型"""
        from torch.nn import MultiheadAttention
        
        class AttentionFusion(nn.Module):
            def __init__(self, input_dims, output_dim, dropout=0.1, device="cpu"):
                super().__init__()
                self.input_dims = input_dims
                self.output_dim = output_dim
                self.device = device
                
                # 为每个模态创建投影层
                self.projections = nn.ModuleDict({
                    name: nn.Linear(dim, output_dim).to(device)
                    for name, dim in input_dims.items()
                })
                
                # 多头注意力层
                self.attention = MultiheadAttention(
                    embed_dim=output_dim,
                    num_heads=4,
                    dropout=dropout
                ).to(device)
                
                # 输出层
                self.output_layer = nn.Sequential(
                    nn.Linear(output_dim, output_dim),
                    nn.ReLU(),
                    nn.Dropout(dropout)
                ).to(device)
            
            def forward(self, features):
                # 投影每个模态的特征
                projected_features = []
                for name, feature in features.items():
                    if name in self.projections:
                        # 将特征转换为张量
                        if not isinstance(feature, torch.Tensor):
                            feature = torch.tensor(feature, dtype=torch.float32).to(self.device)
                        
                        # 投影特征
                        projected = self.projections[name](feature)
                        projected_features.append(projected.unsqueeze(0))  # 添加序列维度
                
                if not projected_features:
                    return torch.zeros((1, self.output_dim), device=self.device)
                
                # 堆叠所有投影特征
                stacked = torch.cat(projected_features, dim=0)  # [num_modalities, batch_size, output_dim]
                
                # 应用多头注意力
                attn_output, _ = self.attention(stacked, stacked, stacked)
                
                # 平均所有模态的注意力输出
                fused = torch.mean(attn_output, dim=0)  # [batch_size, output_dim]
                
                # 应用输出层
                output = self.output_layer(fused)
                
                return output
        
        # 创建注意力融合模型
        self.fusion_model = AttentionFusion(
            input_dims=self.input_dims,
            output_dim=self.output_dim,
            dropout=self.dropout,
            device=self.device
        )
    
    def fuse(self, features: Dict[str, np.ndarray]) -> np.ndarray:
        """
        融合特征
        
        参数:
            features: 特征字典，键为特征名称，值为特征向量
            
        返回:
            融合后的特征向量
        """
        if not features:
            return np.zeros((1, self.get_output_dim()))
        
        # 检查输入维度是否已设置
        if not self.input_dims and self.fusion_method in ["mlp", "attention"]:
            # 从特征中推断输入维度
            input_dims = {name: feature.shape[-1] for name, feature in features.items()}
            self.set_input_dims(input_dims)
        
        # 根据融合方法融合特征
        if self.fusion_method == "concat":
            return self._concat_fusion(features)
        elif self.fusion_method == "weighted_sum":
            return self._weighted_sum_fusion(features)
        elif self.fusion_method in ["mlp", "attention"]:
            return self._model_fusion(features)
        else:
            raise ValueError(f"不支持的融合方法: {self.fusion_method}")
    
    def _concat_fusion(self, features: Dict[str, np.ndarray]) -> np.ndarray:
        """
        拼接融合
        
        参数:
            features: 特征字典
            
        返回:
            融合后的特征向量
        """
        # 确保所有特征的第一维相同
        batch_sizes = [feature.shape[0] for feature in features.values()]
        if len(set(batch_sizes)) > 1:
            raise ValueError("所有特征的批次大小必须相同")
        
        # 拼接特征
        feature_list = []
        for name in sorted(features.keys()):
            feature_list.append(features[name])
        
        return np.concatenate(feature_list, axis=1)
    
    def _weighted_sum_fusion(self, features: Dict[str, np.ndarray]) -> np.ndarray:
        """
        加权求和融合
        
        参数:
            features: 特征字典
            
        返回:
            融合后的特征向量
        """
        # 确保所有特征的维度相同
        dims = [feature.shape[1] for feature in features.values()]
        if len(set(dims)) > 1:
            raise ValueError("所有特征的维度必须相同")
        
        # 计算权重
        weights = {}
        for name in features.keys():
            weights[name] = self.weights.get(name, 1.0 / len(features))
        
        # 归一化权重
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {name: weight / total_weight for name, weight in weights.items()}
        
        # 加权求和
        result = None
        for name, feature in features.items():
            if result is None:
                result = feature * weights[name]
            else:
                result += feature * weights[name]
        
        return result
    
    def _model_fusion(self, features: Dict[str, np.ndarray]) -> np.ndarray:
        """
        使用模型融合
        
        参数:
            features: 特征字典
            
        返回:
            融合后的特征向量
        """
        # 将特征转换为张量
        tensor_features = {}
        for name, feature in features.items():
            if name in self.input_dims:
                tensor_features[name] = torch.tensor(feature, dtype=torch.float32).to(self.device)
        
        # 使用模型融合
        with torch.no_grad():
            fused = self.fusion_model(tensor_features)
        
        # 将结果转换为numpy数组
        return fused.cpu().numpy()
    
    def get_output_dim(self) -> int:
        """
        获取输出维度
        
        返回:
            输出特征向量的维度
        """
        if self.fusion_method == "concat":
            # 拼接融合的输出维度是所有输入维度之和
            return sum(self.input_dims.values()) if self.input_dims else 0
        elif self.fusion_method == "weighted_sum":
            # 加权求和融合的输出维度是输入维度（假设所有输入维度相同）
            return next(iter(self.input_dims.values())) if self.input_dims else 0
        else:
            # MLP和注意力融合的输出维度是指定的输出维度
            return self.output_dim


class FeatureEncodingPipeline:
    """
    特征编码Pipeline
    整合文本编码器、图像编码器、数值特征处理器和特征融合器
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化特征编码Pipeline
        
        参数:
            config: 配置字典，包含以下字段:
                - text_encoder: 文本编码器配置
                - image_encoder: 图像编码器配置
                - numerical_encoder: 数值特征处理器配置
                - feature_fusion: 特征融合器配置
                - enabled_encoders: 启用的编码器列表，可选值为'text', 'image', 'numerical'
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 获取启用的编码器列表
        self.enabled_encoders = config.get("enabled_encoders", ["text", "image", "numerical"])
        
        # 初始化编码器
        self._init_encoders()
        
        # 初始化融合器
        self._init_fusion()
    
    def _init_encoders(self) -> None:
        """初始化编码器"""
        self.encoders = {}
        
        # 初始化文本编码器
        if "text" in self.enabled_encoders:
            text_config = self.config.get("text_encoder", {})
            self.encoders["text"] = BERTTextEncoder(text_config)
            self.logger.info("初始化文本编码器")
        
        # 初始化图像编码器
        if "image" in self.enabled_encoders:
            image_config = self.config.get("image_encoder", {})
            self.encoders["image"] = ResNetImageEncoder(image_config)
            self.logger.info("初始化图像编码器")
        
        # 初始化数值特征处理器
        if "numerical" in self.enabled_encoders:
            numerical_config = self.config.get("numerical_encoder", {})
            self.encoders["numerical"] = NumericalFeatureProcessor(numerical_config)
            self.logger.info("初始化数值特征处理器")
    
    def _init_fusion(self) -> None:
        """初始化融合器"""
        fusion_config = self.config.get("feature_fusion", {})
        self.fusion = MultiModalFeatureFusion(fusion_config)
        self.logger.info("初始化特征融合器")
        
        # 设置输入维度
        input_dims = {}
        for name, encoder in self.encoders.items():
            if hasattr(encoder, "get_output_dim"):
                try:
                    # 尝试获取输出维度
                    input_dims[name] = encoder.get_output_dim()
                except ValueError:
                    # 如果处理器尚未拟合，则跳过
                    if name == "numerical":
                        # 对于数值特征处理器，可以先设置一个默认值，后续会更新
                        self.logger.warning("数值特征处理器尚未拟合，将在fit阶段更新输出维度")
                    else:
                        # 对于其他编码器，重新抛出异常
                        raise
        
        if input_dims:
            self.fusion.set_input_dims(input_dims)
    
    def fit(self, data: Dict[str, Any]) -> 'FeatureEncodingPipeline':
        """
        拟合Pipeline
        
        参数:
            data: 数据字典，包含以下字段:
                - text: 文本数据
                - image: 图像数据
                - numerical: 数值特征数据
            
        返回:
            拟合后的Pipeline
        """
        # 拟合数值特征处理器
        if "numerical" in self.encoders and "numerical" in data:
            self.encoders["numerical"].fit(data["numerical"])
            self.logger.info("拟合数值特征处理器")
            
            # 更新融合器的输入维度
            input_dims = {}
            for name, encoder in self.encoders.items():
                if hasattr(encoder, "get_output_dim"):
                    try:
                        input_dims[name] = encoder.get_output_dim()
                    except ValueError:
                        self.logger.warning(f"无法获取编码器 {name} 的输出维度")
            
            if input_dims:
                self.fusion.set_input_dims(input_dims)
                self.logger.info("更新融合器输入维度")
        
        return self
    
    def transform(self, data: Dict[str, Any]) -> np.ndarray:
        """
        转换数据
        
        参数:
            data: 数据字典，包含以下字段:
                - text: 文本数据
                - image: 图像数据
                - numerical: 数值特征数据
            
        返回:
            转换后的特征向量
        """
        features = {}
        
        # 编码文本
        if "text" in self.encoders and "text" in data:
            features["text"] = self.encoders["text"].encode(data["text"])
            self.logger.info(f"编码文本特征: {features['text'].shape}")
        
        # 编码图像
        if "image" in self.encoders and "image" in data:
            features["image"] = self.encoders["image"].encode(data["image"])
            self.logger.info(f"编码图像特征: {features['image'].shape}")
        
        # 处理数值特征
        if "numerical" in self.encoders and "numerical" in data:
            features["numerical"] = self.encoders["numerical"].transform(data["numerical"])
            self.logger.info(f"处理数值特征: {features['numerical'].shape}")
        
        # 融合特征
        if features:
            fused = self.fusion.fuse(features)
            self.logger.info(f"融合特征: {fused.shape}")
            return fused
        else:
            return np.array([])
    
    def fit_transform(self, data: Dict[str, Any]) -> np.ndarray:
        """
        拟合并转换数据
        
        参数:
            data: 数据字典
            
        返回:
            转换后的特征向量
        """
        self.fit(data)
        return self.transform(data)
    
    def get_output_dim(self) -> int:
        """
        获取输出维度
        
        返回:
            输出特征向量的维度
        """
        return self.fusion.get_output_dim()
