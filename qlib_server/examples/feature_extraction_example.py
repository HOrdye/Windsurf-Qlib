#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多模态特征编码示例
展示如何使用特征提取Pipeline进行多模态特征编码
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
from PIL import Image
from typing import Dict, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.feature_extraction import (
    BERTTextEncoder,
    ResNetImageEncoder,
    NumericalFeatureProcessor,
    MultiModalFeatureFusion,
    FeatureEncodingPipeline
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('__main__')


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
    text_encoder_config = {
        "model_name": "prajjwal1/bert-tiny",  # 使用更小的BERT模型
        "max_length": 64,  # 减小最大长度
        "pooling_strategy": "cls",
        "device": "cpu"
    }
    logger.info(f"使用BERT模型: {text_encoder_config['model_name']}")
    text_encoder = BERTTextEncoder(text_encoder_config)
    
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
    image_encoder_config = {
        "model_name": "resnet18",  # 使用最小的ResNet模型
        "pretrained": True,
        "output_layer": "avgpool",
        "device": "cpu",
        "image_size": (112, 112)  # 减小图像大小
    }
    logger.info(f"使用ResNet模型: {image_encoder_config['model_name']}")
    logger.info(f"图像大小: {image_encoder_config['image_size']}")
    image_encoder = ResNetImageEncoder(image_encoder_config)
    
    # 编码图像
    image_features = image_encoder.encode(images)
    
    logger.info(f"图像特征形状: {image_features.shape}")
    logger.info(f"图像特征输出维度: {image_encoder.get_output_dim()}")
    logger.info(f"图像特征示例: {image_features[0][:5]}...")
    
    return image_features


def demo_numerical_encoder():
    """演示数值特征处理器"""
    logger.info("=== 演示数值特征处理器 ===")
    
    # 生成示例数据
    data = generate_sample_data()
    numerical_df = data['numerical']
    
    # 创建数值特征处理器
    numerical_encoder_config = {
        "scaler": "standard",
        "imputer": "mean",
        "use_pca": False
    }
    numerical_encoder = NumericalFeatureProcessor(numerical_encoder_config)
    
    # 拟合并转换数值特征
    numerical_features = numerical_encoder.fit_transform(numerical_df)
    
    logger.info(f"数值特征形状: {numerical_features.shape}")
    logger.info(f"数值特征输出维度: {numerical_encoder.get_output_dim()}")
    logger.info(f"数值特征示例: {numerical_features[0]}")
    logger.info(f"特征名称: {numerical_encoder.get_feature_names()}")
    
    return numerical_features


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
    fusion = MultiModalFeatureFusion(fusion_config)
    
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


def demo_feature_pipeline():
    """演示特征编码Pipeline"""
    logger.info("=== 演示特征编码Pipeline ===")
    
    # 生成示例数据
    data = generate_sample_data()
    
    # 创建Pipeline配置
    pipeline_config = {
        "enabled_encoders": ["text", "image", "numerical"],
        "text_encoder": {
            "model_name": "bert-base-chinese",
            "max_length": 128,
            "pooling_strategy": "cls",
            "device": "cpu"
        },
        "image_encoder": {
            "model_name": "resnet18",
            "pretrained": True,
            "output_layer": "avgpool",
            "device": "cpu"
        },
        "numerical_encoder": {
            "scaler": "standard",
            "imputer": "mean",
            "use_pca": False
        },
        "feature_fusion": {
            "fusion_method": "concat",
            "weights": {
                "text": 0.4,
                "image": 0.3,
                "numerical": 0.3
            }
        }
    }
    
    # 创建Pipeline
    pipeline = FeatureEncodingPipeline(pipeline_config)
    
    # 拟合并转换数据
    features = pipeline.fit_transform(data)
    
    logger.info(f"Pipeline输出特征形状: {features.shape}")
    logger.info(f"Pipeline输出维度: {pipeline.get_output_dim()}")
    logger.info(f"Pipeline输出特征示例: {features[0][:5]}...")
    
    return features


def main():
    """主函数"""
    logger.info("开始多模态特征编码示例")
    
    try:
        # 演示文本编码器
        text_features = demo_text_encoder()
        
        # 演示图像编码器
        image_features = demo_image_encoder()
        
        # 演示数值特征处理器
        numerical_features = demo_numerical_encoder()
        
        # 演示特征融合
        fused_features = demo_feature_fusion(text_features, image_features, numerical_features)
        
        # 演示特征编码Pipeline
        pipeline_features = demo_feature_pipeline()
        
        logger.info("多模态特征编码示例完成")
    except Exception as e:
        logger.error(f"多模态特征编码示例出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()
