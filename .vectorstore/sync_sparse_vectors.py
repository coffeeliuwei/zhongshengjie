#!/usr/bin/env python
"""
Sparse向量入库脚本 - 为collection添加词汇精确匹配能力

BGE-M3的lexical_weights（Sparse向量）用于词汇精确匹配，配合Dense向量形成混合检索。

使用方法:
    python sync_sparse_vectors.py --collection writing_techniques_v2 --rebuild
    python sync_sparse_vectors.py --collection power_vocabulary_v1
    python sync_sparse_vectors.py --all
    python sync_sparse_vectors.py --status

注意: Sparse向量入库需要重建collection，会删除现有数据后重新入库。
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

try:
    from config_loader import get_model_path, get_hf_cache_dir, get_qdrant_url

    MODEL_PATH = get_model_path()
    HF_CACHE_DIR = get_hf_cache_dir()
    QDRANT_URL = get_qdrant_url()
except ImportError:
    config_path = Path(__file__).parent.parent / "config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        MODEL_PATH = config.get("model", {}).get("model_path")
        HF_CACHE_DIR = config.get("model", {}).get(
            "hf_cache_dir", "E:/huggingface_cache"
        )
        QDRANT_URL = config.get("database", {}).get(
            "qdrant_url", "http://localhost:6333"
        )
    else:
        MODEL_PATH = None
        HF_CACHE_DIR = "E:/huggingface_cache"
        QDRANT_URL = "http://localhost:6333"

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import PointStruct, SparseVector
except ImportError:
    raise ImportError("请安装 qdrant-client: pip install qdrant-client")

try:
    from FlagEmbedding import BGEM3FlagModel
except ImportError:
    raise ImportError("请安装 FlagEmbedding: pip install FlagEmbedding")

import torch

# 数据源配置
DATA_SOURCES = {
    "writing_techniques_v2": {
        "source_dir": "创作技法",
        "text_field": "内容",
        "payload_fields": ["技法名称", "维度", "作家", "标签"],
    },
    "power_vocabulary_v1": {
        "source_dir": ".novel-extractor/filtered",
        "source_file": "power_vocabulary_filtered.jsonl",
        "text_field": "text",
        "payload_fields": ["category", "power_type"],
    },
    "worldview_element_v1": {
        "source_dir": ".novel-extractor/filtered",
        "source_file": "worldview_element_filtered.jsonl",
        "text_field": "text",
        "payload_fields": ["element_type", "total_frequency"],
    },
    "character_relation_v1": {
        "source_dir": ".novel-extractor/filtered",
        "source_file": "character_relation_filtered.jsonl",
        "text_field": "text",
        "payload_fields": ["character1", "character2"],
    },
    "emotion_arc_v1": {
        "source_dir": ".novel-extractor/filtered",
        "source_file": "emotion_arc_filtered.jsonl",
        "text_field": "text",
        "payload_fields": ["arc_type", "emotion_pattern"],
    },
    "dialogue_style_v1": {
        "source_dir": ".novel-extractor/filtered",
        "source_file": "dialogue_style_filtered.jsonl",
        "text_field": "text",
        "payload_fields": ["faction", "style_summary"],
    },
    "foreshadow_pair_v1": {
        "source_dir": ".novel-extractor/filtered",
        "source_file": "foreshadow_pair_filtered.jsonl",
        "text_field": "text",
        "payload_fields": ["pair_count", "avg_distance"],
    },
    "power_cost_v1": {
        "source_dir": ".novel-extractor/filtered",
        "source_file": "power_cost_filtered.jsonl",
        "text_field": "text",
        "payload_fields": ["power_type", "cost_categories"],
    },
    "author_style_v1": {
        "source_dir": ".novel-extractor/filtered",
        "source_file": "author_style_filtered.jsonl",
        "text_field": "text",
        "payload_fields": ["style_pattern", "avg_sentence_length"],
    },
    "case_library_v2": {
        "source_dir": ".case-library/cases",
        "text_field": "content",
        "payload_fields": ["scene_type", "genre", "novel_name"],
        "use_jsonl": True,
    },
    "novel_settings_v2": {
        "source_dir": "设定",
        "text_field": "description",
        "payload_fields": ["name", "type", "properties"],
        "use_jsonl": False,
    },
}


class SparseVectorSyncer:
    """Sparse向量入库器"""

    def __init__(self, use_gpu: bool = True):
        self.client = QdrantClient(url=QDRANT_URL)
        self.model = None
        self.use_gpu = use_gpu
        print(f"[OK] Qdrant连接: {QDRANT_URL}")

    def _load_model(self):
        """加载BGE-M3模型"""
        if self.model is None:
            device = "cuda" if self.use_gpu and torch.cuda.is_available() else "cpu"
            use_fp16 = device == "cuda"

            if device == "cuda":
                print(f"[GPU] 使用GPU: {torch.cuda.get_device_name(0)}")

            model_path = MODEL_PATH
            if not model_path:
                local_path = (
                    Path(HF_CACHE_DIR) / "hub" / "models--BAAI--bge-m3" / "snapshots"
                )
                if local_path.exists():
                    snapshots = list(local_path.iterdir())
                    if snapshots:
                        model_path = str(snapshots[0])

            if model_path:
                print(f"[~] 加载模型: {model_path}")
                self.model = BGEM3FlagModel(
                    model_path, use_fp16=use_fp16, device=device
                )
            else:
                self.model = BGEM3FlagModel(
                    "BAAI/bge-m3", use_fp16=use_fp16, device=device
                )

            print("[OK] BGE-M3模型加载完成")

        return self.model

    def _create_sparse_collection(self, collection_name: str) -> bool:
        """创建支持Dense+Sparse的Collection"""
        try:
            # 删除旧collection
            if self.client.collection_exists(collection_name):
                print(f"  [删除] 旧Collection: {collection_name}")
                self.client.delete_collection(collection_name)

            # 创建新collection（Dense + Sparse）
            from qdrant_client.http.models import VectorParams, SparseVectorParams

            self.client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "dense": VectorParams(size=1024, distance="Cosine"),
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams(modifier="idf"),
                },
            )
            print(f"  [创建] Collection: {collection_name} (Dense+Sparse)")
            return True
        except Exception as e:
            print(f"  [错误] 创建失败: {e}")
            return False

    def _load_data(self, collection_name: str) -> List[Dict]:
        """加载数据"""
        config = DATA_SOURCES.get(collection_name)
        if not config:
            print(f"[错误] 未配置数据源: {collection_name}")
            return []

        project_root = Path(__file__).parent.parent
        items = []

        # 从JSONL文件加载
        if "source_file" in config:
            file_path = project_root / config["source_dir"] / config["source_file"]
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            try:
                                item = json.loads(line)
                                items.append(item)
                            except:
                                continue
                print(f"  [加载] {len(items)}条数据: {file_path}")

        # 从MD文件加载（技法库）
        elif config["source_dir"] == "创作技法":
            tech_dir = project_root / "创作技法"
            if tech_dir.exists():
                for md_file in tech_dir.rglob("*.md"):
                    try:
                        content = md_file.read_text(encoding="utf-8")
                        # 提取技法名称（从文件名或标题）
                        name = md_file.stem
                        items.append(
                            {
                                "技法名称": name,
                                "内容": content,
                                "维度": md_file.parent.name,
                                "source_file": str(md_file.relative_to(tech_dir)),
                            }
                        )
                    except:
                        continue
                print(f"  [加载] {len(items)}条技法: {tech_dir}")

        # 从JSONL目录加载（案例库）
        elif config.get("use_jsonl"):
            case_dir = project_root / config["source_dir"]
            if case_dir.exists():
                for jsonl_file in case_dir.rglob("*.jsonl"):
                    with open(jsonl_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                try:
                                    item = json.loads(line)
                                    items.append(item)
                                except:
                                    continue
                print(f"  [加载] {len(items)}条案例: {case_dir}")

        return items

    def sync_collection(
        self,
        collection_name: str,
        batch_size: int = 100,
        rebuild: bool = True,
    ) -> int:
        """同步单个Collection"""
        print(f"\n{'=' * 60}")
        print(f"[同步] {collection_name} -> Dense+Sparse")
        print("=" * 60)

        # 加载模型
        model = self._load_model()

        # 加载数据
        items = self._load_data(collection_name)
        if not items:
            return 0

        # 创建collection
        if rebuild:
            if not self._create_sparse_collection(collection_name):
                return 0

        # 获取文本字段配置
        config = DATA_SOURCES.get(collection_name, {})
        text_field = config.get("text_field", "text")
        payload_fields = config.get("payload_fields", [])

        # 分批处理
        total_synced = 0
        for i in tqdm(range(0, len(items), batch_size), desc="入库"):
            batch = items[i : i + batch_size]

            # 提取文本
            texts = []
            for item in batch:
                text = str(
                    item.get(text_field, item.get("内容", item.get("content", "")))
                )
                texts.append(text[:2000])  # 截断长文本

            # 编码（Dense + Sparse）
            embeddings = model.encode(
                texts,
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=False,
            )

            # 构建points
            points = []
            for j, item in enumerate(batch):
                # Dense向量
                dense_vec = embeddings["dense_vecs"][j].tolist()

                # Sparse向量（lexical_weights）
                sparse_weights = embeddings["lexical_weights"][j]
                sparse_vec = SparseVector(
                    indices=list(sparse_weights.keys()),
                    values=list(sparse_weights.values()),
                )

                # Payload
                payload = {"text": texts[j]}
                for field in payload_fields:
                    if field in item:
                        payload[field] = item[field]

                # Point
                point = PointStruct(
                    id=i + j,
                    vector={"dense": dense_vec, "sparse": sparse_vec},
                    payload=payload,
                )
                points.append(point)

            # Upsert
            try:
                self.client.upsert(collection_name=collection_name, points=points)
                total_synced += len(points)
            except Exception as e:
                print(f"  [错误] 批次 {i} 失败: {e}")
                continue

        print(f"[完成] {collection_name}: {total_synced}/{len(items)}条")
        return total_synced

    def get_status(self):
        """获取所有Collection状态"""
        print("\n" + "=" * 60)
        print("[状态] Collection向量配置")
        print("=" * 60)

        collections = self.client.get_collections().collections
        for col in collections:
            info = self.client.get_collection(col.name)
            vectors = info.config.params.vectors
            sparse_vectors = info.config.params.sparse_vectors or {}

            d = "dense" in vectors
            s = "sparse" in sparse_vectors
            c = "colbert" in vectors
            count = info.points_count

            vec_type = f"dense={d}, sparse={s}, colbert={c}"
            print(f"  {col.name}: {count} points | {vec_type}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Sparse向量入库")
    parser.add_argument("--collection", type=str, help="指定Collection")
    parser.add_argument("--all", action="store_true", help="同步所有配置的Collection")
    parser.add_argument("--rebuild", action="store_true", help="重建Collection")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--batch-size", type=int, default=100, help="批处理大小")

    args = parser.parse_args()

    syncer = SparseVectorSyncer()

    if args.status:
        syncer.get_status()
        return

    if args.all:
        for collection_name in DATA_SOURCES.keys():
            syncer.sync_collection(
                collection_name, batch_size=args.batch_size, rebuild=True
            )
        syncer.get_status()
        return

    if args.collection:
        syncer.sync_collection(
            args.collection, batch_size=args.batch_size, rebuild=args.rebuild
        )
        syncer.get_status()
        return

    # 默认显示状态
    syncer.get_status()


if __name__ == "__main__":
    main()
