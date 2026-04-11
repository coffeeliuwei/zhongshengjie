#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import chromadb
from pathlib import Path

VECTORSTORE_DIR = Path(r"D:\动画\众生界\.vectorstore")
c = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
col = c.get_collection("novelist_knowledge")
r = col.get()

types = {}
for m in r["metadatas"]:
    t = m.get("类型", "?")
    types[t] = types.get(t, 0) + 1

print("Knowledge database types:")
for t, count in types.items():
    print(f"  {t}: {count}")
