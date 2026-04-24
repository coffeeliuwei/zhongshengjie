#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("knowledge_graph.json", "r", encoding="utf-8") as f:
    data = json.load(f)

entity = data.get("实体", {}).get("techbase_20位主角血脉技术原理速查", {})
print("实体详情:")
print(f"  ID: {entity.get('id')}")
print(f"  名称: {entity.get('名称')}")
print(f"  类型: {entity.get('类型')}")
print()
print("属性:")
attrs = entity.get("属性", {})
for k, v in attrs.items():
    if isinstance(v, list):
        print(f"  {k}: {len(v)}项")
        if v and len(v) <= 10:
            for item in v[:3]:
                if isinstance(item, dict):
                    print(f"    - {item}")
                else:
                    print(f"    - {item}")
    elif isinstance(v, str) and len(v) > 100:
        print(f"  {k}: {v[:100]}...")
    else:
        print(f"  {k}: {v}")
