# 可视化模块 (Visualization Module)

统一的可视化工具集，提供知识图谱、数据库和统计数据的可视化功能。

## 📁 目录结构

```
modules/visualization/
├── __init__.py              # 模块入口
├── graph_visualizer.py      # 知识图谱可视化
├── db_visualizer.py         # 数据库可视化
└── stats_visualizer.py      # 统计可视化
```

## 🚀 快速开始

### 命令行使用

```bash
# 生成知识图谱和技法图谱
python -m core visualize --graph

# 生成统计报告
python -m core visualize --stats
```

### Python API 使用

```python
from modules.visualization import GraphVisualizer, DBVisualizer, StatsVisualizer
from pathlib import Path

# 初始化（可选指定项目根目录）
project_root = Path("D:/动画/众生界")

# ==================== 知识图谱可视化 ====================
graph_viz = GraphVisualizer(project_root)

# 生成知识图谱 HTML
graph_viz.generate_knowledge_graph_html(
    output=project_root / ".vectorstore/knowledge_graph.html"
)

# 生成技法图谱 HTML
graph_viz.generate_technique_graph_html(
    output=project_root / ".vectorstore/technique_graph.html"
)

# ==================== 数据库可视化 ====================
db_viz = DBVisualizer(project_root)

# 列出所有集合
collections = db_viz.list_collections(db_type="qdrant")

# 获取集合统计
stats = db_viz.get_collection_stats("novel_settings", db_type="qdrant")

# 生成完整报告
db_viz.generate_report(
    db_type="qdrant",
    output=project_root / "db_report.json"
)

# ==================== 统计可视化 ====================
stats_viz = StatsVisualizer(project_root)

# 生成统计报告（支持 json/html/text 格式）
stats_viz.generate_report(
    output=project_root / ".vectorstore/stats_report.html",
    format="html"
)

# 打印摘要
stats_viz.print_summary()
```

## 📊 功能详情

### 1. GraphVisualizer - 知识图谱可视化

**功能:**
- 知识图谱可视化 (实体-关系网络)
- 技法图谱可视化 (维度-技法组织)
- 从 Qdrant 数据库读取数据
- 生成交互式 HTML 页面

**核心方法:**
- `load_knowledge_graph_data()` - 加载知识图谱数据
- `load_technique_data()` - 加载技法数据
- `generate_knowledge_graph_html()` - 生成知识图谱 HTML
- `generate_technique_graph_html()` - 生成技法图谱 HTML

**输出特性:**
- Canvas 渲染的交互式图谱
- 支持搜索、类型过滤
- 点击节点查看详情
- 滚轮缩放、拖拽移动
- 暗色主题设计

### 2. DBVisualizer - 数据库可视化

**功能:**
- 连接 Qdrant 向量数据库
- 查询数据库内容
- 统计数据分布
- 分析数据质量

**核心方法:**
- `list_collections()` - 列出所有集合
- `get_collection_stats()` - 获取集合统计
- `generate_report()` - 生成完整报告
- `check_data_integrity()` - 检查数据完整性

**统计维度:**
- 类型分布
- 内容长度分布
- 数据源统计
- 质量指标

### 3. StatsVisualizer - 统计可视化

**功能:**
- 知识图谱统计
- 技法库统计
- 数据库统计
- 生成可视化报告

**核心方法:**
- `get_knowledge_graph_stats()` - 获取知识图谱统计
- `get_technique_stats()` - 获取技法库统计
- `get_database_stats()` - 获取数据库统计
- `get_project_stats()` - 获取项目整体统计
- `generate_report()` - 生成报告 (json/html/text)

## 🔧 配置

### 核心11维度定义

```python
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
```

### 实体类型颜色

```python
TYPE_COLORS = {
    "角色": "#FF6B6B",
    "势力": "#4DABF7",
    "事件": "#69DB7C",
    "时代": "#FFD43B",
    "力量体系": "#A9E34B",
    "派系": "#74C0FC",
}
```

## 📝 输出示例

### 知识图谱 HTML

- 位置: `.vectorstore/knowledge_graph.html`
- 特性:
  - Canvas 渲染节点和关系
  - 左侧实体列表 + 搜索
  - 右侧详情面板
  - 支持缩放和拖拽

### 技法图谱 HTML

- 位置: `.vectorstore/technique_graph.html`
- 特性:
  - 按维度/作家分类浏览
  - 卡片式技法展示
  - 搜索和筛选功能

### 统计报告 HTML

- 位置: `.vectorstore/stats_report.html`
- 特性:
  - 实体/关系分布条形图
  - 数据库状态概览
  - 数据质量指标

## 🔗 依赖

必需依赖:
- `qdrant_client` - Qdrant 数据库客户端
- `sentence_transformers` - 向量化模型

Python 标准库:
- `json` - JSON 处理
- `pathlib` - 路径处理
- `datetime` - 时间处理
- `collections` - 数据结构

## 📚 相关文档

- [知识图谱数据结构](/.vectorstore/knowledge_graph.json)
- [原有可视化脚本](/.vectorstore/graph_visualizer.py)
- [CLI 命令参考](/core/cli.py)

## 🤝 贡献

本模块整合了以下原有脚本的功能:
- `.vectorstore/graph_visualizer.py` - 知识图谱可视化
- `.vectorstore/technique_graph_visualizer.py` - 技法图谱可视化
- `.vectorstore/db_viewer.py` - 数据库查看器
- `.vectorstore/knowledge_graph.py` - 知识图谱管理

原有脚本保留在 `.vectorstore/` 目录中，可继续使用。