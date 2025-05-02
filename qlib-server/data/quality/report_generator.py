"""
数据质量报告生成器实现
用于生成数据质量报告，包括统计信息、异常检测结果、缺失值分析等
"""
from typing import Dict, List, Union, Optional, Any, Tuple
import pandas as pd
import numpy as np
import os
import logging
import json
from datetime import datetime
import matplotlib.pyplot as plt
import warnings
import base64
from io import BytesIO

from .base import BaseQualityReportGenerator

# 配置日志
logger = logging.getLogger(__name__)


class DataQualityReportGenerator(BaseQualityReportGenerator):
    """
    数据质量报告生成器
    用于生成数据质量报告，包括统计信息、异常检测结果、缺失值分析等
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据质量报告生成器
        
        参数:
            config: 配置字典，包含以下字段:
                - report_type: 报告类型，支持'html'、'json'、'markdown'，默认为'html'
                - output_path: 报告输出路径，默认为'/data/qlib/reports'
                - include_plots: 是否包含图表，默认为True
                - plot_format: 图表格式，支持'png'、'svg'，默认为'png'
                - max_rows_per_table: 表格最大行数，默认为100
                - include_anomalies: 是否包含异常检测结果，默认为True
                - include_missing: 是否包含缺失值分析，默认为True
                - include_statistics: 是否包含统计信息，默认为True
                - include_correlation: 是否包含相关性分析，默认为True
                - include_version_info: 是否包含版本信息，默认为True
        """
        super().__init__(config)
        
        # 设置默认配置
        self.report_type = self.config.get("report_type", "html")
        self.output_path = self.config.get("output_path", "/data/qlib/reports")
        self.include_plots = self.config.get("include_plots", True)
        self.plot_format = self.config.get("plot_format", "png")
        self.max_rows_per_table = self.config.get("max_rows_per_table", 100)
        self.include_anomalies = self.config.get("include_anomalies", True)
        self.include_missing = self.config.get("include_missing", True)
        self.include_statistics = self.config.get("include_statistics", True)
        self.include_correlation = self.config.get("include_correlation", True)
        self.include_version_info = self.config.get("include_version_info", True)
        
        # 检查输出路径
        os.makedirs(self.output_path, exist_ok=True)
        
        # 检查matplotlib
        try:
            import matplotlib.pyplot as plt
            self._plt_available = True
        except ImportError:
            self._plt_available = False
            warnings.warn("matplotlib未安装，无法生成图表")
            self.include_plots = False
    
    def generate_report(self, data: pd.DataFrame, report_name: str, 
                       anomalies: Optional[Dict[str, Any]] = None,
                       missing_info: Optional[Dict[str, Any]] = None,
                       version_info: Optional[Dict[str, Any]] = None) -> str:
        """
        生成数据质量报告
        
        参数:
            data: 数据框
            report_name: 报告名称
            anomalies: 异常检测结果，可选
            missing_info: 缺失值分析结果，可选
            version_info: 版本信息，可选
            
        返回:
            报告路径
        """
        # 检查数据
        if not isinstance(data, pd.DataFrame):
            raise TypeError("数据必须是pandas DataFrame类型")
        
        # 准备报告数据
        report_data = self._prepare_report_data(data, anomalies, missing_info, version_info)
        
        # 生成报告
        if self.report_type == "html":
            report_path = self._generate_html_report(report_data, report_name)
        elif self.report_type == "json":
            report_path = self._generate_json_report(report_data, report_name)
        elif self.report_type == "markdown":
            report_path = self._generate_markdown_report(report_data, report_name)
        else:
            logger.warning(f"不支持的报告类型: {self.report_type}，使用HTML类型")
            report_path = self._generate_html_report(report_data, report_name)
        
        logger.info(f"生成数据质量报告成功: {report_path}")
        return report_path
    
    def _prepare_report_data(self, data: pd.DataFrame, 
                           anomalies: Optional[Dict[str, Any]] = None,
                           missing_info: Optional[Dict[str, Any]] = None,
                           version_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        准备报告数据
        
        参数:
            data: 数据框
            anomalies: 异常检测结果，可选
            missing_info: 缺失值分析结果，可选
            version_info: 版本信息，可选
            
        返回:
            报告数据
        """
        report_data = {
            "report_name": "",
            "generation_time": datetime.now().isoformat(),
            "data_info": {
                "rows": data.shape[0],
                "columns": data.shape[1],
                "column_names": data.columns.tolist(),
                "dtypes": {col: str(dtype) for col, dtype in data.dtypes.items()},
                "has_missing": data.isna().any().any(),
                "missing_count": data.isna().sum().sum(),
                "missing_percentage": (data.isna().sum().sum() / (data.shape[0] * data.shape[1])) * 100 if data.shape[0] * data.shape[1] > 0 else 0
            }
        }
        
        # 添加统计信息
        if self.include_statistics:
            report_data["statistics"] = self._generate_statistics(data)
        
        # 添加异常检测结果
        if self.include_anomalies and anomalies is not None:
            report_data["anomalies"] = anomalies
        
        # 添加缺失值分析
        if self.include_missing:
            if missing_info is not None and isinstance(missing_info, dict) and "filled" in missing_info:
                # 使用传入的缺失值信息
                filled_count = missing_info.get("filled", 0)
                report_data["missing_info"] = {
                    "total_missing": data.isna().sum().sum(),
                    "total_missing_percentage": (data.isna().sum().sum() / (data.shape[0] * data.shape[1])) * 100 if data.shape[0] * data.shape[1] > 0 else 0,
                    "filled_count": filled_count,
                    "columns": {},
                    "rows": {
                        "rows_with_missing": (data.isna().sum(axis=1) > 0).sum(),
                        "rows_with_missing_percentage": ((data.isna().sum(axis=1) > 0).sum() / data.shape[0]) * 100 if data.shape[0] > 0 else 0,
                        "distribution": {}
                    },
                    "patterns": {}
                }
            else:
                # 生成完整的缺失值分析
                report_data["missing_info"] = self._generate_missing_info(data)
        
        # 添加相关性分析
        if self.include_correlation:
            report_data["correlation"] = self._generate_correlation(data)
        
        # 添加版本信息
        if self.include_version_info and version_info is not None:
            report_data["version_info"] = version_info
        
        # 添加图表
        if self.include_plots and self._plt_available:
            report_data["plots"] = self._generate_plots(data)
        
        return report_data
    
    def _generate_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        生成统计信息
        
        参数:
            data: 数据框
            
        返回:
            统计信息
        """
        # 数值列统计
        numeric_cols = data.select_dtypes(include=np.number).columns.tolist()
        numeric_stats = {}
        
        for col in numeric_cols:
            numeric_stats[col] = {
                "mean": data[col].mean(),
                "std": data[col].std(),
                "min": data[col].min(),
                "25%": data[col].quantile(0.25),
                "50%": data[col].quantile(0.5),
                "75%": data[col].quantile(0.75),
                "max": data[col].max(),
                "missing": data[col].isna().sum(),
                "missing_percentage": (data[col].isna().sum() / data.shape[0]) * 100
            }
        
        # 类别列统计
        categorical_cols = data.select_dtypes(include=["object", "category"]).columns.tolist()
        categorical_stats = {}
        
        for col in categorical_cols:
            value_counts = data[col].value_counts()
            top_values = value_counts.head(10).to_dict()
            
            categorical_stats[col] = {
                "unique_count": data[col].nunique(),
                "top_value": value_counts.index[0] if not value_counts.empty else None,
                "top_count": value_counts.iloc[0] if not value_counts.empty else 0,
                "top_values": top_values,
                "missing": data[col].isna().sum(),
                "missing_percentage": (data[col].isna().sum() / data.shape[0]) * 100
            }
        
        # 时间列统计
        datetime_cols = data.select_dtypes(include=["datetime", "datetime64"]).columns.tolist()
        datetime_stats = {}
        
        for col in datetime_cols:
            datetime_stats[col] = {
                "min": data[col].min().isoformat() if not data[col].isna().all() else None,
                "max": data[col].max().isoformat() if not data[col].isna().all() else None,
                "range_days": (data[col].max() - data[col].min()).days if not data[col].isna().all() else None,
                "missing": data[col].isna().sum(),
                "missing_percentage": (data[col].isna().sum() / data.shape[0]) * 100
            }
        
        return {
            "numeric": numeric_stats,
            "categorical": categorical_stats,
            "datetime": datetime_stats
        }
    
    def _generate_missing_info(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        生成缺失值分析
        
        参数:
            data: 数据框
            
        返回:
            缺失值分析
        """
        # 列缺失值
        column_missing = {}
        for col in data.columns:
            missing_count = data[col].isna().sum()
            if missing_count > 0:
                column_missing[col] = {
                    "count": missing_count,
                    "percentage": (missing_count / data.shape[0]) * 100
                }
        
        # 行缺失值
        row_missing_counts = data.isna().sum(axis=1)
        row_missing = {
            "rows_with_missing": (row_missing_counts > 0).sum(),
            "rows_with_missing_percentage": ((row_missing_counts > 0).sum() / data.shape[0]) * 100,
            "distribution": {
                str(i): int((row_missing_counts == i).sum()) for i in range(1, min(11, data.shape[1] + 1))
            }
        }
        
        # 如果有超过10个缺失值的行，合并为"10+"
        if data.shape[1] > 10:
            row_missing["distribution"]["10+"] = int((row_missing_counts > 10).sum())
        
        # 缺失值模式（常见的缺失值组合）
        missing_patterns = {}
        if data.shape[1] <= 20:  # 只在列数较少时计算，避免计算量过大
            # 创建缺失值标记
            missing_flags = data.isna().astype(int)
            
            # 获取前10种最常见的缺失值模式
            pattern_counts = missing_flags.value_counts().head(10)
            
            for i, (pattern, count) in enumerate(pattern_counts.items()):
                if isinstance(pattern, tuple):
                    pattern_str = ", ".join([data.columns[j] for j, flag in enumerate(pattern) if flag == 1])
                    if not pattern_str:
                        pattern_str = "无缺失"
                    
                    missing_patterns[f"pattern_{i+1}"] = {
                        "columns": pattern_str,
                        "count": int(count),
                        "percentage": (count / data.shape[0]) * 100
                    }
        
        return {
            "total_missing": data.isna().sum().sum(),
            "total_missing_percentage": (data.isna().sum().sum() / (data.shape[0] * data.shape[1])) * 100,
            "columns": column_missing,
            "rows": row_missing,
            "patterns": missing_patterns
        }
    
    def _generate_correlation(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        生成相关性分析
        
        参数:
            data: 数据框
            
        返回:
            相关性分析
        """
        # 只计算数值列的相关性
        numeric_data = data.select_dtypes(include=np.number)
        
        if numeric_data.shape[1] < 2:
            return {"message": "数值列不足，无法计算相关性"}
        
        # 计算相关性矩阵
        corr_matrix = numeric_data.corr()
        
        # 转换为字典
        corr_dict = {}
        for col1 in corr_matrix.columns:
            corr_dict[col1] = {}
            for col2 in corr_matrix.columns:
                corr_dict[col1][col2] = corr_matrix.loc[col1, col2]
        
        # 找出高相关性对
        high_corr_pairs = []
        for i, col1 in enumerate(corr_matrix.columns):
            for col2 in corr_matrix.columns[i+1:]:
                corr_value = abs(corr_matrix.loc[col1, col2])
                if corr_value >= 0.8:  # 相关系数绝对值大于等于0.8视为高相关
                    high_corr_pairs.append({
                        "column1": col1,
                        "column2": col2,
                        "correlation": corr_matrix.loc[col1, col2]
                    })
        
        # 按相关性绝对值排序
        high_corr_pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        
        return {
            "matrix": corr_dict,
            "high_correlation_pairs": high_corr_pairs
        }
    
    def _generate_plots(self, data: pd.DataFrame) -> Dict[str, str]:
        """
        生成图表
        
        参数:
            data: 数据框
            
        返回:
            图表（Base64编码）
        """
        plots = {}
        
        # 缺失值热图
        plots["missing_heatmap"] = self._plot_missing_heatmap(data)
        
        # 数值列分布图
        numeric_cols = data.select_dtypes(include=np.number).columns.tolist()
        if numeric_cols:
            plots["numeric_distribution"] = self._plot_numeric_distribution(data, numeric_cols)
        
        # 相关性热图
        if len(numeric_cols) >= 2:
            plots["correlation_heatmap"] = self._plot_correlation_heatmap(data, numeric_cols)
        
        return plots
    
    def _plot_missing_heatmap(self, data: pd.DataFrame) -> str:
        """
        绘制缺失值热图
        
        参数:
            data: 数据框
            
        返回:
            Base64编码的图像
        """
        plt.figure(figsize=(10, 6))
        
        # 限制行数，避免图表过大
        if data.shape[0] > 100:
            # 取前100行
            plot_data = data.head(100).isna()
            plt.title("缺失值热图 (前100行)")
        else:
            plot_data = data.isna()
            plt.title("缺失值热图")
        
        plt.imshow(plot_data, cmap='viridis', aspect='auto')
        plt.colorbar(label='缺失')
        plt.xlabel('列')
        plt.ylabel('行')
        
        # 设置x轴标签
        if data.shape[1] <= 20:
            plt.xticks(range(data.shape[1]), data.columns, rotation=90)
        else:
            plt.xticks([])
        
        plt.tight_layout()
        
        # 转换为Base64
        buffer = BytesIO()
        plt.savefig(buffer, format=self.plot_format)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()
        
        return f"data:image/{self.plot_format};base64,{image_base64}"
    
    def _plot_numeric_distribution(self, data: pd.DataFrame, numeric_cols: List[str]) -> str:
        """
        绘制数值列分布图
        
        参数:
            data: 数据框
            numeric_cols: 数值列列表
            
        返回:
            Base64编码的图像
        """
        # 最多显示16个子图
        cols_to_plot = numeric_cols[:min(16, len(numeric_cols))]
        
        # 计算子图行列数
        n_cols = min(4, len(cols_to_plot))
        n_rows = (len(cols_to_plot) - 1) // n_cols + 1
        
        plt.figure(figsize=(n_cols * 4, n_rows * 3))
        
        for i, col in enumerate(cols_to_plot):
            plt.subplot(n_rows, n_cols, i + 1)
            
            # 绘制直方图和核密度估计
            data[col].plot.hist(alpha=0.5, density=True)
            data[col].plot.density()
            
            plt.title(col)
            plt.xlabel('')
            plt.ylabel('')
        
        plt.tight_layout()
        
        # 转换为Base64
        buffer = BytesIO()
        plt.savefig(buffer, format=self.plot_format)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()
        
        return f"data:image/{self.plot_format};base64,{image_base64}"
    
    def _plot_correlation_heatmap(self, data: pd.DataFrame, numeric_cols: List[str]) -> str:
        """
        绘制相关性热图
        
        参数:
            data: 数据框
            numeric_cols: 数值列列表
            
        返回:
            Base64编码的图像
        """
        # 计算相关性
        corr = data[numeric_cols].corr()
        
        plt.figure(figsize=(10, 8))
        
        # 绘制热图
        plt.imshow(corr, cmap='coolwarm', vmin=-1, vmax=1)
        plt.colorbar(label='相关系数')
        
        # 设置标签
        if len(numeric_cols) <= 20:
            plt.xticks(range(len(numeric_cols)), numeric_cols, rotation=90)
            plt.yticks(range(len(numeric_cols)), numeric_cols)
        else:
            plt.xticks([])
            plt.yticks([])
        
        plt.title("相关性热图")
        
        # 添加相关系数文本
        if len(numeric_cols) <= 10:
            for i in range(len(numeric_cols)):
                for j in range(len(numeric_cols)):
                    plt.text(j, i, f"{corr.iloc[i, j]:.2f}", 
                             ha='center', va='center', 
                             color='white' if abs(corr.iloc[i, j]) > 0.5 else 'black')
        
        plt.tight_layout()
        
        # 转换为Base64
        buffer = BytesIO()
        plt.savefig(buffer, format=self.plot_format)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()
        
        return f"data:image/{self.plot_format};base64,{image_base64}"
    
    def _generate_html_report(self, report_data: Dict[str, Any], report_name: str) -> str:
        """
        生成HTML报告
        
        参数:
            report_data: 报告数据
            report_name: 报告名称
            
        返回:
            报告路径
        """
        # 设置报告名称
        report_data["report_name"] = report_name
        
        # 生成报告文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_name}_{timestamp}.html"
        report_path = os.path.join(self.output_path, filename)
        
        # 生成HTML内容
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{report_name} - 数据质量报告</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1, h2, h3, h4 {{
                    color: #2c3e50;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin-bottom: 20px;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
                tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                .card {{
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    padding: 15px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .plot-container {{
                    text-align: center;
                    margin: 20px 0;
                }}
                .plot-container img {{
                    max-width: 100%;
                    height: auto;
                }}
                .alert {{
                    padding: 15px;
                    margin-bottom: 20px;
                    border-radius: 4px;
                }}
                .alert-warning {{
                    background-color: #fcf8e3;
                    border: 1px solid #faebcc;
                    color: #8a6d3b;
                }}
                .alert-danger {{
                    background-color: #f2dede;
                    border: 1px solid #ebccd1;
                    color: #a94442;
                }}
                .summary {{
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <h1>{report_name} - 数据质量报告</h1>
            <p>生成时间: {report_data["generation_time"]}</p>
            
            <div class="card summary">
                <h2>数据概览</h2>
                <table>
                    <tr>
                        <th>行数</th>
                        <td>{report_data["data_info"]["rows"]}</td>
                    </tr>
                    <tr>
                        <th>列数</th>
                        <td>{report_data["data_info"]["columns"]}</td>
                    </tr>
                    <tr>
                        <th>缺失值数量</th>
                        <td>{report_data["data_info"]["missing_count"]}</td>
                    </tr>
                    <tr>
                        <th>缺失值百分比</th>
                        <td>{report_data["data_info"]["missing_percentage"]:.2f}%</td>
                    </tr>
                </table>
            </div>
        """
        
        # 添加版本信息
        if self.include_version_info and "version_info" in report_data:
            version_info = report_data["version_info"]
            html_content += f"""
            <div class="card">
                <h2>版本信息</h2>
                <table>
                    <tr>
                        <th>版本ID</th>
                        <td>{version_info.get("version_id", "")}</td>
                    </tr>
                    <tr>
                        <th>时间戳</th>
                        <td>{version_info.get("timestamp", "")}</td>
                    </tr>
                    <tr>
                        <th>数据哈希</th>
                        <td>{version_info.get("data_hash", "")}</td>
                    </tr>
                    <tr>
                        <th>创建时间</th>
                        <td>{version_info.get("created_at", "")}</td>
                    </tr>
                </table>
            </div>
            """
        
        # 添加统计信息
        if self.include_statistics and "statistics" in report_data:
            stats = report_data["statistics"]
            
            # 数值列统计
            if "numeric" in stats and stats["numeric"]:
                html_content += """
                <div class="card">
                    <h2>数值列统计</h2>
                    <table>
                        <tr>
                            <th>列名</th>
                            <th>均值</th>
                            <th>标准差</th>
                            <th>最小值</th>
                            <th>25%分位数</th>
                            <th>中位数</th>
                            <th>75%分位数</th>
                            <th>最大值</th>
                            <th>缺失值</th>
                            <th>缺失值百分比</th>
                        </tr>
                """
                
                for col, col_stats in stats["numeric"].items():
                    html_content += f"""
                        <tr>
                            <td>{col}</td>
                            <td>{col_stats["mean"]:.4f}</td>
                            <td>{col_stats["std"]:.4f}</td>
                            <td>{col_stats["min"]:.4f}</td>
                            <td>{col_stats["25%"]:.4f}</td>
                            <td>{col_stats["50%"]:.4f}</td>
                            <td>{col_stats["75%"]:.4f}</td>
                            <td>{col_stats["max"]:.4f}</td>
                            <td>{col_stats["missing"]}</td>
                            <td>{col_stats["missing_percentage"]:.2f}%</td>
                        </tr>
                    """
                
                html_content += """
                </table>
                </div>
                """
            
            # 类别列统计
            if "categorical" in stats and stats["categorical"]:
                html_content += """
                <div class="card">
                    <h2>类别列统计</h2>
                    <table>
                        <tr>
                            <th>列名</th>
                            <th>唯一值数量</th>
                            <th>最常见值</th>
                            <th>最常见值计数</th>
                            <th>缺失值</th>
                            <th>缺失值百分比</th>
                        </tr>
                """
                
                for col, col_stats in stats["categorical"].items():
                    html_content += f"""
                        <tr>
                            <td>{col}</td>
                            <td>{col_stats["unique_count"]}</td>
                            <td>{col_stats["top_value"]}</td>
                            <td>{col_stats["top_count"]}</td>
                            <td>{col_stats["missing"]}</td>
                            <td>{col_stats["missing_percentage"]:.2f}%</td>
                        </tr>
                    """
                
                html_content += """
                </table>
                </div>
                """
            
            # 时间列统计
            if "datetime" in stats and stats["datetime"]:
                html_content += """
                <div class="card">
                    <h2>时间列统计</h2>
                    <table>
                        <tr>
                            <th>列名</th>
                            <th>最小值</th>
                            <th>最大值</th>
                            <th>范围(天)</th>
                            <th>缺失值</th>
                            <th>缺失值百分比</th>
                        </tr>
                """
                
                for col, col_stats in stats["datetime"].items():
                    html_content += f"""
                        <tr>
                            <td>{col}</td>
                            <td>{col_stats["min"]}</td>
                            <td>{col_stats["max"]}</td>
                            <td>{col_stats["range_days"]}</td>
                            <td>{col_stats["missing"]}</td>
                            <td>{col_stats["missing_percentage"]:.2f}%</td>
                        </tr>
                    """
                
                html_content += """
                </table>
                </div>
                """
        
        # 添加缺失值分析
        if self.include_missing and "missing_info" in report_data:
            missing_info = report_data["missing_info"]
            
            html_content += f"""
            <div class="card">
                <h2>缺失值分析</h2>
                <div class="summary">
                    <p>总缺失值: {missing_info["total_missing"]} ({missing_info["total_missing_percentage"]:.2f}%)</p>
                    <p>含缺失值的行数: {missing_info["rows"]["rows_with_missing"]} ({missing_info["rows"]["rows_with_missing_percentage"]:.2f}%)</p>
                </div>
            """
            
            # 列缺失值
            if "columns" in missing_info and missing_info["columns"]:
                html_content += """
                <h3>列缺失值</h3>
                <table>
                    <tr>
                        <th>列名</th>
                        <th>缺失值数量</th>
                        <th>缺失值百分比</th>
                    </tr>
                """
                
                for col, col_missing in missing_info["columns"].items():
                    html_content += f"""
                        <tr>
                            <td>{col}</td>
                            <td>{col_missing["count"]}</td>
                            <td>{col_missing["percentage"]:.2f}%</td>
                        </tr>
                    """
                
                html_content += """
                </table>
                """
            
            # 缺失值模式
            if "patterns" in missing_info and missing_info["patterns"]:
                html_content += """
                <h3>缺失值模式</h3>
                <table>
                    <tr>
                        <th>模式</th>
                        <th>列</th>
                        <th>计数</th>
                        <th>百分比</th>
                    </tr>
                """
                
                for pattern_id, pattern_info in missing_info["patterns"].items():
                    html_content += f"""
                        <tr>
                            <td>{pattern_id}</td>
                            <td>{pattern_info["columns"]}</td>
                            <td>{pattern_info["count"]}</td>
                            <td>{pattern_info["percentage"]:.2f}%</td>
                        </tr>
                    """
                
                html_content += """
                </table>
                """
            
            html_content += """
            </div>
            """
        
        # 添加异常检测结果
        if self.include_anomalies and "anomalies" in report_data:
            anomalies = report_data["anomalies"]
            
            html_content += """
            <div class="card">
                <h2>异常检测结果</h2>
            """
            
            if "anomalies" in anomalies and anomalies["anomalies"]:
                html_content += """
                <div class="alert alert-warning">
                    <p>检测到异常值！</p>
                </div>
                <table>
                    <tr>
                        <th>列名</th>
                        <th>行索引</th>
                        <th>值</th>
                        <th>异常类型</th>
                        <th>分数</th>
                    </tr>
                """
                
                for anomaly in anomalies["anomalies"]:
                    html_content += f"""
                        <tr>
                            <td>{anomaly.get("column", "")}</td>
                            <td>{anomaly.get("index", "")}</td>
                            <td>{anomaly.get("value", "")}</td>
                            <td>{anomaly.get("type", "")}</td>
                            <td>{anomaly.get("score", "")}</td>
                        </tr>
                    """
                
                html_content += """
                </table>
                """
            else:
                html_content += """
                <div class="alert">
                    <p>未检测到异常值。</p>
                </div>
                """
            
            html_content += """
            </div>
            """
        
        # 添加相关性分析
        if self.include_correlation and "correlation" in report_data:
            correlation = report_data["correlation"]
            
            if isinstance(correlation, dict) and "high_correlation_pairs" in correlation:
                high_corr_pairs = correlation["high_correlation_pairs"]
                
                if high_corr_pairs:
                    html_content += """
                    <div class="card">
                        <h2>高相关性对</h2>
                        <table>
                            <tr>
                                <th>列1</th>
                                <th>列2</th>
                                <th>相关系数</th>
                            </tr>
                    """
                    
                    for pair in high_corr_pairs:
                        html_content += f"""
                            <tr>
                                <td>{pair["column1"]}</td>
                                <td>{pair["column2"]}</td>
                                <td>{pair["correlation"]:.4f}</td>
                            </tr>
                        """
                    
                    html_content += """
                        </table>
                    </div>
                    """
        
        # 添加图表
        if self.include_plots and "plots" in report_data:
            plots = report_data["plots"]
            
            html_content += """
            <div class="card">
                <h2>数据可视化</h2>
            """
            
            if "missing_heatmap" in plots:
                html_content += f"""
                <div class="plot-container">
                    <h3>缺失值热图</h3>
                    <img src="{plots["missing_heatmap"]}" alt="缺失值热图">
                </div>
                """
            
            if "numeric_distribution" in plots:
                html_content += f"""
                <div class="plot-container">
                    <h3>数值列分布</h3>
                    <img src="{plots["numeric_distribution"]}" alt="数值列分布">
                </div>
                """
            
            if "correlation_heatmap" in plots:
                html_content += f"""
                <div class="plot-container">
                    <h3>相关性热图</h3>
                    <img src="{plots["correlation_heatmap"]}" alt="相关性热图">
                </div>
                """
            
            html_content += """
            </div>
            """
        
        # 结束HTML
        html_content += """
        </body>
        </html>
        """
        
        # 写入文件
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        return report_path

    def _generate_json_report(self, report_data: Dict[str, Any], report_name: str) -> str:
        """
        生成JSON报告
        
        参数:
            report_data: 报告数据
            report_name: 报告名称
            
        返回:
            报告路径
        """
        # 设置报告名称
        report_data["report_name"] = report_name
        
        # 生成报告文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_name}_{timestamp}.json"
        report_path = os.path.join(self.output_path, filename)
        
        # 处理图表数据（Base64编码太长，可能导致JSON文件过大）
        if "plots" in report_data:
            # 保存图表为单独的文件
            plots_dir = os.path.join(self.output_path, f"{report_name}_{timestamp}_plots")
            os.makedirs(plots_dir, exist_ok=True)
            
            plots_info = {}
            for plot_name, plot_data in report_data["plots"].items():
                # 从Base64中提取图像数据
                if "," in plot_data:
                    header, data = plot_data.split(",", 1)
                    plot_format = self.plot_format
                    
                    # 保存图像文件
                    plot_filename = f"{plot_name}.{plot_format}"
                    plot_path = os.path.join(plots_dir, plot_filename)
                    
                    with open(plot_path, "wb") as f:
                        f.write(base64.b64decode(data))
                    
                    # 记录相对路径
                    plots_info[plot_name] = os.path.join(f"{report_name}_{timestamp}_plots", plot_filename)
            
            # 替换报告中的图表数据
            report_data["plots"] = plots_info
        
        # 写入JSON文件
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
        
        return report_path
    
    def _generate_markdown_report(self, report_data: Dict[str, Any], report_name: str) -> str:
        """
        生成Markdown报告
        
        参数:
            report_data: 报告数据
            report_name: 报告名称
            
        返回:
            报告路径
        """
        # 设置报告名称
        report_data["report_name"] = report_name
        
        # 生成报告文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_name}_{timestamp}.md"
        report_path = os.path.join(self.output_path, filename)
        
        # 处理图表数据
        plots_paths = {}
        if "plots" in report_data and self.include_plots:
            # 保存图表为单独的文件
            plots_dir = os.path.join(self.output_path, f"{report_name}_{timestamp}_plots")
            os.makedirs(plots_dir, exist_ok=True)
            
            for plot_name, plot_data in report_data["plots"].items():
                # 从Base64中提取图像数据
                if "," in plot_data:
                    header, data = plot_data.split(",", 1)
                    plot_format = self.plot_format
                    
                    # 保存图像文件
                    plot_filename = f"{plot_name}.{plot_format}"
                    plot_path = os.path.join(plots_dir, plot_filename)
                    
                    with open(plot_path, "wb") as f:
                        f.write(base64.b64decode(data))
                    
                    # 记录相对路径
                    plots_paths[plot_name] = os.path.join(f"{report_name}_{timestamp}_plots", plot_filename)
        
        # 生成Markdown内容
        md_content = f"# {report_name} - 数据质量报告\n\n"
        md_content += f"生成时间: {report_data['generation_time']}\n\n"
        
        # 数据概览
        md_content += "## 数据概览\n\n"
        md_content += "| 指标 | 值 |\n"
        md_content += "| --- | --- |\n"
        md_content += f"| 行数 | {report_data['data_info']['rows']} |\n"
        md_content += f"| 列数 | {report_data['data_info']['columns']} |\n"
        md_content += f"| 缺失值数量 | {report_data['data_info']['missing_count']} |\n"
        md_content += f"| 缺失值百分比 | {report_data['data_info']['missing_percentage']:.2f}% |\n\n"
        
        # 版本信息
        if self.include_version_info and "version_info" in report_data:
            version_info = report_data["version_info"]
            md_content += "## 版本信息\n\n"
            md_content += "| 指标 | 值 |\n"
            md_content += "| --- | --- |\n"
            md_content += f"| 版本ID | {version_info.get('version_id', '')} |\n"
            md_content += f"| 时间戳 | {version_info.get('timestamp', '')} |\n"
            md_content += f"| 数据哈希 | {version_info.get('data_hash', '')} |\n"
            md_content += f"| 创建时间 | {version_info.get('created_at', '')} |\n\n"
        
        # 统计信息
        if self.include_statistics and "statistics" in report_data:
            stats = report_data["statistics"]
            md_content += "## 统计信息\n\n"
            
            # 数值列统计
            if "numeric" in stats and stats["numeric"]:
                md_content += "### 数值列统计\n\n"
                md_content += "| 列名 | 均值 | 标准差 | 最小值 | 25%分位数 | 中位数 | 75%分位数 | 最大值 | 缺失值 | 缺失值百分比 |\n"
                md_content += "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
                
                for col, col_stats in stats["numeric"].items():
                    md_content += f"| {col} | {col_stats['mean']:.4f} | {col_stats['std']:.4f} | {col_stats['min']:.4f} | "
                    md_content += f"{col_stats['25%']:.4f} | {col_stats['50%']:.4f} | {col_stats['75%']:.4f} | "
                    md_content += f"{col_stats['max']:.4f} | {col_stats['missing']} | {col_stats['missing_percentage']:.2f}% |\n"
                
                md_content += "\n"
            
            # 类别列统计
            if "categorical" in stats and stats["categorical"]:
                md_content += "### 类别列统计\n\n"
                md_content += "| 列名 | 唯一值数量 | 最常见值 | 最常见值计数 | 缺失值 | 缺失值百分比 |\n"
                md_content += "| --- | --- | --- | --- | --- | --- |\n"
                
                for col, col_stats in stats["categorical"].items():
                    md_content += f"| {col} | {col_stats['unique_count']} | {col_stats['top_value']} | "
                    md_content += f"{col_stats['top_count']} | {col_stats['missing']} | {col_stats['missing_percentage']:.2f}% |\n"
                
                md_content += "\n"
            
            # 时间列统计
            if "datetime" in stats and stats["datetime"]:
                md_content += "### 时间列统计\n\n"
                md_content += "| 列名 | 最小值 | 最大值 | 范围(天) | 缺失值 | 缺失值百分比 |\n"
                md_content += "| --- | --- | --- | --- | --- | --- |\n"
                
                for col, col_stats in stats["datetime"].items():
                    md_content += f"| {col} | {col_stats['min']} | {col_stats['max']} | "
                    md_content += f"{col_stats['range_days']} | {col_stats['missing']} | {col_stats['missing_percentage']:.2f}% |\n"
                
                md_content += "\n"
        
        # 缺失值分析
        if self.include_missing and "missing_info" in report_data:
            missing_info = report_data["missing_info"]
            md_content += "## 缺失值分析\n\n"
            md_content += f"总缺失值: {missing_info['total_missing']} ({missing_info['total_missing_percentage']:.2f}%)\n\n"
            md_content += f"含缺失值的行数: {missing_info['rows']['rows_with_missing']} ({missing_info['rows']['rows_with_missing_percentage']:.2f}%)\n\n"
            
            # 列缺失值
            if "columns" in missing_info and missing_info["columns"]:
                md_content += "### 列缺失值\n\n"
                md_content += "| 列名 | 缺失值数量 | 缺失值百分比 |\n"
                md_content += "| --- | --- | --- |\n"
                
                for col, col_missing in missing_info["columns"].items():
                    md_content += f"| {col} | {col_missing['count']} | {col_missing['percentage']:.2f}% |\n"
                
                md_content += "\n"
            
            # 缺失值模式
            if "patterns" in missing_info and missing_info["patterns"]:
                md_content += "### 缺失值模式\n\n"
                md_content += "| 模式 | 列 | 计数 | 百分比 |\n"
                md_content += "| --- | --- | --- | --- |\n"
                
                for pattern_id, pattern_info in missing_info["patterns"].items():
                    md_content += f"| {pattern_id} | {pattern_info['columns']} | {pattern_info['count']} | {pattern_info['percentage']:.2f}% |\n"
                
                md_content += "\n"
        
        # 异常检测结果
        if self.include_anomalies and "anomalies" in report_data:
            anomalies = report_data["anomalies"]
            md_content += "## 异常检测结果\n\n"
            
            if "anomalies" in anomalies and anomalies["anomalies"]:
                md_content += "**检测到异常值！**\n\n"
                md_content += "| 列名 | 行索引 | 值 | 异常类型 | 分数 |\n"
                md_content += "| --- | --- | --- | --- | --- |\n"
                
                for anomaly in anomalies["anomalies"]:
                    md_content += f"| {anomaly.get('column', '')} | {anomaly.get('index', '')} | {anomaly.get('value', '')} | "
                    md_content += f"{anomaly.get('type', '')} | {anomaly.get('score', '')} |\n"
                
                md_content += "\n"
            else:
                md_content += "未检测到异常值。\n\n"
        
        # 相关性分析
        if self.include_correlation and "correlation" in report_data:
            correlation = report_data["correlation"]
            
            if isinstance(correlation, dict) and "high_correlation_pairs" in correlation:
                high_corr_pairs = correlation["high_correlation_pairs"]
                
                if high_corr_pairs:
                    md_content += "## 高相关性对\n\n"
                    md_content += "| 列1 | 列2 | 相关系数 |\n"
                    md_content += "| --- | --- | --- |\n"
                    
                    for pair in high_corr_pairs:
                        md_content += f"| {pair['column1']} | {pair['column2']} | {pair['correlation']:.4f} |\n"
                    
                    md_content += "\n"
        
        # 图表
        if self.include_plots and plots_paths:
            md_content += "## 数据可视化\n\n"
            
            if "missing_heatmap" in plots_paths:
                md_content += "### 缺失值热图\n\n"
                md_content += f"![缺失值热图]({plots_paths['missing_heatmap']})\n\n"
            
            if "numeric_distribution" in plots_paths:
                md_content += "### 数值列分布\n\n"
                md_content += f"![数值列分布]({plots_paths['numeric_distribution']})\n\n"
            
            if "correlation_heatmap" in plots_paths:
                md_content += "### 相关性热图\n\n"
                md_content += f"![相关性热图]({plots_paths['correlation_heatmap']})\n\n"
        
        # 写入文件
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        
        return report_path
