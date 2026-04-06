#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证哲学设定和社会结构是否正确合并"""

import sys
import json
from pathlib import Path

# Windows编码修复
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
print("哲学设定验证")
print("=" * 60)

# 检查角色哲学设定
philosophy_count = 0
for entity_id, entity in entities.items():
    if entity_id.startswith("char_"):
        props = entity.get("属性", {})
        if "哲学设定" in props:
            philosophy_count += 1
            name = entity.get("名称", entity_id)
            philosophy = props["哲学设定"].get("哲学流派", "未知")
            print(f"  + {name}: {philosophy}")

print(f"\n总计: {philosophy_count} 个角色有哲学设定")

# 血牙具体验证
xueya = entities.get("char_xueya", {})
if xueya:
    props = xueya.get("属性", {})
    print("\n血牙哲学设定详情:")
    if "哲学设定" in props:
        for key, value in props["哲学设定"].items():
            print(f"  - {key}: {value}")
    else:
        print("  [警告] 血牙无哲学设定!")

print("\n" + "=" * 60)
print("社会结构验证")
print("=" * 60)

# 检查势力社会结构
society_count = 0
for entity_id, entity in entities.items():
    if entity_id.startswith("faction_"):
        props = entity.get("属性", {})
        if "社会结构" in props:
            society_count += 1
            name = entity.get("名称", entity_id)
            print(f"  + {name}")

print(f"\n总计: {society_count} 个势力有社会结构")

# 东方修仙具体验证
eastern = entities.get("faction_eastern_cultivation", {})
if eastern:
    props = eastern.get("属性", {})
    print("\n东方修仙社会结构详情:")
    if "社会结构" in props:
        for key, value in props["社会结构"].items():
            print(f"  - {key}: {type(value).__name__}")
    else:
        print("  [警告] 东方修仙无社会结构!")

print("\n" + "=" * 60)
print("[完成] 验证结束")
print("=" * 60)
