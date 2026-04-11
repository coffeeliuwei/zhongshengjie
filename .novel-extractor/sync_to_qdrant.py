"""
提取数据入库 Qdrant 向量数据库

将 .novel-extractor 提取的数据同步到 Qdrant：
- worldview_element_v1: 世界观元素（地点/组织/势力）
- character_relation_v1: 人物关系图谱
- power_vocabulary_v1: 力量体系词汇
- emotion_arc_v1: 情感曲线模板
- dialogue_style_v1: 势力对话风格
- foreshadow_pair_v1: 伏笔回收配对
- power_cost_v1: 力量代价库
- author_style_v1: 作者风格指纹

使用方法:
    python sync_to_qdrant.py --all
    python sync_to_qdrant.py --dimension worldview_element
    python sync_to_qdrant.py --status
"""

import json
import os
import sys
import gc
from pathlib import Path
from typing import Dict, List, Any, Optional
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent / ".vectorstore"))
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

# 使用项目配置加载器获取路径（避免硬编码）
try:
    from config_loader import (
        get_hf_cache_dir,
        get_cache_dir,
        get_project_root,
        get_temp_dir,
    )

    HF_CACHE_DIR = get_hf_cache_dir()
    CACHE_DIR = get_cache_dir()
    PROJECT_ROOT = get_project_root()
    TEMP_DIR = get_temp_dir()

    # 设置 HuggingFace 缓存目录
    if HF_CACHE_DIR:
        os.environ["HF_HOME"] = HF_CACHE_DIR
        os.environ["HF_HUB_CACHE"] = HF_CACHE_DIR

    # 设置临时目录（避免C盘空间问题）
    if TEMP_DIR:
        os.environ["TEMP"] = str(TEMP_DIR)
        os.environ["TMP"] = str(TEMP_DIR)
except ImportError:
    HF_CACHE_DIR = None
    CACHE_DIR = None
    PROJECT_ROOT = Path(__file__).parent.parent
    TEMP_DIR = None

# 使用项目已有的配置
try:
    from bge_m3_config import BGE_M3_MODEL_NAME, BGE_M3_CACHE_DIR

    os.environ["HF_HOME"] = BGE_M3_CACHE_DIR
    print(f"[INFO] Using BGE-M3 cache: {BGE_M3_CACHE_DIR}")
except ImportError:
    BGE_M3_MODEL_NAME = "BAAI/bge-m3"
    BGE_M3_CACHE_DIR = "E:/huggingface_cache/hub"
    os.environ["HF_HOME"] = BGE_M3_CACHE_DIR

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import PointStruct, SparseVector
except ImportError:
    raise ImportError("请安装 qdrant-client: pip install qdrant-client")

try:
    from FlagEmbedding import BGEM3FlagModel
except ImportError:
    raise ImportError("请安装 FlagEmbedding: pip install FlagEmbedding")

# 配置
PROJECT_DIR = Path(__file__).parent.parent
EXTRACTED_DIR = PROJECT_DIR / ".novel-extractor" / "extracted"
FILTERED_DIR = PROJECT_DIR / ".novel-extractor" / "filtered"  # 噪音过滤后的数据
QDRANT_URL = "http://localhost:6333"

# 是否使用过滤后的数据（优先使用filtered目录）
USE_FILTERED = True

# Collection 配置
COLLECTION_CONFIG = {
    "worldview_element_v1": {
        "name": "世界观元素",
        "file": "worldview_element/worldview_element_items.jsonl",
        "filtered_file": "worldview_element_filtered.jsonl",  # 过滤后的文件
        "text_field": "element_name",
        "payload_fields": [
            "element_type",
            "total_frequency",
            "novel_count",
            "naming_pattern",
            "is_cross_novel",
        ],
    },
    "character_relation_v1": {
        "name": "人物关系",
        "file": "character_relation/character_relation_items.jsonl",
        "filtered_file": "character_relation_filtered.jsonl",
        "text_field": "character1_character2",  # 合成的唯一键
        "payload_fields": ["character1", "character2", "cooccurrence_count"],
    },
    "power_vocabulary_v1": {
        "name": "力量词汇",
        "file": "power_vocabulary/power_vocabulary_items.jsonl",
        "filtered_file": "power_vocabulary_filtered.jsonl",
        "text_field": "term",
        "payload_fields": ["category", "power_type", "total_frequency", "novel_count"],
    },
    "emotion_arc_v1": {
        "name": "情感曲线",
        "file": "emotion_arc/emotion_arc_items.jsonl",
        "filtered_file": "emotion_arc_filtered.jsonl",
        "text_field": "arc_type",
        "payload_fields": [
            "novel_count",
            "avg_variance",
            "avg_turning_points",
            "description",
        ],
    },
    "dialogue_style_v1": {
        "name": "对话风格",
        "file": "dialogue_style/dialogue_style_items.jsonl",
        "filtered_file": "dialogue_style_filtered.jsonl",
        "text_field": "faction",
        "payload_fields": ["novel_count", "total_dialogues", "style_summary"],
    },
    "foreshadow_pair_v1": {
        "name": "伏笔配对",
        "file": "foreshadow_pair/foreshadow_pair_items.jsonl",
        "filtered_file": "foreshadow_pair_filtered.jsonl",
        "text_field": "relation_type",
        "payload_fields": ["pair_count", "avg_distance", "description"],
    },
    "power_cost_v1": {
        "name": "力量代价",
        "file": "power_cost/power_cost_items.jsonl",
        "filtered_file": "power_cost_filtered.jsonl",
        "text_field": "power_type",
        "payload_fields": ["total_expressions", "cost_categories"],
    },
    "author_style_v1": {
        "name": "作者风格",
        "file": "author_style/author_style_items.jsonl",
        "filtered_file": "author_style_filtered.jsonl",
        "text_field": "style_pattern",
        "payload_fields": [
            "novel_count",
            "avg_sentence_length",
            "rhetoric_usage",
            "description",
        ],
    },
}


class ExtractorSyncManager:
    """提取数据入库管理器"""

    def __init__(self, use_docker: bool = True):
        self.client = None
        self.model = None
        self.use_docker = use_docker

    def _get_client(self) -> QdrantClient:
        """获取 Qdrant 客户端"""
        if self.client is None:
            if self.use_docker:
                try:
                    self.client = QdrantClient(url=QDRANT_URL)
                    self.client.get_collections()
                    print(f"[OK] 已连接 Docker Qdrant: {QDRANT_URL}")
                except Exception as e:
                    print(f"[WARN] Docker Qdrant 连接失败: {e}")
                    self.client = QdrantClient(
                        path=str(PROJECT_DIR / ".vectorstore" / "qdrant")
                    )
            else:
                self.client = QdrantClient(
                    path=str(PROJECT_DIR / ".vectorstore" / "qdrant")
                )
        return self.client

    def _load_model(self, use_gpu: bool = True):
        """加载 BGE-M3 模型（支持GPU加速）"""
        if self.model is None:
            # 检测GPU可用性
            import torch

            device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
            use_fp16 = device == "cuda"  # GPU使用fp16加速

            if device == "cuda":
                print(f"[GPU] 使用GPU加速: {torch.cuda.get_device_name(0)}")
            else:
                print(f"[CPU] GPU不可用，使用CPU模式")

            # 使用本地模型路径（避免网络下载）
            local_model_path = (
                Path(BGE_M3_CACHE_DIR)
                / "hub"
                / "models--BAAI--bge-m3"
                / "snapshots"
                / "5617a9f61b028005a4858fdac845db406aefb181"
            )

            if local_model_path.exists():
                print(f"[~] 加载本地 BGE-M3 模型: {local_model_path}")
                self.model = BGEM3FlagModel(
                    str(local_model_path),
                    use_fp16=use_fp16,
                    device=device,
                )
            else:
                print(f"[~] 加载 BGE-M3 模型 (cache: {BGE_M3_CACHE_DIR})...")
                self.model = BGEM3FlagModel(
                    BGE_M3_MODEL_NAME,
                    use_fp16=use_fp16,
                    device=device,
                )
            print("[OK] 模型加载完成")
        return self.model

    def _create_collection(self, collection_name: str) -> bool:
        """创建 Collection"""
        client = self._get_client()

        try:
            collections = [c.name for c in client.get_collections().collections]
            if collection_name in collections:
                print(f"  [删除] 旧 Collection: {collection_name}")
                client.delete_collection(collection_name=collection_name)

            # 创建支持 Dense 向量的 Collection
            client.create_collection(
                collection_name=collection_name,
                vectors_config={"dense": {"size": 1024, "distance": "Cosine"}},
            )
            print(f"  [创建] Collection: {collection_name}")
            return True
        except Exception as e:
            print(f"  [错误] 创建 Collection 失败: {e}")
            return False

    def sync_dimension(
        self,
        dimension_id: str,
        rebuild: bool = False,
        chunk_size: int = 5000,
        resume: bool = True,
        use_filtered: bool = None,  # 是否使用过滤后的数据
    ) -> int:
        """同步单个维度（分块处理，支持断点续传）"""
        config = COLLECTION_CONFIG.get(dimension_id)
        if not config:
            print(f"[错误] 未知的维度: {dimension_id}")
            return 0

        print(f"\n{'=' * 60}")
        print(f"[同步] {config['name']} -> {dimension_id}")
        print(f"{'=' * 60}")

        # 决定使用哪个数据源
        if use_filtered is None:
            use_filtered = USE_FILTERED

        # 优先尝试filtered目录
        file_path = None
        if use_filtered and "filtered_file" in config:
            filtered_path = FILTERED_DIR / config["filtered_file"]
            if filtered_path.exists():
                file_path = filtered_path
                print(f"  [使用] 过滤后的数据: {filtered_path}")

        # 如果filtered不存在，回退到extracted目录
        if file_path is None:
            file_path = EXTRACTED_DIR / config["file"]
            print(f"  [使用] 原始数据: {file_path}")

        if not file_path.exists():
            print(f"  [错误] 数据文件不存在: {file_path}")
            return 0

        # 加载数据
        items = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        item = json.loads(line)
                        items.append(item)
                    except json.JSONDecodeError:
                        continue

        print(f"  发现 {len(items)} 条数据")

        if not items:
            return 0

        client = self._get_client()

        # 检查Collection是否存在及当前进度
        collections = [c.name for c in client.get_collections().collections]
        start_index = 0

        if dimension_id in collections and resume and not rebuild:
            # 断点续传：检查已有数据量
            try:
                info = client.get_collection(dimension_id)
                existing_points = info.points_count
                start_index = existing_points
                print(f"  [续传] 已有 {existing_points} 条，从索引 {start_index} 继续")
            except Exception:
                print(f"  [警告] 无法获取已有数据量，从头开始")
                start_index = 0

        # 创建或重建Collection
        if rebuild or dimension_id not in collections:
            if not self._create_collection(dimension_id):
                return 0
            start_index = 0

        # 加载模型
        model = self._load_model()

        total_synced = start_index  # 已同步的数量

        # 分块处理（从start_index开始）
        for chunk_start in range(start_index, len(items), chunk_size):
            chunk_end = min(chunk_start + chunk_size, len(items))
            chunk_items = items[chunk_start:chunk_end]

            print(f"  处理块 {chunk_start}-{chunk_end} ({len(chunk_items)} 条)...")

            # 构建文本用于编码
            texts = []
            for item in chunk_items:
                text = self._build_text(item, config)
                texts.append(text)

            # 批量编码（小batch）
            embeddings = model.encode(
                texts,
                return_dense=True,
                batch_size=16,  # 减小batch_size避免内存溢出
                max_length=512,
            )

            # 构建 Points
            points = []
            for i, item in enumerate(chunk_items):
                dense_vec = embeddings["dense_vecs"][i].tolist()
                payload = self._build_payload(item, config, texts[i])
                point = PointStruct(
                    id=chunk_start + i,  # 全局ID
                    vector={"dense": dense_vec},
                    payload=payload,
                )
                points.append(point)

            # 上传当前块
            upload_batch_size = 100
            for j in range(0, len(points), upload_batch_size):
                batch = points[j : j + upload_batch_size]
                client.upsert(collection_name=dimension_id, points=batch)

            total_synced += len(points)
            print(
                f"    已同步: {total_synced}/{len(items)} ({100 * total_synced // len(items)}%)"
            )

            # 清理内存
            del embeddings, points, texts
            import gc

            gc.collect()

        print(f"[OK] 已同步 {total_synced} 条数据")
        return total_synced

    def _build_text(self, item: Dict, config: Dict) -> str:
        """构建用于编码的文本"""
        text_field = config["text_field"]

        if text_field == "character1_character2":
            return (
                f"{item.get('character1', '')} 与 {item.get('character2', '')} 的关系"
            )

        return (
            item.get(text_field, "")
            or item.get("element_name", "")
            or item.get("term", "")
            or "未知"
        )

    def _build_payload(self, item: Dict, config: Dict, text: str) -> Dict:
        """构建 payload"""
        payload = {"text": text[:1000]}

        for field in config["payload_fields"]:
            value = item.get(field)
            if value:
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value, ensure_ascii=False)[:2000]
                    payload[field] = value_str
                else:
                    payload[field] = str(value)[:500]

        # 保留完整数据的引用
        payload["_source"] = config["file"]

        return payload

    def sync_all(self, rebuild: bool = True) -> Dict[str, int]:
        """同步所有维度"""
        results = {}

        for dimension_id in COLLECTION_CONFIG.keys():
            file_path = EXTRACTED_DIR / COLLECTION_CONFIG[dimension_id]["file"]
            if file_path.exists():
                results[dimension_id] = self.sync_dimension(
                    dimension_id, rebuild=rebuild
                )
            else:
                print(f"[跳过] {dimension_id}: 数据文件不存在")

        # 打印汇总
        print(f"\n{'=' * 60}")
        print("📊 同步汇总")
        print(f"{'=' * 60}")
        total = 0
        for name, count in results.items():
            config = COLLECTION_CONFIG.get(name, {})
            print(f"  {config.get('name', name)}: {count} 条")
            total += count
        print(f"\n  总计: {total} 条")
        print(f"{'=' * 60}")

        return results

    def get_status(self) -> Dict[str, Any]:
        """获取入库状态"""
        client = self._get_client()

        collections = [c.name for c in client.get_collections().collections]

        status = {}
        for dimension_id, config in COLLECTION_CONFIG.items():
            file_path = EXTRACTED_DIR / config["file"]

            # 文件状态
            file_exists = file_path.exists()
            file_count = 0
            file_size = 0

            if file_exists:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_count = sum(1 for line in f if line.strip())
                file_size = file_path.stat().st_size / 1024 / 1024

            # Qdrant 状态
            in_qdrant = dimension_id in collections
            qdrant_count = 0

            if in_qdrant:
                try:
                    info = client.get_collection(dimension_id)
                    qdrant_count = info.points_count
                except Exception:
                    pass

            status[dimension_id] = {
                "name": config["name"],
                "file_exists": file_exists,
                "file_count": file_count,
                "file_size_mb": round(file_size, 2),
                "in_qdrant": in_qdrant,
                "qdrant_count": qdrant_count,
                "sync_status": "已同步"
                if qdrant_count > 0 and file_count > 0
                else "待同步",
            }

        return status

    def print_status(self):
        """打印状态"""
        status = self.get_status()

        print(f"\n{'=' * 60}")
        print("[STATUS] 提取数据入库状态")
        print(f"{'=' * 60}")

        print("\n[数据文件状态]")
        for dim_id, info in status.items():
            file_status = "[OK]" if info["file_exists"] else "[X]"
            print(
                f"  {file_status} {info['name']}: {info['file_count']} 条 ({info['file_size_mb']} MB)"
            )

        print("\n[Qdrant 入库状态]")
        for dim_id, info in status.items():
            qdrant_status = "[OK]" if info["in_qdrant"] else "[X]"
            sync_status = info["sync_status"]
            print(
                f"  {qdrant_status} {dim_id}: {info['qdrant_count']} points ({sync_status})"
            )


def main():
    import argparse

    parser = argparse.ArgumentParser(description="提取数据入库 Qdrant")
    parser.add_argument(
        "--sync",
        choices=["all"] + list(COLLECTION_CONFIG.keys()),
        default="all",
        help="同步目标",
    )
    parser.add_argument("--rebuild", action="store_true", help="重建 Collection")
    parser.add_argument("--status", action="store_true", help="查看状态")

    args = parser.parse_args()

    sync = ExtractorSyncManager()

    if args.status:
        sync.print_status()
    elif args.sync == "all":
        sync.sync_all(rebuild=args.rebuild)
    else:
        sync.sync_dimension(args.sync, rebuild=args.rebuild)


if __name__ == "__main__":
    main()
