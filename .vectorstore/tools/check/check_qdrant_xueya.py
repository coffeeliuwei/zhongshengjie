# -*- coding: utf-8 -*-
"""检查Qdrant中血牙的完整数据"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
import json
from qdrant_client import QdrantClient\nfrom core.config_loader import get_qdrant_url

client = QdrantClient(url=get_qdrant_url())
results = client.scroll(
    collection_name="novel_settings_v2",
    with_payload=True,
    with_vectors=False,
    limit=200,
)[0]

for p in results:
    if "xueya" in p.payload.get("name", ""):
        print("找到血牙:")
        print(f"  name: {p.payload.get('name')}")
        print(f"  type: {p.payload.get('type')}")
        desc = p.payload.get("description")
        if desc:
            print(f"  description: {desc[:100]}")
        else:
            print(f"  description: None")
        props = p.payload.get("properties", "{}")
        print(f"  properties长度: {len(props)}")
        print(f"  properties内容: {props}")
        print()
        # 解析properties
        props_dict = json.loads(props)
        print(f"  解析后keys: {list(props_dict.keys())}")
        attrs = props_dict.get("属性", {})
        print(f"  属性keys: {list(attrs.keys())}")
        print(f"  初始派别: {attrs.get('初始派别')}")
        print(f"  初始能力: {attrs.get('初始能力')}")
