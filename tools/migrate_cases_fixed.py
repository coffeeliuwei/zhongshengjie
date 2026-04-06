#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分批迁移案例库 - 修复版
=======================

修复：使用 content_preview 而非 content
"""

import gc
import json
import sys
from pathlib import Path
from datetime import datetime

# 加载配置
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config_loader import (
    get_project_root,
    get_model_path,
    get_qdrant_url,
    get_vectorstore_dir,
)

PROJECT_DIR = get_project_root()
BGE_M3_MODEL_PATH = get_model_path()
QDRANT_DOCKER_URL = get_qdrant_url()
PROGRESS_FILE = get_vectorstore_dir() / "migration_progress.json"

BATCH_SIZE = 50  # 每批处理数量
MEMORY_RELEASE_INTERVAL = 20  # 每N批释放内存


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{ts}] {msg}", flush=True)
    except:
        print(
            f"[{ts}] {msg.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')}",
            flush=True,
        )


def load_progress():
    if PROGRESS_FILE.exists():
        try:
            return json.load(open(PROGRESS_FILE, encoding="utf-8"))
        except:
            pass
    return {"last_offset": None, "migrated_count": 0}


def save_progress(progress):
    progress["last_update"] = datetime.now().isoformat()
    json.dump(progress, open(PROGRESS_FILE, "w", encoding="utf-8"), indent=2)


def main():
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import PointStruct
    from FlagEmbedding import BGEM3FlagModel

    client = QdrantClient(url=QDRANT_DOCKER_URL)

    log("=" * 60)
    log("Case Library Migration (Fixed)")
    log("=" * 60)

    # 加载进度
    progress = load_progress()
    start_offset = progress.get("last_offset")
    migrated_count = progress.get("migrated_count", 0)

    log(f"Start offset: {start_offset}")
    log(f"Already migrated: {migrated_count:,}")

    # 获取源和目标数量
    old_info = client.get_collection("case_library")
    new_info = client.get_collection("case_library_v2")
    total_old = old_info.points_count
    total_new = new_info.points_count

    log(f"Source: {total_old:,}, Target: {total_new:,}")

    if total_new >= total_old * 0.99:
        log("Already fully migrated!")
        return

    # 加载模型
    log("\nLoading BGE-M3 model...")
    model = BGEM3FlagModel(BGE_M3_MODEL_PATH, use_fp16=True, device="cpu")
    log("Model loaded")

    # 获取已迁移的ID
    log("\nLoading migrated IDs...")
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
    log(f"Migrated IDs: {len(migrated_ids):,}")

    # 迁移
    log("\nStarting migration...")
    batch = []
    batch_num = 0
    offset = start_offset

    while True:
        batch_num += 1

        # 读取一批数据
        results, new_offset = client.scroll(
            collection_name="case_library",
            offset=offset,
            limit=BATCH_SIZE,
            with_payload=True,
            with_vectors=False,
        )

        if not results:
            log("\nNo more data")
            break

        for point in results:
            # 跳过已迁移的
            if point.id in migrated_ids:
                continue

            try:
                # 使用 content_preview 而非 content
                content = point.payload.get("content_preview", "")
                if not content:
                    content = point.payload.get("content", "")

                if not content or len(content.strip()) < 50:
                    continue

                # 生成向量
                out = model.encode(
                    [content[:2000]], return_dense=True, return_sparse=True
                )

                # 创建新点
                new_point = PointStruct(
                    id=point.id,
                    vector={
                        "dense": out["dense_vecs"][0].tolist(),
                        "sparse": {
                            "indices": list(out["lexical_weights"][0].keys()),
                            "values": list(out["lexical_weights"][0].values()),
                        },
                    },
                    payload={
                        "novel_name": point.payload.get("novel_name", "未知"),
                        "scene_type": point.payload.get("scene_type", "未知"),
                        "genre": point.payload.get("genre", "未知"),
                        "quality_score": point.payload.get("quality_score", 0),
                        "word_count": point.payload.get("word_count", 0),
                        "content": content[:5000],
                    },
                )
                batch.append(new_point)
                migrated_ids.add(point.id)

            except Exception as e:
                continue

        # 写入
        if batch:
            try:
                client.upsert("case_library_v2", batch)
                migrated_count += len(batch)
            except Exception as e:
                log(f"  Error: {e}")
            batch = []

        # 更新进度
        offset = new_offset
        progress["last_offset"] = str(offset) if offset else None
        progress["migrated_count"] = migrated_count

        # 每5批保存进度并报告
        if batch_num % 5 == 0:
            save_progress(progress)
            log(f"  Batch {batch_num}: {migrated_count:,} migrated")

        # 每20批释放内存
        if batch_num % MEMORY_RELEASE_INTERVAL == 0:
            gc.collect()

        if new_offset is None:
            break

    # 最终保存
    save_progress(progress)

    # 验证
    final_info = client.get_collection("case_library_v2")
    log(f"\nFinal: case_library_v2 = {final_info.points_count:,}")
    log(f"Migrated this run: {migrated_count:,}")
    log("Done!")


if __name__ == "__main__":
    main()
