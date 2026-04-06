#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from qdrant_client import QdrantClient
from core.config_loader import get_qdrant_url
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

client = QdrantClient(url=get_qdrant_url())

# 搜索技术基础类型实体
results = client.scroll(
    collection_name="novel_settings_v2",
    scroll_filter=Filter(
        must=[FieldCondition(key="type", match=MatchValue(value="技术基础"))]
    ),
    limit=5,
    with_payload=True,
)[0]

print("技术基础实体样例:")
print()
for p in results:
    props = (
        json.loads(p.payload["properties"])
        if isinstance(p.payload["properties"], str)
        else p.payload["properties"]
    )
    name = props.get("名称", "?")
    attrs = props.get("属性", {})
    print(f"名称: {name}")
    print(f"  文明: {attrs.get('文明', '?')}")
    print(f"  来源: {attrs.get('来源', '?')}")
    print(f"  技术领域: {attrs.get('技术领域', '?')}")
    print()

# 统计各类型实体数量
print("=" * 50)
print("实体类型统计:")
all_points = client.scroll(
    collection_name="novel_settings_v2", limit=200, with_payload=True
)[0]
type_counts = {}
for p in all_points:
    t = p.payload.get("type", "未知")
    type_counts[t] = type_counts.get(t, 0) + 1

for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f"  {t}: {count}")
