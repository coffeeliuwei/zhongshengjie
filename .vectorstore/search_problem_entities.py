#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("knowledge_graph.json", "r", encoding="utf-8") as f:
    data = json.load(f)

entities = data.get("实体", {})

# 搜索问题实体
keywords = ["参考文献", "技术路线图", "速查", "整合"]
print("搜索可能的错误解析实体:")
print("=" * 60)

for eid, e in entities.items():
    name = e.get("名称", "")
    etype = e.get("类型", "")

    # 检查是否匹配关键词
    for kw in keywords:
        if kw in name:
            print(f"\n实体ID: {eid}")
            print(f"名称: {name}")
            print(f"类型: {etype}")
            attrs = e.get("属性", {})
            print("属性:")
            for k, v in attrs.items():
                if isinstance(v, str) and len(v) > 80:
                    print(f"  {k}: {v[:80]}...")
                else:
                    print(f"  {k}: {v}")
            break

# 统计技术基础类型
print("\n" + "=" * 60)
print("技术基础类型实体列表:")
tech_bases = [(eid, e) for eid, e in entities.items() if e.get("类型") == "技术基础"]
for eid, e in tech_bases:
    name = e.get("名称", "")
    attrs = e.get("属性", {})
    civilization = attrs.get("文明", "?")
    source = attrs.get("来源", "?")
    print(f"  - {name} (文明: {civilization}, 来源: {source})")
