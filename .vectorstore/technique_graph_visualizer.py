#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创作技法图谱可视化 - 完整版
从Qdrant数据库读取技法详细内容，支持技法详情展示
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 sys.path 以导入配置加载器
sys.path.insert(0, str(__file__).rsplit(".vectorstore", 1)[0])
from core.config_loader import get_project_root, get_vectorstore_dir, get_qdrant_url

# 配置
PROJECT_DIR = get_project_root()
VECTORSTORE_DIR = get_vectorstore_dir()
OUTPUT_FILE = VECTORSTORE_DIR / "technique_graph.html"

TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 维度定义（核心11维度）
DIMENSIONS = {
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

# 非核心维度定义
NON_CORE_DIMENSIONS = {
    "外部资源": {"writer": "玄一", "color": "#6C7A89", "icon": "📚"},
    "创作模板": {"writer": "玄一", "color": "#95A5A6", "icon": "📋"},
    "实战案例": {"writer": "玄一", "color": "#7F8C8D", "icon": "📝"},
    "未知": {"writer": "全部", "color": "#5D6D7E", "icon": "❓"},
}

# 所有维度
ALL_DIMENSIONS = {**DIMENSIONS, **NON_CORE_DIMENSIONS}

# 作家定义
WRITERS = {
    "苍澜": {"role": "世界观架构师", "color": "#FF6B6B"},
    "玄一": {"role": "剧情编织师", "color": "#4ECDC4"},
    "墨言": {"role": "人物刻画师", "color": "#95E1D3"},
    "剑尘": {"role": "战斗设计师", "color": "#F38181"},
    "云溪": {"role": "意境营造师", "color": "#AA96DA"},
}


def load_techniques_from_qdrant():
    """从Qdrant数据库加载技法详细数据"""
    from qdrant_client import QdrantClient

    # 连接Docker Qdrant
    try:
        client = QdrantClient(url=get_qdrant_url())
        client.get_collections()
        print("  连接: Docker Qdrant (get_qdrant_url())")
    except:
        QDRANT_DIR = VECTORSTORE_DIR / "qdrant"
        client = QdrantClient(path=str(QDRANT_DIR))
        print(f"  连接: 本地文件 {QDRANT_DIR}")

    # 读取所有技法
    print("  读取: writing_techniques_v2 collection...")
    points = client.scroll(
        collection_name="writing_techniques_v2", limit=2000, with_payload=True
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
    dimension_counts = {}
    writer_counts = {}
    core_count = 0
    non_core_count = 0

    for p in points:
        payload = p.payload

        # 维度
        dim = payload.get("dimension", "未知")
        dim = dim_map.get(dim, dim)

        # 技法名称
        name = payload.get("name", "") or payload.get("title", "") or f"技法{p.id}"

        # 技法内容
        content = payload.get("content", "") or payload.get("description", "")

        # 作家
        writer = payload.get("writer", "")

        # 标签
        tags = payload.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        # 判断是否核心维度
        is_core = dim in DIMENSIONS

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

        # 统计
        dimension_counts[dim] = dimension_counts.get(dim, 0) + 1
        if writer:
            writer_counts[writer] = writer_counts.get(writer, 0) + 1

        if is_core:
            core_count += 1
        else:
            non_core_count += 1

    print(f"  技法: {len(techniques)} 条")
    print(f"    核心11维度: {core_count} 条")
    print(f"    非核心维度: {non_core_count} 条")
    print(f"  维度: {len(dimension_counts)} 个")

    return techniques, dimension_counts, writer_counts


def generate_html(techniques, dimension_counts, writer_counts):
    """生成完整的技法图谱HTML"""

    # 按维度组织技法
    techniques_by_dimension = {}
    for t in techniques:
        dim = t["dimension"]
        if dim not in techniques_by_dimension:
            techniques_by_dimension[dim] = []
        techniques_by_dimension[dim].append(t)

    # 按作家组织技法
    techniques_by_writer = {}
    for t in techniques:
        writer = t.get("writer", "")
        if writer and writer in WRITERS:
            if writer not in techniques_by_writer:
                techniques_by_writer[writer] = []
            techniques_by_writer[writer].append(t)

    # 核心技法数
    core_count = sum(1 for t in techniques if t.get("isCore", False))

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>创作技法图谱 - 众生界 - {TIMESTAMP}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
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
            margin-bottom: 4px;
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
            flex-shrink: 0;
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
        
        .dimension-card {{
            background: #21262d;
            border-radius: 6px;
            padding: 12px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.2s;
            border: 1px solid transparent;
        }}
        
        .dimension-card:hover {{
            background: #30363d;
        }}
        
        .dimension-card.active {{
            border-color: #58a6ff;
            background: #1f6feb22;
        }}
        
        .dimension-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
        }}
        
        .dimension-name {{
            font-size: 14px;
            font-weight: 500;
        }}
        
        .dimension-count {{
            font-size: 12px;
            color: #8b949e;
        }}
        
        .dimension-writer {{
            font-size: 12px;
            color: #8b949e;
        }}
        
        .writer-card {{
            background: #21262d;
            border-radius: 6px;
            padding: 10px 12px;
            margin-bottom: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .writer-card:hover {{
            background: #30363d;
        }}
        
        .writer-card.active {{
            background: #1f6feb22;
            border: 1px solid #58a6ff;
        }}
        
        .writer-name {{
            font-size: 14px;
            font-weight: 500;
        }}
        
        .writer-role {{
            font-size: 11px;
            color: #8b949e;
            margin-top: 2px;
        }}
        
        .main-content {{
            flex: 1;
            overflow-y: auto;
            padding: 24px;
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
            font-size: 14px;
        }}
        
        .search-box input:focus {{
            outline: none;
            border-color: #58a6ff;
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
            background: #21262d;
        }}
        
        .technique-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 8px;
        }}
        
        .technique-name {{
            font-size: 15px;
            font-weight: 500;
            color: #c9d1d9;
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
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
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
        
        /* 详情模态框 */
        .modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }}
        
        .modal.show {{
            display: flex;
        }}
        
        .modal-content {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            width: 90%;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
        }}
        
        .modal-header {{
            padding: 20px;
            border-bottom: 1px solid #30363d;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            background: #161b22;
        }}
        
        .modal-title {{
            font-size: 18px;
            font-weight: 500;
        }}
        
        .modal-close {{
            background: none;
            border: none;
            color: #8b949e;
            font-size: 24px;
            cursor: pointer;
            padding: 4px 8px;
        }}
        
        .modal-close:hover {{
            color: #c9d1d9;
        }}
        
        .modal-body {{
            padding: 20px;
        }}
        
        .modal-meta {{
            display: flex;
            gap: 16px;
            margin-bottom: 16px;
            font-size: 13px;
            color: #8b949e;
        }}
        
        .modal-meta span {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        
        .modal-content-text {{
            font-size: 14px;
            line-height: 1.8;
            color: #c9d1d9;
            white-space: pre-wrap;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: #8b949e;
        }}
        
        .empty-state h3 {{
            font-size: 16px;
            margin-bottom: 8px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎨 创作技法图谱</h1>
        <p>共 {len(techniques)} 条技法 | 核心{len(DIMENSIONS)}维度 ({core_count}条) + 非核心{len(NON_CORE_DIMENSIONS)}维度 ({len(techniques) - core_count}条) | {len(WRITERS)} 作家 | 生成时间: {TIMESTAMP}</p>
    </div>
    
    <div class="stats-bar">
        <div class="stat-item">
            <span>总技法:</span>
            <span class="stat-value">{len(techniques)}</span>
        </div>
        <div class="stat-item">
            <span>核心维度:</span>
            <span class="stat-value">{len(DIMENSIONS)}</span>
        </div>
        <div class="stat-item">
            <span>作家:</span>
            <span class="stat-value">{len(WRITERS)}</span>
        </div>
    </div>
    
    <div class="container">
        <div class="sidebar">
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="搜索技法名称或内容...">
            </div>
            
            <div class="sidebar-section">
                <h2>📐 按维度浏览</h2>
                <div id="dimensionList"></div>
            </div>
            
            <div class="sidebar-section">
                <h2>✍️ 按作家浏览</h2>
                <div id="writerList"></div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="technique-list" id="techniqueList"></div>
        </div>
    </div>
    
    <!-- 详情模态框 -->
    <div class="modal" id="detailModal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title" id="modalTitle">技法名称</div>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="modal-meta" id="modalMeta"></div>
                <div class="modal-content-text" id="modalContent"></div>
            </div>
        </div>
    </div>

    <script>
        // 技法数据
        const techniques = {json.dumps(techniques, ensure_ascii=False)};
        const dimensions = {json.dumps(DIMENSIONS, ensure_ascii=False)};
        const nonCoreDimensions = {json.dumps(NON_CORE_DIMENSIONS, ensure_ascii=False)};
        const allDimensions = {{...dimensions, ...nonCoreDimensions}};
        const writers = {json.dumps(WRITERS, ensure_ascii=False)};
        const techniquesByDimension = {json.dumps(techniques_by_dimension, ensure_ascii=False)};
        const techniquesByWriter = {json.dumps(techniques_by_writer, ensure_ascii=False)};
        
        let currentFilter = {{ type: 'all', value: 'all' }};
        let searchQuery = '';
        
        // 初始化
        function init() {{
            renderDimensionList();
            renderWriterList();
            renderTechniqueList(techniques);
            bindEvents();
        }}
        
        // 渲染维度列表
        function renderDimensionList() {{
            const list = document.getElementById('dimensionList');
            
            // 全部
            let html = `<div class="dimension-card ${{currentFilter.type === 'all' ? 'active' : ''}}" onclick="filterByDimension('all')">
                <div class="dimension-header">
                    <span class="dimension-name">📚 全部技法</span>
                    <span class="dimension-count">${{techniques.length}} 条</span>
                </div>
            </div>`;
            
            // 核心维度标题
            html += `<div style="padding: 8px 0 4px; font-size: 11px; color: #6e7681;">核心维度 (11)</div>`;
            
            // 核心维度
            for (const [dim, info] of Object.entries(dimensions)) {{
                const count = techniquesByDimension[dim]?.length || 0;
                html += `<div class="dimension-card ${{currentFilter.type === 'dimension' && currentFilter.value === dim ? 'active' : ''}}" 
                         onclick="filterByDimension('${{dim}}')">
                    <div class="dimension-header">
                        <span class="dimension-name">${{info.icon}} ${{dim}}</span>
                        <span class="dimension-count">${{count}} 条</span>
                    </div>
                    <div class="dimension-writer">负责: ${{info.writer}}</div>
                </div>`;
            }}
            
            // 非核心维度标题
            html += `<div style="padding: 12px 0 4px; font-size: 11px; color: #6e7681;">非核心维度 (${{Object.keys(nonCoreDimensions).length}})</div>`;
            
            // 非核心维度
            for (const [dim, info] of Object.entries(nonCoreDimensions)) {{
                const count = techniquesByDimension[dim]?.length || 0;
                if (count > 0) {{
                    html += `<div class="dimension-card ${{currentFilter.type === 'dimension' && currentFilter.value === dim ? 'active' : ''}}" 
                             onclick="filterByDimension('${{dim}}')">
                        <div class="dimension-header">
                            <span class="dimension-name" style="color: #8b949e">${{info.icon}} ${{dim}}</span>
                            <span class="dimension-count">${{count}} 条</span>
                        </div>
                    </div>`;
                }}
            }}
            
            list.innerHTML = html;
        }}
        
        // 渲染作家列表
        function renderWriterList() {{
            const list = document.getElementById('writerList');
            
            let html = '';
            for (const [name, info] of Object.entries(writers)) {{
                const count = techniquesByWriter[name]?.length || 0;
                html += `<div class="writer-card ${{currentFilter.type === 'writer' && currentFilter.value === name ? 'active' : ''}}"
                         onclick="filterByWriter('${{name}}')">
                    <div class="writer-name" style="color: ${{info.color}}">${{name}}</div>
                    <div class="writer-role">${{info.role}} · ${{count}}条技法</div>
                </div>`;
            }}
            
            list.innerHTML = html;
        }}
        
        // 渲染技法列表
        function renderTechniqueList(techs) {{
            const list = document.getElementById('techniqueList');
            
            // 应用搜索过滤
            let filtered = techs;
            if (searchQuery) {{
                const query = searchQuery.toLowerCase();
                filtered = techs.filter(t => 
                    t.name.toLowerCase().includes(query) || 
                    t.content.toLowerCase().includes(query) ||
                    t.tags.some(tag => tag.toLowerCase().includes(query))
                );
            }}
            
            if (filtered.length === 0) {{
                list.innerHTML = `<div class="empty-state">
                    <h3>没有找到匹配的技法</h3>
                    <p>尝试修改搜索关键词或筛选条件</p>
                </div>`;
                return;
            }}
            
            let html = '';
            for (const t of filtered) {{
                const dimInfo = allDimensions[t.dimension] || {{ color: '#ADB5BD', icon: '' }};
                const isCore = t.isCore;
                html += `<div class="technique-card" onclick="showDetail('${{t.id}}')">
                    <div class="technique-header">
                        <span class="technique-name">${{t.name}}</span>
                        <span class="technique-dimension" style="background: ${{dimInfo.color}}22; color: ${{dimInfo.color}}">${{dimInfo.icon}} ${{t.dimension}}</span>
                    </div>
                    <div class="technique-content">${{t.content || '暂无详细内容'}}</div>
                    ${{t.tags.length > 0 ? `<div class="technique-tags">${{t.tags.map(tag => `<span class="tag">${{tag}}</span>`).join('')}}</div>` : ''}}
                    ${{t.writer ? `<div class="technique-writer">—— ${{t.writer}}</div>` : ''}}
                </div>`;
            }}
            
            list.innerHTML = html;
        }}
        
        // 筛选函数
        function filterByDimension(dim) {{
            currentFilter = {{ type: 'dimension', value: dim }};
            const techs = dim === 'all' ? techniques : (techniquesByDimension[dim] || []);
            renderTechniqueList(techs);
            renderDimensionList();
            renderWriterList();
        }}
        
        function filterByWriter(writer) {{
            currentFilter = {{ type: 'writer', value: writer }};
            const techs = techniquesByWriter[writer] || [];
            renderTechniqueList(techs);
            renderDimensionList();
            renderWriterList();
        }}
        
        // 显示详情
        function showDetail(id) {{
            const t = techniques.find(tech => tech.id === id);
            if (!t) return;
            
            const dimInfo = allDimensions[t.dimension] || {{ color: '#ADB5BD', icon: '' }};
            
            document.getElementById('modalTitle').textContent = t.name;
            document.getElementById('modalMeta').innerHTML = `
                <span style="color: ${{dimInfo.color}}">${{dimInfo.icon}} ${{t.dimension}}</span>
                ${{t.writer ? `<span>✍️ ${{t.writer}}</span>` : ''}}
            `;
            document.getElementById('modalContent').textContent = t.content || '暂无详细内容';
            
            document.getElementById('detailModal').classList.add('show');
        }}
        
        function closeModal() {{
            document.getElementById('detailModal').classList.remove('show');
        }}
        
        // 绑定事件
        function bindEvents() {{
            // 搜索
            document.getElementById('searchInput').addEventListener('input', (e) => {{
                searchQuery = e.target.value;
                const techs = currentFilter.type === 'all' ? techniques : 
                    (currentFilter.type === 'dimension' ? techniquesByDimension[currentFilter.value] : techniquesByWriter[currentFilter.value]) || [];
                renderTechniqueList(techs);
            }});
            
            // 点击模态框外部关闭
            document.getElementById('detailModal').addEventListener('click', (e) => {{
                if (e.target.id === 'detailModal') {{
                    closeModal();
                }}
            }});
            
            // ESC关闭模态框
            document.addEventListener('keydown', (e) => {{
                if (e.key === 'Escape') {{
                    closeModal();
                }}
            }});
        }}
        
        // 启动
        init();
    </script>
</body>
</html>"""

    return html


def main():
    print("=" * 60)
    print("创作技法图谱生成 (从Qdrant数据库)")
    print("=" * 60)

    print("\n[加载数据]")
    techniques, dimension_counts, writer_counts = load_techniques_from_qdrant()

    print("\n[生成HTML]")
    html = generate_html(techniques, dimension_counts, writer_counts)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n[完成] {OUTPUT_FILE}")
    print(f"\n维度统计:")
    for dim, count in sorted(dimension_counts.items(), key=lambda x: -x[1]):
        writer = DIMENSIONS.get(dim, {}).get("writer", "")
        print(f"  {dim}: {count} 条 ({writer})")

    print(f"\n作家统计:")
    for writer, count in sorted(writer_counts.items(), key=lambda x: -x[1]):
        print(f"  {writer}: {count} 条")


if __name__ == "__main__":
    main()
