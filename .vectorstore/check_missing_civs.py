#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("knowledge_graph.json", "r", encoding="utf-8") as f:
    data = json.load(f)

entities = data.get("实体", {})

# 获取所有势力
factions = []
for eid, e in entities.items():
    if e.get("类型") == "势力":
        factions.append(
            {
                "id": eid,
                "名称": e.get("名称", "?"),
                "力量体系": e.get("属性", {}).get("力量体系", "?"),
            }
        )

print("现有势力列表:")
print("-" * 50)
for f in sorted(factions, key=lambda x: x.get("名称", "")):
    print(f"  {f.get('名称')} - 力量体系: {f.get('力量体系')}")

# 检查已有技术基础的文明
print("\n\n已有技术基础的文明:")
print("-" * 50)
tech_civs = set()
for eid, e in entities.items():
    if e.get("类型") == "技术基础":
        civ = e.get("属性", {}).get("文明", "?")
        tech_civs.add(civ)

for civ in sorted(tech_civs):
    print(f"  ✓ {civ}")

# 找出缺少技术基础的势力
print("\n\n缺少技术基础的势力/文明:")
print("-" * 50)
faction_power_systems = set(f.get("力量体系") for f in factions)
tech_civ_names = {"科技文明", "AI文明", "异化人文明"}  # 已有的

# 力量体系对应的文明/势力
power_to_faction = {
    "修仙": "东方修仙",
    "魔法": "西方魔法",
    "神术": "神殿教会",
    "武力": "佣兵联盟",
    "商业": "商盟",
    "军阵": "世俗帝国",
    "科技": "科技文明",
    "兽力": "兽族文明",
    "AI力": "AI文明",
    "异能": "异化人文明",
}

for power, faction in power_to_faction.items():
    if faction not in tech_civ_names:
        print(f"  ✗ {faction} ({power}体系)")
