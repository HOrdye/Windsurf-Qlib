"""
图像编码器模块
包含基于ResNet的图像编码器实现
"""

import logging
import os
from typing import Any, Dict, List, Optional, Union, Tuple

import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

from .base import BaseImageEncoder


class ResNetImageEncoder(BaseImageEncoder):
    """
    基于ResNet的图像编码器
    使用预训练的ResNet模型对图像进行编码
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化ResNet图像编码器
        
        参数:
            config: 配置字典，包含以下字段:
                - model_name: ResNet模型名称，可选值为'resnet18', 'resnet34', 'resnet50', 'resnet101', 'resnet152'，默认为'resnet50'
                - pretrained: 是否使用预训练模型，默认为True
                - output_layer: 输出层，可选值为'avgpool', 'fc'，默认为'avgpool'
                - device: 设备，可选值为'cpu', 'cuda'，默认为'cpu'
                - image_size: 图像大小，默认为(224, 224)
        """
        super().__init__(config)
        
        self.model_name = self.config.get("model_name", "resnet50")
        self.pretrained = self.config.get("pretrained", True)
        self.output_layer = self.config.get("output_layer", "avgpool")
        self.device = self.config.get("device", "cpu")
        self.image_size = self.config.get("image_size", (224, 224))
        
        # 初始化模型和转换器
        self._init_model()
        self._init_transforms()
        
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        super()._validate_config()
        
        # 检查模型名称
        valid_models = ["resnet18", "resnet34", "resnet50", "resnet101", "resnet152"]
        if self.config.get("model_name") not in [None, *valid_models]:
            raise ValueError(f"模型名称必须是以下之一: {valid_models}")
        
        # 检查输出层
        valid_output_layers = ["avgpool", "fc"]
        if self.config.get("output_layer") not in [None, *valid_output_layers]:
            raise ValueError(f"输出层必须是以下之一: {valid_output_layers}")
        
        # 检查设备
        valid_devices = ["cpu", "cuda"]
        if self.config.get("device") not in [None, *valid_devices]:
            raise ValueError(f"设备必须是以下之一: {valid_devices}")
    
    def _init_model(self) -> None:
        """初始化ResNet模型"""
        try:
            # 加载预训练模型
            if self.model_name == "resnet18":
                self.model = models.resnet18(pretrained=self.pretrained)
            elif self.model_name == "resnet34":
                self.model = models.resnet34(pretrained=self.pretrained)
            elif self.model_name == "resnet50":
                self.model = models.resnet50(pretrained=self.pretrained)
            elif self.model_name == "resnet101":
                self.model = models.resnet101(pretrained=self.pretrained)
            elif self.model_name == "resnet152":
                self.model = models.resnet152(pretrained=self.pretrained)
            else:
                raise ValueError(f"不支持的模型名称: {self.model_name}")
            
            # 将模型移动到指定设备
            self.model = self.model.to(self.device)
            
            # 设置为评估模式
            self.model.eval()
            
            # 根据输出层设置特征提取器
            if self.output_layer == "avgpool":
                self.feature_extractor = nn.Sequential(*list(self.model.children())[:-1])
            elif self.output_layer == "fc":
                self.feature_extractor = self.model
            else:
                raise ValueError(f"不支持的输出层: {self.output_layer}")
            
            self.logger.info(f"成功加载ResNet模型: {self.model_name}")
        except Exception as e:
            self.logger.error(f"加载ResNet模型失败: {str(e)}")
            raise
    
    def _init_transforms(self) -> None:
        """初始化图像转换器"""
        self.transform = transforms.Compose([
            transforms.Resize(self.image_size),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
    
    def _preprocess_image(self, image: np.ndarray) -> torch.Tensor:
        """
        预处理图像
        
        参数:
            image: 图像，形状为 (height, width, channels)
            
        返回:
            预处理后的图像张量
        """
        # 将numpy数组转换为PIL图像
        if isinstance(image, np.ndarray):
            if image.dtype == np.uint8:
                pil_image = Image.fromarray(image)
            else:
                # 如果不是uint8类型，先归一化到[0, 255]，再转换为uint8
                image = (image * 255).astype(np.uint8)
                pil_image = Image.fromarray(image)
        else:
            raise ValueError("图像必须是numpy数组")
        
        # 应用转换
        return self.transform(pil_image).unsqueeze(0)
    
    def encode_batch(self, images: List[np.ndarray]) -> np.ndarray:
        """
        批量编码图像
        
        参数:
            images: 图像列表，每个图像为numpy数组，形状为 (height, width, channels)
            
        返回:
            编码后的特征向量，形状为 (batch_size, embedding_dim)
        """
        if not images:
            return np.array([])
        
        # 预处理图像
        batch = torch.cat([self._preprocess_image(img) for img in images])
        
        # 将输入移动到指定设备
        batch = batch.to(self.device)
        
        # 使用模型进行编码
        with torch.no_grad():
            if self.output_layer == "avgpool":
                features = self.feature_extractor(batch)
                # 去除多余的维度
                features = features.squeeze(-1).squeeze(-1)
            else:
                features = self.feature_extractor(batch)
        
        # 将结果转换为numpy数组
        return features.cpu().numpy()
    
    def get_output_dim(self) -> int:
        """
        获取输出维度
        
        返回:
            输出特征向量的维度
        """
        if self.output_layer == "avgpool":
            # ResNet的avgpool输出维度
            return {
                "resnet18": 512,
                "resnet34": 512,
                "resnet50": 2048,
                "resnet101": 2048,
                "resnet152": 2048
            }[self.model_name]
        else:
            # fc层的输出维度
            return 1000  # ImageNet类别数
