#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查数据库中的时间线数据"""

import chromadb
from pathlib import Path

VECTORSTORE_DIR = Path(r"D:\动画\众生界\.vectorstore")
client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
collection = client.get_collection("novelist_knowledge")

# 检查事件类型
results = collection.get(where={"类型": "event"})
print(f"事件类型记录数: {len(results['ids'])}")

for i, (id_, meta, doc) in enumerate(
    zip(results["ids"], results["metadatas"], results["documents"])
):
    print(f"\n[{i + 1}] ID: {id_}")
    print(f"    名称: {meta.get('名称', '?')}")
    print(f"    内容长度: {len(doc)}")
    print(f"    内容预览: {doc[:200]}...")
