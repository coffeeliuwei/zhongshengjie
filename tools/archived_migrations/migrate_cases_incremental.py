#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
案例库增量迁移 - 继续迁移剩余案例
=================================

从 case_library 迁移剩余数据到 case_library_v2 (BGE-M3)
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 加载配置
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config_loader import get_project_root, get_model_path, get_qdrant_url

PROJECT_DIR = get_project_root()
QDRANT_DOCKER_URL = get_qdrant_url()


def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{timestamp}] {msg}", flush=True)
    except:
        print(
            f"[{timestamp}] {msg.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')}",
            flush=True,
        )


def main():
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import PointStruct
    from FlagEmbedding import BGEM3FlagModel

    client = QdrantClient(url=QDRANT_DOCKER_URL)
    model_path = get_model_path()
    model = BGEM3FlagModel(model_path or "BAAI/bge-m3", use_fp16=True, device="cpu")

    log("=" * 60)
    log("Case Library Incremental Migration")
    log("=" * 60)

    # 获取已迁移的ID
    log("Loading migrated IDs...")
    migrated_ids = set()
    offset = None
    while True:
        results, offset = client.scroll(
            collection_name="case_library_v2",
            offset=offset,
            limit=1000,
            with_payload=False,
            with_vectors=False,
        )
        for p in results:
            migrated_ids.add(p.id)
        if offset is None:
            break
    log(f"Already migrated: {len(migrated_ids):,}")

    # 获取源数据总数
    old_info = client.get_collection("case_library")
    total_old = old_info.points_count
    log(f"Source total: {total_old:,}")

    # 计算需要迁移的数量
    to_migrate = total_old - len(migrated_ids)
    log(f"To migrate: {to_migrate:,}")

    if to_migrate <= 0:
        log("Nothing to migrate!")
        return

    # 迁移
    log("\nStarting migration...")
    batch = []
    migrated = 0
    offset = None

    while True:
        results, offset = client.scroll(
            collection_name="case_library",
            offset=offset,
            limit=200,
            with_payload=True,
            with_vectors=False,
        )

        if not results:
            break

        for point in results:
            if point.id in migrated_ids:
                continue

            try:
                content = point.payload.get("content", "")[:2000]
                if not content.strip():
                    continue

                out = model.encode([content], return_dense=True, return_sparse=True)

                new_point = PointStruct(
                    id=point.id,
                    vector={
                        "dense": out["dense_vecs"][0].tolist(),
                        "sparse": {
                            "indices": list(out["lexical_weights"][0].keys()),
                            "values": list(out["lexical_weights"][0].values()),
                        },
                    },
                    payload=point.payload,
                )
                batch.append(new_point)
                migrated_ids.add(point.id)

                if len(batch) >= 50:
                    client.upsert("case_library_v2", batch)
                    migrated += len(batch)
                    if migrated % 1000 == 0:
                        log(f"  Migrated: {migrated:,}")
                    batch = []

            except Exception as e:
                continue

        if offset is None:
            break

        # 每迁移10000条检查一次进度
        if migrated > 0 and migrated % 10000 == 0:
            new_info = client.get_collection("case_library_v2")
            log(f"  Progress: {new_info.points_count:,} / {total_old:,}")

    # 提交剩余数据
    if batch:
        client.upsert("case_library_v2", batch)
        migrated += len(batch)

    # 最终统计
    log("\n" + "=" * 60)
    new_info = client.get_collection("case_library_v2")
    log(f"Final: case_library_v2 = {new_info.points_count:,}")
    log(f"Migrated in this run: {migrated:,}")
    log("=" * 60)


if __name__ == "__main__":
    main()
