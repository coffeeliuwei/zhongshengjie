#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证力量体系和时间线整合"""

import sys
import json
from pathlib import Path

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except:
        pass

KNOWLEDGE_GRAPH = Path("knowledge_graph.json")

with open(KNOWLEDGE_GRAPH, "r", encoding="utf-8") as f:
    data = json.load(f)

entities = data.get("实体", {})

print("=" * 60)
print("力量体系实体验证")
print("=" * 60)

# 统计各类型实体
power_systems = []
power_branches = []
eras = []

for entity_id, entity in entities.items():
    entity_type = entity.get("类型", "")
    if entity_type == "力量体系":
        power_systems.append(entity_id)
    elif entity_type == "力量派别":
        power_branches.append(entity_id)
    elif entity_type == "时代":
        eras.append(entity_id)

print(f"\n力量体系总数: {len(power_systems)}")
for ps in power_systems:
    info = entities[ps].get("属性", {})
    print(f"  + {ps}: {info.get('名称', '未知')}")

print(f"\n力量派别总数: {len(power_branches)}")
beast_bloodlines = []
for pb in power_branches:
    info = entities[pb].get("属性", {})
    name = info.get("名称", "未知")
    print(f"  + {pb}: {name} ({info.get('类型', '未知')})")
    if "血脉" in name or pb.startswith("bloodline_"):
        beast_bloodlines.append((pb, name))

print(f"\n兽族血脉详情:")
for bl_id, bl_name in beast_bloodlines:
    info = entities[bl_id].get("属性", {})
    print(f"  [{bl_id}]")
    for key, value in info.items():
        print(f"    - {key}: {value}")

print("\n" + "=" * 60)
print("时代实体验证")
print("=" * 60)

print(f"\n时代总数: {len(eras)}")
for era_id in eras:
    info = entities[era_id].get("属性", {})
    print(f"  + {era_id}: {info.get('名称', '未知')} ({info.get('时间跨度', '未知')})")

print("\n" + "=" * 60)
print("血牙血脉验证")
print("=" * 60)

xueya = entities.get("char_xueya", {})
if xueya:
    props = xueya.get("属性", {})
    philosophy = props.get("哲学设定", {})
    print(f"哲学起点中血脉信息: {philosophy.get('哲学起点', '未知')}")

print("\n" + "=" * 60)
print("[完成] 验证结束")
print("=" * 60)
