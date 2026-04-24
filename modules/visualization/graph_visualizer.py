#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识图谱可视化模块
整合知识图谱和技法图谱的可视化功能

功能:
    - 知识图谱可视化 (实体关系网络)
    - 技法图谱可视化 (维度-技法组织)
    - 支持多种输出格式 (HTML、JSON、PNG)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict

try:
    from qdrant_client import QdrantClient
except ImportError:
    QdrantClient = None

# [N14 2026-04-18] 改为 core 包内的 config_loader,删除对 .vectorstore 的 sys.path 注入
try:
    import sys

    _project_root = Path(__file__).parent.parent.parent
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))
    from core.config_loader import get_project_root, get_qdrant_url
except ImportError:
    import os

    # 兼容独立运行场景
    def get_project_root():
        return Path.cwd()

    def get_qdrant_url():
        return os.environ.get("QDRANT_URL", "http://localhost:6333")


# ============================================================
# 配置与常量
# ============================================================

# 实体类型颜色
TYPE_COLORS = {
    "角色": "#FF6B6B",
    "势力": "#4DABF7",
    "事件": "#69DB7C",
    "时代": "#FFD43B",
    "力量体系": "#A9E34B",
    "力量派别": "#A9E34B",
    "派系": "#74C0FC",
}

# 关系类型颜色
RELATION_COLORS = {
    "爱慕": "#FF6B6B",
    "执念": "#E64980",
    "三角关系": "#FFA94D",
    "杀死": "#E03131",
    "敌对": "#212529",
    "被入侵": "#868E96",
    "背叛": "#F783AC",
    "属于势力": "#74C0FC",
    "使用力量": "#A9E34B",
    "使用力量体系": "#A9E34B",
    "发生在": "#FFD43B",
    "涉及": "#69DB7C",
    "涉及势力": "#4DABF7",
    "主要势力": "#339AF0",
    "交易": "#20C997",
    "暗中交易": "#66D9E8",
    "技术输出": "#63E6BE",
    "之后是": "#CED4DA",
    "专修派别": "#95E1D3",
    "核心力量体系": "#A9E34B",
}

# 核心11维度定义
CORE_DIMENSIONS = {
    "世界观": {"writer": "苍澜", "color": "#FF6B6B", "icon": "🌍"},
    "剧情": {"writer": "玄一", "color": "#4ECDC4", "icon": "📖"},
    "人物": {"writer": "墨言", "color": "#95E1D3", "icon": "👤"},
    "战斗": {"writer": "剑尘", "color": "#F38181", "icon": "⚔️"},
    "氛围": {"writer": "云溪", "color": "#AA96DA", "icon": "🌙"},
    "叙事": {"writer": "玄一", "color": "#FCBAD3", "icon": "📝"},
    "主题": {"writer": "玄一", "color": "#FFE5B4", "icon": "💡"},
    "情感": {"writer": "墨言", "color": "#FF9A8B", "icon": "❤️"},
    "读者体验": {"writer": "云溪", "color": "#A8D8EA", "icon": "👁️"},
    "元维度": {"writer": "全部", "color": "#CCCCCC", "icon": "🔮"},
    "节奏": {"writer": "玄一", "color": "#B8E0D2", "icon": "⏱️"},
}

# 非核心维度
NON_CORE_DIMENSIONS = {
    "外部资源": {"writer": "玄一", "color": "#6C7A89", "icon": "📚"},
    "创作模板": {"writer": "玄一", "color": "#95A5A6", "icon": "📋"},
    "实战案例": {"writer": "玄一", "color": "#7F8C8D", "icon": "📝"},
    "未知": {"writer": "全部", "color": "#5D6D7E", "icon": "❓"},
}

# 作家定义
WRITERS = {
    "苍澜": {"role": "世界观架构师", "color": "#FF6B6B"},
    "玄一": {"role": "剧情编织师", "color": "#4ECDC4"},
    "墨言": {"role": "人物刻画师", "color": "#95E1D3"},
    "剑尘": {"role": "战斗设计师", "color": "#F38181"},
    "云溪": {"role": "意境营造师", "color": "#AA96DA"},
}


# ============================================================
# 数据结构
# ============================================================


@dataclass
class Entity:
    """实体"""

    id: str
    名称: str
    类型: str
    属性: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Relation:
    """关系"""

    源实体: str
    关系类型: str
    目标实体: str
    属性: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Technique:
    """技法"""

    id: str
    name: str
    dimension: str
    writer: str = ""
    content: str = ""
    tags: List[str] = field(default_factory=list)
    is_core: bool = True


# ============================================================
# 可视化类
# ============================================================


class GraphVisualizer:
    """知识图谱可视化器

    支持功能:
        - 知识图谱可视化 (实体-关系网络)
        - 技法图谱可视化 (维度-技法组织)
        - 从 Qdrant 数据库读取数据
        - 生成交互式 HTML 页面
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        初始化

        Args:
            project_root: 项目根目录，默认从配置自动获取
        """
        self.project_root = project_root or get_project_root()
        self.vectorstore_dir = self.project_root / ".vectorstore"
        self.qdrant_client = None

    def _connect_qdrant(self) -> Optional[Any]:
        """连接 Qdrant 数据库"""
        if QdrantClient is None:
            print("警告: qdrant_client 未安装，无法连接数据库")
            return None

        # 从配置获取 URL
        qdrant_url = get_qdrant_url()

        # 尝试 Docker 连接
        try:
            client = QdrantClient(url=qdrant_url)
            client.get_collections()
            print(f"连接: Qdrant ({qdrant_url})")
            return client
        except Exception as e:
            print(f"Docker 连接失败: {e}")

        # 回退到本地文件
        qdrant_dir = self.vectorstore_dir / "qdrant"
        if qdrant_dir.exists():
            client = QdrantClient(path=str(qdrant_dir))
            print(f"连接: 本地文件 {qdrant_dir}")
            return client

        print("无法连接到 Qdrant 数据库")
        return None

    def load_knowledge_graph_data(self) -> Dict[str, Any]:
        """
        加载知识图谱数据

        Returns:
            包含实体和关系的字典
        """
        client = self._connect_qdrant()
        if client is None:
            return {"实体": {}, "关系": []}

        # 读取实体
        print("读取: novel_settings collection...")
        points = client.scroll(
            collection_name="novel_settings",
            limit=1000,
            with_payload=True,
            with_vectors=False,
        )[0]

        entities = {}
        for point in points:
            payload = point.payload
            entity_id = payload.get("name", str(point.id))
            entity_type = payload.get("type", "未知")

            # 解析属性
            properties_str = payload.get("properties", "{}")
            try:
                props = (
                    json.loads(properties_str)
                    if isinstance(properties_str, str)
                    else properties_str
                )
            except:
                props = {}

            name = (
                props.get("名称", "")
                or props.get("属性", {}).get("名称", "")
                or payload.get("type", "")
                or entity_id
            )

            entities[entity_id] = {"类型": entity_type, "名称": name, "属性": props}

        print(f"实体: {len(entities)} 条")

        # 从 JSON 文件读取关系
        graph_file = self.vectorstore_dir / "knowledge_graph.json"
        relations = []

        if graph_file.exists():
            with open(graph_file, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            json_relations = json_data.get("关系", [])

            # 构建名称到 ID 的映射
            name_to_id = {
                e.get("名称", ""): eid for eid, e in entities.items() if e.get("名称")
            }

            # 转换关系
            for rel in json_relations:
                source_name = rel.get("源实体", "")
                target_name = rel.get("目标实体", "")
                rel_type = rel.get("关系类型", "")

                if source_name in name_to_id and target_name in name_to_id:
                    relations.append(
                        {
                            "源实体": name_to_id[source_name],
                            "源实体名称": source_name,
                            "目标实体": name_to_id[target_name],
                            "目标实体名称": target_name,
                            "关系类型": rel_type,
                        }
                    )

            print(f"关系: {len(relations)} 条")

        return {"实体": entities, "关系": relations}

    def load_technique_data(self) -> List[Dict[str, Any]]:
        """
        加载技法数据

        Returns:
            技法列表
        """
        client = self._connect_qdrant()
        if client is None:
            return []

        print("读取: writing_techniques collection...")
        points = client.scroll(
            collection_name="writing_techniques", limit=2000, with_payload=True
        )[0]

        # 维度名称映射
        dim_map = {
            "世界观维度": "世界观",
            "剧情维度": "剧情",
            "人物维度": "人物",
            "战斗冲突维度": "战斗",
            "氛围意境维度": "氛围",
            "叙事维度": "叙事",
            "主题维度": "主题",
            "情感维度": "情感",
            "读者体验维度": "读者体验",
            "元维度": "元维度",
            "节奏维度": "节奏",
            "外部资源": "外部资源",
            "创作模板": "创作模板",
            "实战案例": "实战案例",
        }

        techniques = []
        for p in points:
            payload = p.payload

            dim = payload.get("dimension", "未知")
            dim = dim_map.get(dim, dim)

            name = payload.get("name", "") or payload.get("title", "") or f"技法{p.id}"
            content = payload.get("content", "") or payload.get("description", "")
            writer = payload.get("writer", "")

            tags = payload.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]

            is_core = dim in CORE_DIMENSIONS

            techniques.append(
                {
                    "id": str(p.id),
                    "name": name,
                    "dimension": dim,
                    "writer": writer,
                    "content": content,
                    "tags": tags,
                    "isCore": is_core,
                }
            )

        print(f"技法: {len(techniques)} 条")
        return techniques

    def generate_knowledge_graph_html(
        self, data: Optional[Dict] = None, output: Optional[Path] = None
    ) -> str:
        """
        生成知识图谱 HTML

        Args:
            data: 图谱数据，默认从数据库加载
            output: 输出文件路径

        Returns:
            HTML 内容
        """
        if data is None:
            data = self.load_knowledge_graph_data()

        entities = data.get("实体", {})
        relations = data.get("关系", [])

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 构建实体列表
        entity_list = []
        for eid, e in entities.items():
            name = e.get("名称", eid)
            etype = e.get("类型", "未知")
            attrs = e.get("属性", {})

            entity_list.append(
                {
                    "id": eid,
                    "name": name,
                    "type": etype,
                    "color": TYPE_COLORS.get(etype, "#ADB5BD"),
                    "attrs": attrs,
                }
            )

        # 构建关系列表
        relation_list = []
        seen_relations = set()

        for rel in relations:
            source_id = rel.get("源实体", "")
            target_id = rel.get("目标实体", "")
            rel_type = rel.get("关系类型", "")

            rel_key = f"{source_id}|{target_id}|{rel_type}"
            if rel_key in seen_relations:
                continue
            seen_relations.add(rel_key)

            source_name = rel.get("源实体名称", "")
            target_name = rel.get("目标实体名称", "")

            if not source_name and source_id in entities:
                source_name = entities[source_id].get("名称", source_id)
            if not target_name and target_id in entities:
                target_name = entities[target_id].get("名称", target_id)

            if source_id and target_id:
                relation_list.append(
                    {
                        "source": source_id,
                        "sourceName": source_name,
                        "target": target_id,
                        "targetName": target_name,
                        "type": rel_type,
                        "color": RELATION_COLORS.get(rel_type, "#ADB5BD"),
                    }
                )

        print(f"\n生成HTML: 实体 {len(entity_list)} | 关系 {len(relation_list)}")

        html = self._render_knowledge_graph_html(entity_list, relation_list, timestamp)

        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"保存: {output}")

        return html

    def generate_technique_graph_html(
        self, techniques: Optional[List] = None, output: Optional[Path] = None
    ) -> str:
        """
        生成技法图谱 HTML

        Args:
            techniques: 技法数据，默认从数据库加载
            output: 输出文件路径

        Returns:
            HTML 内容
        """
        if techniques is None:
            techniques = self.load_technique_data()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 按维度组织
        techniques_by_dimension = {}
        for t in techniques:
            dim = t["dimension"]
            if dim not in techniques_by_dimension:
                techniques_by_dimension[dim] = []
            techniques_by_dimension[dim].append(t)

        # 按作家组织
        techniques_by_writer = {}
        for t in techniques:
            writer = t.get("writer", "")
            if writer and writer in WRITERS:
                if writer not in techniques_by_writer:
                    techniques_by_writer[writer] = []
                techniques_by_writer[writer].append(t)

        # 统计
        dimension_counts = {
            dim: len(techniques_by_dimension.get(dim, []))
            for dim in techniques_by_dimension
        }
        writer_counts = {
            writer: len(techniques_by_writer.get(writer, []))
            for writer in techniques_by_writer
        }
        core_count = sum(1 for t in techniques if t.get("isCore", False))

        html = self._render_technique_graph_html(
            techniques,
            techniques_by_dimension,
            techniques_by_writer,
            dimension_counts,
            writer_counts,
            core_count,
            timestamp,
        )

        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"保存: {output}")

        return html

    def _render_knowledge_graph_html(
        self, entity_list: List, relation_list: List, timestamp: str
    ) -> str:
        """渲染知识图谱 HTML"""
        # 类型统计
        type_count = {}
        for e in entity_list:
            t = e["type"]
            type_count[t] = type_count.get(t, 0) + 1

        # 筛选按钮
        filter_buttons = (
            '<button class="filter-btn active" data-type="all">全部</button>\n'
        )
        for t in sorted(type_count.keys(), key=lambda x: -type_count[x]):
            filter_buttons += f'                <button class="filter-btn" data-type="{t}">{t}</button>\n'

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <title>众生界知识图谱 - {timestamp}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            height: 100vh;
            overflow: hidden;
        }}
        
        .sidebar {{
            position: fixed;
            left: 0;
            top: 0;
            width: 320px;
            height: 100vh;
            background: #161b22;
            border-right: 1px solid #30363d;
            display: flex;
            flex-direction: column;
            z-index: 100;
        }}
        
        .sidebar-header {{
            padding: 16px;
            border-bottom: 1px solid #30363d;
        }}
        
        .sidebar-header h1 {{
            font-size: 18px;
            margin-bottom: 8px;
        }}
        
        .sidebar-header p {{
            font-size: 12px;
            color: #8b949e;
        }}
        
        .search-box {{
            padding: 12px 16px;
            border-bottom: 1px solid #30363d;
        }}
        
        .search-box input {{
            width: 100%;
            padding: 8px 12px;
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            color: #c9d1d9;
            font-size: 14px;
        }}
        
        .search-box input:focus {{
            outline: none;
            border-color: #58a6ff;
        }}
        
        .type-filter {{
            padding: 12px 16px;
            border-bottom: 1px solid #30363d;
        }}
        
        .type-filter label {{
            display: block;
            font-size: 12px;
            color: #8b949e;
            margin-bottom: 8px;
        }}
        
        .filter-buttons {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}
        
        .filter-btn {{
            padding: 4px 10px;
            background: #21262d;
            border: 1px solid #30363d;
            border-radius: 4px;
            font-size: 12px;
            color: #c9d1d9;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .filter-btn:hover {{
            background: #30363d;
        }}
        
        .filter-btn.active {{
            background: #238636;
            border-color: #238636;
        }}
        
        .entity-list {{
            flex: 1;
            overflow-y: auto;
            padding: 8px;
        }}
        
        .entity-item {{
            display: flex;
            align-items: center;
            padding: 8px 12px;
            margin: 2px 0;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .entity-item:hover {{
            background: #21262d;
        }}
        
        .entity-item.selected {{
            background: #1f6feb33;
            border: 1px solid #1f6feb;
        }}
        
        .entity-color {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 10px;
            flex-shrink: 0;
        }}
        
        .entity-name {{
            font-size: 14px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            flex: 1;
        }}
        
        .entity-type {{
            font-size: 11px;
            color: #8b949e;
            margin-left: 8px;
        }}
        
        .detail-panel {{
            position: fixed;
            right: 0;
            top: 0;
            width: 360px;
            height: 100vh;
            background: #161b22;
            border-left: 1px solid #30363d;
            transform: translateX(100%);
            transition: transform 0.3s;
            z-index: 100;
            overflow-y: auto;
        }}
        
        .detail-panel.show {{
            transform: translateX(0);
        }}
        
        .detail-header {{
            padding: 16px;
            border-bottom: 1px solid #30363d;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .detail-header h2 {{
            font-size: 18px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .close-btn {{
            background: none;
            border: none;
            color: #8b949e;
            font-size: 24px;
            cursor: pointer;
            padding: 4px 8px;
        }}
        
        .close-btn:hover {{
            color: #c9d1d9;
        }}
        
        .detail-section {{
            padding: 16px;
            border-bottom: 1px solid #30363d;
        }}
        
        .detail-section h3 {{
            font-size: 14px;
            color: #8b949e;
            margin-bottom: 12px;
        }}
        
        .attr-item {{
            display: flex;
            font-size: 13px;
            margin: 6px 0;
        }}
        
        .attr-key {{
            color: #8b949e;
            min-width: 100px;
            flex-shrink: 0;
        }}
        
        .attr-value {{
            color: #c9d1d9;
            word-break: break-all;
        }}
        
        .relation-item {{
            display: flex;
            align-items: center;
            padding: 8px 12px;
            margin: 4px 0;
            background: #21262d;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .relation-item:hover {{
            background: #30363d;
        }}
        
        .relation-arrow {{
            margin: 0 8px;
            color: #8b949e;
        }}
        
        .relation-type {{
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 3px;
            background: #30363d;
            margin: 0 8px;
        }}
        
        .relation-entity {{
            color: #58a6ff;
        }}
        
        .graph-container {{
            margin-left: 320px;
            height: 100vh;
            position: relative;
        }}
        
        #graph {{
            width: 100%;
            height: 100%;
        }}
        
        .hint {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #21262d;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 13px;
            color: #8b949e;
            z-index: 50;
        }}
        
        .stats {{
            padding: 12px 16px;
            border-bottom: 1px solid #30363d;
            font-size: 12px;
            color: #8b949e;
        }}
        
        .stats strong {{
            color: #58a6ff;
        }}
        
        .timestamp {{
            padding: 8px 16px;
            font-size: 11px;
            color: #6e7681;
            border-bottom: 1px solid #30363d;
        }}
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <h1>众生界知识图谱</h1>
            <p>点击节点查看详情 | 滚轮缩放 | 拖拽移动</p>
        </div>
        
        <div class="timestamp">生成时间: {timestamp}</div>
        
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="搜索实体名称...">
        </div>
        
        <div class="type-filter">
            <label>类型筛选</label>
            <div class="filter-buttons" id="filterButtons">
                {filter_buttons}
            </div>
        </div>
        
        <div class="stats" id="stats">
            实体: <strong>{len(entity_list)}</strong> | 关系: <strong>{len(relation_list)}</strong>
        </div>
        
        <div class="entity-list" id="entityList"></div>
    </div>
    
    <div class="graph-container">
        <canvas id="graph"></canvas>
    </div>
    
    <div class="detail-panel" id="detailPanel">
        <div class="detail-header">
            <h2 id="detailTitle">
                <span class="entity-color" id="detailColor"></span>
                <span id="detailName">实体名称</span>
            </h2>
            <button class="close-btn" onclick="closeDetail()">&times;</button>
        </div>
        
        <div class="detail-section">
            <h3>基本信息</h3>
            <div id="detailAttrs"></div>
        </div>
        
        <div class="detail-section">
            <h3>关系 (<span id="relationCount">0</span>)</h3>
            <div id="detailRelations"></div>
        </div>
    </div>
    
    <div class="hint">点击左侧实体查看详情 | 滚轮缩放 | 拖拽移动</div>

    <script>
        const entities = {json.dumps(entity_list, ensure_ascii=False)};
        const relations = {json.dumps(relation_list, ensure_ascii=False)};
        
        const idToName = {{}};
        entities.forEach(e => {{ idToName[e.id] = e.name; }});
        
        // 构建实体关系索引
        const entityRelations = {{}};
        relations.forEach(r => {{
            if (!entityRelations[r.source]) entityRelations[r.source] = [];
            if (!entityRelations[r.target]) entityRelations[r.target] = [];
            
            entityRelations[r.source].push({{
                direction: 'out',
                entity: r.target,
                entityName: r.targetName,
                type: r.type,
                color: r.color
            }});
            
            entityRelations[r.target].push({{
                direction: 'in',
                entity: r.source,
                entityName: r.sourceName,
                type: r.type,
                color: r.color
            }});
        }});
        
        const canvas = document.getElementById('graph');
        const ctx = canvas.getContext('2d');
        
        let width, height;
        let nodes = [];
        let selectedNode = null;
        let hoveredNode = null;
        
        let scale = 1;
        let offsetX = 0;
        let offsetY = 0;
        let isDragging = false;
        let lastMouseX = 0;
        let lastMouseY = 0;
        
        let currentType = 'all';
        let searchQuery = '';
        
        function init() {{
            resize();
            initNodes();
            renderEntityList();
            bindEvents();
            animate();
        }}
        
        function resize() {{
            const container = canvas.parentElement;
            width = container.clientWidth;
            height = container.clientHeight;
            canvas.width = width * 2;
            canvas.height = height * 2;
            canvas.style.width = width + 'px';
            canvas.style.height = height + 'px';
            ctx.scale(2, 2);
        }}
        
        function initNodes() {{
            nodes = entities.map((e, i) => {{
                const angle = (i / entities.length) * Math.PI * 2;
                const radius = Math.min(width, height) * 0.35;
                return {{
                    ...e,
                    x: width / 2 + Math.cos(angle) * radius,
                    y: height / 2 + Math.sin(angle) * radius,
                    vx: 0,
                    vy: 0,
                    radius: 14
                }};
            }});
        }}
        
        function renderEntityList() {{
            const list = document.getElementById('entityList');
            const filtered = entities.filter(e => {{
                if (currentType !== 'all' && e.type !== currentType) return false;
                if (searchQuery && !e.name.includes(searchQuery)) return false;
                return true;
            }});
            
            list.innerHTML = filtered.map(e => `
                <div class="entity-item ${{selectedNode && selectedNode.id === e.id ? 'selected' : ''}}" 
                     data-id="${{e.id}}" onclick="selectEntity('${{e.id}}')">
                    <div class="entity-color" style="background: ${{e.color}}"></div>
                    <span class="entity-name">${{e.name}}</span>
                    <span class="entity-type">${{e.type}}</span>
                </div>
            `).join('');
        }}
        
        function selectEntity(id) {{
            const node = nodes.find(n => n.id === id);
            if (node) {{
                selectedNode = node;
                showDetail(node);
                renderEntityList();
            }}
        }}
        
        function showDetail(node) {{
            document.getElementById('detailPanel').classList.add('show');
            document.getElementById('detailName').textContent = node.name;
            document.getElementById('detailColor').style.background = node.color;
            
            // 属性
            let attrsHtml = '';
            if (node.attrs) {{
                for (const [k, v] of Object.entries(node.attrs)) {{
                    if (v && k !== '内容长度') {{
                        let displayVal = v;
                        if (Array.isArray(v)) {{
                            displayVal = v.join(', ');
                        }} else if (typeof v === 'object') {{
                            displayVal = JSON.stringify(v, null, 2);
                        }}
                        attrsHtml += `<div class="attr-item"><span class="attr-key">${{k}}</span><span class="attr-value">${{displayVal}}</span></div>`;
                    }}
                }}
            }}
            document.getElementById('detailAttrs').innerHTML = attrsHtml || '<div class="attr-item"><span class="attr-value">-</span></div>';
            
            // 关系
            const rels = entityRelations[node.id] || [];
            document.getElementById('relationCount').textContent = rels.length;
            
            let relsHtml = '';
            rels.forEach(r => {{
                const arrow = r.direction === 'out' ? '→' : '←';
                relsHtml += `
                    <div class="relation-item" onclick="selectEntity('${{r.entity}}')">
                        <span class="relation-entity">${{r.direction === 'out' ? node.name : r.entityName}}</span>
                        <span class="relation-arrow">${{arrow}}</span>
                        <span class="relation-type" style="background: ${{r.color}}22; color: ${{r.color}}">${{r.type}}</span>
                        <span class="relation-arrow">${{arrow}}</span>
                        <span class="relation-entity">${{r.direction === 'out' ? r.entityName : node.name}}</span>
                    </div>
                `;
            }});
            document.getElementById('detailRelations').innerHTML = relsHtml || '<div class="attr-item"><span class="attr-value">无关系</span></div>';
        }}
        
        function closeDetail() {{
            document.getElementById('detailPanel').classList.remove('show');
            selectedNode = null;
            renderEntityList();
        }}
        
        function bindEvents() {{
            document.getElementById('searchInput').addEventListener('input', (e) => {{
                searchQuery = e.target.value;
                renderEntityList();
            }});
            
            document.querySelectorAll('.filter-btn').forEach(btn => {{
                btn.addEventListener('click', () => {{
                    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    currentType = btn.dataset.type;
                    renderEntityList();
                }});
            }});
            
            canvas.addEventListener('mousedown', onMouseDown);
            canvas.addEventListener('mousemove', onMouseMove);
            canvas.addEventListener('mouseup', onMouseUp);
            canvas.addEventListener('wheel', onWheel);
            
            window.addEventListener('resize', () => {{
                resize();
                initNodes();
            }});
        }}
        
        function onMouseDown(e) {{
            const rect = canvas.getBoundingClientRect();
            const x = (e.clientX - rect.left - offsetX) / scale;
            const y = (e.clientY - rect.top - offsetY) / scale;
            
            for (const node of nodes) {{
                const dx = x - node.x;
                const dy = y - node.y;
                if (dx * dx + dy * dy < node.radius * node.radius) {{
                    selectEntity(node.id);
                    return;
                }}
            }}
            
            isDragging = true;
            lastMouseX = e.clientX;
            lastMouseY = e.clientY;
        }}
        
        function onMouseMove(e) {{
            if (isDragging) {{
                offsetX += e.clientX - lastMouseX;
                offsetY += e.clientY - lastMouseY;
                lastMouseX = e.clientX;
                lastMouseY = e.clientY;
            }} else {{
                const rect = canvas.getBoundingClientRect();
                const x = (e.clientX - rect.left - offsetX) / scale;
                const y = (e.clientY - rect.top - offsetY) / scale;
                
                hoveredNode = null;
                for (const node of nodes) {{
                    const dx = x - node.x;
                    const dy = y - node.y;
                    if (dx * dx + dy * dy < node.radius * node.radius) {{
                        hoveredNode = node;
                        canvas.style.cursor = 'pointer';
                        break;
                    }}
                }}
                if (!hoveredNode) {{
                    canvas.style.cursor = 'grab';
                }}
            }}
        }}
        
        function onMouseUp() {{
            isDragging = false;
        }}
        
        function onWheel(e) {{
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            scale *= delta;
            scale = Math.max(0.3, Math.min(3, scale));
        }}
        
        function animate() {{
            update();
            draw();
            requestAnimationFrame(animate);
        }}
        
        function update() {{
            const centerX = width / 2;
            const centerY = height / 2;
            
            nodes.forEach(node => {{
                node.vx += (centerX - node.x) * 0.0001;
                node.vy += (centerY - node.y) * 0.0001;
                
                nodes.forEach(other => {{
                    if (node.id !== other.id) {{
                        const dx = node.x - other.x;
                        const dy = node.y - other.y;
                        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                        if (dist < 100) {{
                            const force = (100 - dist) * 0.01;
                            node.vx += dx / dist * force;
                            node.vy += dy / dist * force;
                        }}
                    }}
                }});
                
                node.x += node.vx;
                node.y += node.vy;
                node.vx *= 0.9;
                node.vy *= 0.9;
            }});
        }}
        
        function draw() {{
            ctx.clearRect(0, 0, width, height);
            ctx.save();
            ctx.translate(offsetX, offsetY);
            ctx.scale(scale, scale);
            
            // 绘制关系线
            relations.forEach(r => {{
                const source = nodes.find(n => n.id === r.source);
                const target = nodes.find(n => n.id === r.target);
                if (!source || !target) return;
                
                ctx.beginPath();
                ctx.moveTo(source.x, source.y);
                ctx.lineTo(target.x, target.y);
                ctx.strokeStyle = r.color + '88';
                ctx.lineWidth = 1.5;
                ctx.stroke();
            }});
            
            // 绘制节点
            nodes.forEach(node => {{
                const isSelected = selectedNode && selectedNode.id === node.id;
                const isHovered = hoveredNode && hoveredNode.id === node.id;
                
                ctx.beginPath();
                ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
                ctx.fillStyle = node.color + (isSelected ? 'ff' : 'cc');
                ctx.fill();
                
                if (isSelected || isHovered) {{
                    ctx.strokeStyle = '#ffffff';
                    ctx.lineWidth = 2;
                    ctx.stroke();
                }}
                
                ctx.font = '12px Microsoft YaHei';
                ctx.fillStyle = '#c9d1d9';
                ctx.textAlign = 'center';
                ctx.fillText(node.name, node.x, node.y + node.radius + 14);
            }});
            
            ctx.restore();
        }}
        
        init();
    </script>
</body>
</html>"""

        return html

    def _render_technique_graph_html(
        self,
        techniques: List,
        techniques_by_dimension: Dict,
        techniques_by_writer: Dict,
        dimension_counts: Dict,
        writer_counts: Dict,
        core_count: int,
        timestamp: str,
    ) -> str:
        """渲染技法图谱 HTML"""

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>创作技法图谱 - {timestamp}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: "Microsoft YaHei", sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            min-height: 100vh;
        }}
        
        .header {{
            background: #161b22;
            border-bottom: 1px solid #30363d;
            padding: 16px 24px;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        
        .header h1 {{
            font-size: 20px;
        }}
        
        .header p {{
            font-size: 13px;
            color: #8b949e;
        }}
        
        .stats-bar {{
            background: #21262d;
            padding: 12px 24px;
            border-bottom: 1px solid #30363d;
            display: flex;
            gap: 24px;
            font-size: 13px;
        }}
        
        .stat-item {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .stat-value {{
            font-weight: bold;
            color: #58a6ff;
        }}
        
        .container {{
            display: flex;
            height: calc(100vh - 100px);
        }}
        
        .sidebar {{
            width: 320px;
            background: #161b22;
            border-right: 1px solid #30363d;
            overflow-y: auto;
        }}
        
        .sidebar-section {{
            padding: 16px;
            border-bottom: 1px solid #30363d;
        }}
        
        .sidebar-section h2 {{
            font-size: 14px;
            color: #8b949e;
            margin-bottom: 12px;
        }}
        
        .search-box {{
            padding: 16px;
            border-bottom: 1px solid #30363d;
        }}
        
        .search-box input {{
            width: 100%;
            padding: 8px 12px;
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            color: #c9d1d9;
        }}
        
        .search-box input:focus {{
            outline: none;
            border-color: #58a6ff;
        }}
        
        .dimension-card {{
            background: #21262d;
            border-radius: 6px;
            padding: 12px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .dimension-card:hover {{
            background: #30363d;
        }}
        
        .dimension-card.active {{
            border: 1px solid #58a6ff;
            background: #1f6feb22;
        }}
        
        .dimension-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .dimension-name {{
            font-size: 14px;
        }}
        
        .dimension-count {{
            font-size: 12px;
            color: #8b949e;
        }}
        
        .dimension-writer {{
            font-size: 12px;
            color: #8b949e;
            margin-top: 4px;
        }}
        
        .main-content {{
            flex: 1;
            overflow-y: auto;
            padding: 24px;
        }}
        
        .technique-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 16px;
        }}
        
        .technique-card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 16px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .technique-card:hover {{
            border-color: #58a6ff;
        }}
        
        .technique-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }}
        
        .technique-name {{
            font-size: 15px;
        }}
        
        .technique-dimension {{
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 4px;
            background: #21262d;
        }}
        
        .technique-content {{
            font-size: 13px;
            color: #8b949e;
            line-height: 1.6;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 3;
        }}
        
        .technique-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            margin-top: 8px;
        }}
        
        .tag {{
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 3px;
            background: #30363d;
            color: #8b949e;
        }}
        
        .technique-writer {{
            font-size: 11px;
            color: #6e7681;
            margin-top: 8px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎨 创作技法图谱</h1>
        <p>共 {len(techniques)} 条技法 | 核心11维度 ({core_count}条) | {len(WRITERS)} 作家 | 生成时间: {timestamp}</p>
    </div>
    
    <div class="stats-bar">
        <div class="stat-item">
            <span>总技法:</span>
            <span class="stat-value">{len(techniques)}</span>
        </div>
        <div class="stat-item">
            <span>核心维度:</span>
            <span class="stat-value">{len(CORE_DIMENSIONS)}</span>
        </div>
        <div class="stat-item">
            <span>作家:</span>
            <span class="stat-value">{len(WRITERS)}</span>
        </div>
    </div>
    
    <div class="container">
        <div class="sidebar">
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="搜索技法...">
            </div>
            
            <div class="sidebar-section">
                <h2>📐 按维度浏览</h2>
                <div id="dimensionList"></div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="technique-list" id="techniqueList"></div>
        </div>
    </div>

    <script>
        const techniques = {json.dumps(techniques, ensure_ascii=False)};
        const dimensions = {json.dumps(CORE_DIMENSIONS, ensure_ascii=False)};
        const nonCoreDimensions = {json.dumps(NON_CORE_DIMENSIONS, ensure_ascii=False)};
        const allDimensions = {{...dimensions, ...nonCoreDimensions}};
        const techniquesByDimension = {json.dumps(techniques_by_dimension, ensure_ascii=False)};
        
        let currentDim = 'all';
        let searchQuery = '';
        
        function init() {{
            renderDimensionList();
            renderTechniqueList(techniques);
            bindEvents();
        }}
        
        function renderDimensionList() {{
            const list = document.getElementById('dimensionList');
            
            let html = `<div class="dimension-card ${{currentDim === 'all' ? 'active' : ''}}" onclick="filterByDimension('all')">
                <div class="dimension-header">
                    <span class="dimension-name">📚 全部技法</span>
                    <span class="dimension-count">${{techniques.length}}</span>
                </div>
            </div>`;
            
            // 核心维度
            for (const [dim, info] of Object.entries(dimensions)) {{
                const count = techniquesByDimension[dim]?.length || 0;
                html += `<div class="dimension-card ${{currentDim === dim ? 'active' : ''}}" onclick="filterByDimension('${{dim}}')">
                    <div class="dimension-header">
                        <span class="dimension-name">${{info.icon}} ${{dim}}</span>
                        <span class="dimension-count">${{count}}</span>
                    </div>
                    <div class="dimension-writer">负责: ${{info.writer}}</div>
                </div>`;
            }}
            
            list.innerHTML = html;
        }}
        
        function renderTechniqueList(techs) {{
            const list = document.getElementById('techniqueList');
            
            let filtered = techs;
            if (searchQuery) {{
                const query = searchQuery.toLowerCase();
                filtered = techs.filter(t => 
                    t.name.toLowerCase().includes(query) || 
                    t.content.toLowerCase().includes(query)
                );
            }}
            
            let html = '';
            for (const t of filtered) {{
                const dimInfo = allDimensions[t.dimension] || {{ color: '#ADB5BD', icon: '' }};
                html += `<div class="technique-card">
                    <div class="technique-header">
                        <span class="technique-name">${{t.name}}</span>
                        <span class="technique-dimension" style="background: ${{dimInfo.color}}22; color: ${{dimInfo.color}}">${{t.dimension}}</span>
                    </div>
                    <div class="technique-content">${{t.content || '暂无详细内容'}}</div>
                    ${{t.tags.length > 0 ? `<div class="technique-tags">${{t.tags.map(tag => `<span class="tag">${{tag}}</span>`).join('')}}</div>` : ''}}
                    ${{t.writer ? `<div class="technique-writer">—— ${{t.writer}}</div>` : ''}}
                </div>`;
            }}
            
            list.innerHTML = html;
        }}
        
        function filterByDimension(dim) {{
            currentDim = dim;
            const techs = dim === 'all' ? techniques : (techniquesByDimension[dim] || []);
            renderTechniqueList(techs);
            renderDimensionList();
        }}
        
        function bindEvents() {{
            document.getElementById('searchInput').addEventListener('input', (e) => {{
                searchQuery = e.target.value;
                const techs = currentDim === 'all' ? techniques : (techniquesByDimension[currentDim] || []);
                renderTechniqueList(techs);
            }});
        }}
        
        init();
    </script>
</body>
</html>"""

        return html


# ============================================================
# 命令行入口
# ============================================================


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="知识图谱可视化")
    parser.add_argument("--knowledge", action="store_true", help="生成知识图谱")
    parser.add_argument("--technique", action="store_true", help="生成技法图谱")
    parser.add_argument("--output", type=str, default="output.html", help="输出文件名")

    args = parser.parse_args()

    viz = GraphVisualizer()

    if args.knowledge:
        output = Path(args.output)
        viz.generate_knowledge_graph_html(output=output)
        print(f"知识图谱已生成: {output}")

    if args.technique:
        output = Path(args.output)
        viz.generate_technique_graph_html(output=output)
        print(f"技法图谱已生成: {output}")

    if not args.knowledge and not args.technique:
        print("请指定 --knowledge 或 --technique")


if __name__ == "__main__":
    main()
