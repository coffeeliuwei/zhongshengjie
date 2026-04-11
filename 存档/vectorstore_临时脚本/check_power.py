#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import chromadb
from pathlib import Path

VECTORSTORE_DIR = Path(r"D:\动画\众生界\.vectorstore")
c = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
col = c.get_collection("novelist_knowledge")

# Get all entries with type containing '力量'
r = col.get(where={"类型": "力量"})
print(f"Entries with type '力量': {len(r['ids'])}")
for i, m in enumerate(r["metadatas"]):
    print(f"  [{i + 1}] ID: {r['ids'][i]}")
    print(f"      Name: {m.get('名称', '?')}")
    print(f"      Type: {m.get('类型', '?')}")
    print(f"      Content: {r['documents'][i][:100]}...")

# Also check what DATA_TYPES mapping produces
from knowledge_search import DATA_TYPES

print(f"\nDATA_TYPES['power'] = '{DATA_TYPES['power']}'")
