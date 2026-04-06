#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
迁移技法从旧collection到v2 (BGE-M3编码)
=====================================

将 writing_techniques (1122条) 迁移到 writing_techniques_v2
使用 BGE-M3 编码 (1024维 dense + sparse)
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 加载配置
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config_loader import get_project_root, get_model_path, get_qdrant_url

PROJECT_DIR = get_project_root()

OLD_COLLECTION = "writing_techniques"
NEW_COLLECTION = "writing_techniques_v2"
QDRANT_DOCKER_URL = get_qdrant_url()


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    log("=" * 60)
    log("技法迁移: writing_techniques → writing_techniques_v2")
    log("=" * 60)

    # 连接Qdrant
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import (
        PointStruct,
        VectorParams,
        Distance,
        SparseVectorParams,
    )

    client = QdrantClient(url=QDRANT_DOCKER_URL)

    # 检查旧collection
    try:
        old_info = client.get_collection(OLD_COLLECTION)
        log(f"旧collection {OLD_COLLECTION}: {old_info.points_count} 条")
    except Exception as e:
        log(f"错误: 旧collection不存在: {e}")
        return

    # 检查新collection
    try:
        new_info = client.get_collection(NEW_COLLECTION)
        log(f"新collection {NEW_COLLECTION}: {new_info.points_count} 条")
    except:
        log(f"创建新collection {NEW_COLLECTION}...")
        client.create_collection(
            collection_name=NEW_COLLECTION,
            vectors_config={"dense": VectorParams(size=1024, distance=Distance.COSINE)},
            sparse_vectors_config={"sparse": SparseVectorParams()},
        )

    # 加载BGE-M3模型
    log("\n[1] 加载BGE-M3模型...")
    from FlagEmbedding import BGEM3FlagModel

    model_path = get_model_path()
    model = BGEM3FlagModel(model_path or "BAAI/bge-m3", use_fp16=True, device="cpu")
    log("    模型加载完成")

    # 读取旧数据
    log("\n[2] 读取旧collection数据...")
    old_data = []
    offset = None
    while True:
        results, offset = client.scroll(
            collection_name=OLD_COLLECTION,
            offset=offset,
            limit=100,
            with_payload=True,
            with_vectors=False,
        )
        old_data.extend(results)
        if offset is None:
            break
        log(f"    已读取 {len(old_data)} 条...")

    log(f"    共读取 {len(old_data)} 条技法")

    # 迁移数据
    log(f"\n[3] 迁移到 {NEW_COLLECTION}...")

    # 维度映射 (确保维度名称正确)
    dimension_fix_map = {
        "世界观": "世界观维度",
        "剧情": "剧情维度",
        "人物": "人物维度",
        "战斗冲突": "战斗冲突维度",
        "氛围意境": "氛围意境维度",
        "情感": "情感维度",
        "叙事": "叙事维度",
    }

    batch_size = 10
    for i, point in enumerate(old_data):
        try:
            # 获取内容
            content = point.payload.get("content", "")
            if not content:
                content = point.payload.get("principle", "")
            if not content:
                continue

            # 生成BGE-M3向量
            out = model.encode([content], return_dense=True, return_sparse=True)

            # 修复维度名称
            dimension = point.payload.get("dimension", "未知")
            dimension = dimension_fix_map.get(dimension, dimension)

            # 创建新点
            new_point = PointStruct(
                id=point.id,  # 保持原ID
                vector={
                    "dense": out["dense_vecs"][0].tolist(),
                    "sparse": {
                        "indices": list(out["lexical_weights"][0].keys()),
                        "values": list(out["lexical_weights"][0].values()),
                    },
                },
                payload={
                    "name": point.payload.get(
                        "name", point.payload.get("title", "未知")
                    ),
                    "dimension": dimension,
                    "writer": point.payload.get("writer", "未知"),
                    "content": content[:3000],
                    "word_count": len(content),
                    "source": point.payload.get(
                        "file", point.payload.get("source", "")
                    ),
                    "scenes": point.payload.get("scenes", []),
                    "principle": point.payload.get("principle", ""),
                    "notes": point.payload.get("notes", []),
                },
            )

            client.upsert(NEW_COLLECTION, [new_point])

            if (i + 1) % batch_size == 0:
                log(f"    已迁移 {i + 1}/{len(old_data)} 条")

        except Exception as e:
            log(f"    警告: ID {point.id} 迁移失败: {e}")
            continue

    # 验证
    log("\n[4] 验证迁移结果...")
    new_info = client.get_collection(NEW_COLLECTION)
    log(f"    {NEW_COLLECTION}: {new_info.points_count} 条")

    log("\n" + "=" * 60)
    log("迁移完成!")
    log("=" * 60)


if __name__ == "__main__":
    main()
