#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识图谱可视化工具 - 从Qdrant数据库生成
直接从向量库读取数据，确保与检索系统一致
"""

import json
from pathlib import Path
from core.config_loader import get_qdrant_url
from typing import Dict, List
from datetime import datetime

# 配置
VECTORSTORE_DIR = Path(__file__).parent
OUTPUT_FILE = VECTORSTORE_DIR / "knowledge_graph.html"
TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 实体类型颜色
TYPE_COLORS = {
    "角色": "#FF6B6B",
    "势力": "#4DABF7",
    "事件": "#69DB7C",
    "时代": "#FFD43B",
    "力量体系": "#A9E34B",
    "力量派别": "#A9E34B",
    "派系": "#74C0FC",
    "技术基础": "#DA77F2",
    "预判模板": "#F59F00",
    "参考数据": "#15AABF",
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
    "属于": "#74C0FC",
    "使用力量": "#A9E34B",
    "使用力量体系": "#A9E34B",
    "发生在": "#FFD43B",
    "涉及": "#69DB7C",
    "涉及势力": "#4DABF7",
    "涉及领域": "#DA77F2",
    "主要势力": "#339AF0",
    "交易": "#20C997",
    "暗中交易": "#66D9E8",
    "技术输出": "#63E6BE",
    "之后是": "#CED4DA",
    "专修派别": "#95E1D3",
    "修炼派别": "#95E1D3",
    "初始修炼派别": "#95E1D3",
    "后续修炼派别": "#95E1D3",
    "核心力量体系": "#A9E34B",
    "属于力量体系": "#A9E34B",
    "来源于": "#F59F00",
    "登场于": "#69DB7C",
    "退场于": "#868E96",
}


def load_from_qdrant() -> Dict:
    """从JSON文件加载知识图谱数据（优先）"""
    json_file = VECTORSTORE_DIR / "knowledge_graph.json"

    # 优先从JSON文件读取
    if json_file.exists():
        print("  读取: knowledge_graph.json")
        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        entities = json_data.get("实体", {})
        relations = json_data.get("关系", [])

        print(f"  实体: {len(entities)} 条")
        print(f"  关系: {len(relations)} 条")

        return {"实体": entities, "关系": relations}

    # 回退到Qdrant
    print("  JSON文件不存在，从Qdrant读取...")
    from qdrant_client import QdrantClient

    try:
        client = QdrantClient(url=get_qdrant_url())
        client.get_collections()
        print("  连接: Docker Qdrant (get_qdrant_url())")
    except Exception as e:
        print(f"  Docker连接失败: {e}")
        QDRANT_DIR = VECTORSTORE_DIR / "qdrant"
        client = QdrantClient(path=str(QDRANT_DIR))
        print(f"  连接: 本地文件 {QDRANT_DIR}")

    print("  读取: novel_settings_v2 collection...")
    points = client.scroll(
        collection_name="novel_settings_v2",
        limit=1000,
        with_payload=True,
        with_vectors=False,
    )[0]

    entities = {}
    entity_count = 0

    for point in points:
        payload = point.payload
        entity_id = payload.get("name", str(point.id))
        entity_type = payload.get("type", "未知")

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
        entity_count += 1

    print(f"  实体: {entity_count} 条")
    print(f"  关系: 0 条")

    return {"实体": entities, "关系": []}


def generate_html(data: Dict) -> str:
    """生成HTML可视化"""
    entities = data.get("实体", {})
    relations = data.get("关系", [])

    # 构建名称到ID的映射
    name_to_id = {}
    for eid, e in entities.items():
        name = e.get("名称", "")
        if name:
            name_to_id[name] = eid

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
    seen_relations = set()  # 去重

    for rel in relations:
        source_name = rel.get("源实体", "")
        target_name = rel.get("目标实体", "")
        rel_type = rel.get("关系类型", "")

        # 通过名称查找ID
        source_id = name_to_id.get(source_name, source_name)
        target_id = name_to_id.get(target_name, target_name)

        # 去重
        rel_key = f"{source_id}|{target_id}|{rel_type}"
        if rel_key in seen_relations:
            continue
        seen_relations.add(rel_key)

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

    print(f"\n生成HTML:")
    print(f"  实体: {len(entity_list)}")
    print(f"  关系: {len(relation_list)}")

    # 生成HTML (使用之前的模板)
    html = generate_html_content(entity_list, relation_list)
    return html


def generate_html_content(entity_list: List, relation_list: List) -> str:
    """生成HTML内容"""
    # 实体类型统计
    type_count = {}
    for e in entity_list:
        t = e["type"]
        type_count[t] = type_count.get(t, 0) + 1

    # 类型筛选按钮
    filter_buttons = '<button class="filter-btn active" data-type="all">全部</button>\n'
    for t in sorted(type_count.keys(), key=lambda x: -type_count[x]):
        filter_buttons += (
            f'                <button class="filter-btn" data-type="{t}">{t}</button>\n'
        )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>众生界知识图谱 - {TIMESTAMP}</title>
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
        
        <div class="timestamp">生成时间: {TIMESTAMP}</div>
        
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
    
    <div class="hint">点击节点高亮相关实体 | 滚轮缩放 | 拖拽移动画布 | ESC或点击关闭按钮取消选中</div>

    <script>
        const entities = {json.dumps(entity_list, ensure_ascii=False)};
        const relations = {json.dumps(relation_list, ensure_ascii=False)};
        
        // 关系类型颜色映射
        const RELATION_COLORS = {{
            "爱慕": "#FF6B6B",
            "执念": "#E64980",
            "三角关系": "#FFA94D",
            "杀死": "#E03131",
            "敌对": "#212529",
            "被入侵": "#868E96",
            "背叛": "#F783AC",
            "属于势力": "#74C0FC",
            "属于": "#74C0FC",
            "使用力量": "#A9E34B",
            "使用力量体系": "#A9E34B",
            "发生在": "#FFD43B",
            "涉及": "#69DB7C",
            "涉及势力": "#4DABF7",
            "涉及领域": "#DA77F2",
            "主要势力": "#339AF0",
            "交易": "#20C997",
            "暗中交易": "#66D9E8",
            "技术输出": "#63E6BE",
            "之后是": "#CED4DA",
            "专修派别": "#95E1D3",
            "修炼派别": "#95E1D3",
            "初始修炼派别": "#95E1D3",
            "后续修炼派别": "#95E1D3",
            "核心力量体系": "#A9E34B",
            "属于力量体系": "#A9E34B",
            "来源于": "#F59F00",
            "登场于": "#69DB7C",
            "退场于": "#868E96",
        }};
        
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
        let isDraggingNode = false;  // ★ 拖动节点
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
                // ★ 点击节点时选中（不自动取消）
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
            
            // 关系 - 按类型分组统计
            const rels = entityRelations[node.id] || [];
            document.getElementById('relationCount').textContent = rels.length;
            
            // 统计关系类型
            const relTypeCounts = {{}};
            rels.forEach(r => {{
                relTypeCounts[r.type] = (relTypeCounts[r.type] || 0) + 1;
            }});
            
            // 生成关系统计摘要
            let summaryHtml = '<div style="margin-bottom: 12px; padding: 8px; background: #21262d; border-radius: 6px;">';
            summaryHtml += '<div style="font-size: 12px; color: #8b949e; margin-bottom: 6px;">关系类型分布</div>';
            for (const [type, count] of Object.entries(relTypeCounts).sort((a, b) => b[1] - a[1])) {{
                const relColor = RELATION_COLORS[type] || '#ADB5BD';
                summaryHtml += `<span style="display: inline-block; margin: 2px 4px 2px 0; padding: 2px 8px; background: ${{relColor}}22; color: ${{relColor}}; border-radius: 4px; font-size: 11px;">${{type}} (${{count}})</span>`;
            }}
            summaryHtml += '</div>';
            
            // 生成关系列表
            let relsHtml = summaryHtml;
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
            
            // ESC键取消选中
            window.addEventListener('keydown', (e) => {{
                if (e.key === 'Escape' && selectedNode) {{
                    closeDetail();
                }}
            }});
            
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
                    // ★ 如果点击的是已选中的节点，开始拖动节点
                    if (selectedNode && selectedNode.id === node.id) {{
                        isDraggingNode = true;
                        canvas.style.cursor = 'grabbing';
                    }} else {{
                        // 否则选中该节点
                        selectEntity(node.id);
                    }}
                    return;
                }}
            }}
            
            // 点击空白区域开始拖动画布（不取消选中）
            isDragging = true;
            lastMouseX = e.clientX;
            lastMouseY = e.clientY;
            canvas.style.cursor = 'grabbing';
        }}
        
        function onMouseMove(e) {{
            if (isDraggingNode && selectedNode) {{
                // ★ 拖动节点
                const rect = canvas.getBoundingClientRect();
                const x = (e.clientX - rect.left - offsetX) / scale;
                const y = (e.clientY - rect.top - offsetY) / scale;
                selectedNode.x = x;
                selectedNode.y = y;
            }} else if (isDragging) {{
                // 拖动画布
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
            isDraggingNode = false;
            canvas.style.cursor = 'grab';
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
                // ★ 正在拖动的节点不受力影响
                if (isDraggingNode && selectedNode && node.id === selectedNode.id) {{
                    return;
                }}
                
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
            
            // ★ 找出选中节点的相关节点和关系
            const relatedNodeIds = new Set();
            const relatedRelations = [];
            
            if (selectedNode) {{
                relations.forEach(r => {{
                    if (r.source === selectedNode.id || r.target === selectedNode.id) {{
                        relatedRelations.push(r);
                        relatedNodeIds.add(r.source);
                        relatedNodeIds.add(r.target);
                    }}
                }});
            }}
            
            // 绘制关系线
            relations.forEach(r => {{
                const source = nodes.find(n => n.id === r.source);
                const target = nodes.find(n => n.id === r.target);
                if (!source || !target) return;
                
                // ★ 判断是否是相关关系
                const isRelated = selectedNode && relatedNodeIds.has(r.source) && relatedNodeIds.has(r.target);
                
                ctx.beginPath();
                ctx.moveTo(source.x, source.y);
                ctx.lineTo(target.x, target.y);
                
                if (isRelated) {{
                    // 高亮相关关系线
                    ctx.strokeStyle = r.color;
                    ctx.lineWidth = 3;
                    ctx.globalAlpha = 1;
                }} else {{
                    // 其他关系线变淡
                    ctx.strokeStyle = r.color;
                    ctx.lineWidth = 1;
                    ctx.globalAlpha = selectedNode ? 0.15 : 0.5;
                }}
                ctx.stroke();
                ctx.globalAlpha = 1;
            }});
            
            // 绘制节点
            nodes.forEach(node => {{
                const isSelected = selectedNode && selectedNode.id === node.id;
                const isHovered = hoveredNode && hoveredNode.id === node.id;
                const isRelated = selectedNode && relatedNodeIds.has(node.id);
                
                ctx.beginPath();
                ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
                
                if (isSelected) {{
                    // 选中的节点最亮
                    ctx.fillStyle = node.color;
                    ctx.globalAlpha = 1;
                }} else if (isRelated) {{
                    // 相关节点高亮
                    ctx.fillStyle = node.color;
                    ctx.globalAlpha = 1;
                }} else if (selectedNode) {{
                    // 其他节点变淡
                    ctx.fillStyle = node.color;
                    ctx.globalAlpha = 0.2;
                }} else {{
                    // 没有选中时正常显示
                    ctx.fillStyle = node.color + 'cc';
                    ctx.globalAlpha = 1;
                }}
                ctx.fill();
                ctx.globalAlpha = 1;
                
                if (isSelected || isHovered) {{
                    ctx.strokeStyle = '#ffffff';
                    ctx.lineWidth = 3;
                    ctx.stroke();
                }} else if (isRelated) {{
                    ctx.strokeStyle = node.color;
                    ctx.lineWidth = 2;
                    ctx.stroke();
                }}
                
                // 节点名称
                ctx.font = '12px Microsoft YaHei';
                if (isSelected || isRelated || !selectedNode) {{
                    ctx.fillStyle = '#c9d1d9';
                    ctx.globalAlpha = 1;
                }} else {{
                    ctx.fillStyle = '#8b949e';
                    ctx.globalAlpha = 0.3;
                }}
                ctx.textAlign = 'center';
                ctx.fillText(node.name, node.x, node.y + node.radius + 14);
                ctx.globalAlpha = 1;
            }});
            
            ctx.restore();
        }}
        
        init();
    </script>
</body>
</html>"""

    return html


def main():
    print("=" * 60)
    print("知识图谱可视化生成 (从Qdrant数据库)")
    print("=" * 60)

    # 从Qdrant加载数据
    print("\n[加载数据]")
    data = load_from_qdrant()

    # 生成HTML
    print("\n[生成HTML]")
    html = generate_html(data)

    # 保存
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n[完成] {OUTPUT_FILE}")
    print(f"时间戳: {TIMESTAMP}")


if __name__ == "__main__":
    main()
