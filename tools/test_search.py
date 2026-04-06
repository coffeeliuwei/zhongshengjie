#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试 BGE-M3 混合检索"""

import os
import sys
from pathlib import Path

# 加载配置
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config_loader import get_vectorstore_dir, get_model_path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from qdrant_client import QdrantClient
from FlagEmbedding import BGEM3FlagModel

# 连接本地 Qdrant
qdrant_path = get_vectorstore_dir() / "qdrant"
client = QdrantClient(path=str(qdrant_path))

# 检查 Collection 状态
collections = client.get_collections().collections
print("Collection 列表:")
for c in collections:
    info = client.get_collection(c.name)
    print(f"  {c.name}: {info.points_count} 条")

# 测试 Dense 检索
print("\n测试 Dense 检索 (novel_settings_v2):")
model_path = get_model_path()
model = BGEM3FlagModel(model_path or "BAAI/bge-m3", use_fp16=True, device="cpu")

query = "林夕"
output = model.encode([query], return_dense=True, return_sparse=True)

# Dense 检索
results = client.query_points(
    collection_name="novel_settings_v2",
    query=output["dense_vecs"][0].tolist(),
    using="dense",
    limit=3,
    with_payload=True,
)

for r in results.points:
    name = r.payload.get("name", "N/A")
    score = r.score
    print(f"  - {name} (score: {score:.4f})")

# 测试 Dense+Sparse 混合检索
print("\n测试 Dense+Sparse 混合检索 (writing_techniques_v2):")
from qdrant_client.http.models import SparseVector
from collections import defaultdict

query2 = "战斗代价描写"
output2 = model.encode([query2], return_dense=True, return_sparse=True)

sparse_vec = SparseVector(
    indices=list(output2["lexical_weights"][0].keys()),
    values=list(output2["lexical_weights"][0].values()),
)

# Dense 召回
dense_results = client.query_points(
    collection_name="writing_techniques_v2",
    query=output2["dense_vecs"][0].tolist(),
    using="dense",
    limit=20,
    with_payload=True,
)

# Sparse 召回
sparse_results = client.query_points(
    collection_name="writing_techniques_v2",
    query=sparse_vec,
    using="sparse",
    limit=20,
    with_payload=True,
)

# 合并结果（RRF）
rrf_scores = defaultdict(float)
doc_data = {}

for i, r in enumerate(dense_results.points):
    rrf_scores[r.id] += 1 / (60 + i)  # RRF 公式
    doc_data[r.id] = r

for i, r in enumerate(sparse_results.points):
    rrf_scores[r.id] += 1 / (60 + i)
    doc_data[r.id] = r

# 排序
sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:5]

print("混合检索结果 (Dense + Sparse, RRF融合):")
for doc_id, score in sorted_ids:
    r = doc_data[doc_id]
    name = r.payload.get("name", "N/A")
    dim = r.payload.get("dimension", "N/A")
    print(f"  - [{dim}] {name} (rrf: {score:.4f})")

print("\n测试完成!")
