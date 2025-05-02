"""
数据质量监控系统主模块
整合异常检测、缺失值处理、版本控制和质量报告生成功能
提供统一的API
"""
from typing import Dict, List, Union, Optional, Any, Tuple
import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime
import json
from pathlib import Path

from .base import (
    BaseAnomalyDetector,
    BaseMissingValueHandler,
    BaseVersionControl,
    BaseQualityReportGenerator,
    DATA_ROOT,
    FEATURE_STORE_DIR,
    VERSION_STORE_DIR
)

# 配置日志
logger = logging.getLogger(__name__)


class DataQualityMonitor:
    """
    数据质量监控系统
    整合异常检测、缺失值处理、版本控制和质量报告生成功能
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据质量监控系统
        
        参数:
            config: 配置字典，包含以下字段:
                - anomaly_detectors: 异常检测器配置列表
                - missing_value_handlers: 缺失值处理器配置列表
                - version_control: 版本控制系统配置
                - report_generators: 质量报告生成器配置列表
                - output_dir: 输出目录，相对于DATA_ROOT
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # 设置输出目录
        self.output_dir = os.path.join(DATA_ROOT, config.get("output_dir", "quality_reports"))
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 初始化组件
        self.anomaly_detectors = []
        self.missing_value_handlers = []
        self.version_control = None
        self.report_generators = []
        
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化各个组件"""
        # 初始化异常检测器
        if "anomaly_detectors" in self.config:
            for detector_config in self.config["anomaly_detectors"]:
                detector_type = detector_config.pop("type")
                detector_class = self._get_detector_class(detector_type)
                if detector_class:
                    self.anomaly_detectors.append(detector_class(detector_config))
        
        # 初始化缺失值处理器
        if "missing_value_handlers" in self.config:
            for handler_config in self.config["missing_value_handlers"]:
                handler_type = handler_config.pop("type")
                handler_class = self._get_handler_class(handler_type)
                if handler_class:
                    self.missing_value_handlers.append(handler_class(handler_config))
        
        # 初始化版本控制系统
        if "version_control" in self.config:
            vc_config = self.config["version_control"]
            vc_type = vc_config.pop("type")
            vc_class = self._get_version_control_class(vc_type)
            if vc_class:
                self.version_control = vc_class(vc_config)
        
        # 初始化质量报告生成器
        if "report_generators" in self.config:
            for generator_config in self.config["report_generators"]:
                generator_type = generator_config.pop("type")
                generator_class = self._get_report_generator_class(generator_type)
                if generator_class:
                    self.report_generators.append(generator_class(generator_config))
    
    def _get_detector_class(self, detector_type: str) -> Optional[type]:
        """
        根据类型获取异常检测器类
        
        参数:
            detector_type: 异常检测器类型
            
        返回:
            异常检测器类
        """
        from .anomaly_detector import StatisticalAnomalyDetector
        from .text_image_detector import TextAnomalyDetector, ImageAnomalyDetector
        
        detector_map = {
            "statistical": StatisticalAnomalyDetector,
            "text": TextAnomalyDetector,
            "image": ImageAnomalyDetector
        }
        
        if detector_type in detector_map:
            return detector_map[detector_type]
        else:
            self.logger.warning(f"未知的异常检测器类型: {detector_type}")
            return None
    
    def _get_handler_class(self, handler_type: str) -> Optional[type]:
        """
        根据类型获取缺失值处理器类
        
        参数:
            handler_type: 缺失值处理器类型
            
        返回:
            缺失值处理器类
        """
        from .missing_value_handler import BasicMissingValueHandler, InterpolationMissingValueHandler
        from .multimodal_handler import MultiModalMissingValueHandler
        
        handler_map = {
            "basic": BasicMissingValueHandler,
            "interpolation": InterpolationMissingValueHandler,
            "multimodal": MultiModalMissingValueHandler
        }
        
        if handler_type in handler_map:
            return handler_map[handler_type]
        else:
            self.logger.warning(f"未知的缺失值处理器类型: {handler_type}")
            return None
    
    def _get_version_control_class(self, vc_type: str) -> Optional[type]:
        """
        根据类型获取版本控制系统类
        
        参数:
            vc_type: 版本控制系统类型
            
        返回:
            版本控制系统类
        """
        from .version_control import DataVersionControl
        
        vc_map = {
            "basic": DataVersionControl
        }
        
        if vc_type in vc_map:
            return vc_map[vc_type]
        else:
            self.logger.warning(f"未知的版本控制系统类型: {vc_type}")
            return None
    
    def _get_report_generator_class(self, generator_type: str) -> Optional[type]:
        """
        根据类型获取质量报告生成器类
        
        参数:
            generator_type: 质量报告生成器类型
            
        返回:
            质量报告生成器类
        """
        from .report_generator import DataQualityReportGenerator
        
        generator_map = {
            "quality": DataQualityReportGenerator
        }
        
        if generator_type in generator_map:
            return generator_map[generator_type]
        else:
            self.logger.warning(f"未知的质量报告生成器类型: {generator_type}")
            return None
    
    def monitor_data(self, data: Any, data_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        监控数据质量
        
        参数:
            data: 待监控的数据
            data_info: 数据信息字典，可选，可包含文本数据、图像数据等
            
        返回:
            监控结果字典
        """
        if data_info is None:
            data_info = {}
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "anomalies": {"anomalies": []},
            "missing_values_filled": 0,
            "version_id": None,
            "report_path": None,
            "quality_reports": {}
        }
        
        # 提取文本和图像数据
        text_data = data_info.get("text_data", {})
        image_data = data_info.get("image_data", {})
        
        # 1. 检测异常
        if self.anomaly_detectors:
            all_anomalies = []
            
            for detector in self.anomaly_detectors:
                detector_name = detector.__class__.__name__
                try:
                    # 根据检测器类型选择数据
                    if "Text" in detector_name and text_data:
                        detection_result = detector.detect(text_data)
                    elif "Image" in detector_name and image_data:
                        detection_result = detector.detect(image_data)
                    else:
                        detection_result = detector.detect(data)
                    
                    if "anomalies" in detection_result:
                        all_anomalies.extend(detection_result["anomalies"])
                    
                    self.logger.info(f"异常检测完成: {detector_name}, 检测到 {len(detection_result.get('anomalies', []))} 个异常")
                except Exception as e:
                    self.logger.error(f"异常检测失败: {detector_name}, 错误: {e}")
            
            result["anomalies"] = {"anomalies": all_anomalies}
        
        # 2. 处理缺失值
        if self.missing_value_handlers:
            # 记录处理前的缺失值数量
            missing_before = data.isna().sum().sum() if hasattr(data, 'isna') else 0
            processed_data = data.copy() if hasattr(data, 'copy') else data
            
            for handler in self.missing_value_handlers:
                handler_name = handler.__class__.__name__
                try:
                    # 根据处理器类型选择数据和参数
                    if "MultiModal" in handler_name:
                        # 为多模态处理器设置文本和图像数据
                        handler_config = handler.config.copy()
                        handler_config["text_data"] = text_data
                        handler_config["image_data"] = image_data
                        handler.config = handler_config
                    
                    processed_data = handler.fill(processed_data)
                    
                    self.logger.info(f"缺失值处理完成: {handler_name}")
                except Exception as e:
                    self.logger.error(f"缺失值处理失败: {handler_name}, 错误: {e}")
            
            # 记录处理后的缺失值数量
            missing_after = processed_data.isna().sum().sum() if hasattr(processed_data, 'isna') else 0
            result["missing_values_filled"] = missing_before - missing_after
            
            # 更新数据为处理后的数据
            data = processed_data
        
        # 3. 保存版本
        if self.version_control:
            try:
                # 准备版本信息
                version_info = {
                    "timestamp": datetime.now().isoformat(),
                    "description": "数据质量监控处理后的数据",
                    "anomalies_count": len(result["anomalies"]["anomalies"]),
                    "missing_values_filled": result["missing_values_filled"]
                }
                
                # 保存版本
                version_id = self.version_control.save_version("stock_data", data, version_info)
                result["version_id"] = version_id
                
                self.logger.info(f"版本保存完成: {version_id}")
            except Exception as e:
                self.logger.error(f"版本保存失败: {e}")
                result["version_id"] = None
        
        # 4. 生成质量报告
        if self.report_generators:
            for generator in self.report_generators:
                generator_name = generator.__class__.__name__
                try:
                    # 生成报告
                    report_path = generator.generate_report(
                        data=data,
                        report_name="stock_data_quality",
                        anomalies=result["anomalies"],
                        missing_info={"filled": result["missing_values_filled"]},
                        version_info={"version_id": result["version_id"]}
                    )
                    
                    result["report_path"] = report_path
                    result["quality_reports"][generator_name] = {"path": report_path}
                    
                    self.logger.info(f"质量报告生成完成: {generator_name}, 路径: {report_path}")
                except Exception as e:
                    self.logger.error(f"质量报告生成失败: {generator_name}, 错误: {e}")
                    result["quality_reports"][generator_name] = {"error": str(e)}
        
        return result
    
    def get_data_version(self, version_id: str) -> Any:
        """
        获取指定版本的数据
        
        参数:
            version_id: 版本ID
            
        返回:
            版本数据
        """
        if self.version_control:
            try:
                return self.version_control.load_version(version_id)
            except Exception as e:
                self.logger.error(f"加载版本失败: {version_id}, 错误: {e}")
                raise
        else:
            raise ValueError("版本控制系统未初始化")
    
    def list_data_versions(self) -> List[Dict[str, Any]]:
        """
        列出所有数据版本
        
        返回:
            版本信息列表
        """
        if self.version_control:
            try:
                return self.version_control.list_versions()
            except Exception as e:
                self.logger.error(f"列出版本失败: {e}")
                raise
        else:
            raise ValueError("版本控制系统未初始化")
    
    def compare_data_versions(self, version_id1: str, version_id2: str) -> Dict[str, Any]:
        """
        比较两个数据版本
        
        参数:
            version_id1: 第一个版本ID
            version_id2: 第二个版本ID
            
        返回:
            比较结果字典
        """
        if self.version_control:
            try:
                return self.version_control.compare_versions(version_id1, version_id2)
            except Exception as e:
                self.logger.error(f"比较版本失败: {version_id1} vs {version_id2}, 错误: {e}")
                raise
        else:
            raise ValueError("版本控制系统未初始化")
    
    def generate_data_quality_report(self, data: Any, report_type: str = "comprehensive") -> Dict[str, Any]:
        """
        生成数据质量报告
        
        参数:
            data: 待分析的数据
            report_type: 报告类型
            
        返回:
            质量报告字典
        """
        for generator in self.report_generators:
            if generator.config.get("report_type") == report_type:
                try:
                    report = generator.generate_report(data)
                    
                    # 保存报告
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    report_path = os.path.join(self.output_dir, f"{report_type}_{timestamp}.html")
                    generator.save_report(report, report_path)
                    
                    self.logger.info(f"质量报告生成完成: {report_type}")
                    return report
                except Exception as e:
                    self.logger.error(f"质量报告生成失败: {report_type}, 错误: {e}")
                    raise
        
        raise ValueError(f"未找到类型为 {report_type} 的报告生成器")
