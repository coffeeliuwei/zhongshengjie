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
        system = e.get("属性", {}).get("所属力量体系", "未知")
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

# 文明 → 力量体系映射
civ_to_power = {
    "科技文明": "科技",
    "AI文明": "AI力",
    "异化人文明": "异能",
}

for civ, power_system in civ_to_power.items():
    techs = tech_bases.get(civ, [])
    branches = power_branches.get(power_system, [])

    print(f"\n【{civ}技术】→ {power_system}体系")
    print("-" * 50)
    print(f"技术基础 ({len(techs)}个):")
    for tech in techs:
        print(f"  • {tech}")

    print(f"\n{power_system}派别 ({len(branches)}个):")
    for branch in branches:
        print(f"  - {branch}")

    # 分析可能的衍生关系
    print(f"\n可能的衍生关系建议:")
    if civ == "异化人文明":
        print("  基因编辑突破 → 变形系 (基因改造变形能力)")
        print("  跨物种基因融合 → 兽化系 (动物基因融合)")
        print("  干细胞与再生医学 → 再生系 (快速愈合)")
        print("  神经科学意识研究 → 心灵感应系 (量子意识)")
    elif civ == "科技文明":
        print("  脑机接口（BCI） → 神经链接系 (脑机控制)")
        print("  意识上传理论 → 意识转移系 (意识数字化)")
        print("  量子计算突破 → 量子计算系 (量子武器)")
    elif civ == "AI文明":
        print("  AI意识理论框架 → 自我进化系 (AI自主进化)")
        print("  量子意识网络 → 网络入侵系 (量子网络攻击)")

print("\n" + "=" * 70)
print("天然力量体系（非科技衍生）:")
print("-" * 50)

natural_systems = ["修仙", "魔法", "神术", "兽力"]
for system in natural_systems:
    branches = power_branches.get(system, [])
    print(f"\n{system}体系 ({len(branches)}个派别):")
    for branch in branches:
        print(f"  - {branch}")

print("\n" + "=" * 70)
print("总结:")
print("-" * 50)
print("科技衍生型力量体系: 科技、AI力、异能")
print("天然/修炼型力量体系: 修仙、魔法、神术、兽力")
