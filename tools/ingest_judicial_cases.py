#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
司法案例向量入库工具
====================

将 filter_judicial_cases.py 过滤后 reviewed/ 目录的文章
用 BGE-M3 嵌入并写入 Qdrant judicial_cases_v1 collection。

每篇文章按 CHUNK_SIZE 字符分块，允许 CHUNK_OVERLAP 字符重叠，
每块独立存储，payload 保留完整元数据便于还原原文。

用法：
    python tools/ingest_judicial_cases.py                    # 默认目录
    python tools/ingest_judicial_cases.py --dir E:/司法案例  # 指定根目录
    python tools/ingest_judicial_cases.py --rebuild          # 强制重建 collection
    python tools/ingest_judicial_cases.py --embed-batch 96   # 调整 GPU batch
"""

import argparse
import hashlib
import os
import sys
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from core.config_loader import (
        get_batch_size,
        get_collection_name,
        get_config,
        get_device,
        get_judicial_cases_dir,
        get_model_path,
        get_qdrant_url,
    )

    DEFAULT_DIR = get_judicial_cases_dir()
    QDRANT_URL = get_qdrant_url()
    MODEL_PATH = get_model_path()
    COLLECTION = get_collection_name("judicial_cases")
    DEVICE = get_device()
    EMBED_BATCH = get_batch_size() or 64
    _cfg = get_config()
    HF_CACHE = _cfg.get("model", {}).get("hf_cache_dir")
except Exception as e:
    print(f"[!] 配置加载失败: {e}，使用默认值")
    DEFAULT_DIR = Path("E:/司法案例")
    QDRANT_URL = "http://localhost:6333"
    MODEL_PATH = "BAAI/bge-m3"
    COLLECTION = "judicial_cases_v1"
    DEVICE = "cpu"
    EMBED_BATCH = 64
    HF_CACHE = None

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


# ── 解析 txt 文件 ─────────────────────────────────────────────────────────────

def parse_article(filepath: Path) -> dict:
    text = filepath.read_text(encoding="utf-8", errors="replace")
    meta = {}
    content = text

    if "===CONTENT===" in text:
        parts = text.split("===CONTENT===", 1)
        for line in parts[0].splitlines():
            if ": " in line and not line.startswith("==="):
                k, v = line.split(": ", 1)
                meta[k.strip()] = v.strip()
        content = parts[1].strip()

    source = "unknown"
    for part in filepath.parts:
        if part in ("spp", "thepaper"):
            source = part
            break

    return {
        "title": meta.get("标题", filepath.stem),
        "date": meta.get("日期", ""),
        "source_site": meta.get("来源", source),
        "section": meta.get("栏目", ""),
        "url": meta.get("URL", ""),
        "content": content,
    }


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += size - overlap
    return chunks


# ── Qdrant 写入 ───────────────────────────────────────────────────────────────

def _upsert_with_retry(client, collection: str, points, retries: int = 5):
    for attempt in range(retries):
        try:
            client.upsert(collection_name=collection, points=points)
            return
        except Exception as e:
            if attempt == retries - 1:
                raise
            wait = 5 * (attempt + 1)
            print(f"\n    [重试] {e.__class__.__name__}，{wait}s 后重试...")
            time.sleep(wait)


# ── 主流程 ───────────────────────────────────────────────────────────────────

def run(reviewed_dir: Path, collection: str, qdrant_url: str, rebuild: bool, embed_batch: int):
    files = sorted(reviewed_dir.rglob("*.txt"))
    files = [f for f in files if not f.name.startswith(".")]
    print(f"[i] 找到 {len(files)} 篇已审核文章")
    if not files:
        print("[!] reviewed/ 为空，先运行 filter_judicial_cases.py")
        return

    # 解析并分块
    all_chunks = []  # (point_id_hex, embed_text, payload)
    for f in files:
        art = parse_article(f)
        parts = chunk_text(art["content"])
        for i, chunk in enumerate(parts):
            uid = hashlib.md5(f"{f}:{i}".encode()).hexdigest()
            all_chunks.append((
                uid,
                chunk,
                {
                    "title": art["title"],
                    "date": art["date"],
                    "source_site": art["source_site"],
                    "section": art["section"],
                    "url": art["url"],
                    "content": chunk,
                    "chunk_index": i,
                    "total_chunks": len(parts),
                    "file": str(f),
                },
            ))

    total = len(all_chunks)
    print(f"[i] 共 {total} 个文本块（平均 {total / len(files):.1f} 块/篇）\n")

    # 连接 Qdrant
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        OptimizersConfigDiff,
        PointStruct,
        SparseVectorParams,
        VectorParams,
    )

    client = QdrantClient(url=qdrant_url, timeout=60)
    existing = [c.name for c in client.get_collections().collections]

    if collection in existing and not rebuild:
        info = client.get_collection(collection)
        print(f"[i] collection {collection} 已有 {info.points_count} 个点")
        print("[i] 使用 --rebuild 强制重建，退出")
        return

    if collection in existing:
        client.delete_collection(collection)
        print(f"[删除] {collection}")

    client.create_collection(
        collection_name=collection,
        vectors_config={"dense": VectorParams(size=1024, distance=Distance.COSINE)},
        sparse_vectors_config={"sparse": SparseVectorParams()},
        optimizers_config=OptimizersConfigDiff(indexing_threshold=0),
    )
    print(f"[创建] {collection}（上传期间禁用 HNSW）\n")

    # 加载 BGE-M3
    if HF_CACHE:
        os.environ["HF_HOME"] = str(HF_CACHE)
        os.environ["TRANSFORMERS_CACHE"] = str(HF_CACHE)

    from FlagEmbedding import BGEM3FlagModel

    print("[加载] BGE-M3 模型...")
    model = BGEM3FlagModel(MODEL_PATH or "BAAI/bge-m3", use_fp16=True, device=DEVICE)
    print("[加载] 完成\n")

    # 流水线：GPU 推理下一批时，后台线程上传当前批
    texts = [c[1] for c in all_chunks]
    ids_hex = [c[0] for c in all_chunks]
    payloads = [c[2] for c in all_chunks]

    synced = 0
    t0 = time.time()
    pending: Optional[Future] = None
    pending_n = 0

    with ThreadPoolExecutor(max_workers=1) as executor:
        for start in range(0, total, embed_batch):
            batch_texts = texts[start : start + embed_batch]
            batch_ids = ids_hex[start : start + embed_batch]
            batch_payloads = payloads[start : start + embed_batch]

            output = model.encode(
                batch_texts,
                batch_size=embed_batch,
                max_length=512,
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=False,
            )
            dense_vecs = output["dense_vecs"].tolist()
            lexical_weights = output["lexical_weights"]

            points = []
            for uid, dense, lw, payload in zip(
                batch_ids, dense_vecs, lexical_weights, batch_payloads
            ):
                points.append(
                    PointStruct(
                        id=int(uid[:8], 16) % (2**63),
                        vector={
                            "dense": dense,
                            "sparse": {
                                "indices": [int(k) for k in lw.keys()],
                                "values": [float(v) for v in lw.values()],
                            },
                        },
                        payload=payload,
                    )
                )

            if pending is not None:
                pending.result()
                synced += pending_n

            pending = executor.submit(_upsert_with_retry, client, collection, points)
            pending_n = len(points)

            elapsed = time.time() - t0
            done_so_far = synced + pending_n
            speed = done_so_far / elapsed if elapsed > 0 else 0
            print(
                f"  [{done_so_far}/{total}] {speed:.1f} 块/s  ",
                end="\r",
            )

        if pending is not None:
            pending.result()
            synced += pending_n

    # 启用 HNSW 索引
    client.update_collection(
        collection_name=collection,
        optimizer_config=OptimizersConfigDiff(indexing_threshold=20000),
    )

    elapsed = time.time() - t0
    print(f"\n[完成] 入库 {synced} 块，耗时 {elapsed:.0f}s")
    print(f"[collection] {collection} @ {qdrant_url}")


def main():
    parser = argparse.ArgumentParser(description="司法案例向量入库")
    parser.add_argument("--dir", default=str(DEFAULT_DIR), help="司法案例根目录")
    parser.add_argument("--rebuild", action="store_true", help="强制重建 collection")
    parser.add_argument(
        "--embed-batch", type=int, default=EMBED_BATCH, help=f"GPU embedding batch（默认{EMBED_BATCH}）"
    )
    args = parser.parse_args()

    reviewed_dir = Path(args.dir) / "reviewed"
    print("=" * 56)
    print("  司法案例向量入库")
    print("=" * 56)
    print(f"  来源: {reviewed_dir}")
    print(f"  目标: {COLLECTION} @ {QDRANT_URL}")
    print(f"  embed batch: {args.embed_batch}")
    print("=" * 56 + "\n")

    run(
        reviewed_dir=reviewed_dir,
        collection=COLLECTION,
        qdrant_url=QDRANT_URL,
        rebuild=args.rebuild,
        embed_batch=args.embed_batch,
    )


if __name__ == "__main__":
    main()
