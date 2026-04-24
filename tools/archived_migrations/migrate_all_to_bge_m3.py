#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整迁移脚本 - 将所有旧版collection迁移到v2 (BGE-M3)
==================================================

迁移内容：
1. novel_settings (160条) → novel_settings_v2 (BGE-M3 1024维)
2. case_library (342,163条) → case_library_v2 (BGE-M3 1024维)

注意：writing_techniques 已完成迁移 (986条)
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
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def migrate_novel_settings():
    """迁移小说设定到v2"""
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import (
        PointStruct,
        VectorParams,
        Distance,
        SparseVectorParams,
    )

    client = QdrantClient(url=QDRANT_DOCKER_URL)

    log("=" * 60)
    log("迁移 novel_settings → novel_settings_v2")
    log("=" * 60)

    # 检查源collection
    try:
        old_info = client.get_collection("novel_settings")
        log(f"源数据: novel_settings ({old_info.points_count} 条)")
    except Exception as e:
        log(f"错误: novel_settings 不存在 - {e}")
        return

    # 创建/检查目标collection
    try:
        new_info = client.get_collection("novel_settings_v2")
        log(f"目标已存在: novel_settings_v2 ({new_info.points_count} 条)")
        if new_info.points_count > 0:
            log("跳过迁移 (目标已有数据)")
            return
    except:
        log("创建 novel_settings_v2...")
        client.create_collection(
            collection_name="novel_settings_v2",
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
    log("\n[2] 读取旧数据...")
    old_data = []
    offset = None
    while True:
        results, offset = client.scroll(
            collection_name="novel_settings",
            offset=offset,
            limit=100,
            with_payload=True,
            with_vectors=False,
        )
        old_data.extend(results)
        if offset is None:
            break
    log(f"    共读取 {len(old_data)} 条")

    # 迁移数据
    log(f"\n[3] 迁移到 novel_settings_v2...")
    batch = []
    for i, point in enumerate(old_data):
        try:
            # 生成内容用于向量化
            content = point.payload.get("description", "")
            if not content:
                content = (
                    f"{point.payload.get('name', '')} {point.payload.get('type', '')}"
                )

            if not content.strip():
                continue

            # 生成BGE-M3向量
            out = model.encode([content], return_dense=True, return_sparse=True)

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
                payload=point.payload,
            )
            batch.append(new_point)

            if len(batch) >= 20:
                client.upsert("novel_settings_v2", batch)
                log(f"    已迁移 {i + 1}/{len(old_data)} 条")
                batch = []

        except Exception as e:
            log(f"    警告: ID {point.id} 迁移失败: {e}")
            continue

    # 提交剩余数据
    if batch:
        client.upsert("novel_settings_v2", batch)

    # 验证
    log("\n[4] 验证迁移结果...")
    new_info = client.get_collection("novel_settings_v2")
    log(f"    novel_settings_v2: {new_info.points_count} 条")
    log("    迁移完成!")


def migrate_case_library():
    """迁移案例库到v2"""
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import PointStruct

    client = QdrantClient(url=QDRANT_DOCKER_URL)

    log("\n" + "=" * 60)
    log("迁移 case_library → case_library_v2")
    log("=" * 60)

    # 检查源和目标
    try:
        old_info = client.get_collection("case_library")
        old_count = old_info.points_count
        log(f"源数据: case_library ({old_count:,} 条)")
    except Exception as e:
        log(f"错误: case_library 不存在 - {e}")
        return

    try:
        new_info = client.get_collection("case_library_v2")
        new_count = new_info.points_count
        log(f"目标已存在: case_library_v2 ({new_count:,} 条)")
    except:
        log("case_library_v2 不存在，需要先创建")
        return

    # 检查是否需要继续迁移
    if new_count >= old_count * 0.99:
        log(f"已迁移 {new_count:,}/{old_count:,} 条，跳过")
        return

    # 加载BGE-M3模型
    log("\n[1] 加载BGE-M3模型...")
    from FlagEmbedding import BGEM3FlagModel

    model_path = get_model_path()
    model = BGEM3FlagModel(model_path or "BAAI/bge-m3", use_fp16=True, device="cpu")
    log("    模型加载完成")

    # 读取旧数据中尚未迁移的部分
    log("\n[2] 读取旧数据...")

    # 先获取已迁移的ID列表
    log("    检查已迁移的ID...")
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
    log(f"    已迁移 {len(migrated_ids):,} 条")

    # 读取旧数据，跳过已迁移的
    log("    读取未迁移数据...")
    old_data = []
    offset = None
    while True:
        results, offset = client.scroll(
            collection_name="case_library",
            offset=offset,
            limit=500,
            with_payload=True,
            with_vectors=False,
        )
        for p in results:
            if p.id not in migrated_ids:
                old_data.append(p)
        if offset is None:
            break
        if len(old_data) >= 50000:  # 限制每次迁移数量
            break

    log(f"    需迁移 {len(old_data):,} 条")

    if not old_data:
        log("    无需迁移")
        return

    # 迁移数据
    log(f"\n[3] 迁移到 case_library_v2...")
    batch = []
    for i, point in enumerate(old_data):
        try:
            # 生成内容用于向量化
            content = point.payload.get("content", "")[:2000]
            if not content.strip():
                continue

            # 生成BGE-M3向量
            out = model.encode([content], return_dense=True, return_sparse=True)

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
                payload=point.payload,
            )
            batch.append(new_point)

            if len(batch) >= 50:
                client.upsert("case_library_v2", batch)
                if (i + 1) % 500 == 0:
                    log(f"    已迁移 {i + 1}/{len(old_data)} 条")
                batch = []

        except Exception as e:
            continue

    # 提交剩余数据
    if batch:
        client.upsert("case_library_v2", batch)

    # 验证
    log("\n[4] 验证迁移结果...")
    new_info = client.get_collection("case_library_v2")
    log(f"    case_library_v2: {new_info.points_count:,} 条")


def main():
    log("=" * 60)
    log("BGE-M3 完整迁移脚本")
    log("=" * 60)

    # 1. 迁移小说设定
    migrate_novel_settings()

    # 2. 迁移案例库
    migrate_case_library()

    # 3. 最终统计
    log("\n" + "=" * 60)
    log("迁移完成统计")
    log("=" * 60)

    from qdrant_client import QdrantClient

    client = QdrantClient(url=QDRANT_DOCKER_URL)

    collections = {
        "novel_settings": "novel_settings_v2",
        "case_library": "case_library_v2",
        "writing_techniques": "writing_techniques_v2",
    }

    for old_name, new_name in collections.items():
        try:
            old_info = client.get_collection(old_name)
            old_count = old_info.points_count
        except:
            old_count = 0

        try:
            new_info = client.get_collection(new_name)
            new_count = new_info.points_count
        except:
            new_count = 0

        status = "✅" if new_count >= old_count * 0.9 else "⚠️"
        log(f"{status} {old_name}: {old_count:,} → {new_name}: {new_count:,}")

    log("\n" + "=" * 60)
    log("全部完成!")
    log("=" * 60)


if __name__ == "__main__":
    main()
