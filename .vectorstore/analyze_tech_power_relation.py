#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析科技基础和力量派别之间的潜在关系
"""

import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("knowledge_graph.json", "r", encoding="utf-8") as f:
    data = json.load(f)

entities = data.get("实体", {})

# 按力量体系分组力量派别
power_branches = {}
for eid, e in entities.items():
    if e.get("类型") == "力量派别":
        system = e.get("属性", {}).get("力量体系", "未知")
        if system not in power_branches:
            power_branches[system] = []
        power_branches[system].append(e.get("名称", "?"))

# 按文明分组技术基础
tech_bases = {}
for eid, e in entities.items():
    if e.get("类型") == "技术基础":
        civ = e.get("属性", {}).get("文明", "未知")
        if civ not in tech_bases:
            tech_bases[civ] = []
        tech_bases[civ].append(e.get("名称", "?"))

print("=" * 70)
print("科技基础与力量派别对照分析")
print("=" * 70)

print("\n【科技文明技术】→ 科技力量派别")
print("-" * 50)
for tech in tech_bases.get("科技文明", []):
    print(f"  {tech}")

print("\n科技体系派别:")
for branch in power_branches.get("科技", []):
    print(f"  - {branch}")

print("\n" + "=" * 70)
print("\n【异化人文明技术】→ 异能力量派别")
print("-" * 50)
for tech in tech_bases.get("异化人文明", []):
    print(f"  {tech}")

print("\n异能体系派别:")
for branch in power_branches.get("异能", []):
    print(f"  - {branch}")

print("\n" + "=" * 70)
print("\n【AI文明技术】→ AI力力量派别")
print("-" * 50)
for tech in tech_bases.get("AI文明", []):
    print(f"  {tech}")

print("\nAI力体系派别:")
for branch in power_branches.get("AI力", []):
    print(f"  - {branch}")

print("\n" + "=" * 70)
print("其他力量体系（可能是天然的）:")
print("-" * 50)
for system in ["修仙", "魔法", "神术", "兽力"]:
    if system in power_branches:
        print(f"\n{system}体系 ({len(power_branches[system])}个派别):")
        for branch in power_branches[system][:5]:
            print(f"  - {branch}")
        if len(power_branches[system]) > 5:
            print(f"  ... 共{len(power_branches[system])}个")
