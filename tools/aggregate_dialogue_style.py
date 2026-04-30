# -*- coding: utf-8 -*-
"""
对话风格跨书聚合 + 重建 Qdrant dialogue_style_v1

将 E:/novel_extracted/dialogue_style/dialogue_style_all.json 中
每本×每势力的 12017 条，聚合成每势力 1 条（共 8 条），重建入库。
"""
import sys
import os
import json
from pathlib import Path
from collections import defaultdict, Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / ".vectorstore"))

# ── 配置 ──────────────────────────────────────────────────────────
DATA_PATH = Path("E:/novel_extracted/dialogue_style/dialogue_style_all.json")
COLLECTION = "dialogue_style_v1"
EMBED_BATCH = 8


def _resolve_model_path() -> str:
    from bge_m3_config import BGE_M3_MODEL_NAME, BGE_M3_CACHE_DIR
    cache = Path(BGE_M3_CACHE_DIR)
    for sub in (cache / "hub", cache):
        snap_dir = sub / "models--BAAI--bge-m3" / "snapshots"
        if snap_dir.exists():
            for snap in sorted(snap_dir.iterdir()):
                if (snap / "tokenizer.json").exists():
                    return str(snap)
    return BGE_M3_MODEL_NAME


def aggregate(data: list) -> list:
    """按 faction 聚合，返回 8 条汇总记录"""
    groups = defaultdict(list)
    for item in data:
        faction = item.get("faction", "未知")
        groups[faction].append(item)

    results = []
    for faction, items in groups.items():
        n = len(items)

        # 数值字段：均值
        avg_dialogues = sum(i.get("total_dialogues", 0) for i in items) / n
        avg_sentence_len = sum(
            i.get("sentence_features", {}).get("avg_sentence_length", 0) for i in items
        ) / n

        # 词频：合并 Counter
        word_freq: Counter = Counter()
        for i in items:
            wf = i.get("word_features", {}).get("known_word_frequency", {})
            word_freq.update({k: v for k, v in wf.items()})

        discovered: Counter = Counter()
        for i in items:
            for dw in i.get("word_features", {}).get("discovered_words", []):
                if isinstance(dw, dict):
                    discovered[dw.get("word", "")] += dw.get("frequency", 1)
                elif isinstance(dw, str):
                    discovered[dw] += 1

        # 语气分布：合并
        tone_total: Counter = Counter()
        for i in items:
            td = i.get("tone_features", {}).get("tone_distribution", {})
            tone_total.update(td)

        # 样例对话：取各本前 2 条，最多保留 20 条
        samples = []
        for i in items:
            samples.extend(i.get("sample_dialogues", [])[:2])
            if len(samples) >= 20:
                break
        samples = samples[:20]

        # style_summary：取出现最多的那条
        summaries = Counter(i.get("style_summary", "") for i in items if i.get("style_summary"))
        best_summary = summaries.most_common(1)[0][0] if summaries else ""

        results.append({
            "faction": faction,
            "novel_count": n,
            "avg_total_dialogues": round(avg_dialogues),
            "avg_sentence_length": round(avg_sentence_len, 1),
            "word_features": {
                "known_word_frequency": dict(word_freq.most_common(50)),
                "discovered_words": [
                    {"word": w, "frequency": c}
                    for w, c in discovered.most_common(30)
                ],
            },
            "tone_features": {"tone_distribution": dict(tone_total)},
            "sample_dialogues": samples,
            "style_summary": best_summary,
        })

    results.sort(key=lambda x: x["novel_count"], reverse=True)
    return results


def build_text(item: dict) -> str:
    return f"{item['faction']}风格：{item.get('style_summary', '')}（基于{item['novel_count']}本小说）"


def main():
    print("=" * 60)
    print("对话风格聚合 + 重建 dialogue_style_v1")
    print("=" * 60)

    # 1. 读取原始数据
    print(f"\n[1] 读取: {DATA_PATH}")
    with open(DATA_PATH, encoding="utf-8", errors="ignore") as f:
        raw = json.load(f)
    print(f"    原始条数: {len(raw):,}")

    # 2. 聚合
    print("\n[2] 按势力聚合...")
    aggregated = aggregate(raw)
    print(f"    聚合后: {len(aggregated)} 条")
    for item in aggregated:
        print(f"    {item['faction']}: {item['novel_count']} 本 → 1条")

    # 3. 加载 BGE-M3
    print("\n[3] 加载 BGE-M3...")
    from bge_m3_config import BGE_M3_CACHE_DIR, USE_FP16, DENSE_VECTOR_SIZE
    os.environ["HF_HOME"] = BGE_M3_CACHE_DIR
    from FlagEmbedding import BGEM3FlagModel
    model_path = _resolve_model_path()
    print(f"    模型路径: {model_path}")
    model = BGEM3FlagModel(model_path, use_fp16=USE_FP16, device="cuda")
    print("    [OK] 模型加载完成")

    # 4. 编码
    texts = [build_text(item) for item in aggregated]
    print(f"\n[4] 编码 {len(texts)} 条...")
    output = model.encode(
        texts,
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=True,
        batch_size=EMBED_BATCH,
    )

    # 5. 重建 Qdrant collection
    print(f"\n[5] 重建 Qdrant collection: {COLLECTION}")
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        PointStruct, VectorParams, Distance,
        SparseVectorParams, SparseVector,
    )
    from bge_m3_config import get_collection_config

    client = QdrantClient(url="http://localhost:6333", timeout=300)
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION in existing:
        client.delete_collection(COLLECTION)
        print(f"    [删除] 旧 collection")

    cfg = get_collection_config()
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=cfg["vectors_config"],
        sparse_vectors_config=cfg["sparse_vectors_config"],
    )
    print(f"    [创建] {COLLECTION}")

    # 6. 上传
    print(f"\n[6] 上传 {len(aggregated)} 条...")
    points = []
    for i, item in enumerate(aggregated):
        dense = output["dense_vecs"][i].tolist()
        sparse_dict = output["lexical_weights"][i]
        colbert = output["colbert_vecs"][i]
        colbert_list = colbert.tolist() if hasattr(colbert, "tolist") else colbert

        points.append(PointStruct(
            id=i,
            vector={
                "dense": dense,
                "colbert": colbert_list,
                "sparse": SparseVector(
                    indices=list(sparse_dict.keys()),
                    values=list(sparse_dict.values()),
                ),
            },
            payload=item,
        ))

    client.upsert(collection_name=COLLECTION, points=points)
    print(f"    [OK] 已上传 {len(points)} 条")

    # 7. 保存聚合结果
    out_path = DATA_PATH.parent / "dialogue_style_aggregated.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(aggregated, f, ensure_ascii=False, indent=2)
    print(f"\n[7] 聚合结果已保存: {out_path}")

    print("\n" + "=" * 60)
    print(f"[DONE] dialogue_style_v1: {len(raw):,} 条 → {len(aggregated)} 条")
    print("=" * 60)


if __name__ == "__main__":
    main()
