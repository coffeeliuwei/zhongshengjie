#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import chromadb
from pathlib import Path
import json

VECTORSTORE_DIR = Path(r"D:\动画\众生界\.vectorstore")
c = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
col = c.get_collection("novelist_knowledge")

# Get all metadata
r = col.get()

# Find unique types and print their raw bytes
types_raw = set()
for m in r["metadatas"]:
    t = m.get("类型", "")
    types_raw.add(t)

print(f"Found {len(types_raw)} unique types:")
for t in types_raw:
    print(f"  Type: '{t}' (len={len(t)})")
    # Also show hex encoding
    print(f"    Hex: {t.encode('utf-8').hex()}")
