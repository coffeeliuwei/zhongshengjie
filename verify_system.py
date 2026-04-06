#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统验证脚本 (Docker Qdrant)
=====================================

验证众生界向量数据库整合后的系统状态
"""

import os

os.environ["HF_HUB_OFFLINE"] = "1"

import sys
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(r"D:\动画\众生界")
VECTORSTORE_DIR = PROJECT_DIR / ".vectorstore"

# Docker Qdrant URL (统一数据源)
QDRANT_DOCKER_URL = "http://localhost:6333"

print("=" * 60)
print("众生界向量数据库系统验证 (Docker Qdrant)")
print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# 1. 检查Qdrant Collections
print("\n[1] Docker Qdrant Collections 状态")
print("-" * 40)

try:
    from qdrant_client import QdrantClient

    client = QdrantClient(url=QDRANT_DOCKER_URL)

    collections = client.get_collections()
    print(f"Collection 数量: {len(collections.collections)}")

    expected = {
        "novel_settings_v2": 196,
        "writing_techniques_v2": 1124,
        "case_library_v2": 256083,
    }

    all_ok = True
    for c in collections.collections:
        info = client.get_collection(c.name)
        expected_count = expected.get(c.name, 0)
        actual_count = info.points_count
        status = "OK" if actual_count >= expected_count * 0.9 else "WARN"
        if status == "WARN":
            all_ok = False
        print(f"  {c.name}: {actual_count:,} 条 (预期: {expected_count:,}) [{status}]")

    # 检查是否有旧版Collection
    old_collections = ["case_library", "novel_settings", "writing_techniques"]
    for name in old_collections:
        try:
            info = client.get_collection(name)
            print(f"  [WARN] 旧版Collection仍存在: {name} ({info.points_count:,} 条)")
            all_ok = False
        except:
            pass

except Exception as e:
    print(f"  [ERROR] Qdrant连接失败: {e}")
    all_ok = False

# 2. 检查知识图谱
print("\n[2] 知识图谱状态")
print("-" * 40)

kg_file = VECTORSTORE_DIR / "knowledge_graph.json"
if kg_file.exists():
    import json

    kg = json.load(open(kg_file, encoding="utf-8"))
    entities = kg.get("实体", {})
    print(f"  实体数量: {len(entities)}")
else:
    print("  [ERROR] 知识图谱文件不存在")
    all_ok = False

# 3. 检查ChromaDB是否已归档
print("\n[3] ChromaDB归档状态")
print("-" * 40)

chroma_dir = VECTORSTORE_DIR / "chroma"
archived_chroma = VECTORSTORE_DIR / "archived" / "chroma_old"

if not chroma_dir.exists():
    print("  [OK] ChromaDB已移除")
else:
    print("  [WARN] ChromaDB目录仍存在")
    all_ok = False

if archived_chroma.exists():
    print("  [OK] ChromaDB已归档到 archived/chroma_old")
else:
    print("  [INFO] ChromaDB归档目录不存在")

# 4. 检查核心模块导入
print("\n[4] 核心模块导入测试")
print("-" * 40)

try:
    sys.path.insert(0, str(VECTORSTORE_DIR))
    from core.technique_search import TechniqueSearcher
    from core.case_search import CaseSearcher
    from core.knowledge_search import KnowledgeSearcher

    print("  [OK] 核心检索模块导入成功")
except ImportError as e:
    print(f"  [ERROR] 模块导入失败: {e}")
    all_ok = False

# 5. 总结
print("\n" + "=" * 60)
if all_ok:
    print("系统验证通过")
else:
    print("系统验证发现问题，请检查上述警告项")
print("=" * 60)
