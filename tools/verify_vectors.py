#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证三向量存储"""

import os
import sys
from pathlib import Path

# 加载配置
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config_loader import get_vectorstore_dir

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from qdrant_client import QdrantClient

client = QdrantClient(path=str(get_vectorstore_dir() / "qdrant"))

print("=== Collection 状态 ===")
for c in client.get_collections().collections:
    info = client.get_collection(c.name)
    print(f"{c.name}: {info.points_count} 条")

print("\n=== 验证三向量存储 ===")

# 检查 novel_settings_v2
info = client.get_collection("novel_settings_v2")
print(f"\nnovel_settings_v2 配置:")
print(f"  vectors: {list(info.config.params.vectors.keys())}")
print(f"  sparse_vectors: {list(info.config.params.sparse_vectors.keys())}")

# 获取一条数据验证
results, _ = client.scroll(
    collection_name="novel_settings_v2",
    limit=1,
    with_vectors=True,
)

if results:
    r = results[0]
    print(f"\n示例数据 ID={r.id}:")
    print(f"  name: {r.payload.get('name', 'N/A')}")
    print(f"  vectors: {list(r.vector.keys())}")
    if "dense" in r.vector:
        print(f"  dense维度: {len(r.vector['dense'])}")
    if "colbert" in r.vector:
        print(f"  colbert tokens数: {len(r.vector['colbert'])}")
    if "sparse" in r.vector:
        print(f"  sparse非零元素: {len(r.vector['sparse'].indices)}")

# 检查 writing_techniques_v2
info2 = client.get_collection("writing_techniques_v2")
print(f"\nwriting_techniques_v2 配置:")
print(f"  vectors: {list(info2.config.params.vectors.keys())}")
print(f"  sparse_vectors: {list(info2.config.params.sparse_vectors.keys())}")

# 获取一条技法数据
results2, _ = client.scroll(
    collection_name="writing_techniques_v2",
    limit=1,
    with_vectors=True,
)

if results2:
    r = results2[0]
    print(f"\n示例技法 ID={r.id}:")
    print(f"  name: {r.payload.get('name', 'N/A')}")
    print(f"  dimension: {r.payload.get('dimension', 'N/A')}")
    print(f"  vectors: {list(r.vector.keys())}")
    if "dense" in r.vector:
        print(f"  dense维度: {len(r.vector['dense'])}")
    if "colbert" in r.vector:
        print(f"  colbert tokens数: {len(r.vector['colbert'])}")

print("\n=== 三向量存储验证通过! ===")
