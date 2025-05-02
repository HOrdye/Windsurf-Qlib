"""
文本和图像异常检测器实现
用于检测文本和图像数据中的异常
"""
from typing import Dict, List, Union, Optional, Any, Tuple
import pandas as pd
import numpy as np
import os
import logging
import json
from pathlib import Path
import warnings
import re

from .base import BaseAnomalyDetector

# 配置日志
logger = logging.getLogger(__name__)


class TextAnomalyDetector(BaseAnomalyDetector):
    """
    文本异常检测器
    检测文本数据中的异常内容
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化文本异常检测器
        
        参数:
            config: 配置字典，包含以下字段:
                - threshold: 异常阈值
                - method: 检测方法，支持'length'、'keyword'、'language'、'sentiment'
                - keywords: 关键词列表，用于keyword方法
                - min_length: 最小文本长度，用于length方法
                - max_length: 最大文本长度，用于length方法
                - expected_language: 预期语言，用于language方法
        """
        super().__init__(config)
        self.method = config.get("method", "length")
        self.keywords = config.get("keywords", [])
        self.min_length = config.get("min_length", 10)
        self.max_length = config.get("max_length", 1000)
        self.expected_language = config.get("expected_language", "zh")
        
        # 检查是否有可选依赖
        if self.method == "language":
            try:
                import langdetect
                self.langdetect_available = True
            except ImportError:
                self.langdetect_available = False
                warnings.warn("langdetect未安装，无法使用language方法")
                self.method = "length"  # 降级到length方法
        
        if self.method == "sentiment":
            try:
                from snownlp import SnowNLP
                self.snownlp_available = True
            except ImportError:
                try:
                    import nltk
                    from nltk.sentiment import SentimentIntensityAnalyzer
                    nltk.download('vader_lexicon', quiet=True)
                    self.nltk_available = True
                    self.snownlp_available = False
                except ImportError:
                    self.nltk_available = False
                    self.snownlp_available = False
                    warnings.warn("SnowNLP和NLTK均未安装，无法使用sentiment方法")
                    self.method = "length"  # 降级到length方法
    
    def detect(self, data: Union[Dict[str, List[str]], List[str]]) -> Dict[str, Any]:
        """
        检测文本异常
        
        参数:
            data: 待检测的文本数据，可以是字典（键为ID，值为文本列表）或文本列表
            
        返回:
            检测结果字典，包含异常信息
        """
        anomalies = []
        
        # 处理不同的输入格式
        if isinstance(data, dict):
            # 字典格式：{id: [text1, text2, ...]}
            for text_id, texts in data.items():
                for i, text in enumerate(texts):
                    anomaly = self._detect_text_anomaly(text, f"{text_id}_{i}")
                    if anomaly:
                        anomaly["id"] = text_id
                        anomaly["index"] = i
                        anomalies.append(anomaly)
        elif isinstance(data, list):
            # 列表格式：[text1, text2, ...]
            for i, text in enumerate(data):
                anomaly = self._detect_text_anomaly(text, str(i))
                if anomaly:
                    anomaly["index"] = i
                    anomalies.append(anomaly)
        else:
            raise TypeError("数据必须是字典或列表类型")
        
        return {
            "anomalies": anomalies,
            "method": self.method,
            "threshold": self.config["threshold"],
            "total_anomalies": len(anomalies),
            "total_samples": len(data) if isinstance(data, list) else sum(len(texts) for texts in data.values())
        }
    
    def _detect_text_anomaly(self, text: str, text_id: str) -> Optional[Dict[str, Any]]:
        """
        检测单个文本的异常
        
        参数:
            text: 待检测的文本
            text_id: 文本ID
            
        返回:
            异常信息字典，如果没有异常则返回None
        """
        if not isinstance(text, str):
            return {
                "text_id": text_id,
                "reason": "非文本类型",
                "method": self.method,
                "value": str(type(text))
            }
        
        if self.method == "length":
            # 长度检测
            text_length = len(text)
            
            if text_length < self.min_length:
                return {
                    "text_id": text_id,
                    "reason": "文本过短",
                    "method": "length",
                    "value": text_length,
                    "threshold": self.min_length
                }
            
            if text_length > self.max_length:
                return {
                    "text_id": text_id,
                    "reason": "文本过长",
                    "method": "length",
                    "value": text_length,
                    "threshold": self.max_length
                }
        
        elif self.method == "keyword":
            # 关键词检测
            if not self.keywords:
                return None
            
            found_keywords = []
            for keyword in self.keywords:
                if keyword.lower() in text.lower():
                    found_keywords.append(keyword)
            
            if found_keywords:
                return {
                    "text_id": text_id,
                    "reason": "包含关键词",
                    "method": "keyword",
                    "value": found_keywords
                }
        
        elif self.method == "language" and self.langdetect_available:
            # 语言检测
            import langdetect
            
            try:
                detected_lang = langdetect.detect(text)
                
                if detected_lang != self.expected_language:
                    return {
                        "text_id": text_id,
                        "reason": "语言不匹配",
                        "method": "language",
                        "value": detected_lang,
                        "expected": self.expected_language
                    }
            except langdetect.lang_detect_exception.LangDetectException:
                return {
                    "text_id": text_id,
                    "reason": "无法检测语言",
                    "method": "language",
                    "value": text[:50] + "..." if len(text) > 50 else text
                }
        
        elif self.method == "sentiment":
            # 情感分析
            sentiment_score = None
            
            if self.snownlp_available:
                # 使用SnowNLP进行中文情感分析
                from snownlp import SnowNLP
                
                try:
                    s = SnowNLP(text)
                    sentiment_score = s.sentiments  # 0-1之间，越接近1越积极
                except Exception as e:
                    self.logger.warning(f"SnowNLP情感分析失败: {e}")
            
            elif self.nltk_available:
                # 使用NLTK进行英文情感分析
                from nltk.sentiment import SentimentIntensityAnalyzer
                
                try:
                    sia = SentimentIntensityAnalyzer()
                    sentiment_scores = sia.polarity_scores(text)
                    sentiment_score = sentiment_scores["compound"]  # -1到1之间，越接近1越积极
                except Exception as e:
                    self.logger.warning(f"NLTK情感分析失败: {e}")
            
            if sentiment_score is not None:
                threshold = self.config["threshold"]
                
                # 检查情感极端值
                if abs(sentiment_score - 0.5) > threshold / 2:
                    return {
                        "text_id": text_id,
                        "reason": "情感极端",
                        "method": "sentiment",
                        "value": sentiment_score,
                        "threshold": threshold
                    }
        
        return None


class ImageAnomalyDetector(BaseAnomalyDetector):
    """
    图像异常检测器
    检测图像数据中的异常
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化图像异常检测器
        
        参数:
            config: 配置字典，包含以下字段:
                - threshold: 异常阈值
                - method: 检测方法，支持'file_check'、'size'、'content'
                - min_width: 最小宽度，用于size方法
                - min_height: 最小高度，用于size方法
                - max_width: 最大宽度，用于size方法
                - max_height: 最大高度，用于size方法
                - max_file_size: 最大文件大小（字节），用于file_check方法
        """
        super().__init__(config)
        self.method = config.get("method", "file_check")
        self.min_width = config.get("min_width", 100)
        self.min_height = config.get("min_height", 100)
        self.max_width = config.get("max_width", 10000)
        self.max_height = config.get("max_height", 10000)
        self.max_file_size = config.get("max_file_size", 10 * 1024 * 1024)  # 10MB
        
        # 检查是否有可选依赖
        try:
            from PIL import Image
            self.pil_available = True
        except ImportError:
            self.pil_available = False
            warnings.warn("PIL未安装，图像处理功能将受限")
            self.method = "file_check"  # 降级到file_check方法
        
        if self.method == "content" and self.pil_available:
            try:
                import cv2
                import numpy as np
                self.cv2_available = True
            except ImportError:
                self.cv2_available = False
                warnings.warn("OpenCV未安装，无法使用content方法")
                self.method = "size"  # 降级到size方法
    
    def detect(self, data: Union[Dict[str, List[str]], List[str]]) -> Dict[str, Any]:
        """
        检测图像异常
        
        参数:
            data: 待检测的图像数据，可以是字典（键为ID，值为图像路径列表）或图像路径列表
            
        返回:
            检测结果字典，包含异常信息
        """
        anomalies = []
        
        # 处理不同的输入格式
        if isinstance(data, dict):
            # 字典格式：{id: [path1, path2, ...]}
            for image_id, paths in data.items():
                for i, path in enumerate(paths):
                    anomaly = self._detect_image_anomaly(path, f"{image_id}_{i}")
                    if anomaly:
                        anomaly["id"] = image_id
                        anomaly["index"] = i
                        anomalies.append(anomaly)
        elif isinstance(data, list):
            # 列表格式：[path1, path2, ...]
            for i, path in enumerate(data):
                anomaly = self._detect_image_anomaly(path, str(i))
                if anomaly:
                    anomaly["index"] = i
                    anomalies.append(anomaly)
        else:
            raise TypeError("数据必须是字典或列表类型")
        
        return {
            "anomalies": anomalies,
            "method": self.method,
            "threshold": self.config["threshold"],
            "total_anomalies": len(anomalies),
            "total_samples": len(data) if isinstance(data, list) else sum(len(paths) for paths in data.values())
        }
    
    def _detect_image_anomaly(self, image_path: str, image_id: str) -> Optional[Dict[str, Any]]:
        """
        检测单个图像的异常
        
        参数:
            image_path: 图像文件路径
            image_id: 图像ID
            
        返回:
            异常信息字典，如果没有异常则返回None
        """
        # 检查文件是否存在
        if not os.path.exists(image_path):
            return {
                "image_id": image_id,
                "path": image_path,
                "reason": "文件不存在",
                "method": "file_check"
            }
        
        # 检查文件大小
        file_size = os.path.getsize(image_path)
        if file_size == 0:
            return {
                "image_id": image_id,
                "path": image_path,
                "reason": "文件为空",
                "method": "file_check",
                "value": file_size
            }
        
        if file_size > self.max_file_size:
            return {
                "image_id": image_id,
                "path": image_path,
                "reason": "文件过大",
                "method": "file_check",
                "value": file_size,
                "threshold": self.max_file_size
            }
        
        # 检查文件扩展名
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
        file_ext = os.path.splitext(image_path)[1].lower()
        if file_ext not in valid_extensions:
            return {
                "image_id": image_id,
                "path": image_path,
                "reason": "文件格式不支持",
                "method": "file_check",
                "value": file_ext
            }
        
        # 如果方法是file_check，到这里就结束了
        if self.method == "file_check" or not self.pil_available:
            return None
        
        # 使用PIL检查图像
        try:
            from PIL import Image
            img = Image.open(image_path)
            
            # 检查图像尺寸
            width, height = img.size
            
            if width < self.min_width or height < self.min_height:
                return {
                    "image_id": image_id,
                    "path": image_path,
                    "reason": "图像过小",
                    "method": "size",
                    "value": {"width": width, "height": height},
                    "threshold": {"min_width": self.min_width, "min_height": self.min_height}
                }
            
            if width > self.max_width or height > self.max_height:
                return {
                    "image_id": image_id,
                    "path": image_path,
                    "reason": "图像过大",
                    "method": "size",
                    "value": {"width": width, "height": height},
                    "threshold": {"max_width": self.max_width, "max_height": self.max_height}
                }
            
            # 如果方法是size，到这里就结束了
            if self.method == "size" or not self.cv2_available:
                return None
            
            # 使用OpenCV进行更深入的图像内容分析
            import cv2
            import numpy as np
            
            # 读取图像
            cv_img = cv2.imread(image_path)
            if cv_img is None:
                return {
                    "image_id": image_id,
                    "path": image_path,
                    "reason": "无法读取图像内容",
                    "method": "content"
                }
            
            # 检查图像是否全黑或全白
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            mean_value = np.mean(gray)
            std_value = np.std(gray)
            
            if std_value < self.config["threshold"]:
                if mean_value < 10:
                    return {
                        "image_id": image_id,
                        "path": image_path,
                        "reason": "图像全黑",
                        "method": "content",
                        "value": {"mean": float(mean_value), "std": float(std_value)},
                        "threshold": self.config["threshold"]
                    }
                elif mean_value > 245:
                    return {
                        "image_id": image_id,
                        "path": image_path,
                        "reason": "图像全白",
                        "method": "content",
                        "value": {"mean": float(mean_value), "std": float(std_value)},
                        "threshold": self.config["threshold"]
                    }
            
            # 检查图像模糊度
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            if laplacian_var < self.config["threshold"] * 100:
                return {
                    "image_id": image_id,
                    "path": image_path,
                    "reason": "图像模糊",
                    "method": "content",
                    "value": float(laplacian_var),
                    "threshold": self.config["threshold"] * 100
                }
        
        except Exception as e:
            return {
                "image_id": image_id,
                "path": image_path,
                "reason": f"图像处理错误: {str(e)}",
                "method": self.method
            }
        
        return None
