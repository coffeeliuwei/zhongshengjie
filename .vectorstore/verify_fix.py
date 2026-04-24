#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("knowledge_graph.json", "r", encoding="utf-8") as f:
    data = json.load(f)

entities = data.get("实体", {})

# 检查问题实体是否已移除
print("检查问题实体是否已移除:")
problem_names = [
    "参考文献",
    "技术路线图整合",
    "20位主角血脉技术原理速查",
    "限制与代价",
    "技术树",
    "使用指南",
]
for name in problem_names:
    found = any(e.get("名称") == name for e in entities.values())
    status = "❌ 仍存在" if found else "✅ 已移除"
    print(f"  {status} - {name}")

# 统计技术基础类型
print("\n技术基础类型实体:")
tech_bases = [
    (e.get("名称", "?"), e.get("属性", {}).get("文明", "?"))
    for e in entities.values()
    if e.get("类型") == "技术基础"
]
for name, civ in tech_bases:
    print(f"  - {name} ({civ})")

print(f"\n共 {len(tech_bases)} 个技术基础实体")

# 统计实体类型分布
print("\n实体类型分布:")
type_counts = {}
for e in entities.values():
    t = e.get("类型", "未知")
    type_counts[t] = type_counts.get(t, 0) + 1
for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f"  {t}: {count}")
