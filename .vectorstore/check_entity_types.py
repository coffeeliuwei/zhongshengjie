#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("knowledge_graph.json", "r", encoding="utf-8") as f:
    data = json.load(f)

entities = data.get("实体", {})

# 统计实体类型
type_counts = {}
for e in entities.values():
    t = e.get("类型", "未知")
    type_counts[t] = type_counts.get(t, 0) + 1

print("实体类型分布:")
for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f"  {t}: {count}")

# 检查元数据
metadata = data.get("元数据", {})
print()
print("元数据:")
print(f"  数据来源: {metadata.get('数据来源', [])}")
print(f"  版本: {metadata.get('版本', '?')}")

# 找一个技术基础实体，查看来源字段
print()
print("技术基础实体样例:")
for eid, e in entities.items():
    if e.get("类型") == "技术基础":
        name = e.get("名称")
        attrs = e.get("属性", {})
        source = attrs.get("来源", "?")
        domain = attrs.get("技术领域", "?")
        civilization = attrs.get("文明", "?")
        print(f"  {name}:")
        print(f"    来源: {source}")
        print(f"    技术领域: {domain}")
        print(f"    文明: {civilization}")
        break
