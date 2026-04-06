#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证JSON、数据库、网页数据同步"""

import sys
import json
from pathlib import Path
from core.config_loader import get_qdrant_url

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except:
        pass

VECTORSTORE_DIR = Path(__file__).parent
KNOWLEDGE_GRAPH = VECTORSTORE_DIR / "knowledge_graph.json"
HTML_FILE = VECTORSTORE_DIR / "knowledge_graph.html"

print("=" * 60)
print("数据同步验证")
print("=" * 60)

# 1. 验证知识图谱JSON
print("\n[1] 知识图谱JSON")
with open(KNOWLEDGE_GRAPH, "r", encoding="utf-8") as f:
    data = json.load(f)

entities = data.get("实体", {})
relations = data.get("关系", [])

print(f"  实体总数: {len(entities)}")
print(f"  关系总数: {len(relations)}")

# 按类型统计
type_count = {}
for entity_id, entity in entities.items():
    entity_type = entity.get("类型", "未知")
    type_count[entity_type] = type_count.get(entity_type, 0) + 1

print("\n  实体类型分布:")
for entity_type, count in sorted(type_count.items(), key=lambda x: -x[1]):
    print(f"    + {entity_type}: {count}")

# 验证血牙血脉
xueya = entities.get("char_xueya", {})
if xueya:
    props = xueya.get("属性", {})
    philosophy = props.get("哲学设定", {})
    print(f"\n  血牙血脉验证:")
    print(f"    哲学起点: {philosophy.get('哲学起点', '未知')[:50]}...")

    # 检查是否有"熊血脉"
    if "熊血脉" in str(philosophy):
        print("    ✅ 血脉正确：熊血脉")
    elif "狼血脉" in str(philosophy):
        print("    ❌ 错误：仍是狼血脉")

# 2. 验证Qdrant数据库
print("\n[2] Qdrant数据库")
try:
    from qdrant_client import QdrantClient

    try:
        client = QdrantClient(url=get_qdrant_url())
        client.get_collections()
        print("  连接方式: Docker Qdrant (get_qdrant_url())")
    except:
        client = QdrantClient(path=str(VECTORSTORE_DIR / "qdrant"))
        print("  连接方式: 本地文件")

    # 获取各collection统计
    collections = ["novel_settings_v2", "writing_techniques_v2", "case_library_v2"]
    for col in collections:
        try:
            info = client.get_collection(col)
            print(f"  + {col}: {info.points_count} 条")
        except Exception as e:
            print(f"  + {col}: 未找到 ({e})")

except Exception as e:
    print(f"  ❌ 连接失败: {e}")

# 3. 验证HTML可视化
print("\n[3] HTML可视化")

# 知识图谱
if HTML_FILE.exists():
    html_content = HTML_FILE.read_text(encoding="utf-8")

    # 检查HTML中的统计数据
    import re

    stats_match = re.search(
        r"实体: <strong>(\d+)</strong> \| 关系: <strong>(\d+)</strong>", html_content
    )
    if stats_match:
        html_entities = stats_match.group(1)
        html_relations = stats_match.group(2)
        print(f"  knowledge_graph.html:")
        print(f"    实体: {html_entities}")
        print(f"    关系: {html_relations} (匹配成功的关系)")

    # 检查熊血脉
    if "熊血脉" in html_content:
        print("    ✅ 包含熊血脉")
    else:
        print("    ❌ 未包含熊血脉")

    print(f"    文件大小: {len(html_content) / 1024:.1f} KB")
else:
    print("  ❌ knowledge_graph.html 不存在")

# 技法图谱
TECHNIQUE_HTML = VECTORSTORE_DIR / "technique_graph.html"
if TECHNIQUE_HTML.exists():
    html_content = TECHNIQUE_HTML.read_text(encoding="utf-8")

    # 检查技法统计
    import re

    tech_match = re.search(r"共 (\d+) 条技法", html_content)
    dim_match = re.search(r"(\d+) 维度", html_content)
    writer_match = re.search(r"(\d+) 作家", html_content)

    print(f"\n  technique_graph.html:")
    if tech_match:
        print(f"    技法: {tech_match.group(1)} 条")
    if dim_match:
        print(f"    维度: {dim_match.group(1)} 个")
    if writer_match:
        print(f"    作家: {writer_match.group(1)} 位")

    # 检查功能
    if "technique-card" in html_content:
        print(f"    功能: 技法卡片展示")
    if "modal-content" in html_content:
        print(f"    功能: 详情模态框")
    if "searchInput" in html_content:
        print(f"    功能: 搜索功能")

    print(f"    文件大小: {len(html_content) / 1024:.1f} KB")
else:
    print("  ❌ technique_graph.html 不存在")

# 4. 数据一致性检查
print("\n[4] 数据一致性")
print("  检查项:")

# 检查力量体系
power_systems = [e for e in entities if e.startswith("power_")]
print(f"  + 力量体系实体: {len(power_systems)} 个")

# 检查时代
eras = [e for e in entities if e.startswith("era_")]
print(f"  + 时代实体: {len(eras)} 个")

# 检查血脉
bloodlines = [e for e in entities if "血脉" in e or e.startswith("bloodline_")]
print(f"  + 血脉实体: {len(bloodlines)} 个")

# 检查狼血脉是否已删除
if "branch_power_兽力_狼血脉" in entities:
    print("  ❌ 错误：旧的狼血脉实体仍存在")
else:
    print("  ✅ 旧的狼血脉实体已删除")

# 检查熊血脉是否存在
if "bloodline_bear" in entities:
    bear_info = entities["bloodline_bear"].get("属性", {})
    print(f"  ✅ 熊血脉实体存在: {bear_info.get('名称', '未知')}")
    print(f"    代表人物: {bear_info.get('代表人物', '未知')}")
else:
    print("  ❌ 熊血脉实体不存在")

print("\n" + "=" * 60)
print("[完成] 数据同步验证结束")
print("=" * 60)
