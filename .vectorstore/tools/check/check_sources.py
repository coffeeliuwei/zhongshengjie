#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查案例库提取情况"""

from qdrant_client import QdrantClient
from pathlib import Path
import json

QDRANT_DIR = Path("qdrant")


def check_case_library():
    client = QdrantClient(path=str(QDRANT_DIR))

    # 获取所有案例
    result = client.scroll(
        collection_name="case_library_v2",
        limit=6000,
        with_payload=True,
        with_vectors=False,
    )

    cases = result[0]
    print(f"案例库总数: {len(cases)}条")
    print()

    # 统计来源分布
    genres = {}
    novels = set()
    for p in cases:
        payload = p.payload
        genre = payload.get("genre", "未知")
        genres[genre] = genres.get(genre, 0) + 1
        novels.add(payload.get("novel_name", "未知"))

    print("按题材统计:")
    for g, c in sorted(genres.items(), key=lambda x: -x[1]):
        print(f"  {g}: {c}条")

    print(f"\n涉及小说数: {len(novels)}本")

    # 列出部分小说名
    print("\n小说样本(前20本):")
    for i, n in enumerate(list(novels)[:20], 1):
        print(f"  {i}. {n}")


if __name__ == "__main__":
    check_case_library()
