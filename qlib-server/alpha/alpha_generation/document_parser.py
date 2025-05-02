"""
文档解析接口
解析各种格式的金融文档，提取结构化信息
"""

import os
import re
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime

import pandas as pd
import numpy as np
from pdfminer.high_level import extract_text
from docx import Document
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import requests
import html2text
from bs4 import BeautifulSoup

# 尝试导入LLM相关库
try:
    from ..llm_inference.base import BaseLLMInference
    from ..llm_inference.inference_engine import OptimizedLLMInference, InferenceConfig
    HAS_LLM = True
    logging.info("成功导入LLM推理模块")
except ImportError as e:
    HAS_LLM = False
    logging.warning(f"未能导入LLM推理模块，部分解析功能将不可用: {e}")

# 配置日志
logger = logging.getLogger(__name__)

class BaseDocumentParser(ABC):
    """文档解析基类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化文档解析器
        
        参数:
            config: 配置参数
        """
        self.config = config or {}
        self.content = None
        self.metadata = {}
    
    @abstractmethod
    def parse(self, source: str) -> Dict[str, Any]:
        """
        解析文档
        
        参数:
            source: 文档路径或URL
            
        返回:
            解析结果，包含内容和元数据
        """
        pass
    
    @abstractmethod
    def extract_sections(self) -> Dict[str, str]:
        """
        提取文档中的各个章节
        
        返回:
            章节字典，键为章节名，值为章节内容
        """
        pass
    
    def clean_text(self, text: str) -> str:
        """
        清理文本
        
        参数:
            text: 原始文本
            
        返回:
            清理后的文本
        """
        if not text:
            return ""
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除特殊控制字符
        text = re.sub(r'[\x00-\x1F\x7F]', '', text)
        
        # 统一换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        return text.strip()
    
    def save_parsed_result(self, output_path: str) -> str:
        """
        保存解析结果
        
        参数:
            output_path: 输出路径
            
        返回:
            保存的文件路径
        """
        if not self.content:
            raise ValueError("没有解析结果可保存")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        result = {
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"解析结果已保存至 {output_path}")
        return output_path


class PDFParser(BaseDocumentParser):
    """PDF文档解析器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化PDF解析器
        
        参数:
            config: 配置参数，可包含:
                - use_ocr: 是否使用OCR处理扫描PDF
                - ocr_language: OCR语言
                - extract_tables: 是否提取表格
        """
        super().__init__(config)
        self.use_ocr = self.config.get('use_ocr', False)
        self.ocr_language = self.config.get('ocr_language', 'chi_sim+eng')
        self.extract_tables = self.config.get('extract_tables', True)
        self.pdf_doc = None
        self.tables = []
    
    def parse(self, source: str) -> Dict[str, Any]:
        """
        解析PDF文档
        
        参数:
            source: PDF文件路径
            
        返回:
            解析结果
        """
        logger.info(f"开始解析PDF文档: {source}")
        
        try:
            # 初始化结果
            self.content = ""
            self.metadata = {'source': source, 'type': 'pdf'}
            self.tables = []
            
            # 打开PDF文档
            self.pdf_doc = fitz.open(source)
            
            # 提取元数据
            pdf_metadata = self.pdf_doc.metadata
            if pdf_metadata:
                self.metadata.update({
                    'title': pdf_metadata.get('title', ''),
                    'author': pdf_metadata.get('author', ''),
                    'subject': pdf_metadata.get('subject', ''),
                    'keywords': pdf_metadata.get('keywords', ''),
                    'creator': pdf_metadata.get('creator', ''),
                    'producer': pdf_metadata.get('producer', ''),
                    'page_count': len(self.pdf_doc)
                })
            
            # 处理每一页
            full_text = []
            for page_num, page in enumerate(self.pdf_doc):
                # 获取页面文本
                text = page.get_text()
                
                # 如果页面没有文本且启用了OCR，进行OCR识别
                if not text.strip() and self.use_ocr:
                    pix = page.get_pixmap()
                    img_path = f"temp_page_{page_num}.png"
                    pix.save(img_path)
                    
                    try:
                        img = Image.open(img_path)
                        text = pytesseract.image_to_string(img, lang=self.ocr_language)
                        os.remove(img_path)
                    except Exception as e:
                        logger.error(f"OCR处理失败: {e}")
                
                # 清理并添加文本
                text = self.clean_text(text)
                full_text.append(text)
                
                # 如果需要提取表格
                if self.extract_tables:
                    self._extract_tables_from_page(page, page_num)
            
            # 合并所有文本
            self.content = "\n\n".join(full_text)
            
            # 添加表格信息到元数据
            if self.tables:
                self.metadata['tables_count'] = len(self.tables)
                self.metadata['tables'] = [
                    {'page': table['page'], 'rows': len(table['data'])} 
                    for table in self.tables
                ]
            
            logger.info(f"PDF文档解析完成: {len(full_text)} 页, {len(self.tables)} 个表格")
            
            return {
                'content': self.content,
                'metadata': self.metadata,
                'tables': self.tables,
                'success': True
            }
            
        except Exception as e:
            error_msg = f"PDF解析失败: {e}"
            logger.error(error_msg)
            return {
                'content': None,
                'metadata': {'source': source, 'error': error_msg},
                'success': False
            }
        finally:
            # 关闭文档
            if self.pdf_doc:
                self.pdf_doc.close()
    
    def _extract_tables_from_page(self, page, page_num: int) -> None:
        """提取页面中的表格"""
        try:
            # 使用PyMuPDF的表格识别功能
            tables = page.find_tables()
            for i, table in enumerate(tables):
                table_data = table.extract()
                if table_data:
                    self.tables.append({
                        'page': page_num + 1,
                        'index': i + 1,
                        'data': table_data,
                        'headers': table_data[0] if table_data else []
                    })
        except Exception as e:
            logger.warning(f"从第 {page_num+1} 页提取表格失败: {e}")
    
    def extract_sections(self) -> Dict[str, str]:
        """
        提取PDF文档中的章节
        
        返回:
            章节字典
        """
        if not self.content:
            logger.warning("没有解析内容，无法提取章节")
            return {}
        
        # 使用正则表达式匹配可能的章节标题
        # 如: "1. 引言", "第一章 简介", "1.1 背景", 等
        section_patterns = [
            r'^(\d+\.\s+.+?)$',  # 1. 标题
            r'^(第[一二三四五六七八九十]+[章节]\s+.+?)$',  # 第一章 标题
            r'^(\d+\.\d+\s+.+?)$'  # 1.1 标题
        ]
        
        sections = {}
        current_section = "前言"
        current_content = []
        
        for line in self.content.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # 检查是否是章节标题
            is_section_title = False
            for pattern in section_patterns:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    # 保存当前章节
                    if current_content:
                        sections[current_section] = '\n'.join(current_content)
                        current_content = []
                    
                    # 开始新章节
                    current_section = match.group(1)
                    is_section_title = True
                    break
            
            # 如果不是章节标题，添加到当前章节内容
            if not is_section_title:
                current_content.append(line)
        
        # 保存最后一个章节
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections


class DocxParser(BaseDocumentParser):
    """Word文档解析器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化Word文档解析器
        
        参数:
            config: 配置参数，可包含:
                - extract_tables: 是否提取表格
                - extract_images: 是否提取图片
        """
        super().__init__(config)
        self.extract_tables = self.config.get('extract_tables', True)
        self.extract_images = self.config.get('extract_images', False)
        self.doc = None
        self.tables = []
        self.images = []
    
    def parse(self, source: str) -> Dict[str, Any]:
        """
        解析Word文档
        
        参数:
            source: Word文件路径
            
        返回:
            解析结果
        """
        logger.info(f"开始解析Word文档: {source}")
        
        try:
            # 初始化结果
            self.content = ""
            self.metadata = {'source': source, 'type': 'docx'}
            self.tables = []
            self.images = []
            
            # 打开Word文档
            self.doc = Document(source)
            
            # 提取元数据
            core_properties = self.doc.core_properties
            if core_properties:
                self.metadata.update({
                    'title': core_properties.title or '',
                    'author': core_properties.author or '',
                    'created': core_properties.created.isoformat() if core_properties.created else '',
                    'modified': core_properties.modified.isoformat() if core_properties.modified else '',
                    'last_modified_by': core_properties.last_modified_by or '',
                    'paragraph_count': len(self.doc.paragraphs)
                })
            
            # 提取段落内容
            paragraphs = []
            for para in self.doc.paragraphs:
                text = para.text.strip()
                if text:
                    paragraphs.append(text)
            
            # 合并所有文本
            self.content = "\n\n".join(paragraphs)
            
            # 提取表格
            if self.extract_tables:
                self._extract_tables()
            
            # 提取图片
            if self.extract_images:
                self._extract_images(source)
            
            # 添加表格和图片信息到元数据
            if self.tables:
                self.metadata['tables_count'] = len(self.tables)
            
            if self.images:
                self.metadata['images_count'] = len(self.images)
            
            logger.info(f"Word文档解析完成: {len(paragraphs)} 段落, {len(self.tables)} 个表格, {len(self.images)} 张图片")
            
            return {
                'content': self.content,
                'metadata': self.metadata,
                'tables': self.tables,
                'images': self.images,
                'success': True
            }
            
        except Exception as e:
            error_msg = f"Word文档解析失败: {e}"
            logger.error(error_msg)
            return {
                'content': None,
                'metadata': {'source': source, 'error': error_msg},
                'success': False
            }
    
    def _extract_tables(self) -> None:
        """提取Word文档中的表格"""
        try:
            for i, table in enumerate(self.doc.tables):
                table_data = []
                for row in table.rows:
                    row_data = [cell.text.strip() for cell in row.cells]
                    table_data.append(row_data)
                
                if table_data:
                    self.tables.append({
                        'index': i + 1,
                        'data': table_data,
                        'headers': table_data[0] if table_data else []
                    })
        except Exception as e:
            logger.warning(f"提取表格失败: {e}")
    
    def _extract_images(self, source: str) -> None:
        """
        提取Word文档中的图片
        
        注意：此方法需要处理docx内部结构，提取二进制图片数据
        """
        try:
            # 此功能需要更复杂的docx解析，在这里仅做示例
            # 实际实现需要使用zipfile解析docx内部结构
            logger.info("图片提取功能暂未完全实现")
        except Exception as e:
            logger.warning(f"提取图片失败: {e}")
    
    def extract_sections(self) -> Dict[str, str]:
        """
        提取Word文档中的章节
        
        返回:
            章节字典
        """
        if not self.doc:
            logger.warning("没有解析文档，无法提取章节")
            return {}
        
        sections = {}
        current_section = "序言"
        current_content = []
        
        for para in self.doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            
            # 通过段落样式判断章节标题
            # 通常标题会使用"Heading"样式
            if para.style.name.startswith('Heading') or re.match(r'^(\d+\.|\d+\.\d+|第[一二三四五六七八九十]+[章节])\s+', text):
                # 保存当前章节
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                    current_content = []
                
                # 开始新章节
                current_section = text
            else:
                # 添加到当前章节内容
                current_content.append(text)
        
        # 保存最后一个章节
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections


class WebPageParser(BaseDocumentParser):
    """网页解析器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化网页解析器
        
        参数:
            config: 配置参数，可包含:
                - extract_tables: 是否提取表格
                - remove_ads: 是否移除广告
                - headers: 请求头
        """
        super().__init__(config)
        self.extract_tables = self.config.get('extract_tables', True)
        self.remove_ads = self.config.get('remove_ads', True)
        self.headers = self.config.get('headers', {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.soup = None
        self.tables = []
    
    def parse(self, source: str) -> Dict[str, Any]:
        """
        解析网页
        
        参数:
            source: 网页URL
            
        返回:
            解析结果
        """
        logger.info(f"开始解析网页: {source}")
        
        try:
            # 初始化结果
            self.content = ""
            self.metadata = {'source': source, 'type': 'webpage'}
            self.tables = []
            
            # 获取网页内容
            response = requests.get(source, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # 提取元数据
            self.metadata['status_code'] = response.status_code
            self.metadata['content_type'] = response.headers.get('Content-Type', '')
            self.metadata['encoding'] = response.encoding
            
            # 解析HTML
            self.soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取标题
            title = self.soup.title.string if self.soup.title else ""
            self.metadata['title'] = title.strip() if title else ""
            
            # 移除广告和不需要的元素
            if self.remove_ads:
                self._remove_ads()
            
            # 提取正文内容
            main_content = self._extract_main_content()
            
            # 使用html2text将HTML转换为纯文本
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            h.ignore_tables = not self.extract_tables
            self.content = h.handle(main_content)
            
            # 提取表格
            if self.extract_tables:
                self._extract_tables()
            
            logger.info(f"网页解析完成: {len(self.content)} 字符, {len(self.tables)} 个表格")
            
            return {
                'content': self.content,
                'metadata': self.metadata,
                'tables': self.tables,
                'success': True
            }
            
        except Exception as e:
            error_msg = f"网页解析失败: {e}"
            logger.error(error_msg)
            return {
                'content': None,
                'metadata': {'source': source, 'error': error_msg},
                'success': False
            }
    
    def _remove_ads(self) -> None:
        """移除广告和无关内容"""
        if not self.soup:
            return
        
        # 常见的广告和无关元素选择器
        ad_selectors = [
            'div.advertisement', 'div.ad', 'div.ads', 'ins.adsbygoogle',
            'div.banner', 'div.sidebar', 'div.comments', 'footer',
            'div.related-articles', 'div.social-media', 'nav', 'header'
        ]
        
        for selector in ad_selectors:
            for element in self.soup.select(selector):
                element.decompose()
    
    def _extract_main_content(self) -> str:
        """提取网页主要内容"""
        if not self.soup:
            return ""
        
        # 尝试找到主要内容区域
        # 常见的主要内容选择器
        content_selectors = [
            'article', 'div.article', 'div.content', 'div.main',
            'div.post', 'div.entry', 'div.blog-post', 'main'
        ]
        
        for selector in content_selectors:
            content = self.soup.select_one(selector)
            if content:
                return str(content)
        
        # 如果没找到，返回整个body
        return str(self.soup.body) if self.soup.body else str(self.soup)
    
    def _extract_tables(self) -> None:
        """提取网页中的表格"""
        if not self.soup:
            return
        
        try:
            for i, table in enumerate(self.soup.find_all('table')):
                table_data = []
                for row in table.find_all('tr'):
                    cells = row.find_all(['td', 'th'])
                    row_data = [cell.get_text(strip=True) for cell in cells]
                    table_data.append(row_data)
                
                if table_data:
                    self.tables.append({
                        'index': i + 1,
                        'data': table_data,
                        'headers': table_data[0] if table_data else []
                    })
        except Exception as e:
            logger.warning(f"提取表格失败: {e}")
    
    def extract_sections(self) -> Dict[str, str]:
        """
        提取网页中的章节
        
        返回:
            章节字典
        """
        if not self.soup:
            logger.warning("没有解析内容，无法提取章节")
            return {}
        
        sections = {}
        headings = self.soup.find_all(['h1', 'h2', 'h3'])
        
        if not headings:
            # 如果没有找到标题，则整个内容作为一个章节
            sections["主要内容"] = self.content
            return sections
        
        # 按标题划分章节
        current_section = "引言"
        current_content = []
        
        for tag in self.soup.body.find_all():
            if tag.name in ['h1', 'h2', 'h3']:
                # 保存当前章节
                if current_content:
                    sections[current_section] = '\n'.join([c.get_text(strip=True) for c in current_content])
                    current_content = []
                
                # 开始新章节
                current_section = tag.get_text(strip=True)
            elif current_section and tag.name not in ['script', 'style', 'meta', 'link']:
                # 添加到当前章节内容
                current_content.append(tag)
        
        # 保存最后一个章节
        if current_content:
            sections[current_section] = '\n'.join([c.get_text(strip=True) for c in current_content])
        
        return sections


class DocumentParserFactory:
    """文档解析器工厂类"""
    
    @staticmethod
    def get_parser(source: str, parser_type: str = None, config: Dict[str, Any] = None) -> BaseDocumentParser:
        """
        根据文件类型或指定类型获取解析器
        
        参数:
            source: 文档路径或URL
            parser_type: 指定解析器类型，可选值: 'pdf', 'docx', 'webpage'
            config: 解析器配置
            
        返回:
            文档解析器实例
        """
        # 如果未指定解析器类型，根据文件扩展名或URL协议判断
        if not parser_type:
            if source.startswith(('http://', 'https://')):
                parser_type = 'webpage'
            elif source.lower().endswith('.pdf'):
                parser_type = 'pdf'
            elif source.lower().endswith(('.docx', '.doc')):
                parser_type = 'docx'
            else:
                raise ValueError(f"无法确定文档类型: {source}")
        
        # 创建对应类型的解析器
        if parser_type == 'pdf':
            return PDFParser(config)
        elif parser_type == 'docx':
            return DocxParser(config)
        elif parser_type == 'webpage':
            return WebPageParser(config)
        else:
            raise ValueError(f"不支持的解析器类型: {parser_type}")


class DocumentParser:
    """文档解析接口，整合各种解析器的功能"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化文档解析接口
        
        参数:
            config: 配置参数，可包含各类解析器的配置
        """
        self.config = config or {}
        self.parser = None
        self.parsed_result = None
    
    def parse(self, source: str, parser_type: str = None) -> Dict[str, Any]:
        """
        解析文档
        
        参数:
            source: 文档路径或URL
            parser_type: 可选的指定解析器类型
            
        返回:
            解析结果
        """
        # 获取解析器
        try:
            parser_config = self.config.get(parser_type, {}) if parser_type else {}
            self.parser = DocumentParserFactory.get_parser(source, parser_type, parser_config)
            
            # 解析文档
            self.parsed_result = self.parser.parse(source)
            
            return self.parsed_result
        except Exception as e:
            error_msg = f"文档解析失败: {e}"
            logger.error(error_msg)
            return {
                'content': None,
                'metadata': {'source': source, 'error': error_msg},
                'success': False
            }
    
    def extract_sections(self) -> Dict[str, str]:
        """
        提取文档章节
        
        返回:
            章节字典
        """
        if not self.parser:
            logger.warning("没有初始化解析器，请先调用parse方法")
            return {}
        
        return self.parser.extract_sections()
    
    def save_result(self, output_path: str) -> str:
        """
        保存解析结果
        
        参数:
            output_path: 输出路径
            
        返回:
            保存的文件路径
        """
        if not self.parser or not self.parsed_result:
            logger.warning("没有解析结果，请先调用parse方法")
            return ""
        
        return self.parser.save_parsed_result(output_path)
    
    @staticmethod
    def get_supported_formats() -> List[str]:
        """
        获取支持的文档格式
        
        返回:
            格式列表
        """
        return ['pdf', 'docx', 'doc', 'webpage']
    
    def get_content(self) -> str:
        """
        获取解析后的内容
        
        返回:
            文档内容
        """
        if not self.parsed_result:
            return ""
        
        return self.parsed_result.get('content', "")
