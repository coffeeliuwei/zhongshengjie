"""
轻量混合检索管理器 - Dense + Sparse
针对 BGE-M3 轻量迁移版本优化

检索策略：
1. Dense 召回 (语义相似度)
2. Sparse 召回 (关键词匹配)
3. RRF 融合排序

使用方法：
    from hybrid_search_manager_lite import HybridSearchManager

    search = HybridSearchManager()
    results = search.search_technique("战斗代价", dimension="战斗冲突维度")
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# 从配置加载器导入路径获取函数
try:
    from core.config_loader import get_project_root, get_qdrant_storage_dir

    HAS_CONFIG_LOADER = True
except ImportError:
    HAS_CONFIG_LOADER = False
    from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

try:
    from qdrant_client import QdrantClient
    from qdrant_client import models
    from qdrant_client.http.models import SparseVector
except ImportError:
    raise ImportError("请安装 qdrant-client: pip install qdrant-client")

# 配置 - 从配置加载器获取项目路径
if HAS_CONFIG_LOADER:
    PROJECT_DIR = get_project_root()
    QDRANT_PATH = get_qdrant_storage_dir()
else:
    PROJECT_DIR = Path.cwd()
    QDRANT_PATH = PROJECT_DIR / ".vectorstore" / "qdrant"

# Collection 名称 (v2 = BGE-M3)
COLLECTIONS = {
    "novel": "novel_settings_v2",
    "technique": "writing_techniques_v2",
    "case": "case_library_v2",
}

# 检索配置
RETRIEVAL_CONFIG = {
    "dense_limit": 50,
    "sparse_limit": 50,
    "final_limit": 10,
}

# 实体类型
ENTITY_TYPES = ["势力", "派系", "角色", "力量体系", "力量派别", "时代", "事件"]

# 技法维度
TECHNIQUE_DIMENSIONS = [
    "世界观维度",
    "剧情维度",
    "人物维度",
    "战斗冲突维度",
    "氛围意境维度",
    "叙事维度",
    "主题维度",
    "情感维度",
    "读者体验维度",
    "元维度",
    "节奏维度",
]


class HybridSearchManager:
    """
    轻量混合检索管理器 (Dense + Sparse)

    针对已迁移到 BGE-M3 的 v2 Collection
    """

    def __init__(self, qdrant_path: Path = None):
        self.qdrant_path = qdrant_path or QDRANT_PATH
        self._client = None
        self._model = None

    def _get_client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(path=str(self.qdrant_path))
        return self._client

    def _load_model(self):
        if self._model is None:
            from FlagEmbedding import BGEM3FlagModel

            self._model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True, device="cpu")
        return self._model

    def _encode_query(self, query: str) -> dict:
        """编码查询，返回 Dense 和 Sparse 向量"""
        model = self._load_model()
        output = model.encode([query], return_dense=True, return_sparse=True)

        return {
            "dense": output["dense_vecs"][0].tolist(),
            "sparse_indices": list(output["lexical_weights"][0].keys()),
            "sparse_values": list(output["lexical_weights"][0].values()),
        }

    # ==================== 小说设定检索 ====================

    def search_novel(
        self,
        query: str,
        entity_type: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """检索小说设定"""
        client = self._get_client()
        collection = COLLECTIONS["novel"]

        # 检查 Collection 是否存在
        if not self._collection_exists(collection):
            return []

        # 编码查询
        vectors = self._encode_query(query)

        # Dense 检索
        filter_cond = None
        if entity_type:
            filter_cond = models.Filter(
                must=[
                    models.FieldCondition(
                        key="type", match=models.MatchValue(value=entity_type)
                    )
                ]
            )

        dense_results = client.query_points(
            collection_name=collection,
            query=vectors["dense"],
            using="dense",
            query_filter=filter_cond,
            limit=RETRIEVAL_CONFIG["dense_limit"],
            with_payload=True,
        )

        # Sparse 检索
        sparse_vec = SparseVector(
            indices=vectors["sparse_indices"], values=vectors["sparse_values"]
        )

        sparse_results = client.query_points(
            collection_name=collection,
            query=sparse_vec,
            using="sparse",
            query_filter=filter_cond,
            limit=RETRIEVAL_CONFIG["sparse_limit"],
            with_payload=True,
        )

        # RRF 融合
        merged = self._rrf_merge(dense_results.points, sparse_results.points, top_k)

        # 格式化结果
        return [
            {
                "id": r.id,
                "name": r.payload.get("name", "未知"),
                "type": r.payload.get("type", "未知"),
                "description": r.payload.get("description", ""),
                "score": r.score,
            }
            for r in merged
        ]

    def get_character(self, name: str) -> Optional[Dict]:
        """获取角色设定"""
        results = self.search_novel(name, entity_type="角色", top_k=10)
        for r in results:
            if name in r.get("name", ""):
                return r
        return None

    def get_faction(self, name: str) -> Optional[Dict]:
        """获取势力设定"""
        results = self.search_novel(name, entity_type="势力", top_k=10)
        for r in results:
            if name in r.get("name", ""):
                return r
        return None

    # ==================== 创作技法检索 ====================

    def search_technique(
        self,
        query: str,
        dimension: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """检索创作技法"""
        client = self._get_client()
        collection = COLLECTIONS["technique"]

        if not self._collection_exists(collection):
            return []

        vectors = self._encode_query(query)

        # 过滤条件
        filter_cond = None
        if dimension:
            filter_cond = models.Filter(
                must=[
                    models.FieldCondition(
                        key="dimension", match=models.MatchValue(value=dimension)
                    )
                ]
            )

        # Dense 检索
        dense_results = client.query_points(
            collection_name=collection,
            query=vectors["dense"],
            using="dense",
            query_filter=filter_cond,
            limit=RETRIEVAL_CONFIG["dense_limit"],
            with_payload=True,
        )

        # Sparse 检索
        sparse_vec = SparseVector(
            indices=vectors["sparse_indices"], values=vectors["sparse_values"]
        )

        sparse_results = client.query_points(
            collection_name=collection,
            query=sparse_vec,
            using="sparse",
            query_filter=filter_cond,
            limit=RETRIEVAL_CONFIG["sparse_limit"],
            with_payload=True,
        )

        # RRF 融合
        merged = self._rrf_merge(dense_results.points, sparse_results.points, top_k)

        return [
            {
                "id": r.id,
                "name": r.payload.get("name", "未知"),
                "dimension": r.payload.get("dimension", "未知"),
                "writer": r.payload.get("writer", "未知"),
                "content": r.payload.get("content", ""),
                "word_count": r.payload.get("word_count", 0),
                "score": r.score,
            }
            for r in merged
            if r.score >= min_score
        ]

    def list_dimensions(self) -> List[str]:
        """列出技法维度"""
        return TECHNIQUE_DIMENSIONS

    # ==================== 案例检索 ====================

    def search_case(
        self,
        query: str,
        scene_type: Optional[str] = None,
        genre: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """检索标杆案例"""
        client = self._get_client()
        collection = COLLECTIONS["case"]

        if not self._collection_exists(collection):
            return []

        vectors = self._encode_query(query)

        # 过滤条件
        conditions = []
        if scene_type:
            conditions.append(
                models.FieldCondition(
                    key="scene_type", match=models.MatchValue(value=scene_type)
                )
            )
        if genre:
            conditions.append(
                models.FieldCondition(key="genre", match=models.MatchValue(value=genre))
            )

        filter_cond = models.Filter(must=conditions) if conditions else None

        # Dense 检索
        dense_results = client.query_points(
            collection_name=collection,
            query=vectors["dense"],
            using="dense",
            query_filter=filter_cond,
            limit=RETRIEVAL_CONFIG["dense_limit"],
            with_payload=True,
        )

        # Sparse 检索
        sparse_vec = SparseVector(
            indices=vectors["sparse_indices"], values=vectors["sparse_values"]
        )

        sparse_results = client.query_points(
            collection_name=collection,
            query=sparse_vec,
            using="sparse",
            query_filter=filter_cond,
            limit=RETRIEVAL_CONFIG["sparse_limit"],
            with_payload=True,
        )

        # RRF 融合
        merged = self._rrf_merge(dense_results.points, sparse_results.points, top_k)

        return [
            {
                "id": r.id,
                "novel_name": r.payload.get("novel_name", "未知"),
                "scene_type": r.payload.get("scene_type", "未知"),
                "genre": r.payload.get("genre", "未知"),
                "quality_score": r.payload.get("quality_score", 0),
                "content": r.payload.get("content", ""),
                "score": r.score,
            }
            for r in merged
            if r.score >= min_score
        ]

    # ==================== 工具方法 ====================

    def _collection_exists(self, name: str) -> bool:
        """检查 Collection 是否存在"""
        client = self._get_client()
        collections = [c.name for c in client.get_collections().collections]
        return name in collections

    def _rrf_merge(self, dense_results: list, sparse_results: list, top_k: int) -> list:
        """RRF (Reciprocal Rank Fusion) 融合"""
        k = 60  # RRF 常数

        rrf_scores = defaultdict(float)
        doc_data = {}

        for i, r in enumerate(dense_results):
            rrf_scores[r.id] += 1 / (k + i)
            doc_data[r.id] = r

        for i, r in enumerate(sparse_results):
            rrf_scores[r.id] += 1 / (k + i)
            doc_data[r.id] = r

        # 排序
        sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]

        # 返回结果
        results = []
        for doc_id, score in sorted_ids:
            r = doc_data[doc_id]
            r.score = score
            results.append(r)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计"""
        client = self._get_client()
        stats = {}

        collections = [c.name for c in client.get_collections().collections]

        for key, name in COLLECTIONS.items():
            display = {
                "novel": "小说设定库",
                "technique": "创作技法库",
                "case": "案例库",
            }[key]

            if name in collections:
                info = client.get_collection(name)
                stats[display] = {
                    "总数": info.points_count,
                    "状态": info.status.value,
                    "Collection": name,
                }
            else:
                stats[display] = {
                    "总数": 0,
                    "状态": "未创建",
                    "Collection": name,
                }

        return stats


# 命令行入口
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="轻量混合检索")
    parser.add_argument("--query", type=str, help="查询文本")
    parser.add_argument(
        "--type", choices=["novel", "technique", "case"], default="technique"
    )
    parser.add_argument("--dimension", type=str, help="技法维度过滤")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--stats", action="store_true", help="显示统计")

    args = parser.parse_args()

    search = HybridSearchManager()

    if args.stats:
        print("\n数据库统计:")
        for name, info in search.get_stats().items():
            print(f"  {name}: {info}")

    elif args.query:
        print(f"\n查询: {args.query}")

        if args.type == "novel":
            results = search.search_novel(args.query, top_k=args.top_k)
        elif args.type == "technique":
            results = search.search_technique(
                args.query, dimension=args.dimension, top_k=args.top_k
            )
        else:
            results = search.search_case(args.query, top_k=args.top_k)

        print(f"\n找到 {len(results)} 条结果:")
        for i, r in enumerate(results, 1):
            print(f"\n[{i}] {r.get('name', r.get('novel_name', '未知'))}")
            print(f"    分数: {r['score']:.4f}")
            if "dimension" in r:
                print(f"    维度: {r['dimension']}")
            content = r.get("content", "")[:100]
            if content:
                print(f"    内容: {content}...")
