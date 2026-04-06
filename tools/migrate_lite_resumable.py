#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BGE-M3 轻量迁移脚本 - Dense + Sparse (无ColBERT)
支持可暂停、断点续传

存储需求：
- novel_settings_v2: ~1 MB
- writing_techniques_v2: ~5 MB
- case_library_v2: ~3 GB
总计: ~3.1 GB (比ColBERT方案节省 270+ GB)
"""

import os
import sys
import json
import re
import gc
import signal
from pathlib import Path
from datetime import datetime

# 加载配置
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config_loader import (
    get_project_root,
    get_model_path,
    get_vectorstore_dir,
    get_techniques_dir,
    get_case_library_dir,
)

PROJECT_DIR = get_project_root()
sys.path.insert(0, str(PROJECT_DIR / ".vectorstore"))

PROGRESS_FILE = get_vectorstore_dir() / "migration_lite_progress.json"
paused = False


def signal_handler(signum, frame):
    global paused
    print("\n\n[!] 暂停中，保存进度...")
    paused = True


signal.signal(signal.SIGINT, signal_handler)


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
    json.dump(p, open(PROGRESS_FILE, "w", encoding="utf-8"), indent=2)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument(
        "--collection", choices=["novel", "technique", "case", "all"], default="all"
    )
    args = parser.parse_args()

    if args.status:
        show_status()
        return
    if args.reset:
        PROGRESS_FILE.unlink(missing_ok=True)
        log("进度已重置")
        return

    log("=" * 60)
    log("BGE-M3 轻量迁移 (Dense + Sparse)")
    log("存储需求: ~3.1 GB | 按 Ctrl+C 暂停")
    log("=" * 60)

    # 加载模型
    log("[1/3] 加载模型...")
    from FlagEmbedding import BGEM3FlagModel

    model_path = get_model_path()
    model = BGEM3FlagModel(model_path or "BAAI/bge-m3", use_fp16=True, device="cpu")
    log("      完成")

    # 连接 Qdrant
    log("[2/3] 连接 Qdrant...")
    from qdrant_client import QdrantClient
    from qdrant_client import models
    from qdrant_client.http.models import PointStruct, SparseVector

    # 定义PointStruct别名供后续使用
    global PointStruct, SparseVector

    client = QdrantClient(path=str(get_vectorstore_dir() / "qdrant"))
    log("      完成")

    progress = load_progress()
    total = 0

    if args.collection in ["novel", "all"]:
        n, progress = sync_novel(model, client, progress)
        total += n
        if paused:
            save_progress(progress)
            log("[!] 已暂停")
            return

    if args.collection in ["technique", "all"]:
        n, progress = sync_technique(model, client, progress)
        total += n
        if paused:
            save_progress(progress)
            log("[!] 已暂停")
            return

    if args.collection in ["case", "all"]:
        n, progress = sync_case(model, client, progress)
        total += n
        if paused:
            save_progress(progress)
            log("[!] 已暂停")
            return

    PROGRESS_FILE.unlink(missing_ok=True)
    log("=" * 60)
    log(f"完成! 总计: {total} 条")
    log("=" * 60)


def show_status():
    p = load_progress()
    print("\n迁移进度:")
    for k, v in p.items():
        if k == "last_update":
            continue
        done = v["last_id"] + 1 if v["last_id"] >= 0 else 0
        total = v.get("total", 0)
        if total > 0:
            pct = done / total * 100
            print(f"  {k}: {done}/{total} ({pct:.1f}%)")
        else:
            print(f"  {k}: 未开始")
    print(f"\n最后更新: {p.get('last_update', 'N/A')}")


def create_lite_collection(client, name):
    """创建轻量Collection (Dense + Sparse)"""
    from qdrant_client import models

    try:
        client.delete_collection(name)
    except:
        pass

    client.create_collection(
        collection_name=name,
        vectors_config={
            "dense": models.VectorParams(size=1024, distance=models.Distance.COSINE),
        },
        sparse_vectors_config={"sparse": models.SparseVectorParams()},
    )


def sync_novel(model, client, progress):
    global paused
    from bge_m3_config import COLLECTION_NAMES
    from qdrant_client.http.models import PointStruct, SparseVector

    name = COLLECTION_NAMES["novel_settings"]
    key = "novel"

    # 读取数据
    kg = json.load(
        open(get_vectorstore_dir() / "knowledge_graph.json", encoding="utf-8")
    )
    entities = list(kg.get("实体", {}).items())
    total = len(entities)

    if progress[key]["total"] == 0:
        progress[key]["total"] = total
        create_lite_collection(client, name)

    last_id = progress[key]["last_id"]
    log(f"[novel] {total}条, 从ID {last_id + 1} 继续")

    count = 0
    for i, (n, p) in enumerate(entities):
        if i <= last_id:
            continue
        if paused:
            return count, progress

        if (i + 1) % 50 == 0:
            log(f"  novel: {i + 1}/{total}")

        text = f"【{n}】类型:{p.get('类型', '')} 描述:{p.get('描述', '')}"
        out = model.encode([text], return_dense=True, return_sparse=True)

        client.upsert(
            name,
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
                        "name": n,
                        "type": p.get("类型", "未知"),
                        "description": str(p.get("描述", ""))[:2000],
                    },
                )
            ],
        )

        progress[key]["last_id"] = i
        count += 1
        if count % 50 == 0:
            save_progress(progress)

    log(f"  novel: 完成 {count} 条")
    return count, progress


def sync_technique(model, client, progress):
    global paused
    from bge_m3_config import COLLECTION_NAMES
    from qdrant_client.http.models import PointStruct, SparseVector

    name = COLLECTION_NAMES["writing_techniques"]
    key = "technique"

    DIM = {
        "01-世界观维度": "世界观维度",
        "02-剧情维度": "剧情维度",
        "03-人物维度": "人物维度",
        "04-战斗冲突维度": "战斗冲突维度",
        "05-氛围意境维度": "氛围意境维度",
        "06-叙事维度": "叙事维度",
        "07-主题维度": "主题维度",
        "08-情感维度": "情感维度",
        "09-读者体验维度": "读者体验维度",
        "10-元维度": "元维度",
        "11-节奏维度": "节奏维度",
        "99-外部资源": "综合维度",
        "99-实战经验": "综合维度",
        "99-学习模块": "综合维度",
        "99-从小说提取": "综合维度",
    }
    WRI = {
        "世界观维度": "苍澜",
        "剧情维度": "玄一",
        "人物维度": "墨言",
        "战斗冲突维度": "剑尘",
        "氛围意境维度": "云溪",
        "叙事维度": "玄一",
        "主题维度": "玄一",
        "情感维度": "墨言",
        "读者体验维度": "云溪",
        "元维度": "全部",
        "节奏维度": "玄一",
        "综合维度": "全员",
    }

    # 收集技法
    techs = []
    for f in get_techniques_dir().rglob("*.md"):
        if f.name in ["README.md", "01-创作检查清单.md", "00-学习路径规划.md"]:
            continue
        dim = DIM.get(f.parent.name, "未知")
        content = open(f, encoding="utf-8").read()
        for sec in extract_sections(content):
            if len(sec["content"]) >= 100:
                techs.append(
                    {
                        "name": sec["name"],
                        "dimension": dim,
                        "writer": WRI.get(dim, "未知"),
                        "content": sec["content"][:5000],
                    }
                )

    total = len(techs)

    if progress[key]["total"] == 0:
        progress[key]["total"] = total
        create_lite_collection(client, name)

    last_id = progress[key]["last_id"]
    log(f"[technique] {total}条, 从ID {last_id + 1} 继续")

    count = 0
    for i, t in enumerate(techs):
        if i <= last_id:
            continue
        if paused:
            return count, progress

        if (i + 1) % 100 == 0:
            log(f"  technique: {i + 1}/{total}")

        out = model.encode([t["content"][:500]], return_dense=True, return_sparse=True)

        client.upsert(
            name,
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
                        "name": t["name"],
                        "dimension": t["dimension"],
                        "writer": t["writer"],
                        "content": t["content"],
                        "word_count": len(t["content"]),
                    },
                )
            ],
        )

        progress[key]["last_id"] = i
        count += 1
        if count % 50 == 0:
            save_progress(progress)

    log(f"  technique: 完成 {count} 条")
    return count, progress


def sync_case(model, client, progress):
    global paused
    from bge_m3_config import COLLECTION_NAMES
    from qdrant_client.http.models import PointStruct, SparseVector

    name = COLLECTION_NAMES["case_library"]
    key = "case"

    # 收集案例
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

    if progress[key]["total"] == 0:
        progress[key]["total"] = total
        create_lite_collection(client, name)

    last_id = progress[key]["last_id"]
    log(f"[case] {total}条, 从ID {last_id + 1} 继续 | 预计 {total * 0.3 / 60:.0f} 分钟")

    count = 0
    for i, c in enumerate(cases):
        if i <= last_id:
            continue
        if paused:
            return count, progress

        if (i + 1) % 1000 == 0:
            eta = (total - i - 1) * 0.3 / 60
            log(
                f"  case: {i + 1}/{total} ({(i + 1) / total * 100:.1f}%) | 剩余 {eta:.0f} 分钟"
            )

        content = c.get("content", "")[:1000]
        if len(content) < 50:
            progress[key]["last_id"] = i
            continue

        out = model.encode([content], return_dense=True, return_sparse=True)

        client.upsert(
            name,
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

        progress[key]["last_id"] = i
        count += 1
        if count % 50 == 0:  # 更频繁保存和清理
            save_progress(progress)
            gc.collect()

    log(f"  case: 完成 {count} 条")
    return count, progress


def extract_sections(content):
    secs = []
    for part in re.split(r"\n(?=## [一二三四五六七八九十]+、)", content):
        if not part.strip():
            continue
        m = re.search(r"^## [一二三四五六七八九十]+、[^：]*：?(.+)$", part, re.M)
        if m:
            secs.append({"name": m.group(1).strip(), "content": part})
        else:
            for sub in re.split(r"\n(?=### )", part):
                sm = re.search(r"^### (.+)$", sub, re.M)
                if sm:
                    secs.append({"name": sm.group(1).strip(), "content": sub})
    return secs


if __name__ == "__main__":
    main()
