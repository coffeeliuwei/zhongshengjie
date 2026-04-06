#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("knowledge_graph.json", "r", encoding="utf-8") as f:
    data = json.load(f)

entities = data.get("实体", {})

# 检查力量派别实体
print("力量派别实体样例:")
count = 0
for eid, e in entities.items():
    if e.get("类型") == "力量派别":
        count += 1
        if count <= 5:
            print(f"\n  ID: {eid}")
            print(f"  名称: {e.get('名称')}")
            attrs = e.get("属性", {})
            print(f"  属性: {list(attrs.keys())}")
            if attrs:
                for k, v in list(attrs.items())[:3]:
                    print(f"    {k}: {v}")

print(f"\n共 {count} 个力量派别实体")

# 检查力量体系实体
print("\n\n力量体系实体:")
for eid, e in entities.items():
    if e.get("类型") == "力量体系":
        print(f"  - {e.get('名称')}")
