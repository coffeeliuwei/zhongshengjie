#!/usr/bin/env python
"""
混合检索系统 - Dense + ColBERT + RRF融合

基于现有collection向量配置：
- 有ColBERT: writing_techniques_v2, novel_settings_v2 (Dense+ColBERT融合)
- 只有Dense: case_library_v2, worldview_element_v1等 (仅Dense)

使用方法:
    from hybrid_retriever import HybridRetriever

    retriever = HybridRetriever()
    results = retriever.retrieve("修仙突破", collection="writing_techniques_v2", top_k=10)
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import QueryResponse, ScoredPoint
except ImportError:
    raise ImportError("请安装 qdrant-client: pip install qdrant-client")

try:
    from FlagEmbedding import BGEM3FlagModel
except ImportError:
    raise ImportError("请安装 FlagEmbedding: pip install FlagEmbedding")

# 导入配置加载器（避免硬编码）
try:
    from config_loader import get_model_path, get_hf_cache_dir, get_qdrant_url

    MODEL_PATH = get_model_path()
    HF_CACHE_DIR = get_hf_cache_dir()
    QDRANT_URL = get_qdrant_url()
except ImportError:
    # 回退到config.json
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
        QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")


@dataclass
class SearchResult:
    """检索结果"""

    id: str
    score: float
    payload: Dict[str, Any]
    source: str  # dense/colbert/rrf_fusion
    dense_rank: Optional[int] = None
    colbert_rank: Optional[int] = None


class HybridRetriever:
    """混合检索器 - Dense + ColBERT + RRF融合"""

    # Collection向量配置缓存
    COLLECTION_VECTOR_CONFIG = {}

    def __init__(self, use_gpu: bool = True):
        """初始化检索器"""
        self.client = None
        self.model = None
        self.use_gpu = use_gpu
        self._init_model()
        self._init_client()
        self._scan_vector_configs()

    def _init_model(self):
        """初始化BGE-M3模型"""
        import torch

        device = "cuda" if self.use_gpu and torch.cuda.is_available() else "cpu"
        use_fp16 = device == "cuda"

        if device == "cuda":
            print(f"[GPU] 使用GPU加速: {torch.cuda.get_device_name(0)}")
        else:
            print(f"[CPU] 使用CPU模式")

        # 模型路径
        model_path = MODEL_PATH  # 使用模块级变量

        if model_path:
            print(f"[~] 加载本地模型: {model_path}")
            self.model = BGEM3FlagModel(
                model_path,
                use_fp16=use_fp16,
                device=device,
            )
        else:
            # 自动检测本地模型
            local_model_path = (
                Path(HF_CACHE_DIR) / "hub" / "models--BAAI--bge-m3" / "snapshots"
            )
            if local_model_path.exists():
                snapshots = list(local_model_path.iterdir())
                if snapshots:
                    model_path = str(snapshots[0])
                    print(f"[~] 自动检测到本地模型: {model_path}")
                    self.model = BGEM3FlagModel(
                        model_path,
                        use_fp16=use_fp16,
                        device=device,
                    )
                    return

            print(f"[~] 从HuggingFace加载模型...")
            self.model = BGEM3FlagModel(
                "BAAI/bge-m3",
                use_fp16=use_fp16,
                device=device,
            )

        print("[OK] BGE-M3模型加载完成")

    def _init_client(self):
        """初始化Qdrant客户端"""
        self.client = QdrantClient(url=QDRANT_URL)
        print(f"[OK] Qdrant连接: {QDRANT_URL}")

    def _scan_vector_configs(self):
        """扫描所有collection的向量配置"""
        collections = self.client.get_collections().collections
        for col in collections:
            try:
                info = self.client.get_collection(col.name)
                vectors = info.config.params.vectors
                self.COLLECTION_VECTOR_CONFIG[col.name] = {
                    "dense": "dense" in vectors,
                    "colbert": "colbert" in vectors,
                    "sparse": "sparse" in vectors,
                }
            except Exception as e:
                print(f"[WARN] 无法获取 {col.name} 配置: {e}")

        print(f"[OK] 扫描到 {len(self.COLLECTION_VECTOR_CONFIG)} 个collection配置")

    def get_collection_config(self, collection: str) -> Dict[str, bool]:
        """获取collection向量配置"""
        return self.COLLECTION_VECTOR_CONFIG.get(
            collection, {"dense": True, "colbert": False, "sparse": False}
        )

    def encode_query(self, query: str) -> Dict[str, Any]:
        """编码查询为多向量"""
        return self.model.encode(
            [query],
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=True,
        )

    def dense_search(
        self, collection: str, dense_vec: List[float], top_k: int = 50
    ) -> List[ScoredPoint]:
        """Dense向量检索"""
        if not self.get_collection_config(collection)["dense"]:
            return []

        results = self.client.query_points(
            collection_name=collection,
            query=dense_vec,
            using="dense",
            limit=top_k,
            with_payload=True,
        )
        return results.points

    def colbert_search(
        self, collection: str, colbert_vecs: List[List[float]], top_k: int = 50
    ) -> List[ScoredPoint]:
        """ColBERT向量检索（多向量，late interaction）"""
        if not self.get_collection_config(collection)["colbert"]:
            return []

        # ColBERT是多向量检索，每个token一个向量
        # Qdrant的MultiVectorComparator.MAX_SIM需要传入所有token向量
        try:
            # colbert_vecs是二维数组: [num_tokens, 1024]
            # 需要转换为Qdrant接受的格式
            results = self.client.query_points(
                collection_name=collection,
                query=colbert_vecs,  # 直接传入多向量数组
                using="colbert",
                limit=top_k,
                with_payload=True,
            )
            return results.points
        except Exception as e:
            # 如果多向量检索失败，回退到Dense
            print(f"[WARN] ColBERT检索失败（回退到Dense）: {str(e)[:100]}")
            return []

    def rrf_fusion(
        self,
        dense_results: List[ScoredPoint],
        colbert_results: List[ScoredPoint],
        k: int = 60,
        top_k: int = 10,
    ) -> List[SearchResult]:
        """RRF (Reciprocal Rank Fusion) 融合"""
        scores = defaultdict(float)
        payload_map = {}
        dense_rank_map = {}
        colbert_rank_map = {}

        # Dense贡献
        for rank, hit in enumerate(dense_results):
            scores[hit.id] += 1.0 / (k + rank + 1)
            payload_map[hit.id] = hit.payload
            dense_rank_map[hit.id] = rank + 1

        # ColBERT贡献
        for rank, hit in enumerate(colbert_results):
            scores[hit.id] += 1.0 / (k + rank + 1)
            payload_map[hit.id] = hit.payload
            colbert_rank_map[hit.id] = rank + 1

        # 排序
        sorted_ids = sorted(scores.items(), key=lambda x: -x[1])

        # 构建结果
        results = []
        for id, score in sorted_ids[:top_k]:
            results.append(
                SearchResult(
                    id=str(id),
                    score=score,
                    payload=payload_map.get(id, {}),
                    source="rrf_fusion",
                    dense_rank=dense_rank_map.get(id),
                    colbert_rank=colbert_rank_map.get(id),
                )
            )

        return results

    def retrieve(
        self,
        query: str,
        collection: str,
        top_k: int = 10,
        dense_top_k: int = 50,
        colbert_top_k: int = 50,
        fusion_k: int = 60,
        verbose: bool = False,
    ) -> List[SearchResult]:
        """
        混合检索

        Args:
            query: 查询文本
            collection: collection名称
            top_k: 最终返回数量
            dense_top_k: Dense检索数量
            colbert_top_k: ColBERT检索数量
            fusion_k: RRF融合参数
            verbose: 是否打印详细信息

        Returns:
            List[SearchResult]: 融合后的检索结果
        """
        start_time = time.time()

        if verbose:
            print(f"\n[检索] query='{query}' collection='{collection}'")

        # 编码查询
        embedding = self.encode_query(query)

        # 检查向量配置
        config = self.get_collection_config(collection)

        if verbose:
            print(f"  向量配置: dense={config['dense']}, colbert={config['colbert']}")

        # Dense检索
        dense_results = []
        if config["dense"]:
            dense_results = self.dense_search(
                collection,
                embedding["dense_vecs"][0].tolist(),
                top_k=dense_top_k,
            )
            if verbose:
                print(f"  Dense检索: {len(dense_results)} 条结果")

        # ColBERT检索（如果支持）
        colbert_results = []
        if config["colbert"]:
            colbert_results = self.colbert_search(
                collection,
                embedding["colbert_vecs"][0],
                top_k=colbert_top_k,
            )
            if verbose:
                print(f"  ColBERT检索: {len(colbert_results)} 条结果")

        # RRF融合
        if config["colbert"] and colbert_results:
            fused_results = self.rrf_fusion(
                dense_results, colbert_results, k=fusion_k, top_k=top_k
            )
        else:
            # 只有Dense，直接返回Dense结果
            fused_results = [
                SearchResult(
                    id=str(hit.id),
                    score=hit.score,
                    payload=hit.payload,
                    source="dense",
                    dense_rank=i + 1,
                )
                for i, hit in enumerate(dense_results[:top_k])
            ]

        elapsed = time.time() - start_time
        if verbose:
            print(f"  耗时: {elapsed:.3f}s")
            print(f"  最终结果: {len(fused_results)} 条")

        return fused_results

    def multi_collection_retrieve(
        self,
        query: str,
        collections: List[str],
        top_k_per_collection: int = 5,
        final_top_k: int = 10,
        verbose: bool = False,
    ) -> Dict[str, List[SearchResult]]:
        """
        多collection检索

        Args:
            query: 查询文本
            collections: collection列表
            top_k_per_collection: 每个collection返回数量
            final_top_k: 最终融合数量
            verbose: 详细输出

        Returns:
            Dict[str, List[SearchResult]]: 各collection结果
        """
        results = {}
        all_results = []

        for collection in collections:
            col_results = self.retrieve(
                query,
                collection,
                top_k=top_k_per_collection,
                verbose=verbose,
            )
            results[collection] = col_results
            all_results.extend(col_results)

        # 全局排序
        all_results.sort(key=lambda x: -x.score)

        return results


class RetrievalCache:
    """检索缓存"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.cache: Dict[str, Tuple[List[SearchResult], float]] = {}
        self.max_size = max_size
        self.ttl = ttl  # 秒

    def get(self, key: str) -> Optional[List[SearchResult]]:
        """获取缓存"""
        if key in self.cache:
            results, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return results
            else:
                del self.cache[key]
        return None

    def set(self, key: str, results: List[SearchResult]):
        """设置缓存"""
        if len(self.cache) >= self.max_size:
            # 删除最旧的
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

        self.cache[key] = (results, time.time())

    def warm_up(
        self, retriever: HybridRetriever, queries: List[str], collections: List[str]
    ):
        """预热热门查询"""
        for query in queries:
            for collection in collections:
                key = f"{query}|{collection}"
                results = retriever.retrieve(query, collection, verbose=False)
                self.set(key, results)

        print(
            f"[OK] 预热完成: {len(queries)} x {len(collections)} = {len(queries) * len(collections)} 条缓存"
        )


# 热门查询列表（用于预热）
POPULAR_QUERIES = [
    "修仙突破境界",
    "战斗场景",
    "师徒传承",
    "人物出场",
    "开篇场景",
    "情感描写",
    "悬念设置",
    "伏笔回收",
]

# 主要检索collection
MAIN_COLLECTIONS = [
    "writing_techniques_v2",
    "case_library_v2",
    "novel_settings_v2",
    "worldview_element_v1",
    "power_vocabulary_v1",
    "character_relation_v1",
]


def create_cached_retriever(
    warm_up: bool = False,
) -> Tuple[HybridRetriever, RetrievalCache]:
    """创建带缓存的检索器"""
    retriever = HybridRetriever()
    cache = RetrievalCache()

    if warm_up:
        cache.warm_up(retriever, POPULAR_QUERIES, MAIN_COLLECTIONS)

    return retriever, cache


if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("混合检索系统测试")
    print("=" * 60)

    retriever = HybridRetriever()

    test_queries = [
        "修仙突破境界",
        "战斗胜利有代价",
        "师徒传承关系",
    ]

    for query in test_queries:
        print(f"\n{'=' * 60}")
        print(f"查询: {query}")
        print("=" * 60)

        # 测试技法库
        results = retriever.retrieve(
            query, "writing_techniques_v2", top_k=3, verbose=True
        )
        for i, r in enumerate(results):
            text = r.payload.get(
                "内容", r.payload.get("技法名称", r.payload.get("text", ""))
            )
            print(f"\n  [{i + 1}] score={r.score:.4f} source={r.source}")
            print(f"      dense_rank={r.dense_rank}, colbert_rank={r.colbert_rank}")
            print(f"      内容: {text[:100]}...")

        # 测试案例库
        results = retriever.retrieve(query, "case_library_v2", top_k=3, verbose=True)
        for i, r in enumerate(results):
            text = r.payload.get("content", r.payload.get("text", ""))
            print(f"\n  [{i + 1}] score={r.score:.4f} source={r.source}")
            print(f"      内容: {text[:100]}...")
