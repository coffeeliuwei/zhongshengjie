#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分批增量迁移 - 低内存模式
=========================

特性：
1. 每批只处理100条，避免内存溢出
2. 支持断点续传（记录进度到文件）
3. 定期释放内存
4. 可控制迁移速度

用法：
    python tools/migrate_batch_low_memory.py
"""

import os
import sys
import gc
import json
from pathlib import Path
from datetime import datetime

# 加载配置
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config_loader import (
    get_project_root,
    get_model_path,
    get_vectorstore_dir,
    get_qdrant_url,
)

PROJECT_DIR = get_project_root()
QDRANT_DOCKER_URL = get_qdrant_url()
PROGRESS_FILE = get_vectorstore_dir() / "migration_progress.json"

# 配置
BATCH_SIZE = 100  # 每批处理数量
MAX_MEMORY_BATCHES = 10  # 每N批强制释放内存


def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{timestamp}] {msg}", flush=True)
    except:
        print(
            f"[{timestamp}] {msg.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')}",
            flush=True,
        )


def load_progress():
    """加载迁移进度"""
    if PROGRESS_FILE.exists():
        try:
            return json.load(open(PROGRESS_FILE, encoding="utf-8"))
        except:
            pass
    return {
        "case_library": {"last_offset": None, "migrated_count": 0},
        "last_update": None,
    }


def save_progress(progress):
    """保存迁移进度"""
    progress["last_update"] = datetime.now().isoformat()
    json.dump(progress, open(PROGRESS_FILE, "w", encoding="utf-8"), indent=2)


def migrate_cases_batch():
    """分批迁移案例库"""
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import PointStruct

    client = QdrantClient(url=QDRANT_DOCKER_URL)

    log("=" * 60)
    log("Case Library Batch Migration (Low Memory Mode)")
    log("=" * 60)

    # 加载进度
    progress = load_progress()
    start_offset = progress["case_library"].get("last_offset")
    migrated_count = progress["case_library"].get("migrated_count", 0)

    log(f"Resuming from offset: {start_offset}")
    log(f"Already migrated: {migrated_count:,}")

    # 获取总数
    old_info = client.get_collection("case_library")
    total = old_info.points_count
    log(f"Total to migrate: {total:,}")

    # 加载模型（只加载一次）
    log("\nLoading BGE-M3 model...")
    from FlagEmbedding import BGEM3FlagModel

    model_path = get_model_path()
    model = BGEM3FlagModel(model_path or "BAAI/bge-m3", use_fp16=True, device="cpu")
    log("Model loaded")

    # 分批迁移
    offset = start_offset
    batch_num = 0

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
            log("\nNo more data to migrate")
            break

        # 处理这批数据
        batch = []
        for point in results:
            try:
                content = point.payload.get("content", "")[:2000]
                if not content.strip():
                    continue

                # 生成向量
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

            except Exception as e:
                continue

        # 写入Qdrant
        if batch:
            try:
                client.upsert("case_library_v2", batch)
                migrated_count += len(batch)
            except Exception as e:
                log(f"  Error writing batch: {e}")

        # 更新进度
        offset = new_offset
        progress["case_library"]["last_offset"] = str(offset) if offset else None
        progress["case_library"]["migrated_count"] = migrated_count

        # 每N批保存一次进度
        if batch_num % 5 == 0:
            save_progress(progress)
            log(
                f"  Batch {batch_num}: {migrated_count:,} / {total:,} ({migrated_count * 100 / total:.1f}%)"
            )

        # 每N批释放内存
        if batch_num % MAX_MEMORY_BATCHES == 0:
            gc.collect()

        # 检查是否完成
        if new_offset is None:
            log("\nMigration completed!")
            break

        # 安全检查：如果迁移数量超过预期，停止
        if migrated_count > total + 10000:
            log(f"\nWarning: Migrated count ({migrated_count}) exceeds total ({total})")
            break

    # 最终保存
    save_progress(progress)

    # 验证
    new_info = client.get_collection("case_library_v2")
    log(f"\nFinal: case_library_v2 = {new_info.points_count:,}")
    log(f"Migrated in this run: {migrated_count:,}")

    # 清理模型释放内存
    del model
    gc.collect()


def main():
    log("=" * 60)
    log("BGE-M3 Batch Migration (Low Memory)")
    log(f"Batch size: {BATCH_SIZE}")
    log(f"Memory release every: {MAX_MEMORY_BATCHES} batches")
    log("=" * 60)

    migrate_cases_batch()

    log("\nDone!")


if __name__ == "__main__":
    main()
