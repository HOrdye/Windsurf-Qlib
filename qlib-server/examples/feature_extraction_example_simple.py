#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多模态特征编码示例（简化版）
主要展示数值特征处理和简单的特征融合
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('__main__')


class SimpleTextEncoder:
    """简单文本编码器，使用词袋模型"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.vocab = {}
        self.output_dim = 0
    
    def encode(self, texts):
        """编码文本"""
        if isinstance(texts, str):
            texts = [texts]
        
        # 构建词汇表
        if not self.vocab:
            for text in texts:
                for word in text.lower().split():
                    if word not in self.vocab:
                        self.vocab[word] = len(self.vocab)
            self.output_dim = len(self.vocab)
        
        # 编码文本
        features = np.zeros((len(texts), len(self.vocab)))
        for i, text in enumerate(texts):
            for word in text.lower().split():
                if word in self.vocab:
                    features[i, self.vocab[word]] += 1
        
        return features
    
    def get_output_dim(self):
        """获取输出维度"""
        return self.output_dim


class SimpleImageEncoder:
    """简单图像编码器，使用颜色直方图"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.bins = self.config.get("bins", 8)
        self.output_dim = self.bins * 3  # RGB三通道
    
    def encode(self, images):
        """编码图像"""
        if isinstance(images, np.ndarray) and len(images.shape) == 3:
            images = [images]
        
        features = np.zeros((len(images), self.output_dim))
        for i, image in enumerate(images):
            # 计算RGB三通道的直方图
            for c in range(3):  # RGB三通道
                hist, _ = np.histogram(image[:, :, c], bins=self.bins, range=(0, 255))
                features[i, c*self.bins:(c+1)*self.bins] = hist / hist.sum()
        
        return features
    
    def get_output_dim(self):
        """获取输出维度"""
        return self.output_dim


class SimpleNumericalEncoder:
    """简单数值特征处理器"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.mean = None
        self.std = None
        self.feature_names = []
        self.output_dim = 0
    
    def fit(self, data):
        """拟合数值特征处理器"""
        # 选择数值列
        numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
        self.feature_names = numeric_cols
        self.output_dim = len(numeric_cols)
        
        # 计算均值和标准差
        self.mean = data[numeric_cols].mean()
        self.std = data[numeric_cols].std()
        
        return self
    
    def transform(self, data):
        """转换数值特征"""
        if self.mean is None or self.std is None:
            raise ValueError("处理器尚未拟合")
        
        # 标准化数值特征
        return (data[self.feature_names] - self.mean) / (self.std + 1e-8)
    
    def fit_transform(self, data):
        """拟合并转换数值特征"""
        self.fit(data)
        return self.transform(data)
    
    def get_feature_names(self):
        """获取特征名称"""
        return self.feature_names
    
    def get_output_dim(self):
        """获取输出维度"""
        return self.output_dim


class SimpleFeatureFusion:
    """简单特征融合器"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.fusion_method = self.config.get("fusion_method", "concat")
        self.weights = self.config.get("weights", {})
        self.input_dims = {}
    
    def set_input_dims(self, input_dims):
        """设置输入维度"""
        self.input_dims = input_dims
    
    def fuse(self, features):
        """融合特征"""
        if not features:
            return np.array([])
        
        if self.fusion_method == "concat":
            return self._concat_fusion(features)
        elif self.fusion_method == "weighted_sum":
            return self._weighted_sum_fusion(features)
        else:
            raise ValueError(f"不支持的融合方法: {self.fusion_method}")
    
    def _concat_fusion(self, features):
        """拼接融合"""
        feature_list = []
        for name in sorted(features.keys()):
            feature_list.append(features[name])
        
        return np.concatenate(feature_list, axis=1)
    
    def _weighted_sum_fusion(self, features):
        """加权求和融合"""
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
    
    def get_output_dim(self):
        """获取输出维度"""
        if self.fusion_method == "concat":
            return sum(self.input_dims.values())
        else:
            return next(iter(self.input_dims.values())) if self.input_dims else 0


def generate_sample_data():
    """生成示例数据"""
    # 生成文本数据
    texts = [
        "美国股市今日上涨，道琼斯指数创历史新高",
        "科技股领涨，苹果和微软股价大幅上涨",
        "市场对经济复苏持乐观态度，投资者信心增强",
        "央行宣布维持利率不变，符合市场预期",
        "原油价格上涨，能源股表现强劲"
    ]
    
    # 生成图像数据（创建简单的彩色图像）
    images = []
    for i in range(5):
        # 创建一个随机颜色的图像
        img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        images.append(img)
    
    # 生成数值特征数据
    numerical_data = {
        'price': [100.5, 200.3, 150.8, 300.2, 250.1],
        'volume': [1000000, 2000000, 1500000, 3000000, 2500000],
        'pe_ratio': [15.2, 20.5, 18.3, 25.1, 22.7],
        'market_cap': [1000000000, 2000000000, 1500000000, 3000000000, 2500000000],
        'dividend_yield': [0.02, 0.03, 0.025, 0.04, 0.035]
    }
    numerical_df = pd.DataFrame(numerical_data)
    
    return {
        'text': texts,
        'image': images,
        'numerical': numerical_df
    }


def demo_text_encoder():
    """演示文本编码器"""
    logger.info("=== 演示文本编码器 ===")
    
    # 生成示例数据
    data = generate_sample_data()
    texts = data['text']
    
    # 创建文本编码器
    text_encoder = SimpleTextEncoder()
    
    # 编码文本
    text_features = text_encoder.encode(texts)
    
    logger.info(f"文本特征形状: {text_features.shape}")
    logger.info(f"文本特征输出维度: {text_encoder.get_output_dim()}")
    logger.info(f"文本特征示例: {text_features[0][:5]}...")
    
    return text_features


def demo_image_encoder():
    """演示图像编码器"""
    logger.info("=== 演示图像编码器 ===")
    
    # 生成示例数据
    data = generate_sample_data()
    images = data['image']
    
    # 创建图像编码器
    image_encoder = SimpleImageEncoder({"bins": 8})
    
    # 编码图像
    image_features = image_encoder.encode(images)
    
    logger.info(f"图像特征形状: {image_features.shape}")
    logger.info(f"图像特征输出维度: {image_encoder.get_output_dim()}")
    logger.info(f"图像特征示例: {image_features[0]}")
    
    return image_features


def demo_numerical_encoder():
    """演示数值特征处理器"""
    logger.info("=== 演示数值特征处理器 ===")
    
    # 生成示例数据
    data = generate_sample_data()
    numerical_df = data['numerical']
    
    # 创建数值特征处理器
    numerical_encoder = SimpleNumericalEncoder()
    
    # 拟合并转换数值特征
    numerical_features = numerical_encoder.fit_transform(numerical_df)
    
    logger.info(f"数值特征形状: {numerical_features.shape}")
    logger.info(f"数值特征输出维度: {numerical_encoder.get_output_dim()}")
    logger.info(f"数值特征示例: {numerical_features.iloc[0].values}")
    logger.info(f"特征名称: {numerical_encoder.get_feature_names()}")
    
    return numerical_features.values


def demo_feature_fusion(text_features, image_features, numerical_features):
    """演示特征融合"""
    logger.info("=== 演示特征融合 ===")
    
    # 创建特征融合器
    fusion_config = {
        "fusion_method": "concat",
        "weights": {
            "text": 0.4,
            "image": 0.3,
            "numerical": 0.3
        }
    }
    fusion = SimpleFeatureFusion(fusion_config)
    
    # 设置输入维度
    input_dims = {
        "text": text_features.shape[1],
        "image": image_features.shape[1],
        "numerical": numerical_features.shape[1]
    }
    fusion.set_input_dims(input_dims)
    
    # 融合特征
    features = {
        "text": text_features,
        "image": image_features,
        "numerical": numerical_features
    }
    fused_features = fusion.fuse(features)
    
    logger.info(f"融合特征形状: {fused_features.shape}")
    logger.info(f"融合特征输出维度: {fusion.get_output_dim()}")
    logger.info(f"融合特征示例: {fused_features[0][:5]}...")
    
    return fused_features


def main():
    """主函数"""
    logger.info("开始多模态特征编码示例（简化版）")
    
    try:
        # 演示文本编码器
        text_features = demo_text_encoder()
        
        # 演示图像编码器
        image_features = demo_image_encoder()
        
        # 演示数值特征处理器
        numerical_features = demo_numerical_encoder()
        
        # 演示特征融合
        fused_features = demo_feature_fusion(text_features, image_features, numerical_features)
        
        logger.info("多模态特征编码示例（简化版）完成")
    except Exception as e:
        logger.error(f"多模态特征编码示例出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()
