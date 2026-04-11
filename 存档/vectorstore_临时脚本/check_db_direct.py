#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""直接检查数据库中的角色记录"""

import chromadb
from pathlib import Path

VECTORSTORE_DIR = Path(r"D:\动画\众生界\.vectorstore")

client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
collection = client.get_collection("novelist_knowledge")

print("=" * 70)
print("直接检查数据库记录")
print("=" * 70)

# 直接通过ID获取血牙
print("\n[通过ID获取血牙 char_xueya]")
result = collection.get(ids=["char_xueya"])
if result["ids"]:
    print(f"  ID: {result['ids'][0]}")
    print(f"  名称: {result['metadatas'][0].get('名称', '?')}")
    print(f"  类型: {result['metadatas'][0].get('类型', '?')}")
    print(f"  内容长度: {len(result['documents'][0])} 字符")
    print(f"  内容:\n{result['documents'][0]}")
else:
    print("  未找到记录")

# 列出所有character类型
print("\n[列出所有角色记录]")
result = collection.get(where={"类型": "character"})
print(f"  共 {len(result['ids'])} 条角色记录:")
for i, (id_, meta) in enumerate(zip(result["ids"], result["metadatas"])):
    name = meta.get("名称", "?")
    content_len = len(result["documents"][i])
    print(f"    [{i + 1}] ID: {id_}, 名称: {name}, 内容长度: {content_len}")

# 检查是否有重名或ID冲突
print("\n[检查血牙相关记录]")
result = collection.get()
for i, (id_, doc, meta) in enumerate(
    zip(result["ids"], result["documents"], result["metadatas"])
):
    if "血牙" in doc or "血牙" in meta.get("名称", ""):
        print(f"  找到: ID={id_}, 名称={meta.get('名称', '?')}")
        print(f"        内容长度: {len(doc)}")
        print(f"        内容预览: {doc[:100]}...")
