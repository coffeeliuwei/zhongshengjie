#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("knowledge_graph.json", "r", encoding="utf-8") as f:
    data = json.load(f)

entities = data.get("实体", {})
relations = data.get("关系", [])

# 检查实体的ID和名称
print("实体样例 (ID -> 名称):")
for eid, e in list(entities.items())[:5]:
    print(f"  {eid} -> {e.get('名称', '?')}")

print()
print("关系样例:")
for r in relations[:3]:
    print(
        f"  源: {r.get('源实体')}, 目标: {r.get('目标实体')}, 类型: {r.get('关系类型')}"
    )

# 检查关系中的实体是否能匹配到实体ID
print()
print("检查关系匹配:")
sample_rel = relations[0]
source_name = sample_rel.get("源实体")
print(f"  关系中的源实体: {source_name}")
print(f'  是否存在实体ID为"{source_name}": {source_name in entities}')

# 建立名称到ID的映射
name_to_id = {}
for eid, e in entities.items():
    name = e.get("名称", "")
    if name:
        name_to_id[name] = eid

print(f'  名称"{source_name}"对应的ID: {name_to_id.get(source_name, "未找到")}')
