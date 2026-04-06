#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查Qdrant Docker数据库状态"""

import os

os.environ["HF_HUB_OFFLINE"] = "1"

from qdrant_client import QdrantClient

# Docker Qdrant URL (统一数据源)
QDRANT_DOCKER_URL = "http://localhost:6333"

print("=" * 60)
print("Qdrant Docker Collections 状态")
print("=" * 60)

try:
    client = QdrantClient(url=QDRANT_DOCKER_URL)

    collections = client.get_collections()

    for c in collections.collections:
        info = client.get_collection(c.name)
        print(f"{c.name}: {info.points_count:,}")

    print()
    print("=" * 60)
    print("数据库连接成功")
    print("=" * 60)

except Exception as e:
    print(f"错误: {e}")
