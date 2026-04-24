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

print("关系类型统计:")
for rt, count in sorted(rel_types.items(), key=lambda x: -x[1]):
    print(f"  {rt}: {count}")

print()
print("来源于关系样例 (前5条):")
count = 0
for r in relations:
    if r.get("关系类型") == "来源于":
        print(f"  {r.get('源实体')} -> {r.get('目标实体')}")
        count += 1
        if count >= 5:
            break

print()
print("涉及领域关系样例 (前5条):")
count = 0
for r in relations:
    if r.get("关系类型") == "涉及领域":
        print(f"  {r.get('源实体')} -> {r.get('目标实体')}")
        count += 1
        if count >= 5:
            break

print()
print("涉及势力关系样例 (前5条):")
count = 0
for r in relations:
    if r.get("关系类型") == "涉及势力":
        print(f"  {r.get('源实体')} -> {r.get('目标实体')}")
        count += 1
        if count >= 5:
            break
