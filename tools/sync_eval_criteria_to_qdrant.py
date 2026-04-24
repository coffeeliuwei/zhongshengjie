#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
审核维度同步到向量库
===================

将 evaluation_criteria_migrated.json 中的26条审核标准上传到 Qdrant。

数据来源: tools/evaluation_criteria_migrated.json
目标Collection: evaluation_criteria_v1
向量模型: BGE-M3 (1024维 dense)

参考: evaluation-criteria-extension-design.md 第4节
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# 加载配置
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config_loader import get_qdrant_url, get_model_path


def log(msg: str):
    """日志输出"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def load_criteria() -> List[Dict[str, Any]]:
    """加载审核维度数据"""
    json_path = PROJECT_ROOT / "tools" / "evaluation_criteria_migrated.json"

    if not json_path.exists():
        log(f"错误: 数据文件不存在 {json_path}")
        return []

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    criteria = data.get("criteria", [])
    log(f"加载 {len(criteria)} 条审核标准")
    return criteria


def generate_embedding_text(criteria: Dict[str, Any]) -> str:
    """
    为审核维度生成嵌入文本

    Args:
        criteria: 审核维度数据

    Returns:
        用于生成嵌入的文本
    """
    dimension_type = criteria.get("dimension_type", "")
    name = criteria.get("name", "")
    pattern = criteria.get("pattern", "")

    # 根据类型生成不同的嵌入文本
    if dimension_type == "prohibition":
        # 禁止项: 名称 + 模式 + 示例
        examples = criteria.get("examples", [])
        examples_text = "、".join(examples[:3]) if examples else ""
        return f"禁止项检测: {name}\n模式: {pattern}\n示例: {examples_text}"

    elif dimension_type == "technique_criteria":
        # 技法标准: 维度 + 技法名 + 描述 + 阈值
        dimension_name = criteria.get("dimension_name", "")
        technique_name = criteria.get("technique_name", "")
        description = criteria.get("technique_description", "")
        threshold = criteria.get("threshold_score", "")
        return f"{dimension_name}: {technique_name}\n标准: {description}\n阈值: {threshold}"

    elif dimension_type == "threshold":
        # 阈值配置: 名称 + 阈值数据
        threshold_data = criteria.get("threshold", "")
        return f"整体质量评估: {name}\n配置: {threshold_data}"

    else:
        return f"{dimension_type}: {name}"


def create_collection(client, collection_name: str):
    """创建Collection"""
    from qdrant_client.http.models import VectorParams, Distance

    # 检查是否已存在
    collections = client.get_collections().collections
    existing_names = [c.name for c in collections]

    if collection_name in existing_names:
        info = client.get_collection(collection_name)
        log(f"Collection {collection_name} 已存在: {info.points_count} 条")
        return False  # 不需要创建

    # 创建新Collection
    log(f"创建 Collection {collection_name}...")
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
    )
    log(f"Collection {collection_name} 创建成功")
    return True


def upload_criteria(
    client, criteria: List[Dict[str, Any]], collection_name: str, model
):
    """上传审核维度到向量库"""
    from qdrant_client.http.models import PointStruct

    log(f"\n[上传] 处理 {len(criteria)} 条审核标准...")

    points = []
    success_count = 0
    error_count = 0

    for i, c in enumerate(criteria):
        try:
            # 生成嵌入文本
            embedding_text = generate_embedding_text(c)

            # 生成向量
            embedding = model.encode(
                [embedding_text], return_dense=True, return_sparse=False
            )
            dense_vecs = embedding.get("dense_vecs")

            if dense_vecs is None or len(dense_vecs) == 0:
                log(f"  [{i + 1}] 警告: 向量生成失败 - {c.get('name', 'unknown')}")
                error_count += 1
                continue

            import numpy as np

            vector = np.array(dense_vecs[0]).tolist()

            # 构建payload
            payload = {
                "criteria_id": c.get("id", ""),  # 原ID存到payload
                "dimension_type": c.get("dimension_type", ""),
                "dimension_name": c.get("dimension_name", ""),
                "name": c.get("name", ""),
                "pattern": c.get("pattern", ""),
                "examples": c.get("examples", []),
                "threshold": c.get("threshold", ""),
                "threshold_score": c.get("threshold_score"),
                "technique_name": c.get("technique_name", ""),
                "technique_description": c.get("technique_description", ""),
                "source": c.get("source", "migrated"),
                "created_at": c.get("created_at", ""),
                "is_active": c.get("is_active", True),
            }

            # 创建Point（使用整数ID）
            import uuid

            point_id = i + 1  # 使用整数ID（1-26）

            point = PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
            points.append(point)
            success_count += 1

            if (i + 1) % 10 == 0:
                log(f"  处理进度: {i + 1}/{len(criteria)}")

        except Exception as e:
            log(f"  [{i + 1}] 错误: {e}")
            error_count += 1

    # 批量上传
    if points:
        log(f"\n[上传] 批量上传 {len(points)} 条...")
        client.upsert(collection_name=collection_name, points=points)
        log(f"  成功: {success_count} 条")
        log(f"  失败: {error_count} 条")

    return success_count, error_count


def verify_upload(client, collection_name: str):
    """验证上传结果"""
    log(f"\n[验证] 检查 Collection {collection_name}...")

    info = client.get_collection(collection_name)
    log(f"  总数: {info.points_count} 条")

    # 检索测试
    log(f"\n[检索测试] 搜索 'AI味表达'...")

    # 这里不做向量检索，只做payload过滤验证
    results, _ = client.scroll(
        collection_name=collection_name,
        limit=5,
        with_payload=True,
    )

    if results:
        log(f"  找到 {len(results)} 条记录:")
        for r in results[:3]:
            name = r.payload.get("name", "unknown")
            type_ = r.payload.get("dimension_type", "unknown")
            log(f"    - {name} ({type_})")

    return info.points_count


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="审核维度同步到向量库")
    parser.add_argument("--sync", action="store_true", help="执行同步")
    parser.add_argument("--verify", action="store_true", help="验证结果")
    parser.add_argument("--status", action="store_true", help="查看状态")

    args = parser.parse_args()

    # 连接Qdrant
    from qdrant_client import QdrantClient

    qdrant_url = get_qdrant_url()
    client = QdrantClient(url=qdrant_url)

    collection_name = "evaluation_criteria_v1"

    if args.status:
        # 查看状态
        collections = client.get_collections().collections
        existing = [c.name for c in collections]

        if collection_name in existing:
            info = client.get_collection(collection_name)
            log(f"\n[{collection_name} 状态]")
            log(f"  点数: {info.points_count}")

            # 按类型统计
            results, _ = client.scroll(collection_name, limit=100, with_payload=True)
            by_type = {}
            for r in results:
                t = r.payload.get("dimension_type", "unknown")
                by_type[t] = by_type.get(t, 0) + 1

            log(f"  按类型:")
            for t, count in by_type.items():
                log(f"    {t}: {count}")
        else:
            log(f"\n[{collection_name}] Collection不存在，使用 --sync 创建并上传")

        # 检查JSON文件
        json_path = PROJECT_ROOT / "tools" / "evaluation_criteria_migrated.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            log(f"\n[数据文件] {json_path}")
            log(f"  待上传: {data.get('count', 0)} 条")
        else:
            log(f"\n[数据文件] 不存在")

        return

    if args.sync:
        log("=" * 60)
        log("审核维度同步到向量库")
        log("=" * 60)

        # 1. 加载模型
        log("\n[1] 加载BGE-M3模型...")
        from FlagEmbedding import BGEM3FlagModel

        model_path = get_model_path()
        model = BGEM3FlagModel(model_path or "BAAI/bge-m3", use_fp16=True, device="cpu")
        log("    模型加载完成")

        # 2. 加载审核维度
        log("\n[2] 加载审核维度数据...")
        criteria = load_criteria()

        if not criteria:
            log("错误: 无数据可上传")
            return

        # 3. 创建Collection
        log("\n[3] 创建Collection...")
        created = create_collection(client, collection_name)

        # 4. 上传数据
        log("\n[4] 上传审核维度...")
        success, error = upload_criteria(client, criteria, collection_name, model)

        # 5. 验证
        log("\n[5] 验证上传结果...")
        count = verify_upload(client, collection_name)

        log("\n" + "=" * 60)
        log(f"同步完成: {success} 条成功, {error} 条失败")
        log(f"Collection {collection_name}: {count} 条记录")
        log("=" * 60)

        return

    if args.verify:
        log("\n[验证] 检查上传结果...")
        verify_upload(client, collection_name)
        return

    # 无参数时显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
