#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查时间线相关数据"""

import chromadb
from pathlib import Path

VECTORSTORE_DIR = Path(r"D:\动画\众生界\.vectorstore")
client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
collection = client.get_collection("novelist_knowledge")

# 搜索时间线相关
print("搜索'时间线'相关记录:")
results = collection.get()
for i, (id_, meta, doc) in enumerate(
    zip(results["ids"], results["metadatas"], results["documents"])
):
    if (
        "时间线" in str(meta)
        or "时代" in str(meta)
        or "觉醒" in str(meta)
        or "时间线" in doc[:200]
    ):
        print(f"\nID: {id_}")
        print(f"类型: {meta.get('类型', '?')}")
        print(f"名称: {meta.get('名称', '?')}")
        print(f"内容预览: {doc[:150]}...")

# 统计各类型
print("\n\n各类型统计:")
type_counts = {}
for meta in results["metadatas"]:
    t = meta.get("类型", "未知")
    type_counts[t] = type_counts.get(t, 0) + 1

for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f"  {t}: {count}")
