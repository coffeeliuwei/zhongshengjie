#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("knowledge_graph.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 搜索参考文献相关
print('搜索"参考文献"相关实体:')
for eid, e in data.get("实体", {}).items():
    name = e.get("名称", "")
    if "参考文献" in name or "参考" in name:
        print(f"\n  ID: {eid}")
        print(f"  名称: {name}")
        print(f"  类型: {e.get('类型')}")
        attrs = e.get("属性", {})
        for k, v in attrs.items():
            print(f"  {k}: {v}")

# 搜索来源于李道远团队的关系
print('\n\n搜索"来源于"->"李道远团队"的关系:')
for r in data.get("关系", []):
    if r.get("关系类型") == "来源于" and "李道远" in r.get("目标实体", ""):
        print(f"  源: {r.get('源实体')} -> 目标: {r.get('目标实体')}")
