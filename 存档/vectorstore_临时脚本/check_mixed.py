#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import chromadb
from pathlib import Path

VECTORSTORE_DIR = Path(r"D:\动画\众生界\.vectorstore")
c = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
col = c.get_collection("novelist_knowledge")

# Find entries with unexpected types
r = col.get()

# Decode the hex types
target_types = ["代价", "技法"]

print("Entries with type '代价' or '技法':")
for i, m in enumerate(r["metadatas"]):
    t = m.get("类型", "")
    if t in target_types:
        print(f"\n[{i}] ID: {r['ids'][i]}")
        print(f"    Name: {m.get('名称', '?')}")
        print(f"    Type: {t}")
        print(f"    Source: {m.get('来源文件', '?')}")
        print(f"    Content preview: {r['documents'][i][:100]}...")

print(f"\n\nTotal knowledge entries: {len(r['ids'])}")
