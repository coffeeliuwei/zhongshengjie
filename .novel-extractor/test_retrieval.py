#!/usr/bin/env python
"""测试BGE-M3融合检索效果"""

import json
import sys

sys.path.insert(0, ".")

from qdrant_client import QdrantClient
from FlagEmbedding import BGEM3FlagModel


def load_config():
    with open("../config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def test_retrieval():
    config = load_config()
    model_path = config["model"]["model_path"]
    cache_dir = config["model"]["hf_cache_dir"]

    print("加载BGE-M3模型...")
    model = BGEM3FlagModel(
        model_path, use_fp16=True, normalize_embeddings=True, cache_dir=cache_dir
    )

    client = QdrantClient(url="http://localhost:6333")

    test_queries = [
        "修仙突破境界",
        "师徒传承关系",
        "剑法功法招式",
        "主角遭遇挫折后的成长",
    ]

    for query in test_queries:
        print(f"\n=== 测试查询: {query} ===")

        embedding = model.encode(
            [query], return_dense=True, return_sparse=True, return_colbert_vecs=True
        )

        # Dense检索 - worldview_element
        print("\n[Dense检索] worldview_element_v1:")
        dense_hits = client.query_points(
            collection_name="worldview_element_v1",
            query=embedding["dense_vecs"][0].tolist(),
            using="dense",
            limit=3,
            with_payload=True,
        )
        for i, hit in enumerate(dense_hits.points):
            text = hit.payload.get("text", "")
            element_type = hit.payload.get("element_type", "")
            print(f"  {i + 1}. score={hit.score:.4f} type={element_type}")
            print(f"     text: {text[:100]}")

        # Dense检索 - power_vocabulary
        print("\n[Dense检索] power_vocabulary_v1:")
        vocab_hits = client.query_points(
            collection_name="power_vocabulary_v1",
            query=embedding["dense_vecs"][0].tolist(),
            using="dense",
            limit=3,
            with_payload=True,
        )
        for i, hit in enumerate(vocab_hits.points):
            text = hit.payload.get("text", "")
            category = hit.payload.get("category", "")
            print(f"  {i + 1}. score={hit.score:.4f} category={category}")
            print(f"     text: {text[:100]}")

        # Dense检索 - character_relation
        print("\n[Dense检索] character_relation_v1:")
        char_hits = client.query_points(
            collection_name="character_relation_v1",
            query=embedding["dense_vecs"][0].tolist(),
            using="dense",
            limit=2,
            with_payload=True,
        )
        for i, hit in enumerate(char_hits.points):
            text = hit.payload.get("text", "")
            c1 = hit.payload.get("character1", "")
            c2 = hit.payload.get("character2", "")
            print(f"  {i + 1}. score={hit.score:.4f} chars={c1}-{c2}")
            print(f"     text: {text[:80]}")


if __name__ == "__main__":
    test_retrieval()
