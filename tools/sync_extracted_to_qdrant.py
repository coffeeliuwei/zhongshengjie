"""
tools/sync_extracted_to_qdrant.py
将 E:\\novel_extracted\\{dim}\\{dim}_all.json 向量化并同步到 Qdrant

每个 collection 全量重建（删除旧数据 + 重新写入）。

用法:
    python tools/sync_extracted_to_qdrant.py              # 同步全部8个维度
    python tools/sync_extracted_to_qdrant.py --dim author_style_v1
    python tools/sync_extracted_to_qdrant.py --dry-run    # 不实际写入，只统计条数
"""

import json
import sys
import argparse
import time
from pathlib import Path
from typing import List, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config_loader import get_config

_cfg = get_config()
EXTRACTED_OUTPUT_DIR = Path(
    _cfg.get("extractor", {}).get("output_dir", r"E:\novel_extracted")
)
QDRANT_URL = _cfg.get("database", {}).get("qdrant_url", "http://localhost:6333")
VECTOR_SIZE = _cfg.get("model", {}).get("vector_size", 1024)
EMBED_BATCH_SIZE = _cfg.get("model", {}).get("batch_size", 20)
HF_CACHE = _cfg.get("model", {}).get("hf_cache_dir", r"D:\huggingface_cache")
MODEL_NAME = _cfg.get("model", {}).get("embedding", {}).get("name", "BAAI/bge-m3")
MODEL_PATH = _cfg.get("model", {}).get("embedding", {}).get("model_path", None)

# 每次 upsert 到 Qdrant 的批次大小
UPSERT_BATCH = 200


# ==================== embedding 文本生成函数 ====================


def _text_author_style(item: Dict) -> str:
    return f"{item.get('style_pattern', '')}。{item.get('description', '')}"


def _text_character_relation(item: Dict) -> str:
    c1 = item.get("character1", "")
    c2 = item.get("character2", "")
    cnt = item.get("cooccurrence_count", 0)
    return f"{c1} 与 {c2} 共现{cnt}次"


def _text_dialogue_style(item: Dict) -> str:
    return f"{item.get('faction', '')}风格：{item.get('style_summary', '')}"


def _text_emotion_arc(item: Dict) -> str:
    return f"{item.get('arc_type', '')}：{item.get('description', '')}"


def _text_foreshadow_pair(item: Dict) -> str:
    return f"{item.get('relation_type', '')}：{item.get('description', '')}"


def _text_power_cost(item: Dict) -> str:
    cats = item.get("cost_categories", [])
    cats_str = "、".join(str(c) for c in cats[:5]) if cats else ""
    return f"{item.get('power_type', '')}体系代价：{cats_str}"


def _text_power_vocabulary(item: Dict) -> str:
    return f"{item.get('term', '')}（{item.get('category', '')}，{item.get('power_type', '')}体系）"


def _text_worldview_element(item: Dict) -> str:
    return f"{item.get('element_name', '')}（{item.get('element_type', '')}）"


# ==================== 维度配置表 ====================

SYNC_DIMENSIONS: Dict[str, Dict] = {
    "author_style_v1": {
        "source_dir": "author_style",
        "name": "作者风格指纹",
        "text_fn": _text_author_style,
    },
    "character_relation_v1": {
        "source_dir": "character_relation",
        "name": "人物关系网络",
        "text_fn": _text_character_relation,
    },
    "dialogue_style_v1": {
        "source_dir": "dialogue_style",
        "name": "势力对话风格",
        "text_fn": _text_dialogue_style,
    },
    "emotion_arc_v1": {
        "source_dir": "emotion_arc",
        "name": "情感弧线",
        "text_fn": _text_emotion_arc,
    },
    "foreshadow_pair_v1": {
        "source_dir": "foreshadow_pair",
        "name": "伏笔配对",
        "text_fn": _text_foreshadow_pair,
    },
    "power_cost_v1": {
        "source_dir": "power_cost",
        "name": "力量体系代价",
        "text_fn": _text_power_cost,
    },
    "power_vocabulary_v1": {
        "source_dir": "power_vocabulary",
        "name": "力量词汇库",
        "text_fn": _text_power_vocabulary,
    },
    "worldview_element_v1": {
        "source_dir": "worldview_element",
        "name": "世界观元素",
        "text_fn": _text_worldview_element,
    },
}


# ==================== 核心函数 ====================


def load_model():
    """加载 BGE-M3 模型（FlagEmbedding）"""
    import os

    os.environ["HF_HOME"] = str(HF_CACHE)
    os.environ["TRANSFORMERS_CACHE"] = str(HF_CACHE)

    from FlagEmbedding import BGEM3FlagModel

    model_path = MODEL_PATH if MODEL_PATH else MODEL_NAME
    print(f"[模型] 加载 {model_path} ...")
    model = BGEM3FlagModel(model_path, use_fp16=True)
    print("[模型] 加载完成")
    return model


def embed_batch(model, texts: List[str]) -> List[List[float]]:
    """批量向量化，返回 dense 向量列表"""
    result = model.encode(texts, batch_size=EMBED_BATCH_SIZE, max_length=512)
    return result["dense_vecs"].tolist()


def rebuild_collection(client, collection_name: str) -> None:
    """删除旧 collection 并重建（仅 dense 1024维 Cosine）"""
    from qdrant_client.models import VectorParams, Distance

    existing = [c.name for c in client.get_collections().collections]
    if collection_name in existing:
        print(f"  [删除] 旧 collection: {collection_name}")
        client.delete_collection(collection_name)

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    print(f"  [创建] collection: {collection_name}")


def _make_payload(item: Dict, embed_text: str) -> Dict:
    """构造 payload，去掉超过500字符的列表字段"""
    payload = {}
    for k, v in item.items():
        if isinstance(v, list):
            if len(json.dumps(v, ensure_ascii=False)) > 500:
                continue
        payload[k] = v
    payload["_embed_text"] = embed_text
    return payload


def sync_dimension(
    client, model, dim_id: str, config: Dict, dry_run: bool = False
) -> int:
    """同步单个维度，返回已同步条数"""
    source_file = (
        EXTRACTED_OUTPUT_DIR / config["source_dir"] / f"{config['source_dir']}_all.json"
    )

    print(f"\n{'=' * 60}")
    print(f"[同步] {config['name']}  →  {dim_id}")
    print(f"{'=' * 60}")

    if not source_file.exists():
        print(f"  [跳过] 文件不存在: {source_file}")
        return 0

    print(f"  [加载] {source_file}")
    with open(source_file, encoding="utf-8") as f:
        items: List[Dict] = json.load(f)
    total = len(items)
    print(f"  [数据] {total} 条")

    if dry_run:
        print(f"  [DRY-RUN] 预计写入 {total} 条，跳过实际操作")
        return total

    rebuild_collection(client, dim_id)

    text_fn = config["text_fn"]
    synced = 0
    t0 = time.time()

    from qdrant_client.models import PointStruct

    for batch_start in range(0, total, UPSERT_BATCH):
        batch = items[batch_start : batch_start + UPSERT_BATCH]

        # 生成 embedding 文本，兜底取第一个非空字符串字段
        texts = []
        for item in batch:
            text = text_fn(item).strip()
            if not text:
                for v in item.values():
                    if isinstance(v, str) and v.strip():
                        text = v[:512]
                        break
            texts.append(text[:512])

        vectors = embed_batch(model, texts)

        points = []
        for i, (item, vec) in enumerate(zip(batch, vectors)):
            point_id = batch_start + i + 1  # 整数ID，从1开始
            payload = _make_payload(item, texts[i])
            points.append(PointStruct(id=point_id, vector=vec, payload=payload))

        client.upsert(collection_name=dim_id, points=points)
        synced += len(batch)

        elapsed = time.time() - t0
        speed = synced / elapsed if elapsed > 0 else 0
        eta = (total - synced) / speed if speed > 0 else 0
        print(
            f"  [{synced:>6}/{total}] {synced / total * 100:5.1f}%"
            f"  速度:{speed:.0f}条/s  剩余:{eta / 60:.1f}min",
            end="\r",
            flush=True,
        )

    print(f"\n  [完成] {synced} 条  耗时:{(time.time() - t0) / 60:.1f}min")
    return synced


def main():
    parser = argparse.ArgumentParser(
        description="将 novel_extracted _all.json 同步到 Qdrant"
    )
    parser.add_argument(
        "--dim",
        choices=list(SYNC_DIMENSIONS.keys()),
        help="只同步指定维度（不指定则同步全部8个）",
    )
    parser.add_argument("--dry-run", action="store_true", help="不实际写入，只统计条数")
    args = parser.parse_args()

    from qdrant_client import QdrantClient

    print(f"[连接] Qdrant: {QDRANT_URL}")
    client = QdrantClient(url=QDRANT_URL, timeout=60)

    try:
        client.get_collections()
        print("[连接] OK")
    except Exception as e:
        print(f"[错误] 无法连接 Qdrant: {e}")
        sys.exit(1)

    model = None
    if not args.dry_run:
        model = load_model()

    targets = {args.dim: SYNC_DIMENSIONS[args.dim]} if args.dim else SYNC_DIMENSIONS

    total_synced = 0
    t_start = time.time()

    for dim_id, config in targets.items():
        count = sync_dimension(client, model, dim_id, config, dry_run=args.dry_run)
        total_synced += count

    elapsed = time.time() - t_start
    print(f"\n{'=' * 60}")
    print(f"[DONE] 共同步 {total_synced} 条  总耗时 {elapsed / 3600:.1f}h")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
