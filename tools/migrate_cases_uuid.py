#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
案例库UUID数据迁移 - 处理ID格式差异
================================

从 case_library (UUID IDs) 迁移到 case_library_v2 (Mixed IDs)
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
    log("Case Library UUID Migration (Fixed)")
    log("=" * 60)

    # 获取目标库中已有的UUID IDs（仅检查UUID类型）
    log("Checking existing UUID IDs in target...")
    existing_uuid_ids = set()
    offset = None
    uuid_count = 0
    int_count = 0
    while True:
        results, offset = client.scroll(
            collection_name="case_library_v2",
            offset=offset,
            limit=1000,
            with_payload=False,
            with_vectors=False,
        )
        for p in results:
            if isinstance(p.id, str):  # UUID是字符串类型
                existing_uuid_ids.add(p.id)
                uuid_count += 1
            else:
                int_count += 1
        if offset is None:
            break
    log(f"Target UUID IDs: {len(existing_uuid_ids):,}")
    log(f"Target Integer IDs: {int_count:,}")

    # 获取源库信息
    old_info = client.get_collection("case_library")
    total_source = old_info.points_count
    log(f"Source total (UUID): {total_source:,}")

    # 计算需要迁移的数量（源库UUID - 目标库已有UUID）
    to_migrate = total_source - len(existing_uuid_ids)
    log(f"UUID data to migrate: {to_migrate:,}")

    if to_migrate <= 0:
        log("All UUID data already migrated!")
        # 显示最终统计
        new_info = client.get_collection("case_library_v2")
        log(f"Final count: case_library_v2 = {new_info.points_count:,}")
        return

    # 迁移
    log("\nStarting UUID migration...")
    batch = []
    migrated = 0
    failed = 0
    skipped = 0

    # 先收集所有源库ID
    log("Collecting all source IDs...")
    all_source_ids = list(existing_uuid_ids)  # Already collected
    source_points = []
    offset = None
    while True:
        results, offset = client.scroll(
            collection_name="case_library",
            offset=offset,
            limit=500,
            with_payload=True,
            with_vectors=False,
        )
        if not results:
            break
        for point in results:
            if point.id not in existing_uuid_ids:
                source_points.append(point)
        if offset is None:
            break

    total_to_migrate = len(source_points)
    log(f"Found {total_to_migrate:,} points to migrate")

    if total_to_migrate == 0:
        log("Nothing to migrate!")
        return

    for i, point in enumerate(source_points):
        try:
            # 尝试不同的content字段名
            content = (
                point.payload.get("content", "")
                or point.payload.get("content_preview", "")
                or point.payload.get("text", "")
                or point.payload.get("case_content", "")
            )
            content = content[:2000] if content else ""

            if not content.strip():
                skipped += 1
                continue

            out = model.encode([content], return_dense=True, return_sparse=True)

            new_point = PointStruct(
                id=point.id,  # 保持原始UUID ID
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

            if len(batch) >= 50:
                client.upsert("case_library_v2", batch)
                migrated += len(batch)
                log(f"  Migrated: {migrated:,} / {total_to_migrate:,}")
                batch = []

        except Exception as e:
            failed += 1
            if failed <= 10:
                log(f"  Error: {e}")
            continue

        # 每500条检查一次进度
        if (i + 1) % 500 == 0:
            log(f"  Processing: {i + 1:,} / {total_to_migrate:,}")

    # 提交剩余数据
    if batch:
        try:
            client.upsert("case_library_v2", batch)
            migrated += len(batch)
        except Exception as e:
            log(f"Final batch error: {e}")
            failed += len(batch)

    # 最终统计
    log("\n" + "=" * 60)
    new_info = client.get_collection("case_library_v2")
    log(f"Final: case_library_v2 = {new_info.points_count:,} points")
    log(f"Migrated in this run: {migrated:,}")
    log(f"Failed: {failed:,}")
    log(f"Skipped (empty content): {skipped:,}")
    log(f"UUID coverage: {len(existing_uuid_ids) + migrated:,} / {total_source:,}")
    log("=" * 60)


if __name__ == "__main__":
    main()
