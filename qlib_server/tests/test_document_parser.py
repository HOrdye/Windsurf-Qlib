#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文档解析器单元测试
"""
import os
import unittest
import tempfile
from unittest.mock import patch, MagicMock
import json
import pandas as pd
from bs4 import BeautifulSoup

# 修复导入路径
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from alpha.alpha_generation.document_parser import (
    BaseDocumentParser,
    PDFParser,
    DocxParser, 
    WebPageParser,
    DocumentParserFactory,
    DocumentParser
)

class TestBaseDocumentParser(unittest.TestCase):
    """基础文档解析器测试"""
    
    def setUp(self):
        """测试初始化"""
        self.config = {'test_key': 'test_value'}
        self.parser = BaseDocumentParser(self.config)
    
    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.parser.config, self.config)
        self.assertIsNone(self.parser.content)
        self.assertEqual(self.parser.metadata, {})
        self.assertEqual(self.parser.tables, [])
    
    def test_parse_not_implemented(self):
        """测试parse方法异常"""
        with self.assertRaises(NotImplementedError):
            self.parser.parse("test_source")
    
    def test_extract_sections_not_implemented(self):
        """测试extract_sections方法异常"""
        with self.assertRaises(NotImplementedError):
            self.parser.extract_sections()
    
    def test_save_parsed_result(self):
        """测试保存解析结果"""
        self.parser.content = "测试内容"
        self.parser.metadata = {"source": "test.txt"}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "output.json")
            result_path = self.parser.save_parsed_result(output_path)
            
            self.assertEqual(result_path, output_path)
            self.assertTrue(os.path.exists(output_path))
            
            # 验证保存的内容
            with open(output_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                self.assertEqual(saved_data["content"], "测试内容")
                self.assertEqual(saved_data["metadata"]["source"], "test.txt")


class TestPDFParser(unittest.TestCase):
    """PDF解析器测试"""
    
    @patch('alpha.alpha_generation.document_parser.pdfplumber.open')
    def setUp(self, mock_pdf_open):
        """测试初始化"""
        # 设置mock返回值
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF测试内容"
        mock_page.extract_tables.return_value = [
            [["表头1", "表头2"], ["数据1", "数据2"]]
        ]
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        
        self.config = {'extract_tables': True}
        self.parser = PDFParser(self.config)
        self.source = "test.pdf"
    
    @patch('alpha.alpha_generation.document_parser.pdfplumber.open')
    def test_parse(self, mock_pdf_open):
        """测试PDF解析"""
        # 设置mock返回值
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF测试内容"
        mock_page.extract_tables.return_value = [
            [["表头1", "表头2"], ["数据1", "数据2"]]
        ]
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        
        # 测试解析方法
        result = self.parser.parse(self.source)
        
        # 验证结果
        self.assertTrue(result["success"])
        self.assertEqual(result["content"], "PDF测试内容")
        self.assertEqual(result["metadata"]["source"], self.source)
        self.assertEqual(result["metadata"]["type"], "pdf")
        self.assertEqual(len(result["tables"]), 1)
        self.assertEqual(result["tables"][0]["data"][0][0], "表头1")
    
    @patch('alpha.alpha_generation.document_parser.pytesseract.image_to_string')
    @patch('alpha.alpha_generation.document_parser.pdfplumber.open')
    def test_ocr_extraction(self, mock_pdf_open, mock_ocr):
        """测试OCR提取"""
        # 设置OCR配置
        self.parser.config["use_ocr"] = True
        
        # 设置mock返回值
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""  # 无文本，触发OCR
        mock_page.to_image.return_value.save.return_value = "temp_image.png"
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        
        mock_ocr.return_value = "OCR提取的文本"
        
        # 测试解析方法
        with patch('os.path.exists', return_value=True):
            with patch('os.remove'):
                result = self.parser.parse(self.source)
        
        # 验证结果
        self.assertTrue(result["success"])
        self.assertEqual(result["content"], "OCR提取的文本")
        self.assertEqual(result["metadata"]["ocr_used"], True)
    
    @patch('alpha.alpha_generation.document_parser.pdfplumber.open')
    def test_extract_sections(self, mock_pdf_open):
        """测试提取章节"""
        # 设置mock返回值
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "# 标题1\n内容1\n## 标题2\n内容2\n"
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        
        # 先解析文档
        self.parser.parse(self.source)
        
        # 测试提取章节
        sections = self.parser.extract_sections()
        
        # 验证结果
        self.assertIn("标题1", sections)
        self.assertIn("标题2", sections)
        

class TestDocxParser(unittest.TestCase):
    """Word文档解析器测试"""
    
    @patch('alpha.alpha_generation.document_parser.Document')
    def setUp(self, mock_docx):
        """测试初始化"""
        # 设置mock返回值
        mock_doc = MagicMock()
        mock_paragraph1 = MagicMock()
        mock_paragraph1.text = "标题1"
        mock_paragraph1.style.name = "Heading 1"
        
        mock_paragraph2 = MagicMock()
        mock_paragraph2.text = "内容1"
        mock_paragraph2.style.name = "Normal"
        
        mock_doc.paragraphs = [mock_paragraph1, mock_paragraph2]
        
        mock_table = MagicMock()
        mock_cell1 = MagicMock()
        mock_cell1.text = "表头1"
        mock_cell2 = MagicMock()
        mock_cell2.text = "表头2"
        mock_cell3 = MagicMock()
        mock_cell3.text = "数据1"
        mock_cell4 = MagicMock()
        mock_cell4.text = "数据2"
        
        mock_row1 = MagicMock()
        mock_row1.cells = [mock_cell1, mock_cell2]
        mock_row2 = MagicMock()
        mock_row2.cells = [mock_cell3, mock_cell4]
        
        mock_table.rows = [mock_row1, mock_row2]
        mock_doc.tables = [mock_table]
        
        mock_docx.return_value = mock_doc
        
        self.config = {'extract_tables': True}
        self.parser = DocxParser(self.config)
        self.source = "test.docx"
    
    @patch('alpha.alpha_generation.document_parser.Document')
    def test_parse(self, mock_docx):
        """测试Word解析"""
        # 设置mock返回值
        mock_doc = MagicMock()
        mock_paragraph1 = MagicMock()
        mock_paragraph1.text = "标题1"
        mock_paragraph1.style.name = "Heading 1"
        
        mock_paragraph2 = MagicMock()
        mock_paragraph2.text = "内容1"
        mock_paragraph2.style.name = "Normal"
        
        mock_doc.paragraphs = [mock_paragraph1, mock_paragraph2]
        
        mock_table = MagicMock()
        mock_cell1 = MagicMock()
        mock_cell1.text = "表头1"
        mock_cell2 = MagicMock()
        mock_cell2.text = "表头2"
        mock_cell3 = MagicMock()
        mock_cell3.text = "数据1"
        mock_cell4 = MagicMock()
        mock_cell4.text = "数据2"
        
        mock_row1 = MagicMock()
        mock_row1.cells = [mock_cell1, mock_cell2]
        mock_row2 = MagicMock()
        mock_row2.cells = [mock_cell3, mock_cell4]
        
        mock_table.rows = [mock_row1, mock_row2]
        mock_doc.tables = [mock_table]
        
        mock_docx.return_value = mock_doc
        
        # 测试解析方法
        result = self.parser.parse(self.source)
        
        # 验证结果
        self.assertTrue(result["success"])
        self.assertIn("标题1", result["content"])
        self.assertIn("内容1", result["content"])
        self.assertEqual(result["metadata"]["source"], self.source)
        self.assertEqual(result["metadata"]["type"], "docx")
        self.assertEqual(len(result["tables"]), 1)
        self.assertEqual(result["tables"][0]["data"][0][0], "表头1")
    
    @patch('alpha.alpha_generation.document_parser.Document')
    def test_extract_sections(self, mock_docx):
        """测试提取章节"""
        # 设置mock返回值
        mock_doc = MagicMock()
        mock_paragraph1 = MagicMock()
        mock_paragraph1.text = "标题1"
        mock_paragraph1.style.name = "Heading 1"
        
        mock_paragraph2 = MagicMock()
        mock_paragraph2.text = "内容1"
        mock_paragraph2.style.name = "Normal"
        
        mock_paragraph3 = MagicMock()
        mock_paragraph3.text = "标题2"
        mock_paragraph3.style.name = "Heading 2"
        
        mock_paragraph4 = MagicMock()
        mock_paragraph4.text = "内容2"
        mock_paragraph4.style.name = "Normal"
        
        mock_doc.paragraphs = [mock_paragraph1, mock_paragraph2, mock_paragraph3, mock_paragraph4]
        mock_doc.tables = []
        
        mock_docx.return_value = mock_doc
        
        # 先解析文档
        self.parser.parse(self.source)
        
        # 测试提取章节
        sections = self.parser.extract_sections()
        
        # 验证结果
        self.assertIn("标题1", sections)
        self.assertIn("标题2", sections)
        self.assertEqual(sections["标题1"], "内容1")


class TestWebPageParser(unittest.TestCase):
    """网页解析器测试"""
    
    @patch('alpha.alpha_generation.document_parser.requests.get')
    def setUp(self, mock_get):
        """测试初始化"""
        # 设置mock返回值
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.encoding = "utf-8"
        mock_response.text = """
        <html>
            <head><title>测试网页</title></head>
            <body>
                <h1>标题1</h1>
                <p>内容1</p>
                <h2>标题2</h2>
                <p>内容2</p>
                <table>
                    <tr><th>表头1</th><th>表头2</th></tr>
                    <tr><td>数据1</td><td>数据2</td></tr>
                </table>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        self.config = {'extract_tables': True, 'remove_ads': True}
        self.parser = WebPageParser(self.config)
        self.source = "http://example.com"
    
    @patch('alpha.alpha_generation.document_parser.requests.get')
    def test_parse(self, mock_get):
        """测试网页解析"""
        # 设置mock返回值
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.encoding = "utf-8"
        mock_response.text = """
        <html>
            <head><title>测试网页</title></head>
            <body>
                <h1>标题1</h1>
                <p>内容1</p>
                <h2>标题2</h2>
                <p>内容2</p>
                <table>
                    <tr><th>表头1</th><th>表头2</th></tr>
                    <tr><td>数据1</td><td>数据2</td></tr>
                </table>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        # 测试解析方法
        result = self.parser.parse(self.source)
        
        # 验证结果
        self.assertTrue(result["success"])
        self.assertIn("标题1", result["content"])
        self.assertIn("内容1", result["content"])
        self.assertEqual(result["metadata"]["source"], self.source)
        self.assertEqual(result["metadata"]["type"], "webpage")
        self.assertEqual(result["metadata"]["title"], "测试网页")
        self.assertEqual(len(result["tables"]), 1)
    
    @patch('alpha.alpha_generation.document_parser.requests.get')
    def test_remove_ads(self, mock_get):
        """测试移除广告"""
        # 设置mock返回值
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.encoding = "utf-8"
        mock_response.text = """
        <html>
            <head><title>测试网页</title></head>
            <body>
                <h1>标题1</h1>
                <p>内容1</p>
                <div class="advertisement">广告内容</div>
                <h2>标题2</h2>
                <p>内容2</p>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        # 测试解析方法
        result = self.parser.parse(self.source)
        
        # 验证结果
        self.assertTrue(result["success"])
        self.assertIn("标题1", result["content"])
        self.assertIn("内容2", result["content"])
        self.assertNotIn("广告内容", result["content"])
    
    @patch('alpha.alpha_generation.document_parser.requests.get')
    def test_extract_sections(self, mock_get):
        """测试提取章节"""
        # 设置mock返回值
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.encoding = "utf-8"
        mock_response.text = """
        <html>
            <head><title>测试网页</title></head>
            <body>
                <h1>标题1</h1>
                <p>内容1</p>
                <h2>标题2</h2>
                <p>内容2</p>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        # 先解析文档
        self.parser.parse(self.source)
        
        # 测试提取章节
        sections = self.parser.extract_sections()
        
        # 验证结果
        self.assertIn("标题1", sections)
        self.assertIn("标题2", sections)


class TestDocumentParserFactory(unittest.TestCase):
    """文档解析器工厂测试"""
    
    def test_get_parser_by_file_extension(self):
        """测试根据文件扩展名获取解析器"""
        # PDF解析器
        parser = DocumentParserFactory.get_parser("test.pdf")
        self.assertIsInstance(parser, PDFParser)
        
        # Word解析器
        parser = DocumentParserFactory.get_parser("test.docx")
        self.assertIsInstance(parser, DocxParser)
        
        # 网页解析器
        parser = DocumentParserFactory.get_parser("http://example.com")
        self.assertIsInstance(parser, WebPageParser)
    
    def test_get_parser_by_type(self):
        """测试根据指定类型获取解析器"""
        # PDF解析器
        parser = DocumentParserFactory.get_parser("test.txt", parser_type="pdf")
        self.assertIsInstance(parser, PDFParser)
        
        # Word解析器
        parser = DocumentParserFactory.get_parser("test.txt", parser_type="docx")
        self.assertIsInstance(parser, DocxParser)
        
        # 网页解析器
        parser = DocumentParserFactory.get_parser("test.txt", parser_type="webpage")
        self.assertIsInstance(parser, WebPageParser)
    
    def test_invalid_parser_type(self):
        """测试无效的解析器类型"""
        with self.assertRaises(ValueError):
            DocumentParserFactory.get_parser("test.txt", parser_type="invalid")
    
    def test_unknown_file_type(self):
        """测试未知的文件类型"""
        with self.assertRaises(ValueError):
            DocumentParserFactory.get_parser("test.unknown")


class TestDocumentParser(unittest.TestCase):
    """文档解析接口测试"""
    
    def setUp(self):
        """测试初始化"""
        self.config = {
            'pdf': {'extract_tables': True},
            'docx': {'extract_tables': True},
            'webpage': {'remove_ads': True}
        }
        self.parser = DocumentParser(self.config)
    
    @patch('alpha.alpha_generation.document_parser.DocumentParserFactory.get_parser')
    def test_parse(self, mock_get_parser):
        """测试解析文档"""
        # 设置mock返回值
        mock_specific_parser = MagicMock()
        mock_specific_parser.parse.return_value = {
            'content': '测试内容',
            'metadata': {'source': 'test.pdf'},
            'tables': [],
            'success': True
        }
        mock_get_parser.return_value = mock_specific_parser
        
        # 测试解析方法
        result = self.parser.parse("test.pdf")
        
        # 验证结果
        self.assertTrue(result["success"])
        self.assertEqual(result["content"], "测试内容")
        self.assertEqual(result["metadata"]["source"], "test.pdf")
    
    @patch('alpha.alpha_generation.document_parser.DocumentParserFactory.get_parser')
    def test_extract_sections(self, mock_get_parser):
        """测试提取章节"""
        # 设置mock返回值
        mock_specific_parser = MagicMock()
        mock_specific_parser.parse.return_value = {
            'content': '测试内容',
            'metadata': {'source': 'test.pdf'},
            'tables': [],
            'success': True
        }
        mock_specific_parser.extract_sections.return_value = {
            '标题1': '内容1',
            '标题2': '内容2'
        }
        mock_get_parser.return_value = mock_specific_parser
        
        # 先解析文档
        self.parser.parse("test.pdf")
        
        # 测试提取章节
        sections = self.parser.extract_sections()
        
        # 验证结果
        self.assertIn("标题1", sections)
        self.assertIn("标题2", sections)
        self.assertEqual(sections["标题1"], "内容1")
    
    @patch('alpha.alpha_generation.document_parser.DocumentParserFactory.get_parser')
    def test_save_result(self, mock_get_parser):
        """测试保存结果"""
        # 设置mock返回值
        mock_specific_parser = MagicMock()
        mock_specific_parser.parse.return_value = {
            'content': '测试内容',
            'metadata': {'source': 'test.pdf'},
            'tables': [],
            'success': True
        }
        mock_specific_parser.save_parsed_result.return_value = "output.json"
        mock_get_parser.return_value = mock_specific_parser
        
        # 先解析文档
        self.parser.parse("test.pdf")
        
        # 测试保存结果
        result_path = self.parser.save_result("output.json")
        
        # 验证结果
        self.assertEqual(result_path, "output.json")
    
    def test_get_supported_formats(self):
        """测试获取支持的格式"""
        formats = self.parser.get_supported_formats()
        self.assertIn("pdf", formats)
        self.assertIn("docx", formats)
        self.assertIn("webpage", formats)


if __name__ == '__main__':
    unittest.main()
