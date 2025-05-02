"""
模型量化模块
支持INT8/INT4推理的模型量化器实现
"""

import logging
import os
import gc
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn as nn
from transformers import AutoModelForCausalLM, PreTrainedModel

from .base import BaseModelQuantizer


class Int8Quantizer(BaseModelQuantizer):
    """
    INT8量化器
    将模型量化为INT8精度
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化INT8量化器
        
        参数:
            config: 配置字典，包含以下字段:
                - per_channel: 是否使用per-channel量化，默认为True
                - dynamic: 是否使用动态量化，默认为False
                - static_method: 静态量化方法，可选值为'min_max', 'histogram'，默认为'min_max'
                - calibration_dataset: 校准数据集，用于静态量化
                - device: 设备，可选值为'cpu', 'cuda'，默认为'cuda'
        """
        super().__init__(config)
        
        self.per_channel = self.config.get("per_channel", True)
        self.dynamic = self.config.get("dynamic", False)
        self.static_method = self.config.get("static_method", "min_max")
        self.calibration_dataset = self.config.get("calibration_dataset", None)
        self.device = self.config.get("device", "cuda")
        
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        super()._validate_config()
        
        # 检查静态量化方法
        valid_static_methods = ["min_max", "histogram"]
        if self.config.get("static_method") not in [None, *valid_static_methods]:
            raise ValueError(f"静态量化方法必须是以下之一: {valid_static_methods}")
        
        # 检查设备
        valid_devices = ["cpu", "cuda"]
        if self.config.get("device") not in [None, *valid_devices]:
            raise ValueError(f"设备必须是以下之一: {valid_devices}")
        
        # 如果使用静态量化，检查校准数据集
        if not self.dynamic and self.calibration_dataset is None:
            self.logger.warning("使用静态量化但未提供校准数据集，将使用默认校准数据")
    
    def quantize(self, model: Any) -> Any:
        """
        量化模型
        
        参数:
            model: 原始模型
            
        返回:
            量化后的模型
        """
        self.logger.info(f"开始INT8量化，per_channel={self.per_channel}, dynamic={self.dynamic}")
        
        # 确保模型在正确的设备上
        if hasattr(model, "to"):
            model = model.to(self.device)
        
        # 根据模型类型选择量化方法
        if isinstance(model, PreTrainedModel):
            return self._quantize_transformers_model(model)
        elif isinstance(model, nn.Module):
            return self._quantize_torch_model(model)
        else:
            raise TypeError(f"不支持的模型类型: {type(model)}")
    
    def _quantize_torch_model(self, model: nn.Module) -> nn.Module:
        """
        量化PyTorch模型
        
        参数:
            model: PyTorch模型
            
        返回:
            量化后的模型
        """
        # 根据dynamic属性选择量化方法
        if self.dynamic:
            return self._dynamic_quantize(model)
        else:
            return self._static_quantize(model)
    
    def _dynamic_quantize(self, model: nn.Module) -> nn.Module:
        """
        动态量化PyTorch模型
        
        参数:
            model: PyTorch模型
            
        返回:
            量化后的模型
        """
        try:
            # 对于CPU上的模型，使用torch.quantization.quantize_dynamic
            if self.device == "cpu":
                import torch.quantization
                
                # 指定要量化的层类型
                quantized_layers = {nn.Linear}
                
                # 进行动态量化
                quantized_model = torch.quantization.quantize_dynamic(
                    model, 
                    quantized_layers,
                    dtype=torch.qint8
                )
                
                self.logger.info("成功使用torch.quantization.quantize_dynamic进行INT8动态量化")
                return quantized_model
            
            # 对于GPU上的模型，使用CUDA量化
            else:
                self.logger.warning("CUDA上的动态量化需要使用特定的CUDA库，回退到静态量化")
                return self._static_quantize(model)
                
        except Exception as e:
            self.logger.error(f"动态量化失败: {str(e)}")
            self.logger.info("返回原始模型")
            return model
    
    def _static_quantize(self, model: nn.Module) -> nn.Module:
        """
        静态量化PyTorch模型
        
        参数:
            model: PyTorch模型
            
        返回:
            量化后的模型
        """
        try:
            # 目前PyTorch的静态量化主要支持CPU
            if self.device == "cuda":
                self.logger.warning("CUDA上的静态量化需要使用特定的CUDA库，回退到CPU量化")
                model = model.cpu()
            
            import torch.quantization
            
            # 创建量化配置
            qconfig = torch.quantization.get_default_qconfig('fbgemm')
            
            # 准备量化
            model_prepared = torch.quantization.prepare(model)
            
            # 校准（如果有校准数据集）
            if self.calibration_dataset is not None:
                self._calibrate(model_prepared)
            
            # 转换为量化模型
            quantized_model = torch.quantization.convert(model_prepared)
            
            self.logger.info("成功使用torch.quantization进行INT8静态量化")
            
            # 如果原始设备是CUDA，将量化模型移回CUDA
            if self.device == "cuda":
                # 注意：某些量化操作可能不支持CUDA
                try:
                    quantized_model = quantized_model.cuda()
                except Exception as e:
                    self.logger.warning(f"无法将量化模型移动到CUDA: {str(e)}")
            
            return quantized_model
            
        except Exception as e:
            self.logger.error(f"静态量化失败: {str(e)}")
            self.logger.info("返回原始模型")
            return model
    
    def _calibrate(self, model: nn.Module) -> None:
        """
        校准模型（用于静态量化）
        
        参数:
            model: 准备量化的模型
        """
        self.logger.info("开始校准模型")
        
        # 使用校准数据集进行校准
        for data in self.calibration_dataset:
            # 前向传播，收集量化统计信息
            model(data)
        
        self.logger.info("校准完成")
    
    def _quantize_transformers_model(self, model: PreTrainedModel) -> PreTrainedModel:
        """
        量化Transformers模型
        
        参数:
            model: Transformers模型
            
        返回:
            量化后的模型
        """
        try:
            # 使用transformers的内置量化功能
            from transformers import BitsAndBytesConfig
            
            # 创建量化配置
            quantization_config = BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_enable_fp32_cpu_offload=True,
                llm_int8_threshold=6.0
            )
            
            # 获取模型配置
            model_config = model.config
            
            # 清理内存
            del model
            gc.collect()
            torch.cuda.empty_cache()
            
            # 重新加载量化模型
            quantized_model = AutoModelForCausalLM.from_pretrained(
                model_config._name_or_path,
                quantization_config=quantization_config,
                device_map="auto"
            )
            
            self.logger.info("成功使用transformers的内置功能进行INT8量化")
            return quantized_model
            
        except (ImportError, AttributeError) as e:
            self.logger.warning(f"无法使用transformers的内置量化功能: {str(e)}")
            self.logger.info("回退到PyTorch量化")
            return self._quantize_torch_model(model)
    
    def get_quantization_type(self) -> str:
        """
        获取量化类型
        
        返回:
            量化类型
        """
        if self.dynamic:
            return "int8_dynamic"
        else:
            return "int8_static"
    
    def get_memory_footprint(self, model: Any) -> float:
        """
        获取模型内存占用
        
        参数:
            model: 模型
            
        返回:
            内存占用（MB）
        """
        # 计算模型参数占用的内存
        param_size = 0
        for param in model.parameters():
            param_size += param.nelement() * param.element_size()
        
        # 计算模型缓冲区占用的内存
        buffer_size = 0
        for buffer in model.buffers():
            buffer_size += buffer.nelement() * buffer.element_size()
        
        # 转换为MB
        total_size = (param_size + buffer_size) / 1024 / 1024
        
        return total_size


class Int4Quantizer(BaseModelQuantizer):
    """
    INT4量化器
    将模型量化为INT4精度
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化INT4量化器
        
        参数:
            config: 配置字典，包含以下字段:
                - group_size: 量化组大小，默认为128
                - bits: 量化位数，默认为4
                - use_double_quant: 是否使用双重量化，默认为True
                - quant_type: 量化类型，可选值为'nf4', 'fp4'，默认为'nf4'
                - device: 设备，可选值为'cpu', 'cuda'，默认为'cuda'
        """
        super().__init__(config)
        
        self.group_size = self.config.get("group_size", 128)
        self.bits = self.config.get("bits", 4)
        self.use_double_quant = self.config.get("use_double_quant", True)
        self.quant_type = self.config.get("quant_type", "nf4")
        self.device = self.config.get("device", "cuda")
        
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        super()._validate_config()
        
        # 检查量化类型
        valid_quant_types = ["nf4", "fp4"]
        if self.config.get("quant_type") not in [None, *valid_quant_types]:
            raise ValueError(f"量化类型必须是以下之一: {valid_quant_types}")
        
        # 检查设备
        valid_devices = ["cpu", "cuda"]
        if self.config.get("device") not in [None, *valid_devices]:
            raise ValueError(f"设备必须是以下之一: {valid_devices}")
    
    def quantize(self, model: Any) -> Any:
        """
        量化模型
        
        参数:
            model: 原始模型
            
        返回:
            量化后的模型
        """
        self.logger.info(f"开始INT4量化，group_size={self.group_size}, quant_type={self.quant_type}")
        
        # 确保模型在正确的设备上
        if hasattr(model, "to"):
            model = model.to(self.device)
        
        # 根据模型类型选择量化方法
        if isinstance(model, PreTrainedModel):
            return self._quantize_transformers_model(model)
        else:
            self.logger.warning(f"INT4量化目前主要支持Transformers模型，其他模型类型可能无法正确量化")
            return model
    
    def _quantize_transformers_model(self, model: PreTrainedModel) -> PreTrainedModel:
        """
        量化Transformers模型
        
        参数:
            model: Transformers模型
            
        返回:
            量化后的模型
        """
        try:
            # 使用transformers的内置量化功能
            from transformers import BitsAndBytesConfig
            
            # 创建量化配置
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=self.use_double_quant,
                bnb_4bit_quant_type=self.quant_type
            )
            
            # 获取模型配置
            model_config = model.config
            
            # 清理内存
            del model
            gc.collect()
            torch.cuda.empty_cache()
            
            # 重新加载量化模型
            quantized_model = AutoModelForCausalLM.from_pretrained(
                model_config._name_or_path,
                quantization_config=quantization_config,
                device_map="auto"
            )
            
            self.logger.info("成功使用transformers的内置功能进行INT4量化")
            return quantized_model
            
        except (ImportError, AttributeError) as e:
            self.logger.error(f"无法使用transformers的内置量化功能: {str(e)}")
            self.logger.warning("INT4量化目前主要通过transformers和bitsandbytes库实现")
            self.logger.warning("如果需要使用INT4量化，请确保安装了最新版本的transformers和bitsandbytes")
            return model
    
    def get_quantization_type(self) -> str:
        """
        获取量化类型
        
        返回:
            量化类型
        """
        return f"int4_{self.quant_type}"
    
    def get_memory_footprint(self, model: Any) -> float:
        """
        获取模型内存占用
        
        参数:
            model: 模型
            
        返回:
            内存占用（MB）
        """
        # 计算模型参数占用的内存
        param_size = 0
        for param in model.parameters():
            param_size += param.nelement() * param.element_size()
        
        # 计算模型缓冲区占用的内存
        buffer_size = 0
        for buffer in model.buffers():
            buffer_size += buffer.nelement() * buffer.element_size()
        
        # 转换为MB
        total_size = (param_size + buffer_size) / 1024 / 1024
        
        return total_size


class DynamicQuantizer(BaseModelQuantizer):
    """
    动态量化器
    根据配置动态选择量化方法
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化动态量化器
        
        参数:
            config: 配置字典，包含以下字段:
                - quantization_bit: 量化位数，可选值为8, 4，默认为8
                - quantization_type: 量化类型，可选值为'dynamic', 'static'，默认为'dynamic'
                - quantization_scheme: 量化方案，可选值为'per_tensor', 'per_channel'，默认为'per_tensor'
                - device: 设备，可选值为'cpu', 'cuda'，默认为'cuda'
        """
        super().__init__(config)
        
        self.quantization_bit = self.config.get("quantization_bit", 8)
        self.quantization_type = self.config.get("quantization_type", "dynamic")
        self.quantization_scheme = self.config.get("quantization_scheme", "per_tensor")
        self.device = self.config.get("device", "cuda")
        
        # 初始化实际使用的量化器
        self._init_quantizer()
    
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        super()._validate_config()
        
        # 检查量化位数
        valid_bits = [8, 4]
        if self.config.get("quantization_bit") not in [None, *valid_bits]:
            raise ValueError(f"量化位数必须是以下之一: {valid_bits}")
        
        # 检查量化类型
        valid_types = ["dynamic", "static"]
        if self.config.get("quantization_type") not in [None, *valid_types]:
            raise ValueError(f"量化类型必须是以下之一: {valid_types}")
        
        # 检查量化方案
        valid_schemes = ["per_tensor", "per_channel"]
        if self.config.get("quantization_scheme") not in [None, *valid_schemes]:
            raise ValueError(f"量化方案必须是以下之一: {valid_schemes}")
        
        # 检查设备
        valid_devices = ["cpu", "cuda"]
        if self.config.get("device") not in [None, *valid_devices]:
            raise ValueError(f"设备必须是以下之一: {valid_devices}")
    
    def _init_quantizer(self) -> None:
        """初始化实际使用的量化器"""
        if self.quantization_bit == 8:
            # 使用INT8量化器
            int8_config = {
                "per_channel": self.quantization_scheme == "per_channel",
                "dynamic": self.quantization_type == "dynamic",
                "device": self.device
            }
            self.quantizer = Int8Quantizer(int8_config)
        else:
            # 使用INT4量化器
            int4_config = {
                "group_size": 128,
                "bits": 4,
                "device": self.device
            }
            self.quantizer = Int4Quantizer(int4_config)
    
    def quantize(self, model: Any, calibration_data: Optional[List[torch.Tensor]] = None) -> Any:
        """
        量化模型
        
        参数:
            model: 原始模型
            calibration_data: 校准数据，用于静态量化
            
        返回:
            量化后的模型
        """
        self.logger.info(f"使用动态量化器，bit={self.quantization_bit}, type={self.quantization_type}, scheme={self.quantization_scheme}")
        
        # 确保模型在正确的设备上
        if hasattr(model, "to"):
            model = model.to(self.device)
        
        # 使用实际的量化器进行量化
        if self.quantization_type == "static" and calibration_data is not None:
            # 对于静态量化，传入校准数据
            if hasattr(self.quantizer, "_calibrate"):
                # 先校准
                self.quantizer._calibrate(model, calibration_data)
                # 再量化
                return self.quantizer.quantize(model)
            else:
                self.logger.warning("所选量化器不支持校准，将使用动态量化")
                return self.quantizer.quantize(model)
        else:
            # 对于动态量化，直接量化
            return self.quantizer.quantize(model)
    
    def get_quantization_type(self) -> str:
        """
        获取量化类型
        
        返回:
            量化类型
        """
        return self.quantization_type
    
    def get_memory_footprint(self, model: Any) -> float:
        """
        获取模型内存占用
        
        参数:
            model: 模型
            
        返回:
            内存占用（MB）
        """
        return self.quantizer.get_memory_footprint(model)


class StaticQuantizer(BaseModelQuantizer):
    """
    静态量化器
    使用校准数据进行静态量化
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化静态量化器
        
        参数:
            config: 配置字典，包含以下字段:
                - quantization_bit: 量化位数，可选值为8, 4，默认为8
                - quantization_type: 量化类型，固定为'static'
                - quantization_scheme: 量化方案，可选值为'per_tensor', 'per_channel'，默认为'per_channel'
                - calibration_samples: 校准样本数量，默认为100
                - calibration_method: 校准方法，可选值为'min_max', 'histogram'，默认为'min_max'
                - device: 设备，可选值为'cpu', 'cuda'，默认为'cuda'
        """
        super().__init__(config)
        
        self.quantization_bit = self.config.get("quantization_bit", 8)
        self.quantization_scheme = self.config.get("quantization_scheme", "per_channel")
        self.calibration_samples = self.config.get("calibration_samples", 100)
        self.calibration_method = self.config.get("calibration_method", "min_max")
        self.device = self.config.get("device", "cuda")
        
        # 初始化实际使用的量化器
        self._init_quantizer()
    
    def _validate_config(self) -> None:
        """验证配置是否合法"""
        super()._validate_config()
        
        # 检查量化位数
        valid_bits = [8, 4]
        if self.config.get("quantization_bit") not in [None, *valid_bits]:
            raise ValueError(f"量化位数必须是以下之一: {valid_bits}")
        
        # 检查量化方案
        valid_schemes = ["per_tensor", "per_channel"]
        if self.config.get("quantization_scheme") not in [None, *valid_schemes]:
            raise ValueError(f"量化方案必须是以下之一: {valid_schemes}")
        
        # 检查校准方法
        valid_methods = ["min_max", "histogram"]
        if self.config.get("calibration_method") not in [None, *valid_methods]:
            raise ValueError(f"校准方法必须是以下之一: {valid_methods}")
        
        # 检查设备
        valid_devices = ["cpu", "cuda"]
        if self.config.get("device") not in [None, *valid_devices]:
            raise ValueError(f"设备必须是以下之一: {valid_devices}")
    
    def _init_quantizer(self) -> None:
        """初始化实际使用的量化器"""
        if self.quantization_bit == 8:
            # 使用INT8量化器
            int8_config = {
                "per_channel": self.quantization_scheme == "per_channel",
                "dynamic": False,  # 静态量化
                "static_method": self.calibration_method,
                "device": self.device
            }
            self.quantizer = Int8Quantizer(int8_config)
        else:
            # 使用INT4量化器
            int4_config = {
                "group_size": 128,
                "bits": 4,
                "device": self.device
            }
            self.quantizer = Int4Quantizer(int4_config)
            self.logger.warning("INT4量化器不支持完全的静态量化，将使用部分静态量化技术")
    
    def _prepare_calibration_data(self, calibration_data: List[torch.Tensor]) -> List[torch.Tensor]:
        """
        准备校准数据
        
        参数:
            calibration_data: 原始校准数据
            
        返回:
            处理后的校准数据
        """
        # 确保校准数据不超过指定的样本数量
        if len(calibration_data) > self.calibration_samples:
            self.logger.info(f"校准数据样本数量({len(calibration_data)})超过指定值({self.calibration_samples})，将随机采样")
            indices = np.random.choice(len(calibration_data), self.calibration_samples, replace=False)
            calibration_data = [calibration_data[i] for i in indices]
        
        # 确保校准数据在正确的设备上
        processed_data = []
        for data in calibration_data:
            if isinstance(data, torch.Tensor) and hasattr(data, "to"):
                processed_data.append(data.to(self.device))
            else:
                processed_data.append(data)
        
        return processed_data
    
    def quantize(self, model: Any, calibration_data: Optional[List[torch.Tensor]] = None) -> Any:
        """
        量化模型
        
        参数:
            model: 原始模型
            calibration_data: 校准数据，用于静态量化
            
        返回:
            量化后的模型
        """
        self.logger.info(f"使用静态量化器，bit={self.quantization_bit}, scheme={self.quantization_scheme}, method={self.calibration_method}")
        
        # 确保模型在正确的设备上
        if hasattr(model, "to"):
            model = model.to(self.device)
        
        # 检查校准数据
        if calibration_data is None or len(calibration_data) == 0:
            self.logger.warning("未提供校准数据，将使用动态量化")
            return self.quantizer.quantize(model)
        
        # 准备校准数据
        processed_calibration_data = self._prepare_calibration_data(calibration_data)
        
        # 使用实际的量化器进行量化
        if hasattr(self.quantizer, "_calibrate"):
            # 先校准
            self.quantizer._calibrate(model, processed_calibration_data)
            # 再量化
            return self.quantizer.quantize(model)
        else:
            self.logger.warning("所选量化器不支持校准，将使用动态量化")
            return self.quantizer.quantize(model)
    
    def get_quantization_type(self) -> str:
        """
        获取量化类型
        
        返回:
            量化类型
        """
        return "static"
    
    def get_memory_footprint(self, model: Any) -> float:
        """
        获取模型内存占用
        
        参数:
            model: 模型
            
        返回:
            内存占用（MB）
        """
        return self.quantizer.get_memory_footprint(model)
