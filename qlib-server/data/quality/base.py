"""
数据质量监控系统基础接口定义
定义了异常检测、缺失值处理、版本控制和质量报告生成的基类
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Union, Optional, Any, Tuple
import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局配置
DATA_ROOT = os.environ.get("QLIB_DATA_ROOT", "/data/qlib")
FEATURE_STORE_DIR = os.path.join(DATA_ROOT, "features")
VERSION_STORE_DIR = os.path.join(DATA_ROOT, "versions")


class BaseAnomalyDetector(ABC):
    """
    数据异常检测器基类
    定义了数据异常检测的基本接口
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化异常检测器
        
        参数:
            config: 配置字典，包含异常检测器的参数
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._validate_config()
    
    def _validate_config(self):
        """验证配置是否合法"""
        required_keys = ["threshold"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"配置缺少必要参数: {key}")
    
    @abstractmethod
    def detect(self, data: Any) -> Dict[str, Any]:
        """
        检测数据异常的抽象方法
        
        参数:
            data: 待检测的数据
            
        返回:
            检测结果字典，包含异常信息
        """
        pass
    
    def report(self, detection_result: Dict[str, Any]) -> str:
        """
        生成异常检测报告
        
        参数:
            detection_result: 检测结果字典
            
        返回:
            异常检测报告字符串
        """
        report_str = f"异常检测报告 ({self.__class__.__name__}):\n"
        
        if "anomalies" in detection_result:
            anomalies = detection_result["anomalies"]
            report_str += f"检测到 {len(anomalies)} 个异常\n"
            
            for i, anomaly in enumerate(anomalies[:5]):  # 只显示前5个异常
                report_str += f"  {i+1}. {anomaly}\n"
            
            if len(anomalies) > 5:
                report_str += f"  ... 还有 {len(anomalies) - 5} 个异常未显示\n"
        else:
            report_str += "未检测到异常\n"
        
        return report_str


class BaseMissingValueHandler(ABC):
    """
    数据缺失值处理器基类
    定义了数据缺失值处理的基本接口
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化缺失值处理器
        
        参数:
            config: 配置字典，包含缺失值处理器的参数
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._validate_config()
    
    def _validate_config(self):
        """验证配置是否合法"""
        required_keys = ["method"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"配置缺少必要参数: {key}")
    
    @abstractmethod
    def fill(self, data: Any) -> Any:
        """
        填充数据缺失值的抽象方法
        
        参数:
            data: 待处理的数据
            
        返回:
            处理后的数据
        """
        pass
    
    def report(self, data_before: Any, data_after: Any) -> str:
        """
        生成缺失值处理报告
        
        参数:
            data_before: 处理前的数据
            data_after: 处理后的数据
            
        返回:
            缺失值处理报告字符串
        """
        report_str = f"缺失值处理报告 ({self.__class__.__name__}):\n"
        
        if isinstance(data_before, pd.DataFrame) and isinstance(data_after, pd.DataFrame):
            na_before = data_before.isna().sum().sum()
            na_after = data_after.isna().sum().sum()
            
            report_str += f"处理前缺失值总数: {na_before}\n"
            report_str += f"处理后缺失值总数: {na_after}\n"
            report_str += f"填充缺失值数量: {na_before - na_after}\n"
            
            if na_before > 0:
                report_str += f"填充率: {(na_before - na_after) / na_before * 100:.2f}%\n"
        
        return report_str


class BaseVersionControl(ABC):
    """
    数据版本控制系统基类
    定义了数据版本控制的基本接口
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化版本控制系统
        
        参数:
            config: 配置字典，包含版本控制系统的参数
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._validate_config()
        
        # 确保版本存储目录存在
        os.makedirs(VERSION_STORE_DIR, exist_ok=True)
    
    def _validate_config(self):
        """验证配置是否合法"""
        required_keys = ["storage_path"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"配置缺少必要参数: {key}")
    
    @abstractmethod
    def save_version(self, data: Any, version_info: Dict[str, Any]) -> str:
        """
        保存数据版本的抽象方法
        
        参数:
            data: 待保存的数据
            version_info: 版本信息字典
            
        返回:
            版本ID
        """
        pass
    
    @abstractmethod
    def load_version(self, version_id: str) -> Any:
        """
        加载数据版本的抽象方法
        
        参数:
            version_id: 版本ID
            
        返回:
            加载的数据
        """
        pass
    
    @abstractmethod
    def list_versions(self) -> List[Dict[str, Any]]:
        """
        列出所有版本的抽象方法
        
        返回:
            版本信息列表
        """
        pass
    
    @abstractmethod
    def compare_versions(self, version_id1: str, version_id2: str) -> Dict[str, Any]:
        """
        比较两个版本的抽象方法
        
        参数:
            version_id1: 第一个版本ID
            version_id2: 第二个版本ID
            
        返回:
            比较结果字典
        """
        pass


class BaseReportGenerator(ABC):
    """
    数据质量报告生成器基类
    定义了数据质量报告生成的基本接口
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化报告生成器
        
        参数:
            config: 配置字典，包含报告生成器的参数
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._validate_config()
    
    def _validate_config(self):
        """验证配置是否合法"""
        required_keys = ["report_format", "output_path"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"配置缺少必要参数: {key}")
    
    @abstractmethod
    def generate_report(self, data: Any, report_name: str, **kwargs) -> str:
        """
        生成数据质量报告的抽象方法
        
        参数:
            data: 待分析的数据
            report_name: 报告名称
            **kwargs: 其他参数
            
        返回:
            报告路径
        """
        pass


class BaseQualityReportGenerator(ABC):
    """
    数据质量报告生成器基类
    定义了数据质量报告生成的基本接口
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化质量报告生成器
        
        参数:
            config: 配置字典，包含质量报告生成器的参数
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._validate_config()
    
    def _validate_config(self):
        """验证配置是否合法"""
        required_keys = ["report_type"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"配置缺少必要参数: {key}")
    
    @abstractmethod
    def generate_report(self, data: Any) -> Dict[str, Any]:
        """
        生成数据质量报告的抽象方法
        
        参数:
            data: 待分析的数据
            
        返回:
            质量报告字典
        """
        pass
    
    def save_report(self, report: Dict[str, Any], output_path: str) -> None:
        """
        保存数据质量报告
        
        参数:
            report: 质量报告字典
            output_path: 输出路径
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 根据文件扩展名选择保存格式
        if output_path.endswith('.json'):
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        elif output_path.endswith('.html'):
            # 简单的HTML报告
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>数据质量报告</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #333; }}
                    .section {{ margin-bottom: 20px; }}
                    .metric {{ margin: 10px 0; }}
                    .good {{ color: green; }}
                    .warning {{ color: orange; }}
                    .error {{ color: red; }}
                </style>
            </head>
            <body>
                <h1>数据质量报告</h1>
                <div class="section">
                    <h2>报告概述</h2>
                    <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>报告类型: {self.config['report_type']}</p>
                </div>
            """
            
            # 添加报告内容
            for section, content in report.items():
                html_content += f'<div class="section"><h2>{section}</h2>'
                
                if isinstance(content, dict):
                    for key, value in content.items():
                        status_class = ""
                        if isinstance(value, dict) and "status" in value:
                            status = value["status"]
                            if status == "good":
                                status_class = "good"
                            elif status == "warning":
                                status_class = "warning"
                            elif status == "error":
                                status_class = "error"
                        
                        html_content += f'<div class="metric"><strong>{key}:</strong> <span class="{status_class}">{value}</span></div>'
                elif isinstance(content, list):
                    html_content += '<ul>'
                    for item in content:
                        html_content += f'<li>{item}</li>'
                    html_content += '</ul>'
                else:
                    html_content += f'<p>{content}</p>'
                
                html_content += '</div>'
            
            html_content += """
            </body>
            </html>
            """
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
        else:
            # 默认保存为文本格式
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"数据质量报告 ({self.config['report_type']})\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                for section, content in report.items():
                    f.write(f"## {section}\n")
                    
                    if isinstance(content, dict):
                        for key, value in content.items():
                            f.write(f"- {key}: {value}\n")
                    elif isinstance(content, list):
                        for item in content:
                            f.write(f"- {item}\n")
                    else:
                        f.write(f"{content}\n")
                    
                    f.write("\n")
        
        self.logger.info(f"质量报告已保存到: {output_path}")
