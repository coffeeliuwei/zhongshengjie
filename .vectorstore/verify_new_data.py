#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("knowledge_graph.json", "r", encoding="utf-8") as f:
    data = json.load(f)

entities = data.get("实体", {})

# 统计类型
type_counts = {}
for e in entities.values():
    t = e.get("类型", "未知")
    type_counts[t] = type_counts.get(t, 0) + 1

print("实体类型分布:")
for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f"  {t}: {count}")

# 检查场景模板
print("\n场景模板:")
templates = [e for e in entities.values() if e.get("类型") == "预判模板"]
print(f"  共{len(templates)}个")
for t in templates[:3]:
    attrs = t.get("属性", {})
    print(f"  - {t.get('名称')}: {attrs.get('核心要素', '?')}")

# 检查情绪状态
print("\n情绪状态对照表:")
if "emotion_states_reference" in entities:
    ref = entities["emotion_states_reference"]
    attrs = ref.get("属性", {})
    for emotion, data in attrs.items():
        print(f"  - {emotion}: {data.get('行为倾向', '?')}")

# 检查角色深度设定
print("\n角色深度设定:")
char_count = 0
for eid, e in entities.items():
    if e.get("类型") == "角色":
        name = e.get("名称")
        attrs = e.get("属性", {})
        if isinstance(attrs, str):
            attrs = json.loads(attrs)
        backstory = attrs.get("过往经历", {})
        emotions = attrs.get("情绪触发", {})
        imprints = attrs.get("行为烙印", [])
        if backstory or emotions or imprints:
            char_count += 1
            if char_count <= 3:
                print(f"  {name}:")
                print(f"    过往经历: {len(backstory)}项")
                print(f"    情绪触发: {len(emotions)}种")
                print(f"    行为烙印: {len(imprints)}条")

print(f"\n  共{char_count}个角色有深度设定")
