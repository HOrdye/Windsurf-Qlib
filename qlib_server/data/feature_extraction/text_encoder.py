"""
文本编码器模块
包含基于BERT的文本编码器实现
"""

import logging
import os
from typing import Any, Dict, List, Optional, Union

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer, BertModel, BertTokenizer

from .base import BaseTextEncoder


class BERTTextEncoder(BaseTextEncoder):
    """
    基于BERT的文本编码器
    使用预训练的BERT模型对文本进行编码
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化BERT文本编码器
        
        参数:
            config: 配置字典，包含以下字段:
                - model_name: BERT模型名称，默认为'bert-base-chinese'
                - max_length: 文本最大长度，默认为128
                - pooling_strategy: 池化策略，可选值为'cls', 'mean', 'max'，默认为'cls'
                - device: 设备，可选值为'cpu', 'cuda'，默认为'cpu'
                - cache_dir: 模型缓存目录，默认为None
        """
        super().__init__(config)
        
        self.model_name = self.config.get("model_name", "bert-base-chinese")
        self.max_length = self.config.get("max_length", 128)
        self.pooling_strategy = self.config.get("pooling_strategy", "cls")
        self.device = self.config.get("device", "cpu")
        self.cache_dir = self.config.get("cache_dir", None)
        
        # 初始化模型和分词器
        self._init_model()
        
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        super()._validate_config()
        
        # 检查池化策略
        valid_pooling_strategies = ["cls", "mean", "max"]
        if self.config.get("pooling_strategy") not in [None, *valid_pooling_strategies]:
            raise ValueError(f"池化策略必须是以下之一: {valid_pooling_strategies}")
        
        # 检查设备
        valid_devices = ["cpu", "cuda"]
        if self.config.get("device") not in [None, *valid_devices]:
            raise ValueError(f"设备必须是以下之一: {valid_devices}")
    
    def _init_model(self) -> None:
        """初始化BERT模型和分词器"""
        try:
            # 使用清华大学开源软件镜像站作为模型下载源
            os.environ['HF_ENDPOINT'] = 'https://mirrors.tuna.tsinghua.edu.cn/hugging-face-models'
            os.environ['TRANSFORMERS_OFFLINE'] = '0'  # 确保在线模式
            
            # 设置模型缓存目录
            if self.cache_dir is None:
                self.cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
                os.makedirs(self.cache_dir, exist_ok=True)
            
            self.logger.info(f"使用模型缓存目录: {self.cache_dir}")
            self.logger.info(f"使用Hugging Face镜像: {os.environ.get('HF_ENDPOINT')}")
            
            # 加载分词器
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name, 
                cache_dir=self.cache_dir,
                mirror='tuna'
            )
            
            # 加载模型
            self.model = AutoModel.from_pretrained(
                self.model_name, 
                cache_dir=self.cache_dir,
                mirror='tuna'
            )
            
            # 将模型移动到指定设备
            self.model = self.model.to(self.device)
            
            # 设置为评估模式
            self.model.eval()
            
            self.logger.info(f"成功加载BERT模型: {self.model_name}")
        except Exception as e:
            self.logger.error(f"加载BERT模型失败: {str(e)}")
            raise
    
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """
        批量编码文本
        
        参数:
            texts: 文本列表
            
        返回:
            编码后的特征向量，形状为 (batch_size, embedding_dim)
        """
        if not texts:
            return np.array([])
        
        # 对文本进行分词
        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt"
        )
        
        # 将输入移动到指定设备
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # 使用模型进行编码
        with torch.no_grad():
            outputs = self.model(**inputs)
            
            # 获取最后一层的隐藏状态
            last_hidden_state = outputs.last_hidden_state
            
            # 根据池化策略获取文本表示
            if self.pooling_strategy == "cls":
                # 使用[CLS]标记的表示作为文本表示
                embeddings = last_hidden_state[:, 0]
            elif self.pooling_strategy == "mean":
                # 使用所有标记的平均值作为文本表示
                # 创建注意力掩码，排除填充标记
                attention_mask = inputs["attention_mask"]
                embeddings = torch.sum(last_hidden_state * attention_mask.unsqueeze(-1), dim=1)
                embeddings = embeddings / torch.sum(attention_mask, dim=1, keepdim=True)
            elif self.pooling_strategy == "max":
                # 使用所有标记的最大值作为文本表示
                # 创建注意力掩码，排除填充标记
                attention_mask = inputs["attention_mask"]
                # 将填充标记的表示设为很小的值
                masked_hidden = last_hidden_state * attention_mask.unsqueeze(-1) - 1e10 * (1 - attention_mask.unsqueeze(-1))
                embeddings = torch.max(masked_hidden, dim=1)[0]
            else:
                raise ValueError(f"不支持的池化策略: {self.pooling_strategy}")
        
        # 将结果转换为numpy数组
        return embeddings.cpu().numpy()
    
    def get_output_dim(self) -> int:
        """
        获取输出维度
        
        返回:
            输出特征向量的维度
        """
        return self.model.config.hidden_size
