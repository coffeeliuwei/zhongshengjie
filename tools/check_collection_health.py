#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
集合健康检查工具
================

快速报告 case_library_v2 的规模、质量分布和样本预览。

用法：
    python tools/check_collection_health.py
    python tools/check_collection_health.py --sample 20
"""
import argparse
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    parser = argparse.ArgumentParser(description="集合健康检查")
    parser.add_argument("--sample", type=int, default=10, help="随机抽样条数")
    parser.add_argument("--collection", default="case_library_v2", help="集合名称")
    args = parser.parse_args()

    from qdrant_client import QdrantClient

    client = QdrantClient(url=os.environ.get("QDRANT_URL", "http://localhost:6333"))

    # 基础信息
    try:
        info = client.get_collection(args.collection)
    except Exception as e:
        print(f"[错误] 无法获取集合 {args.collection}: {e}")
        sys.exit(1)

    print("=" * 60)
    print(f"集合: {args.collection}")
    print("=" * 60)
    print(f"  总条目数: {info.points_count:,}")
    print(f"  向量维度: {info.config.params.vectors}")
    print()

    # 质量分分布
    print("[质量分分布]")
    score_buckets = {"<6": 0, "6-7": 0, "7-8": 0, "8-9": 0, ">=9": 0}
    offset = None
    scanned = 0
    max_scan = 5000

    while scanned < max_scan:
        result, offset = client.scroll(
            collection_name=args.collection,
            limit=500,
            offset=offset,
            with_payload=["quality_score"],
            with_vectors=False,
        )
        for point in result:
            qs = point.payload.get("quality_score", 7.0) if point.payload else 7.0
            if qs < 6:
                score_buckets["<6"] += 1
            elif qs < 7:
                score_buckets["6-7"] += 1
            elif qs < 8:
                score_buckets["7-8"] += 1
            elif qs < 9:
                score_buckets["8-9"] += 1
            else:
                score_buckets[">=9"] += 1
            scanned += 1
        if offset is None or scanned >= max_scan:
            break

    total_scanned = sum(score_buckets.values())
    for bucket, count in score_buckets.items():
        pct = count / total_scanned * 100 if total_scanned else 0
        print(f"  {bucket}: {count} ({pct:.1f}%)")
    print(f"  (基于前 {total_scanned} 条样本)")
    print()

    # 随机抽样预览
    print(f"[随机抽样 {args.sample} 条]")
    sample_result, _ = client.scroll(
        collection_name=args.collection,
        limit=args.sample,
        with_payload=True,
        with_vectors=False,
    )
    for i, point in enumerate(sample_result, 1):
        payload = point.payload or {}
        preview = (payload.get("content") or "")[:80].replace("\n", " ")
        scene = payload.get("scene_type", "?")
        qs = payload.get("quality_score", "?")
        print(f"  [{i:02d}] scene={scene} q={qs}")
        print(f"       {preview}")
    print()
    print("健康检查完成。")


if __name__ == "__main__":
    main()