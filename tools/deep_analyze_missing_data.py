#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
深度分析缺失数据payload结构
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

os.environ["HF_HUB_OFFLINE"] = "1"

# 从配置获取 Qdrant URL
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))
try:
    from core.config_loader import get_qdrant_url, get_collection_name

    QDRANT_URL = get_qdrant_url()
    OLD_COLLECTION = "writing_techniques"
    NEW_COLLECTION = get_collection_name("writing_techniques")
except Exception:
    import os
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
    OLD_COLLECTION = "writing_techniques"
    NEW_COLLECTION = "writing_techniques_v2"

# 读取缺失ID列表
REPORT_FILE = (
    Path(__file__).parent.parent / "logs" / "migration_difference_analysis.json"
)
with open(REPORT_FILE, "r", encoding="utf-8") as f:
    report = json.load(f)

MISSING_IDS = report["reasons"][0]["affected_ids"][:20]  # 分析前20个样本


def log(msg):
    print(msg, flush=True)


def main():
    log("=" * 60)
    log("深度分析缺失数据payload结构")
    log("=" * 60)

    from qdrant_client import QdrantClient

    client = QdrantClient(url=QDRANT_URL)

    log(f"\n分析前20个缺失ID的完整payload结构...")

    # 分析正常数据和缺失数据的payload结构对比
    normal_ids = ["1", "2", "3", "100", "200"]  # 一些可能正常的ID

    log("\n[1] 正常数据样本 (ID=1,2,3,100,200):")
    for id in normal_ids:
        try:
            points = client.retrieve(
                collection_name=OLD_COLLECTION,
                ids=[int(id)],
                with_payload=True,
                with_vectors=False,
            )
            if points:
                point = points[0]
                log(f"\nID {id} payload keys: {list(point.payload.keys())}")
                log(f"完整payload:")
                for key, value in point.payload.items():
                    if isinstance(value, str) and len(value) > 100:
                        log(f"  {key}: {value[:100]}... (长度: {len(value)})")
                    else:
                        log(f"  {key}: {value}")
        except Exception as e:
            log(f"ID {id}: 获取失败 {e}")

    log("\n[2] 缺失数据样本分析:")
    for id in MISSING_IDS:
        try:
            points = client.retrieve(
                collection_name=OLD_COLLECTION,
                ids=[int(id)],
                with_payload=True,
                with_vectors=False,
            )
            if points:
                point = points[0]
                log(f"\n--- ID {id} ---")
                log(f"payload keys: {list(point.payload.keys())}")
                log(f"完整payload:")

                # 检查是否有特殊字段
                payload = point.payload

                # 常见字段检查
                content_fields = [
                    "content",
                    "principle",
                    "text",
                    "description",
                    "body",
                    "raw_text",
                    "data",
                ]
                found_content_field = None

                for field in content_fields:
                    if field in payload:
                        found_content_field = field
                        value = payload[field]
                        if isinstance(value, str) and len(value) > 100:
                            log(f"  [{field}] 存在! 预览: {value[:100]}...")
                        else:
                            log(f"  [{field}] 存在! 内容: {value}")

                if not found_content_field:
                    log(f"  [警告] 无常见内容字段!")

                # 打印所有字段
                for key, value in payload.items():
                    if isinstance(value, str) and len(value) > 50:
                        log(f"  {key}: {value[:50]}...")
                    elif isinstance(value, list) and len(value) > 0:
                        log(
                            f"  {key}: [{type(value[0]).__name__}...] (长度: {len(value)})"
                        )
                    else:
                        log(f"  {key}: {value}")

        except Exception as e:
            log(f"ID {id}: 获取失败 {e}")

    # 统计payload结构差异
    log("\n[3] 统计分析:")

    # 统计缺失数据的payload字段分布
    all_missing_ids = report["reasons"][0]["affected_ids"]
    field_stats = {}
    empty_payload_count = 0

    for id in all_missing_ids[:50]:  # 分析50个样本
        try:
            points = client.retrieve(
                collection_name=OLD_COLLECTION,
                ids=[int(id)],
                with_payload=True,
                with_vectors=False,
            )
            if points:
                point = points[0]
                if not point.payload:
                    empty_payload_count += 1
                else:
                    for key in point.payload.keys():
                        if key not in field_stats:
                            field_stats[key] = 0
                        field_stats[key] += 1
        except:
            pass

    log(f"\n缺失数据payload字段分布 (50个样本):")
    log(f"  完全空payload: {empty_payload_count}")
    for field, count in sorted(field_stats.items(), key=lambda x: -x[1]):
        log(f"  {field}: {count}/50 条数据有此字段")

    log("\n" + "=" * 60)
    log("分析完成")
    log("=" * 60)


if __name__ == "__main__":
    main()
