"""
多模态协同填充处理器实现
利用其他模态数据辅助填充缺失值
"""
from typing import Dict, List, Union, Optional, Any, Tuple
import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime
import warnings

from .base import BaseMissingValueHandler

# 配置日志
logger = logging.getLogger(__name__)


class MultiModalMissingValueHandler(BaseMissingValueHandler):
    """
    多模态协同填充处理器
    利用其他模态数据辅助填充缺失值
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化多模态协同填充处理器
        
        参数:
            config: 配置字典，包含以下字段:
                - method: 填充方法，支持'correlation'、'embedding'、'ensemble'
                - target_columns: 目标列，需要填充缺失值的列
                - auxiliary_columns: 辅助列，用于辅助填充的列
                - group_col: 分组列名，默认为'instrument'
                - time_col: 时间列名，默认为'datetime'
                - text_data: 文本数据字典，可选
                - image_data: 图像数据字典，可选
                - embedding_dim: 嵌入维度，用于embedding方法
        """
        super().__init__(config)
        self.target_columns = config.get("target_columns", [])
        self.auxiliary_columns = config.get("auxiliary_columns", [])
        self.group_col = config.get("group_col", "instrument")
        self.time_col = config.get("time_col", "datetime")
        self.text_data = config.get("text_data", {})
        self.image_data = config.get("image_data", {})
        self.embedding_dim = config.get("embedding_dim", 32)
        
        # 检查是否有可选依赖
        if self.config["method"] == "embedding":
            try:
                import torch
                self.torch_available = True
            except ImportError:
                self.torch_available = False
                warnings.warn("PyTorch未安装，无法使用embedding方法")
                self.config["method"] = "correlation"  # 降级到correlation方法
        
        if self.config["method"] == "ensemble":
            try:
                from sklearn.ensemble import RandomForestRegressor
                self.sklearn_available = True
            except ImportError:
                self.sklearn_available = False
                warnings.warn("scikit-learn未安装，无法使用ensemble方法")
                self.config["method"] = "correlation"  # 降级到correlation方法
    
    def fill(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        填充数据缺失值
        
        参数:
            data: 待处理的数据框
            
        返回:
            处理后的数据框
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError("数据必须是pandas DataFrame类型")
        
        # 复制数据，避免修改原始数据
        result = data.copy()
        
        # 验证目标列
        if not self.target_columns:
            self.logger.warning("未指定目标列，使用所有含缺失值的数值列")
            self.target_columns = [
                col for col in result.select_dtypes(include=np.number).columns
                if result[col].isna().any()
            ]
        else:
            # 确保所有指定的列都存在
            missing_cols = set(self.target_columns) - set(result.columns)
            if missing_cols:
                self.logger.warning(f"以下目标列不存在: {missing_cols}")
            
            # 筛选存在的列
            self.target_columns = [col for col in self.target_columns if col in result.columns]
        
        if not self.target_columns:
            self.logger.warning("没有可处理的目标列")
            return result
        
        # 验证辅助列
        if not self.auxiliary_columns:
            self.logger.warning("未指定辅助列，使用所有非目标列的数值列")
            self.auxiliary_columns = [
                col for col in result.select_dtypes(include=np.number).columns
                if col not in self.target_columns
            ]
        else:
            # 确保所有指定的列都存在
            missing_cols = set(self.auxiliary_columns) - set(result.columns)
            if missing_cols:
                self.logger.warning(f"以下辅助列不存在: {missing_cols}")
            
            # 筛选存在的列
            self.auxiliary_columns = [col for col in self.auxiliary_columns if col in result.columns]
        
        if not self.auxiliary_columns:
            self.logger.warning("没有可用的辅助列，使用基本插值")
            # 使用线性插值
            for col in self.target_columns:
                result[col] = result[col].interpolate(method="linear")
            return result
        
        # 按分组处理
        if self.group_col in result.columns:
            groups = result[self.group_col].unique()
            for group in groups:
                group_mask = result[self.group_col] == group
                group_data = result.loc[group_mask].copy()
                
                # 对每个目标列进行处理
                for col in self.target_columns:
                    if group_data[col].isna().any():
                        group_data[col] = self._fill_column_multimodal(group_data, col, group)
                
                # 更新结果
                result.loc[group_mask, self.target_columns] = group_data[self.target_columns]
        else:
            # 不分组处理
            for col in self.target_columns:
                if result[col].isna().any():
                    result[col] = self._fill_column_multimodal(result, col)
        
        return result
    
    def _fill_column_multimodal(self, data: pd.DataFrame, target_col: str, group: Optional[str] = None) -> pd.Series:
        """
        使用多模态协同填充单列的缺失值
        
        参数:
            data: 数据框
            target_col: 目标列名
            group: 分组值，可选
            
        返回:
            处理后的列
        """
        method = self.config["method"]
        
        # 复制目标列，避免修改原始数据
        result = data[target_col].copy()
        
        # 如果没有缺失值，直接返回
        if not result.isna().any():
            return result
        
        # 获取缺失值索引
        na_mask = result.isna()
        na_indices = np.where(na_mask)[0]
        
        if method == "correlation":
            # 相关性填充
            return self._fill_by_correlation(data, target_col, na_indices)
        
        elif method == "embedding" and self.torch_available:
            # 嵌入填充
            return self._fill_by_embedding(data, target_col, na_indices, group)
        
        elif method == "ensemble" and self.sklearn_available:
            # 集成填充
            return self._fill_by_ensemble(data, target_col, na_indices)
        
        else:
            self.logger.warning(f"不支持的方法或依赖缺失: {method}，使用相关性填充")
            return self._fill_by_correlation(data, target_col, na_indices)
    
    def _fill_by_correlation(self, data: pd.DataFrame, target_col: str, na_indices: np.ndarray) -> pd.Series:
        """
        使用相关性方法填充缺失值
        
        参数:
            data: 数据框
            target_col: 目标列名
            na_indices: 缺失值索引
            
        返回:
            处理后的列
        """
        # 复制目标列，避免修改原始数据
        result = data[target_col].copy()
        
        # 计算相关性
        corr = data.corr()[target_col].abs()
        
        # 排除目标列自身
        corr = corr.drop(target_col)
        
        # 排除辅助列中不在相关性计算结果中的列
        aux_cols = [col for col in self.auxiliary_columns if col in corr.index]
        
        if not aux_cols:
            self.logger.warning("没有有效的辅助列，使用线性插值")
            return result.interpolate(method="linear")
        
        # 按相关性排序
        corr = corr[aux_cols].sort_values(ascending=False)
        
        # 选择相关性最高的列
        top_cols = corr.index[:min(3, len(corr))].tolist()
        
        # 使用线性回归填充
        try:
            from sklearn.linear_model import LinearRegression
            
            # 准备训练数据
            train_mask = ~data[target_col].isna()
            X_train = data.loc[train_mask, top_cols]
            y_train = data.loc[train_mask, target_col]
            
            # 训练模型
            model = LinearRegression()
            model.fit(X_train, y_train)
            
            # 预测缺失值
            X_pred = data.loc[na_indices, top_cols]
            y_pred = model.predict(X_pred)
            
            # 填充缺失值
            result.iloc[na_indices] = y_pred
            
            return result
        
        except Exception as e:
            self.logger.warning(f"线性回归填充失败: {e}，使用加权平均填充")
            
            # 使用加权平均填充
            for idx in na_indices:
                weights = corr.values
                values = data.iloc[idx][top_cols].values
                
                # 处理辅助列中的缺失值
                valid_mask = ~np.isnan(values)
                if not any(valid_mask):
                    # 如果所有辅助列都是缺失值，使用线性插值
                    continue
                
                # 计算加权平均
                valid_weights = weights[valid_mask]
                valid_values = values[valid_mask]
                result.iloc[idx] = np.average(valid_values, weights=valid_weights)
            
            # 处理仍然缺失的值
            if result.isna().any():
                result = result.interpolate(method="linear")
            
            return result
    
    def _fill_by_embedding(self, data: pd.DataFrame, target_col: str, na_indices: np.ndarray, group: Optional[str] = None) -> pd.Series:
        """
        使用嵌入方法填充缺失值
        
        参数:
            data: 数据框
            target_col: 目标列名
            na_indices: 缺失值索引
            group: 分组值，可选
            
        返回:
            处理后的列
        """
        import torch
        import torch.nn as nn
        import torch.optim as optim
        from torch.utils.data import DataLoader, TensorDataset
        
        # 复制目标列，避免修改原始数据
        result = data[target_col].copy()
        
        # 准备数值特征
        aux_cols = [col for col in self.auxiliary_columns if col in data.columns]
        
        if not aux_cols:
            self.logger.warning("没有有效的辅助列，使用线性插值")
            return result.interpolate(method="linear")
        
        # 准备训练数据
        train_mask = ~data[target_col].isna()
        X_train_num = data.loc[train_mask, aux_cols].values
        y_train = data.loc[train_mask, target_col].values
        
        # 标准化数值特征
        X_mean = np.nanmean(X_train_num, axis=0)
        X_std = np.nanstd(X_train_num, axis=0)
        X_std[X_std == 0] = 1  # 避免除以零
        X_train_num = (X_train_num - X_mean) / X_std
        
        # 处理数值特征中的缺失值
        X_train_num = np.nan_to_num(X_train_num)
        
        # 准备文本特征
        X_train_text = None
        if self.text_data:
            try:
                # 构建文本特征
                text_features = []
                for idx in data.index[train_mask]:
                    if isinstance(data.index, pd.MultiIndex):
                        # 处理多级索引
                        instrument, dt = idx
                        if isinstance(dt, pd.Timestamp):
                            dt = dt.strftime("%Y%m%d")
                        key = f"{instrument}_{dt}"
                    else:
                        # 处理单级索引
                        if self.group_col in data.columns and self.time_col in data.columns:
                            instrument = data.loc[idx, self.group_col]
                            dt = data.loc[idx, self.time_col]
                            if isinstance(dt, pd.Timestamp):
                                dt = dt.strftime("%Y%m%d")
                            key = f"{instrument}_{dt}"
                        else:
                            key = str(idx)
                    
                    # 获取文本数据
                    texts = self.text_data.get(key, [])
                    
                    # 简单的文本特征：文本长度和文本数量
                    text_len = np.mean([len(text) for text in texts]) if texts else 0
                    text_count = len(texts)
                    
                    text_features.append([text_len, text_count])
                
                X_train_text = np.array(text_features)
                
                # 标准化文本特征
                text_mean = np.mean(X_train_text, axis=0)
                text_std = np.std(X_train_text, axis=0)
                text_std[text_std == 0] = 1  # 避免除以零
                X_train_text = (X_train_text - text_mean) / text_std
            
            except Exception as e:
                self.logger.warning(f"文本特征处理失败: {e}")
                X_train_text = None
        
        # 准备图像特征
        X_train_image = None
        if self.image_data:
            try:
                # 构建图像特征
                image_features = []
                for idx in data.index[train_mask]:
                    if isinstance(data.index, pd.MultiIndex):
                        # 处理多级索引
                        instrument, dt = idx
                        if isinstance(dt, pd.Timestamp):
                            dt = dt.strftime("%Y%m%d")
                        key = f"{instrument}_{dt}"
                    else:
                        # 处理单级索引
                        if self.group_col in data.columns and self.time_col in data.columns:
                            instrument = data.loc[idx, self.group_col]
                            dt = data.loc[idx, self.time_col]
                            if isinstance(dt, pd.Timestamp):
                                dt = dt.strftime("%Y%m%d")
                            key = f"{instrument}_{dt}"
                        else:
                            key = str(idx)
                    
                    # 获取图像数据
                    images = self.image_data.get(key, [])
                    
                    # 简单的图像特征：图像数量
                    image_count = len(images)
                    
                    image_features.append([image_count])
                
                X_train_image = np.array(image_features)
                
                # 标准化图像特征
                image_mean = np.mean(X_train_image, axis=0)
                image_std = np.std(X_train_image, axis=0)
                image_std[image_std == 0] = 1  # 避免除以零
                X_train_image = (X_train_image - image_mean) / image_std
            
            except Exception as e:
                self.logger.warning(f"图像特征处理失败: {e}")
                X_train_image = None
        
        # 组合特征
        features = [X_train_num]
        if X_train_text is not None:
            features.append(X_train_text)
        if X_train_image is not None:
            features.append(X_train_image)
        
        X_train = np.hstack(features)
        
        # 转换为张量
        X_train_tensor = torch.tensor(X_train, dtype=torch.float32)
        y_train_tensor = torch.tensor(y_train, dtype=torch.float32).view(-1, 1)
        
        # 定义模型
        class EmbeddingModel(nn.Module):
            def __init__(self, input_dim, embedding_dim):
                super().__init__()
                self.encoder = nn.Sequential(
                    nn.Linear(input_dim, embedding_dim * 2),
                    nn.ReLU(),
                    nn.Linear(embedding_dim * 2, embedding_dim)
                )
                self.decoder = nn.Sequential(
                    nn.Linear(embedding_dim, embedding_dim * 2),
                    nn.ReLU(),
                    nn.Linear(embedding_dim * 2, 1)
                )
            
            def forward(self, x):
                embedding = self.encoder(x)
                output = self.decoder(embedding)
                return output
        
        # 创建模型
        input_dim = X_train.shape[1]
        model = EmbeddingModel(input_dim, self.embedding_dim)
        
        # 定义损失函数和优化器
        criterion = nn.MSELoss()
        optimizer = optim.Adam(model.parameters(), lr=0.001)
        
        # 创建数据加载器
        dataset = TensorDataset(X_train_tensor, y_train_tensor)
        dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
        
        # 训练模型
        model.train()
        for epoch in range(50):  # 训练50个epoch
            for batch_X, batch_y in dataloader:
                # 前向传播
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                
                # 反向传播和优化
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
        
        # 准备预测数据
        X_pred_num = data.iloc[na_indices][aux_cols].values
        X_pred_num = (X_pred_num - X_mean) / X_std
        X_pred_num = np.nan_to_num(X_pred_num)
        
        # 准备文本特征
        X_pred_text = None
        if X_train_text is not None:
            try:
                # 构建文本特征
                text_features = []
                for idx in data.index[na_indices]:
                    if isinstance(data.index, pd.MultiIndex):
                        # 处理多级索引
                        instrument, dt = idx
                        if isinstance(dt, pd.Timestamp):
                            dt = dt.strftime("%Y%m%d")
                        key = f"{instrument}_{dt}"
                    else:
                        # 处理单级索引
                        if self.group_col in data.columns and self.time_col in data.columns:
                            instrument = data.loc[idx, self.group_col]
                            dt = data.loc[idx, self.time_col]
                            if isinstance(dt, pd.Timestamp):
                                dt = dt.strftime("%Y%m%d")
                            key = f"{instrument}_{dt}"
                        else:
                            key = str(idx)
                    
                    # 获取文本数据
                    texts = self.text_data.get(key, [])
                    
                    # 简单的文本特征：文本长度和文本数量
                    text_len = np.mean([len(text) for text in texts]) if texts else 0
                    text_count = len(texts)
                    
                    text_features.append([text_len, text_count])
                
                X_pred_text = np.array(text_features)
                
                # 标准化文本特征
                X_pred_text = (X_pred_text - text_mean) / text_std
            
            except Exception as e:
                self.logger.warning(f"预测文本特征处理失败: {e}")
                X_pred_text = None
        
        # 准备图像特征
        X_pred_image = None
        if X_train_image is not None:
            try:
                # 构建图像特征
                image_features = []
                for idx in data.index[na_indices]:
                    if isinstance(data.index, pd.MultiIndex):
                        # 处理多级索引
                        instrument, dt = idx
                        if isinstance(dt, pd.Timestamp):
                            dt = dt.strftime("%Y%m%d")
                        key = f"{instrument}_{dt}"
                    else:
                        # 处理单级索引
                        if self.group_col in data.columns and self.time_col in data.columns:
                            instrument = data.loc[idx, self.group_col]
                            dt = data.loc[idx, self.time_col]
                            if isinstance(dt, pd.Timestamp):
                                dt = dt.strftime("%Y%m%d")
                            key = f"{instrument}_{dt}"
                        else:
                            key = str(idx)
                    
                    # 获取图像数据
                    images = self.image_data.get(key, [])
                    
                    # 简单的图像特征：图像数量
                    image_count = len(images)
                    
                    image_features.append([image_count])
                
                X_pred_image = np.array(image_features)
                
                # 标准化图像特征
                X_pred_image = (X_pred_image - image_mean) / image_std
            
            except Exception as e:
                self.logger.warning(f"预测图像特征处理失败: {e}")
                X_pred_image = None
        
        # 组合特征
        features = [X_pred_num]
        if X_pred_text is not None:
            features.append(X_pred_text)
        if X_pred_image is not None:
            features.append(X_pred_image)
        
        X_pred = np.hstack(features)
        
        # 转换为张量
        X_pred_tensor = torch.tensor(X_pred, dtype=torch.float32)
        
        # 预测
        model.eval()
        with torch.no_grad():
            y_pred = model(X_pred_tensor).numpy().flatten()
        
        # 填充缺失值
        result.iloc[na_indices] = y_pred
        
        return result
    
    def _fill_by_ensemble(self, data: pd.DataFrame, target_col: str, na_indices: np.ndarray) -> pd.Series:
        """
        使用集成方法填充缺失值
        
        参数:
            data: 数据框
            target_col: 目标列名
            na_indices: 缺失值索引
            
        返回:
            处理后的列
        """
        from sklearn.ensemble import RandomForestRegressor
        
        # 复制目标列，避免修改原始数据
        result = data[target_col].copy()
        
        # 准备辅助列
        aux_cols = [col for col in self.auxiliary_columns if col in data.columns]
        
        if not aux_cols:
            self.logger.warning("没有有效的辅助列，使用线性插值")
            return result.interpolate(method="linear")
        
        # 准备训练数据
        train_mask = ~data[target_col].isna()
        X_train = data.loc[train_mask, aux_cols]
        y_train = data.loc[train_mask, target_col]
        
        # 处理训练数据中的缺失值
        X_train = X_train.fillna(X_train.mean())
        
        # 训练模型
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        # 准备预测数据
        X_pred = data.iloc[na_indices][aux_cols]
        
        # 处理预测数据中的缺失值
        X_pred = X_pred.fillna(X_train.mean())
        
        # 预测
        y_pred = model.predict(X_pred)
        
        # 填充缺失值
        result.iloc[na_indices] = y_pred
        
        return result
