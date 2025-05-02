"""
金融专业知识图谱模块
实现金融领域知识的图谱构建、查询和可视化
"""

import os
import json
import logging
from typing import Dict, List, Optional, Set, Tuple, Union, Any

import networkx as nx
from networkx.readwrite import json_graph
import numpy as np
import pandas as pd
from tqdm import tqdm

# 配置日志
logger = logging.getLogger(__name__)

class FinancialKnowledgeGraph:
    """金融专业知识图谱"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化金融知识图谱
        
        参数:
            config: 配置参数，包含:
                - data_path: 知识图谱数据路径
                - entity_types: 实体类型列表
                - relation_types: 关系类型列表
                - embedding_dim: 嵌入维度
        """
        self.config = config or {}
        self.data_path = self.config.get('data_path', os.path.join('/data/qlib', 'knowledge_graph'))
        self.entity_types = self.config.get('entity_types', ['factor', 'industry', 'concept', 'metric'])
        self.relation_types = self.config.get('relation_types', ['belongs_to', 'correlates_with', 'derives_from', 'influences'])
        self.embedding_dim = self.config.get('embedding_dim', 128)
        
        # 初始化图谱
        self.graph = nx.DiGraph()
        self.entity_embeddings = {}
        self.relation_embeddings = {}
        
        # 加载知识图谱
        self._load_graph()
        
        logger.info(f"金融知识图谱初始化完成，包含 {len(self.graph.nodes)} 个节点和 {len(self.graph.edges)} 条边")
    
    def _load_graph(self) -> None:
        """加载知识图谱数据"""
        try:
            # 检查知识图谱文件是否存在
            graph_file = os.path.join(self.data_path, 'financial_knowledge_graph.json')
            embeddings_file = os.path.join(self.data_path, 'knowledge_embeddings.npz')
            
            if os.path.exists(graph_file):
                with open(graph_file, 'r', encoding='utf-8') as f:
                    graph_data = json.load(f)
                    self.graph = json_graph.node_link_graph(graph_data)
                logger.info(f"从 {graph_file} 加载知识图谱成功")
            else:
                logger.warning(f"知识图谱文件 {graph_file} 不存在，将初始化空图谱")
                self._initialize_base_graph()
            
            # 加载嵌入
            if os.path.exists(embeddings_file):
                embeddings = np.load(embeddings_file)
                self.entity_embeddings = {entity: embeddings['entity_embeddings'][i] 
                                         for i, entity in enumerate(embeddings['entity_ids'])}
                self.relation_embeddings = {relation: embeddings['relation_embeddings'][i] 
                                           for i, relation in enumerate(embeddings['relation_ids'])}
                logger.info(f"从 {embeddings_file} 加载知识嵌入成功")
            else:
                logger.warning(f"知识嵌入文件 {embeddings_file} 不存在")
        
        except Exception as e:
            logger.error(f"加载知识图谱失败: {e}")
            # 如果加载失败，初始化基础图谱
            self._initialize_base_graph()
    
    def _initialize_base_graph(self) -> None:
        """初始化基础知识图谱"""
        logger.info("初始化基础知识图谱")
        
        # 添加基础金融领域节点
        base_entities = {
            'factor': ['momentum', 'value', 'size', 'volatility', 'quality', 'growth', 'dividend', 'liquidity'],
            'industry': ['technology', 'finance', 'healthcare', 'consumer', 'energy', 'materials', 'utilities', 'real_estate'],
            'concept': ['esg', 'ai', 'blockchain', 'renewable_energy', 'e-commerce', 'cloud_computing'],
            'metric': ['pe_ratio', 'pb_ratio', 'roe', 'roa', 'eps', 'revenue_growth', 'net_profit_margin']
        }
        
        # 添加节点
        for entity_type, entities in base_entities.items():
            for entity in entities:
                self.add_entity(entity, entity_type)
        
        # 添加基础关系
        base_relations = [
            ('momentum', 'correlates_with', 'volatility'),
            ('value', 'correlates_with', 'quality'),
            ('size', 'correlates_with', 'liquidity'),
            ('pe_ratio', 'belongs_to', 'value'),
            ('pb_ratio', 'belongs_to', 'value'),
            ('roe', 'belongs_to', 'quality'),
            ('roa', 'belongs_to', 'quality'),
            ('eps', 'belongs_to', 'growth'),
            ('revenue_growth', 'belongs_to', 'growth'),
            ('technology', 'influences', 'ai'),
            ('technology', 'influences', 'cloud_computing'),
            ('finance', 'influences', 'blockchain'),
            ('energy', 'influences', 'renewable_energy'),
            ('esg', 'influences', 'quality'),
            ('value', 'derives_from', 'pe_ratio'),
            ('value', 'derives_from', 'pb_ratio')
        ]
        
        for source, relation, target in base_relations:
            self.add_relation(source, target, relation)
        
        # 初始化随机嵌入
        np.random.seed(42)
        for node in self.graph.nodes:
            self.entity_embeddings[node] = np.random.randn(self.embedding_dim).astype(np.float32)
        
        for relation in self.relation_types:
            self.relation_embeddings[relation] = np.random.randn(self.embedding_dim).astype(np.float32)
        
        logger.info(f"基础知识图谱初始化完成，包含 {len(self.graph.nodes)} 个节点和 {len(self.graph.edges)} 条边")
    
    def save_graph(self) -> None:
        """保存知识图谱到文件"""
        try:
            # 确保目录存在
            os.makedirs(self.data_path, exist_ok=True)
            
            # 保存图结构
            graph_file = os.path.join(self.data_path, 'financial_knowledge_graph.json')
            graph_data = json_graph.node_link_data(self.graph)
            with open(graph_file, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, ensure_ascii=False, indent=2)
            
            # 保存嵌入
            embeddings_file = os.path.join(self.data_path, 'knowledge_embeddings.npz')
            entity_ids = list(self.entity_embeddings.keys())
            entity_embs = np.array([self.entity_embeddings[eid] for eid in entity_ids])
            
            relation_ids = list(self.relation_embeddings.keys())
            relation_embs = np.array([self.relation_embeddings[rid] for rid in relation_ids])
            
            np.savez(embeddings_file, 
                    entity_ids=entity_ids, 
                    entity_embeddings=entity_embs,
                    relation_ids=relation_ids,
                    relation_embeddings=relation_embs)
            
            logger.info(f"知识图谱和嵌入保存成功: {graph_file}, {embeddings_file}")
        
        except Exception as e:
            logger.error(f"保存知识图谱失败: {e}")
    
    def add_entity(self, entity_id: str, entity_type: str, attributes: Dict[str, Any] = None) -> bool:
        """
        添加实体节点
        
        参数:
            entity_id: 实体ID
            entity_type: 实体类型
            attributes: 实体属性
        
        返回:
            添加是否成功
        """
        if entity_id in self.graph:
            logger.warning(f"实体 {entity_id} 已存在，将更新属性")
            
            # 更新属性
            for key, value in (attributes or {}).items():
                self.graph.nodes[entity_id][key] = value
            
            # 确保类型属性存在
            self.graph.nodes[entity_id]['type'] = entity_type
            
            return False
        
        # 添加新节点
        self.graph.add_node(entity_id, type=entity_type, **(attributes or {}))
        
        # 生成嵌入
        if entity_id not in self.entity_embeddings:
            self.entity_embeddings[entity_id] = np.random.randn(self.embedding_dim).astype(np.float32)
        
        return True
    
    def add_relation(self, source_id: str, target_id: str, relation_type: str, 
                    weight: float = 1.0, attributes: Dict[str, Any] = None) -> bool:
        """
        添加关系边
        
        参数:
            source_id: 源实体ID
            target_id: 目标实体ID
            relation_type: 关系类型
            weight: 关系权重
            attributes: 关系属性
        
        返回:
            添加是否成功
        """
        if source_id not in self.graph:
            logger.warning(f"源实体 {source_id} 不存在")
            return False
        
        if target_id not in self.graph:
            logger.warning(f"目标实体 {target_id} 不存在")
            return False
        
        # 检查边是否已存在
        if self.graph.has_edge(source_id, target_id):
            # 更新边属性
            for key, value in (attributes or {}).items():
                self.graph[source_id][target_id][key] = value
            
            # 更新关系类型和权重
            self.graph[source_id][target_id]['type'] = relation_type
            self.graph[source_id][target_id]['weight'] = weight
            
            logger.info(f"更新关系: {source_id} --{relation_type}--> {target_id}")
            return False
        
        # 添加新边
        self.graph.add_edge(source_id, target_id, type=relation_type, weight=weight, **(attributes or {}))
        logger.info(f"添加关系: {source_id} --{relation_type}--> {target_id}")
        
        # 确保关系类型嵌入存在
        if relation_type not in self.relation_embeddings:
            self.relation_embeddings[relation_type] = np.random.randn(self.embedding_dim).astype(np.float32)
        
        return True
    
    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        获取实体信息
        
        参数:
            entity_id: 实体ID
        
        返回:
            实体信息字典
        """
        if entity_id not in self.graph:
            logger.warning(f"实体 {entity_id} 不存在")
            return None
        
        entity_data = dict(self.graph.nodes[entity_id])
        
        # 添加相邻节点信息
        entity_data['relations'] = []
        
        # 出边关系
        for _, target, data in self.graph.out_edges(entity_id, data=True):
            entity_data['relations'].append({
                'source': entity_id,
                'target': target,
                'type': data.get('type', 'unknown'),
                'weight': data.get('weight', 1.0),
                'direction': 'outgoing'
            })
        
        # 入边关系
        for source, _, data in self.graph.in_edges(entity_id, data=True):
            entity_data['relations'].append({
                'source': source,
                'target': entity_id,
                'type': data.get('type', 'unknown'),
                'weight': data.get('weight', 1.0),
                'direction': 'incoming'
            })
        
        return entity_data
    
    def search_entities(self, query: str, entity_type: Optional[str] = None, 
                       limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索实体
        
        参数:
            query: 搜索关键词
            entity_type: 可选的实体类型筛选
            limit: 结果数量限制
        
        返回:
            实体列表
        """
        results = []
        query = query.lower()
        
        for node, data in self.graph.nodes(data=True):
            # 检查节点ID或标签是否包含查询词
            node_matches = query in node.lower()
            
            # 检查实体类型是否匹配
            type_matches = entity_type is None or data.get('type') == entity_type
            
            if node_matches and type_matches:
                entity_data = self.get_entity(node)
                if entity_data:
                    results.append(entity_data)
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_entity_embedding(self, entity_id: str) -> Optional[np.ndarray]:
        """
        获取实体嵌入向量
        
        参数:
            entity_id: 实体ID
        
        返回:
            嵌入向量
        """
        if entity_id not in self.entity_embeddings:
            logger.warning(f"实体 {entity_id} 的嵌入不存在")
            return None
        
        return self.entity_embeddings[entity_id]
    
    def get_related_entities(self, entity_id: str, relation_type: Optional[str] = None, 
                            max_depth: int = 1) -> List[Dict[str, Any]]:
        """
        获取相关实体
        
        参数:
            entity_id: 起始实体ID
            relation_type: 可选的关系类型筛选
            max_depth: 关系深度限制
        
        返回:
            相关实体列表
        """
        if entity_id not in self.graph:
            logger.warning(f"实体 {entity_id} 不存在")
            return []
        
        # 使用BFS找出所有相关节点
        visited = set([entity_id])
        queue = [(entity_id, 0)]  # (node, depth)
        related_entities = []
        
        while queue:
            node, depth = queue.pop(0)
            
            if depth > max_depth:
                continue
            
            # 处理出边
            for _, target, data in self.graph.out_edges(node, data=True):
                edge_type = data.get('type')
                
                # 检查关系类型是否匹配
                if relation_type is None or edge_type == relation_type:
                    if target not in visited:
                        visited.add(target)
                        queue.append((target, depth + 1))
                        
                        # 添加到结果
                        entity_data = self.get_entity(target)
                        entity_data['relation_path'] = [(node, edge_type, target)]
                        entity_data['distance'] = depth + 1
                        related_entities.append(entity_data)
            
            # 处理入边
            for source, _, data in self.graph.in_edges(node, data=True):
                edge_type = data.get('type')
                
                # 检查关系类型是否匹配
                if relation_type is None or edge_type == relation_type:
                    if source not in visited:
                        visited.add(source)
                        queue.append((source, depth + 1))
                        
                        # 添加到结果
                        entity_data = self.get_entity(source)
                        entity_data['relation_path'] = [(source, edge_type, node)]
                        entity_data['distance'] = depth + 1
                        related_entities.append(entity_data)
        
        return related_entities
    
    def export_graph_data(self) -> Dict[str, Any]:
        """
        导出知识图谱数据用于前端可视化
        
        返回:
            图谱数据字典，包含节点和边
        """
        nodes = []
        links = []
        
        # 导出节点
        for node, data in self.graph.nodes(data=True):
            node_type = data.get('type', 'unknown')
            nodes.append({
                'id': node,
                'name': node.replace('_', ' ').title(),
                'category': node_type,
                'value': len(list(self.graph.neighbors(node)))
            })
        
        # 导出边
        for source, target, data in self.graph.edges(data=True):
            links.append({
                'source': source,
                'target': target,
                'relation': data.get('type', 'related_to'),
                'weight': data.get('weight', 1.0)
            })
        
        return {'nodes': nodes, 'links': links}
    
    def import_from_dataframe(self, df: pd.DataFrame, source_col: str, target_col: str, 
                             relation_col: str, entity_type_mapping: Dict[str, str]) -> int:
        """
        从DataFrame导入知识图谱数据
        
        参数:
            df: 包含图谱数据的DataFrame
            source_col: 源实体列名
            target_col: 目标实体列名
            relation_col: 关系类型列名
            entity_type_mapping: 实体类型映射函数或字典
        
        返回:
            导入的关系数量
        """
        count = 0
        
        for _, row in tqdm(df.iterrows(), total=len(df), desc="导入知识图谱"):
            source = str(row[source_col])
            target = str(row[target_col])
            relation = str(row[relation_col])
            
            # 确定实体类型
            source_type = entity_type_mapping.get(source, 'unknown')
            target_type = entity_type_mapping.get(target, 'unknown')
            
            # 添加实体
            self.add_entity(source, source_type)
            self.add_entity(target, target_type)
            
            # 添加关系
            success = self.add_relation(source, target, relation)
            if success:
                count += 1
        
        logger.info(f"从DataFrame导入了 {count} 条关系")
        return count
    
    def find_path(self, source_id: str, target_id: str, max_length: int = 3) -> List[List[Tuple[str, str, str]]]:
        """
        查找两个实体之间的路径
        
        参数:
            source_id: 源实体ID
            target_id: 目标实体ID
            max_length: 最大路径长度
        
        返回:
            路径列表，每个路径是一个三元组列表 [(source, relation, target), ...]
        """
        if source_id not in self.graph:
            logger.warning(f"源实体 {source_id} 不存在")
            return []
        
        if target_id not in self.graph:
            logger.warning(f"目标实体 {target_id} 不存在")
            return []
        
        # 尝试找到所有简单路径
        try:
            simple_paths = list(nx.all_simple_paths(self.graph, source_id, target_id, cutoff=max_length))
        except nx.NetworkXNoPath:
            return []
        
        # 将路径转换为三元组列表
        path_triplets = []
        for path in simple_paths:
            triplets = []
            for i in range(len(path) - 1):
                source = path[i]
                target = path[i + 1]
                relation = self.graph[source][target].get('type', 'related_to')
                triplets.append((source, relation, target))
            path_triplets.append(triplets)
        
        return path_triplets
