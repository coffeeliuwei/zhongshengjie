#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用Docker Qdrant完成剩余迁移
"""

import os
import sys
import json
import gc
from pathlib import Path
from datetime import datetime

# 加载配置
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config_loader import (
    get_project_root,
    get_model_path,
    get_vectorstore_dir,
    get_case_library_dir,
    get_qdrant_url,
)

PROJECT_DIR = get_project_root()
sys.path.insert(0, str(PROJECT_DIR / ".vectorstore"))

PROGRESS_FILE = get_vectorstore_dir() / "migration_lite_progress.json"
QDRANT_URL = get_qdrant_url()


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def load_progress():
    if PROGRESS_FILE.exists():
        return json.load(open(PROGRESS_FILE, encoding="utf-8"))
    return {
        "novel": {"last_id": -1, "total": 0},
        "technique": {"last_id": -1, "total": 0},
        "case": {"last_id": -1, "total": 0},
    }


def save_progress(p):
    p["last_update"] = datetime.now().isoformat()
    json.dump(
        p, open(PROGRESS_FILE, "w", encoding="utf-8"), indent=2, ensure_ascii=False
    )


def main():
    log("=" * 60)
    log("Docker Qdrant 迁移")
    log("=" * 60)

    # 加载进度
    progress = load_progress()
    last_id = progress["case"]["last_id"]

    log(f"从ID {last_id + 1} 继续")

    # 加载模型
    log("[1/3] 加载模型...")
    from FlagEmbedding import BGEM3FlagModel

    model_path = get_model_path()
    model = BGEM3FlagModel(model_path or "BAAI/bge-m3", use_fp16=True, device="cpu")
    log("      完成")

    # 连接Docker Qdrant
    log(f"[2/3] 连接Docker Qdrant ({QDRANT_URL})...")
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import PointStruct, SparseVector

    client = QdrantClient(url=QDRANT_URL)
    log("      完成")

    # 收集案例
    log("[3/3] 收集案例...")
    cases = []
    cases_dir = get_case_library_dir() / "cases"

    for scene_dir in cases_dir.iterdir():
        if not scene_dir.is_dir():
            continue
        scene_type = scene_dir.name
        for jf in scene_dir.glob("*.json"):
            try:
                d = json.load(open(jf, encoding="utf-8"))
                parts = jf.stem.split("_")
                d["scene_type"] = d.get("scene_type", scene_type)
                d["genre"] = d.get("genre", parts[1] if len(parts) >= 2 else "未知")
                d["novel_name"] = d.get(
                    "novel_name", "_".join(parts[2:]) if len(parts) >= 3 else "未知"
                )
                cases.append(d)
            except:
                pass

    total = len(cases)
    log(f"      总计 {total} 条")

    # 确保collection存在
    from qdrant_client.http.models import VectorParams, Distance, SparseVectorParams

    collection_name = "case_library_v2"
    try:
        client.get_collection(collection_name)
        log(f"Collection {collection_name} 已存在")
    except:
        log(f"创建Collection {collection_name}...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config={"dense": VectorParams(size=1024, distance=Distance.COSINE)},
            sparse_vectors_config={"sparse": SparseVectorParams()},
        )

    # 迁移
    count = 0
    for i, c in enumerate(cases):
        if i <= last_id:
            continue

        if (i + 1) % 1000 == 0:
            eta = (total - i - 1) * 0.3 / 60
            log(
                f"  case: {i + 1}/{total} ({(i + 1) / total * 100:.1f}%) | 剩余 {eta:.0f} 分钟"
            )

        content = c.get("content", "")[:1000]
        if len(content) < 50:
            progress["case"]["last_id"] = i
            continue

        out = model.encode([content], return_dense=True, return_sparse=True)

        client.upsert(
            collection_name,
            [
                PointStruct(
                    id=i,
                    vector={
                        "dense": out["dense_vecs"][0].tolist(),
                        "sparse": SparseVector(
                            indices=list(out["lexical_weights"][0].keys()),
                            values=list(out["lexical_weights"][0].values()),
                        ),
                    },
                    payload={
                        "novel_name": c.get("novel_name", "未知"),
                        "scene_type": c.get("scene_type", "未知"),
                        "genre": c.get("genre", "未知"),
                        "quality_score": c.get(
                            "quality_score", c.get("confidence", 0) * 10
                        ),
                        "word_count": c.get("word_count", len(c.get("content", ""))),
                        "content": c.get("content", "")[:2000],
                    },
                )
            ],
        )

        progress["case"]["last_id"] = i
        count += 1
        if count % 100 == 0:
            save_progress(progress)
            gc.collect()

    log(f"  case: 完成 {count} 条")
    save_progress(progress)
    log("迁移完成!")


if __name__ == "__main__":
    main()
