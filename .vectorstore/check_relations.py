#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("knowledge_graph.json", "r", encoding="utf-8") as f:
    data = json.load(f)

relations = data.get("关系", [])

# 统计关系类型
rel_types = {}
for r in relations:
    rt = r.get("关系类型", "未知")
    rel_types[rt] = rel_types.get(rt, 0) + 1

print("现有关系类型统计:")
for rt, count in sorted(rel_types.items(), key=lambda x: -x[1]):
    print(f"  {rt}: {count}")

print()
print('检查是否有"来源于"关系:')
has_source = any(r.get("关系类型") == "来源于" for r in relations)
print(f"  存在: {has_source}")

print()
print('检查是否有"涉及领域"关系:')
has_domain = any(r.get("关系类型") == "涉及领域" for r in relations)
print(f"  存在: {has_domain}")

print()
print('检查是否有"涉及势力"关系:')
has_faction = any(r.get("关系类型") == "涉及势力" for r in relations)
print(f"  存在: {has_faction}")
