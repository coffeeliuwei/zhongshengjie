#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("knowledge_graph.json", "r", encoding="utf-8") as f:
    data = json.load(f)

entities = data.get("实体", {})

# 搜索包含'血脉'的实体
print('搜索包含"血脉"的实体:')
found = False
for eid, e in entities.items():
    name = e.get("名称", "")
    etype = e.get("类型", "")
    attrs_str = str(e.get("属性", {}))
    if "血脉" in name or "血脉" in attrs_str:
        found = True
        print(f"\n  ID: {eid}")
        print(f"  名称: {name}")
        print(f"  类型: {etype}")

if not found:
    print('  未找到包含"血脉"的实体')

# 搜索包含'速查'的实体
print('\n搜索包含"速查"的实体:')
found = False
for eid, e in entities.items():
    name = e.get("名称", "")
    if "速查" in name:
        found = True
        print(f"  ID: {eid}")
        print(f"  名称: {name}")
        print(f"  类型: {e.get('类型', '')}")

if not found:
    print('  未找到包含"速查"的实体')

# 检查元数据中的数据来源
print("\n数据来源:")
metadata = data.get("元数据", {})
sources = metadata.get("数据来源", [])
if isinstance(sources, list):
    for s in sources:
        print(f"  - {s}")
else:
    print(f"  {sources}")
