#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""直接测试Qdrant Docker检索"""

import os

os.environ["HF_HUB_OFFLINE"] = "1"

from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
from pathlib import Path

PROJECT_DIR = Path(r"D:\动画\众生界")

# Docker Qdrant URL (统一数据源)
QDRANT_DOCKER_URL = "http://localhost:6333"

print("=" * 60)
print("向量数据库状态检查 (Docker Qdrant)")
print("=" * 60)

client = QdrantClient(url=QDRANT_DOCKER_URL)

# 列出所有collections
print("\n所有Collections:")
collections = client.get_collections()
for c in collections.collections:
    info = client.get_collection(c.name)
    print(f"  {c.name}: {info.points_count:,} 条")

print("\n" + "=" * 60)
print("技法检索测试 (writing_techniques_v2)")
print("=" * 60)

# 加载模型
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# 测试查询
query = "战斗代价描写"
query_vector = model.encode(query, show_progress_bar=False).tolist()

results = client.search(
    collection_name="writing_techniques_v2",
    query_vector=("dense", query_vector),
    limit=3,
    with_payload=True,
)

print(f"\n查询: {query}\n")
for r in results:
    payload = r.payload or {}
    print(f"技法: {payload.get('name', '未知')}")
    print(f"维度: {payload.get('dimension', '未知')}")
    print(f"作家: {payload.get('writer', '未知')}")
    print(f"相似度: {r.score:.4f}")
    print()

print("=" * 60)
print("案例检索测试 (case_library)")
print("=" * 60)

query2 = "玄幻开篇"
query_vector2 = model.encode(query2, show_progress_bar=False).tolist()

results2 = client.search(
    collection_name="case_library",
    query_vector=query_vector2,
    limit=3,
    with_payload=True,
)

print(f"\n查询: {query2}\n")
for r in results2:
    payload = r.payload or {}
    print(f"来源: {payload.get('novel', payload.get('novel_name', '未知'))}")
    print(f"场景: {payload.get('scene_type', '未知')}")
    print(f"题材: {payload.get('genre', '未知')}")
    print(f"相似度: {r.score:.4f}")
    print()

print("=" * 60)
print("工作流状态检查")
print("=" * 60)

# 检查知识图谱
kg_file = PROJECT_DIR / ".vectorstore" / "knowledge_graph.json"
if kg_file.exists():
    import json

    kg = json.load(open(kg_file, encoding="utf-8"))
    entities = kg.get("实体", {})
    print(f"\n知识图谱实体数: {len(entities)}")
    print("示例实体:")
    for i, (name, data) in enumerate(list(entities.items())[:3]):
        print(f"  - {name}: {data.get('类型', '未知')}")

# 检查章节大纲
outline_dir = PROJECT_DIR / "章节大纲"
if outline_dir.exists():
    outlines = list(outline_dir.glob("*.md"))
    print(f"\n章节大纲数: {len(outlines)}")
    for o in outlines[:3]:
        print(f"  - {o.name}")

# 检查章节经验日志
exp_dir = PROJECT_DIR / "章节经验日志"
if exp_dir.exists():
    logs = list(exp_dir.glob("*.json"))
    print(f"\n章节经验日志数: {len(logs)}")
    for l in logs[:3]:
        print(f"  - {l.name}")

print("\n" + "=" * 60)
print("检查完成")
print("=" * 60)
