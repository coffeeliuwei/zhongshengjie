#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
技法库迁移差异分析
================

分析 writing_techniques 和 writing_techniques_v2 之间的136条差异原因
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

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

PROJECT_ROOT = Path(__file__).parent.parent

OUTPUT_FILE = PROJECT_ROOT / "logs" / "migration_difference_analysis.json"


def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def main():
    log("=" * 60)
    log("技法库迁移差异分析")
    log("=" * 60)
    log(f"Qdrant URL: {QDRANT_URL}")
    log(f"旧collection: {OLD_COLLECTION}")
    log(f"新collection: {NEW_COLLECTION}")

    # 连接Qdrant
    from qdrant_client import QdrantClient

    client = QdrantClient(url=QDRANT_URL)

    # [1] 获取collection结构对比
    log("\n[1] 获取collection结构...")

    try:
        old_info = client.get_collection(OLD_COLLECTION)
        log(f"旧collection {OLD_COLLECTION}:")
        log(f"  - points_count: {old_info.points_count}")
        log(f"  - status: {old_info.status}")
    except Exception as e:
        log(f"错误: 旧collection不存在: {e}")
        return

    try:
        new_info = client.get_collection(NEW_COLLECTION)
        log(f"新collection {NEW_COLLECTION}:")
        log(f"  - points_count: {new_info.points_count}")
        log(f"  - status: {new_info.status}")
    except Exception as e:
        log(f"错误: 新collection不存在: {e}")
        return

    difference = old_info.points_count - new_info.points_count
    log(f"\n差异: {difference} 条未迁移")

    # [2] 获取所有旧数据ID
    log("\n[2] 获取旧collection所有ID...")

    old_ids = set()
    old_data = {}
    offset = None

    while True:
        results, offset = client.scroll(
            collection_name=OLD_COLLECTION,
            offset=offset,
            limit=100,
            with_payload=True,
            with_vectors=False,
        )
        for point in results:
            old_ids.add(str(point.id))
            old_data[str(point.id)] = {
                "id": str(point.id),
                "name": point.payload.get("name", point.payload.get("title", "未知")),
                "dimension": point.payload.get("dimension", "未知"),
                "writer": point.payload.get("writer", "未知"),
                "content_preview": (
                    point.payload.get("content", "")
                    or point.payload.get("principle", "")
                )[:200],
                "has_content": bool(
                    point.payload.get("content", "")
                    or point.payload.get("principle", "")
                ),
                "source": point.payload.get("file", point.payload.get("source", "")),
            }
        if offset is None:
            break

    log(f"旧collection共 {len(old_ids)} 个ID")

    # [3] 获取所有新数据ID
    log("\n[3] 获取新collection所有ID...")

    new_ids = set()
    offset = None

    while True:
        results, offset = client.scroll(
            collection_name=NEW_COLLECTION,
            offset=offset,
            limit=100,
            with_payload=True,
            with_vectors=False,
        )
        for point in results:
            new_ids.add(str(point.id))
        if offset is None:
            break

    log(f"新collection共 {len(new_ids)} 个ID")

    # [4] 找出缺失的ID
    log("\n[4] 分析缺失数据...")

    missing_ids = old_ids - new_ids
    log(f"缺失ID数量: {len(missing_ids)}")

    # [5] 分析缺失数据特征
    log("\n[5] 分析缺失数据特征...")

    missing_data = [old_data[id] for id in missing_ids if id in old_data]

    # 按维度统计
    dimension_stats = defaultdict(int)
    writer_stats = defaultdict(int)
    has_content_stats = defaultdict(int)
    empty_content_count = 0

    for item in missing_data:
        dimension_stats[item["dimension"]] += 1
        writer_stats[item["writer"]] += 1
        has_content_stats[str(item["has_content"])] += 1
        if not item["has_content"]:
            empty_content_count += 1

    log("\n缺失数据维度分布:")
    for dim, count in sorted(dimension_stats.items(), key=lambda x: -x[1]):
        log(f"  {dim}: {count} 条")

    log("\n缺失数据作家分布:")
    for writer, count in sorted(writer_stats.items(), key=lambda x: -x[1])[:10]:
        log(f"  {writer}: {count} 条")

    log(f"\n内容有效性统计:")
    log(f"  有内容: {has_content_stats['True']} 条")
    log(f"  无内容: {has_content_stats['False']} 条 (可能跳过)")

    # [6] 抽样展示缺失数据
    log("\n[6] 缺失数据样本 (前10条):")

    for i, item in enumerate(missing_data[:10]):
        log(f"\n样本 {i + 1}:")
        log(f"  ID: {item['id']}")
        log(f"  名称: {item['name']}")
        log(f"  维度: {item['dimension']}")
        log(f"  作家: {item['writer']}")
        log(f"  内容预览: {item['content_preview'][:100]}...")
        log(f"  来源: {item['source']}")

    # [7] 分析迁移脚本逻辑问题
    log("\n[7] 分析迁移脚本逻辑...")

    # 检查脚本中可能跳过的条件
    reasons = []

    # 原因1: 内容为空
    if empty_content_count > 0:
        reasons.append(
            {
                "reason": "content_or_principle_empty",
                "count": empty_content_count,
                "description": "迁移脚本中第113-116行检查: if not content: continue - 跳过无内容的技法",
                "affected_ids": [
                    item["id"] for item in missing_data if not item["has_content"]
                ],
            }
        )

    # 原因2: 维度映射问题 - 检查是否有需要映射但未映射的维度
    dimension_fix_map = {
        "世界观": "世界观维度",
        "剧情": "剧情维度",
        "人物": "人物维度",
        "战斗冲突": "战斗冲突维度",
        "氛围意境": "氛围意境维度",
        "情感": "情感维度",
        "叙事": "叙事维度",
    }

    unmapped_dimensions = set()
    for dim in dimension_stats.keys():
        if dim in dimension_fix_map or dim.endswith("维度"):
            # 已映射或已经是正确格式
            pass
        else:
            unmapped_dimensions.add(dim)

    if unmapped_dimensions:
        reasons.append(
            {
                "reason": "dimension_mapping_mismatch",
                "count": sum(dimension_stats[d] for d in unmapped_dimensions),
                "description": "维度名称不在映射表中，可能导致payload不一致",
                "unmapped_dimensions": list(unmapped_dimensions),
            }
        )

    # 原因3: 迁移中断 - 检查ID范围
    # 如果缺失数据集中在前或后，可能是迁移过程中断
    missing_id_ints = []
    for id in missing_ids:
        try:
            missing_id_ints.append(int(id))
        except:
            pass

    if missing_id_ints:
        min_id = min(missing_id_ints)
        max_id = max(missing_id_ints)
        reasons.append(
            {
                "reason": "id_range_analysis",
                "description": f"缺失ID范围: {min_id} - {max_id}",
                "distribution": "分散分布可能是筛选条件跳过，集中分布可能是迁移中断",
            }
        )

    # [8] 生成报告
    log("\n[8] 生成差异分析报告...")

    report = {
        "timestamp": datetime.now().isoformat(),
        "collections": {
            "old": {
                "name": OLD_COLLECTION,
                "points_count": old_info.points_count,
            },
            "new": {
                "name": NEW_COLLECTION,
                "points_count": new_info.points_count,
            },
            "difference": difference,
        },
        "missing_analysis": {
            "total_missing": len(missing_ids),
            "dimension_distribution": dict(dimension_stats),
            "writer_distribution": dict(writer_stats),
            "content_validity": dict(has_content_stats),
        },
        "reasons": reasons,
        "missing_samples": missing_data[:10],
        "all_missing_ids": sorted(list(missing_ids)),
    }

    # 确保日志目录存在
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    log(f"报告已保存: {OUTPUT_FILE}")

    # [9] 输出结论和建议
    log("\n" + "=" * 60)
    log("分析结论")
    log("=" * 60)

    if empty_content_count > 0:
        log(f"\n主要原因: {empty_content_count} 条技法无content/principle字段")
        log("迁移脚本第113-116行会跳过这些数据")
        log("建议: 检查这些技法的payload结构，确认是否需要修复")

    if len(missing_ids) - empty_content_count > 0:
        remaining = len(missing_ids) - empty_content_count
        log(f"\n其他缺失: {remaining} 条可能因其他原因未迁移")
        log("建议: 检查迁移日志是否有错误记录")

    log("\n" + "=" * 60)
    log("分析完成")
    log("=" * 60)


if __name__ == "__main__":
    main()
