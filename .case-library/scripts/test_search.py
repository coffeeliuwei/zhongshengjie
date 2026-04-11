#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试Qdrant Docker检索功能"""

from qdrant_client import QdrantClient
from qdrant_client.http.models import QueryRequest
from sentence_transformers import SentenceTransformer

# 连接Docker Qdrant
client = QdrantClient(url="http://localhost:6333")
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# 测试查询
queries = ["打脸震惊反转为傲", "战斗热血生死对决"]

print("=" * 60)
print("Qdrant Docker 检索测试")
print("=" * 60)

for query in queries:
    print(f"\n查询: {query}")
    print("-" * 40)

    # 生成嵌入
    vector = model.encode(query).tolist()

    # 检索 (使用query方法)
    results = client.query_points(collection_name="case_library", query=vector, limit=3)

    for i, hit in enumerate(results.points, 1):
        payload = hit.payload
        print(f"\n[{i}] 相似度: {hit.score:.4f}")
        print(f"    场景: {payload.get('scene_type', 'N/A')}")
        print(f"    小说: {payload.get('novel_name', 'N/A')}")
        preview = payload.get("content_preview", "")
        if preview:
            print(f"    预览: {preview[:80]}...")

print("\n" + "=" * 60)
print("检索测试完成！Docker模式工作正常")
print("=" * 60)
