"""
BGE-M3 混合检索管理器
支持 Dense + Sparse + ColBERT 三种模式混合检索

检索策略：
1. 召回阶段：Dense + Sparse 并行检索，RRF 融合
2. 重排阶段：ColBERT 对 Top-K 候选重排序

使用方法：
    from .hybrid_search_manager import HybridSearchManager

    search = HybridSearchManager()
    results = search.search_technique("战斗场景描写", dimension="战斗冲突维度")
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional

# 从配置加载器导入路径获取函数
from core.config_loader import (
    get_project_root,
    get_qdrant_url,
    get_model_path,
    get_vectorstore_dir,
    get_qdrant_storage_dir,
)

try:
    from qdrant_client import QdrantClient
    from qdrant_client import models
    from qdrant_client.http.models import SparseVector
except ImportError:
    raise ImportError("请安装 qdrant-client: pip install qdrant-client")

# 导入配置
import sys

config_dir = get_vectorstore_dir()
if str(config_dir) not in sys.path:
    sys.path.insert(0, str(config_dir))
from bge_m3_config import (
    BGE_M3_MODEL_NAME,
    BGE_M3_CACHE_DIR,
    USE_FP16,
    COLLECTION_NAMES,
    HYBRID_WEIGHTS,
    DEFAULT_WEIGHT_PRESET,
    RETRIEVAL_CONFIG,
)


class HybridSearchManager:
    """
    BGE-M3 混合检索管理器

    支持从三大混合向量库检索数据：
    - novel_settings_v2: 小说设定（Dense + Sparse + ColBERT）
    - writing_techniques_v2: 创作技法（Dense + Sparse + ColBERT）
    - case_library_v2: 标杆案例（Dense + Sparse + ColBERT）

    检索流程：
    1. 使用 BGE-M3 编码查询，生成三种向量
    2. Dense + Sparse 并行召回，RRF 融合
    3. ColBERT 对候选集重排序
    """

    # 实体类型列表
    ENTITY_TYPES = ["势力", "派系", "角色", "力量体系", "力量派别", "时代", "事件"]

    # 技法维度列表
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

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        use_docker: bool = True,
        docker_url: str = None,
        weight_preset: str = DEFAULT_WEIGHT_PRESET,
    ):
        """
        初始化混合检索管理器

        Args:
            project_dir: 项目根目录（默认从配置加载）
            use_docker: 是否使用 Docker Qdrant
            docker_url: Docker Qdrant URL（默认从配置加载）
            weight_preset: 权重预设 (general/semantic/exact/dense_only)
        """
        # 从配置加载路径
        if project_dir is None:
            self.project_dir = get_project_root()
        else:
            self.project_dir = Path(project_dir)

        self.vectorstore_dir = get_vectorstore_dir()
        self.qdrant_dir = get_qdrant_storage_dir()

        # Qdrant 客户端
        self._client = None
        self._model = None
        self.use_docker = use_docker

        # 从配置加载 URL
        if docker_url is None:
            self.docker_url = get_qdrant_url()
        else:
            self.docker_url = docker_url

        # 权重配置
        self.weights = HYBRID_WEIGHTS.get(
            weight_preset, HYBRID_WEIGHTS[DEFAULT_WEIGHT_PRESET]
        )
        self.weight_preset = weight_preset

        # 检索配置
        self.recall_config = RETRIEVAL_CONFIG["recall"]
        self.rerank_config = RETRIEVAL_CONFIG["rerank"]

        # 设置 HuggingFace 缓存
        os.environ["HF_HOME"] = BGE_M3_CACHE_DIR
        model_path = get_model_path()
        if model_path is not None:
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

    def _get_client(self) -> QdrantClient:
        """获取 Qdrant 客户端"""
        if self._client is None:
            if self.use_docker:
                try:
                    self._client = QdrantClient(url=self.docker_url)
                    self._client.get_collections()
                except Exception:
                    self._client = QdrantClient(path=str(self.qdrant_dir))
            else:
                self._client = QdrantClient(path=str(self.qdrant_dir))
        return self._client

    def _load_model(self):
        """加载 BGE-M3 模型"""
        if self._model is None:
            try:
                from FlagEmbedding import BGEM3FlagModel

                self._model = BGEM3FlagModel(
                    BGE_M3_MODEL_NAME,
                    use_fp16=USE_FP16,
                    device="cpu",
                )
            except ImportError as e:
                raise ImportError(
                    f"请安装 FlagEmbedding: pip install FlagEmbedding ({e})"
                )
        return self._model

    def _encode_query(self, query: str) -> Dict[str, Any]:
        """
        编码查询文本，生成三种向量

        Args:
            query: 查询文本

        Returns:
            包含三种向量的字典
        """
        model = self._load_model()

        output = model.encode(
            [query],
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=True,
        )

        return {
            "dense": output["dense_vecs"][0].tolist(),
            "sparse_indices": list(output["lexical_weights"][0].keys()),
            "sparse_values": list(output["lexical_weights"][0].values()),
            "colbert": output["colbert_vecs"][0],
        }

    def set_weight_preset(self, preset: str):
        """
        设置权重预设

        Args:
            preset: 预设名称 (general/semantic/exact/dense_only)
        """
        if preset in HYBRID_WEIGHTS:
            self.weights = HYBRID_WEIGHTS[preset]
            self.weight_preset = preset
            print(f"权重预设已切换为: {preset}")
        else:
            print(f"未知预设: {preset}，可用预设: {list(HYBRID_WEIGHTS.keys())}")

    # ==================== 小说设定检索 ====================

    def search_novel(
        self,
        query: str,
        entity_type: Optional[str] = None,
        top_k: int = 10,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        混合检索小说设定

        Args:
            query: 查询文本
            entity_type: 实体类型过滤（角色、势力、力量体系等）
            top_k: 返回数量
            use_rerank: 是否使用 ColBERT 重排

        Returns:
            检索结果列表
        """
        client = self._get_client()
        collection_name = COLLECTION_NAMES["novel_settings"]

        # 检查 Collection 是否存在
        collections = [c.name for c in client.get_collections().collections]
        if collection_name not in collections:
            print(f"Collection {collection_name} 不存在，请先运行同步")
            return []

        # 编码查询
        query_vectors = self._encode_query(query)

        # 构建过滤条件
        query_filter = None
        if entity_type:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="type",
                        match=models.MatchValue(value=entity_type),
                    )
                ]
            )

        # 阶段1: Dense + Sparse 混合召回
        try:
            sparse_vector = SparseVector(
                indices=query_vectors["sparse_indices"],
                values=query_vectors["sparse_values"],
            )

            results = client.query_points(
                collection_name=collection_name,
                prefetch=[
                    models.Prefetch(
                        query=query_vectors["dense"],
                        using="dense",
                        limit=self.recall_config["dense_limit"],
                        filter=query_filter,
                    ),
                    models.Prefetch(
                        query=sparse_vector,
                        using="sparse",
                        limit=self.recall_config["sparse_limit"],
                        filter=query_filter,
                    ),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=self.recall_config["fusion_limit"],
                with_payload=True,
            )
        except Exception as e:
            print(f"检索错误: {e}")
            return []

        # 阶段2: ColBERT 重排（可选）
        if use_rerank and self.rerank_config["enabled"] and len(results.points) > 0:
            results = self._colbert_rerank(
                client, collection_name, query_vectors["colbert"], results.points, top_k
            )
        else:
            results = results.points[:top_k]

        # 格式化结果
        formatted = []
        for p in results:
            formatted.append(
                {
                    "id": p.id,
                    "name": p.payload.get("name", "未知"),
                    "type": p.payload.get("type", "未知"),
                    "description": p.payload.get("description", ""),
                    "properties": p.payload.get("properties", ""),
                    "score": p.score,
                }
            )

        return formatted

    def get_character(self, name: str) -> Optional[Dict[str, Any]]:
        """获取角色设定"""
        results = self.search_novel(name, entity_type="角色", top_k=10)
        for r in results:
            if name in r.get("name", ""):
                return r
        return None

    def get_faction(self, name: str) -> Optional[Dict[str, Any]]:
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
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        混合检索创作技法

        Args:
            query: 查询文本
            dimension: 维度过滤（世界观维度、剧情维度等）
            top_k: 返回数量
            min_score: 最低相似度
            use_rerank: 是否使用 ColBERT 重排

        Returns:
            检索结果列表
        """
        client = self._get_client()
        collection_name = COLLECTION_NAMES["writing_techniques"]

        # 检查 Collection 是否存在
        collections = [c.name for c in client.get_collections().collections]
        if collection_name not in collections:
            print(f"Collection {collection_name} 不存在，请先运行同步")
            return []

        # 编码查询
        query_vectors = self._encode_query(query)

        # 构建过滤条件
        query_filter = None
        if dimension:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="dimension",
                        match=models.MatchValue(value=dimension),
                    )
                ]
            )

        # 阶段1: Dense + Sparse 混合召回
        try:
            sparse_vector = SparseVector(
                indices=query_vectors["sparse_indices"],
                values=query_vectors["sparse_values"],
            )

            results = client.query_points(
                collection_name=collection_name,
                prefetch=[
                    models.Prefetch(
                        query=query_vectors["dense"],
                        using="dense",
                        limit=self.recall_config["dense_limit"],
                        filter=query_filter,
                    ),
                    models.Prefetch(
                        query=sparse_vector,
                        using="sparse",
                        limit=self.recall_config["sparse_limit"],
                        filter=query_filter,
                    ),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=self.recall_config["fusion_limit"],
                with_payload=True,
            )
        except Exception as e:
            print(f"检索错误: {e}")
            return []

        # 阶段2: ColBERT 重排
        if use_rerank and self.rerank_config["enabled"] and len(results.points) > 0:
            results = self._colbert_rerank(
                client, collection_name, query_vectors["colbert"], results.points, top_k
            )
        else:
            results = results.points[:top_k]

        # 格式化结果
        formatted = []
        for p in results:
            if p.score < min_score:
                continue
            formatted.append(
                {
                    "id": p.id,
                    "name": p.payload.get("name", "未知"),
                    "dimension": p.payload.get("dimension", "未知"),
                    "writer": p.payload.get("writer", "未知"),
                    "source_file": p.payload.get("source_file", ""),
                    "content": p.payload.get("content", ""),
                    "word_count": p.payload.get("word_count", 0),
                    "score": p.score,
                }
            )

        return formatted

    def list_dimensions(self) -> List[str]:
        """列出所有技法维度"""
        return self.TECHNIQUE_DIMENSIONS

    # ==================== 案例检索 ====================

    def search_case(
        self,
        query: str,
        scene_type: Optional[str] = None,
        genre: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.5,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        混合检索标杆案例

        Args:
            query: 查询文本
            scene_type: 场景类型过滤
            genre: 题材类型过滤
            top_k: 返回数量
            min_score: 最低相似度
            use_rerank: 是否使用 ColBERT 重排

        Returns:
            检索结果列表
        """
        client = self._get_client()
        collection_name = COLLECTION_NAMES["case_library"]

        # 检查 Collection 是否存在
        collections = [c.name for c in client.get_collections().collections]
        if collection_name not in collections:
            print(f"Collection {collection_name} 不存在，请先运行同步")
            return []

        # 编码查询
        query_vectors = self._encode_query(query)

        # 构建过滤条件
        filter_conditions = []
        if scene_type:
            filter_conditions.append(
                models.FieldCondition(
                    key="scene_type",
                    match=models.MatchValue(value=scene_type),
                )
            )
        if genre:
            filter_conditions.append(
                models.FieldCondition(
                    key="genre",
                    match=models.MatchValue(value=genre),
                )
            )

        query_filter = None
        if filter_conditions:
            query_filter = models.Filter(must=filter_conditions)

        # 阶段1: Dense + Sparse 混合召回
        try:
            sparse_vector = SparseVector(
                indices=query_vectors["sparse_indices"],
                values=query_vectors["sparse_values"],
            )

            results = client.query_points(
                collection_name=collection_name,
                prefetch=[
                    models.Prefetch(
                        query=query_vectors["dense"],
                        using="dense",
                        limit=self.recall_config["dense_limit"],
                        filter=query_filter,
                    ),
                    models.Prefetch(
                        query=sparse_vector,
                        using="sparse",
                        limit=self.recall_config["sparse_limit"],
                        filter=query_filter,
                    ),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=self.recall_config["fusion_limit"],
                with_payload=True,
            )
        except Exception as e:
            print(f"检索错误: {e}")
            return []

        # 阶段2: ColBERT 重排
        if use_rerank and self.rerank_config["enabled"] and len(results.points) > 0:
            results = self._colbert_rerank(
                client, collection_name, query_vectors["colbert"], results.points, top_k
            )
        else:
            results = results.points[:top_k]

        # 格式化结果
        formatted = []
        for p in results:
            if p.score < min_score:
                continue
            formatted.append(
                {
                    "id": p.id,
                    "novel_name": p.payload.get("novel_name", "未知"),
                    "scene_type": p.payload.get("scene_type", "未知"),
                    "genre": p.payload.get("genre", "未知"),
                    "quality_score": p.payload.get("quality_score", 0),
                    "word_count": p.payload.get("word_count", 0),
                    "content": p.payload.get("content", ""),
                    "score": p.score,
                    "cross_genre_value": p.payload.get("cross_genre_value", ""),
                }
            )

        return formatted

    # ==================== ColBERT 重排 ====================

    def _colbert_rerank(
        self,
        client: QdrantClient,
        collection_name: str,
        query_colbert: Any,
        candidates: List[Any],
        top_k: int,
        content_field: str = "content",
    ) -> List[Any]:
        """
        使用 ColBERT 对候选集重排序（动态编码，不依赖存储的向量）

        Args:
            client: Qdrant 客户端
            collection_name: Collection 名称
            query_colbert: 查询的 ColBERT 向量
            candidates: 候选点列表
            top_k: 返回数量
            content_field: payload 中存储文档内容的字段名

        Returns:
            重排后的候选点列表
        """
        if len(candidates) <= top_k:
            return candidates

        try:
            model = self._load_model()

            # 从 payload 获取文档内容并动态编码
            doc_contents = []
            for p in candidates:
                content = p.payload.get(content_field, "")
                if not content:
                    # 尝试其他字段
                    content = p.payload.get("description", "")
                doc_contents.append(content[:500] if content else "空内容")

            # 批量编码候选文档
            doc_output = model.encode(
                doc_contents,
                return_colbert_vecs=True,
            )

            # 计算每个候选的 ColBERT 分数
            scores = []
            query_colbert_tensor = (
                query_colbert if hasattr(query_colbert, "shape") else None
            )

            for i, candidate in enumerate(candidates):
                doc_colbert = doc_output["colbert_vecs"][i]

                # 使用模型的 colbert_score 方法计算分数
                if query_colbert_tensor is not None and doc_colbert is not None:
                    try:
                        score = model.colbert_score(query_colbert, doc_colbert).item()
                    except:
                        score = 0.0
                else:
                    score = 0.0

                scores.append((candidate, score))

            # 按分数排序
            scores.sort(key=lambda x: x[1], reverse=True)

            # 返回 top_k 个结果
            reranked = []
            for candidate, score in scores[:top_k]:
                # 更新分数
                candidate.score = score
                reranked.append(candidate)

            return reranked

        except Exception as e:
            print(f"ColBERT 重排错误: {e}")
            import traceback

            traceback.print_exc()
            return candidates[:top_k]

    # ==================== 统计 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        client = self._get_client()
        stats = {}

        collections = [c.name for c in client.get_collections().collections]

        for key, collection_name in COLLECTION_NAMES.items():
            display_name = {
                "novel_settings": "小说设定库",
                "writing_techniques": "创作技法库",
                "case_library": "案例库",
            }.get(key, key)

            if collection_name in collections:
                info = client.get_collection(collection_name)
                stats[display_name] = {
                    "总数": info.points_count,
                    "状态": info.status.value,
                    "Collection": collection_name,
                }
            else:
                stats[display_name] = {
                    "总数": 0,
                    "状态": "未创建",
                    "Collection": collection_name,
                }

        return stats

    def list_characters(self) -> List[str]:
        """列出所有角色名称"""
        client = self._get_client()
        collection_name = COLLECTION_NAMES["novel_settings"]

        try:
            results = client.scroll(
                collection_name=collection_name,
                with_payload=True,
                with_vectors=False,
                limit=1000,
            )[0]

            return [
                p.payload.get("name", "未知")
                for p in results
                if p.payload.get("type") == "角色"
            ]
        except Exception:
            return []

    def list_factions(self) -> List[str]:
        """列出所有势力名称"""
        client = self._get_client()
        collection_name = COLLECTION_NAMES["novel_settings"]

        try:
            results = client.scroll(
                collection_name=collection_name,
                with_payload=True,
                with_vectors=False,
                limit=1000,
            )[0]

            return [
                p.payload.get("name", "未知")
                for p in results
                if p.payload.get("type") == "势力"
            ]
        except Exception:
            return []

    # ==================== 扩展维度检索 ====================

    def search_worldview(
        self,
        query: str,
        element_type: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """检索世界观元素"""
        collection_name = COLLECTION_NAMES.get("worldview_element")
        if not collection_name:
            return []

        client = self._get_client()
        collections = [c.name for c in client.get_collections().collections]
        if collection_name not in collections:
            return []

        query_vectors = self._encode_query(query)

        try:
            results = client.query_points(
                collection_name=collection_name,
                query=query_vectors["dense"],
                using="dense",
                limit=top_k,
                with_payload=True,
            )

            formatted = []
            for p in results.points:
                formatted.append(
                    {
                        "id": p.id,
                        "text": p.payload.get("text", ""),
                        "element_type": p.payload.get("element_type", ""),
                        "total_frequency": p.payload.get("total_frequency", 0),
                        "score": p.score,
                    }
                )

            if element_type:
                formatted = [
                    r for r in formatted if element_type in r.get("element_type", "")
                ]

            return formatted
        except Exception as e:
            print(f"世界观检索错误: {e}")
            return []

    def search_power_vocabulary(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """检索力量词汇"""
        collection_name = COLLECTION_NAMES.get("power_vocabulary")
        if not collection_name:
            return []

        client = self._get_client()
        collections = [c.name for c in client.get_collections().collections]
        if collection_name not in collections:
            return []

        query_vectors = self._encode_query(query)

        try:
            results = client.query_points(
                collection_name=collection_name,
                query=query_vectors["dense"],
                using="dense",
                limit=top_k,
                with_payload=True,
            )

            formatted = []
            for p in results.points:
                formatted.append(
                    {
                        "id": p.id,
                        "text": p.payload.get("text", ""),
                        "category": p.payload.get("category", ""),
                        "power_type": p.payload.get("power_type", ""),
                        "score": p.score,
                    }
                )

            if category:
                formatted = [r for r in formatted if category in r.get("category", "")]

            return formatted
        except Exception as e:
            print(f"力量词汇检索错误: {e}")
            return []

    def search_character_relation(
        self,
        query: str,
        character: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """检索人物关系"""
        collection_name = COLLECTION_NAMES.get("character_relation")
        if not collection_name:
            return []

        client = self._get_client()
        collections = [c.name for c in client.get_collections().collections]
        if collection_name not in collections:
            return []

        query_vectors = self._encode_query(query)

        try:
            results = client.query_points(
                collection_name=collection_name,
                query=query_vectors["dense"],
                using="dense",
                limit=top_k,
                with_payload=True,
            )

            formatted = []
            for p in results.points:
                formatted.append(
                    {
                        "id": p.id,
                        "text": p.payload.get("text", ""),
                        "character1": p.payload.get("character1", ""),
                        "character2": p.payload.get("character2", ""),
                        "score": p.score,
                    }
                )

            if character:
                formatted = [
                    r
                    for r in formatted
                    if character in r.get("character1", "")
                    or character in r.get("character2", "")
                ]

            return formatted
        except Exception as e:
            print(f"人物关系检索错误: {e}")
            return []

    def retrieve_for_scene(
        self,
        scene_type: str,
        context: Optional[str] = None,
        top_k: int = 3,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        场景创作素材检索

        根据场景类型自动选择合适的检索源，返回技法+案例+词汇的完整素材包

        Args:
            scene_type: 场景类型 "战斗"/"开篇"/"情感"等
            context: 额外上下文
            top_k: 每类返回数量

        Returns:
            Dict[str, List]: 按类型分组的素材
        """
        query = scene_type + "场景"
        if context:
            query = context + " " + scene_type + "场景"

        source_map = {
            # 原有8种场景（保持不变）
            "战斗": ["technique", "case", "power_vocabulary"],
            "开篇": ["technique", "case", "worldview_element"],
            "情感": ["technique", "case", "emotion_arc"],
            "对话": ["technique", "case", "dialogue_style"],
            "悬念": ["technique", "case", "foreshadow_pair"],
            "转折": ["technique", "case"],
            "心理": ["technique", "case"],
            "环境": ["technique", "case", "worldview_element"],
            # 新增20种场景（2026-04-13统一扩展）
            "打脸": ["technique", "case", "power_vocabulary"],
            "高潮": ["technique", "case", "power_vocabulary", "emotion_arc"],
            "人物出场": ["technique", "case", "novel"],
            "成长蜕变": ["technique", "case", "emotion_arc"],
            "伏笔设置": ["technique", "case", "foreshadow_pair"],
            "伏笔回收": ["technique", "case", "foreshadow_pair"],
            "阴谋揭露": ["technique", "case", "foreshadow_pair"],
            "社交": ["technique", "case", "dialogue_style"],
            "势力登场": ["technique", "case", "worldview_element", "novel"],
            "修炼突破": ["technique", "case", "power_vocabulary"],
            "资源获取": ["technique", "case", "power_vocabulary"],
            "探索发现": ["technique", "case", "worldview_element"],
            "情报揭示": ["technique", "case"],
            "危机降临": ["technique", "case"],
            "冲突升级": ["technique", "case"],
            "团队组建": ["technique", "case"],
            "反派出场": ["technique", "case", "novel"],
            "恢复休养": ["technique", "case"],
            "回忆场景": ["technique", "case"],
            "结尾": ["technique", "case", "worldview_element"],
        }

        sources = source_map.get(scene_type, ["technique", "case"])

        results = {}
        for source in sources:
            if source == "technique":
                results["technique"] = self.search_technique(query, top_k=top_k)
            elif source == "case":
                results["case"] = self.search_case(query, top_k=top_k)
            elif source == "power_vocabulary":
                results["power"] = self.search_power_vocabulary(query, top_k=top_k)
            elif source == "worldview_element":
                results["worldview"] = self.search_worldview(query, top_k=top_k)
            elif source == "dialogue_style":
                results["dialogue"] = self.search_extended(
                    "dialogue_style", query, top_k=top_k
                )
            elif source == "emotion_arc":
                results["emotion"] = self.search_extended(
                    "emotion_arc", query, top_k=top_k
                )
            elif source == "foreshadow_pair":
                results["foreshadow"] = self.search_extended(
                    "foreshadow_pair", query, top_k=top_k
                )
            elif source == "novel":
                results["novel"] = self.search_novel(query, top_k=top_k)

        return results

    def search_extended(
        self,
        collection_key: str,
        query: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """通用扩展维度检索"""
        collection_name = COLLECTION_NAMES.get(collection_key)
        if not collection_name:
            return []

        client = self._get_client()
        collections = [c.name for c in client.get_collections().collections]
        if collection_name not in collections:
            return []

        query_vectors = self._encode_query(query)

        try:
            results = client.query_points(
                collection_name=collection_name,
                query=query_vectors["dense"],
                using="dense",
                limit=top_k,
                with_payload=True,
            )

            formatted = []
            for p in results.points:
                formatted.append(
                    {
                        "id": p.id,
                        "text": p.payload.get("text", p.payload.get("content", "")),
                        "payload": p.payload,
                        "score": p.score,
                    }
                )

            return formatted
        except Exception as e:
            print(f"扩展检索错误: {e}")
            return []


# CLI 入口
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BGE-M3 混合检索管理器")
    parser.add_argument("--query", type=str, help="查询文本")
    parser.add_argument(
        "--type",
        choices=["novel", "technique", "case"],
        default="technique",
        help="检索类型",
    )
    parser.add_argument("--dimension", type=str, help="技法维度过滤")
    parser.add_argument("--top-k", type=int, default=5, help="返回数量")
    parser.add_argument("--no-rerank", action="store_true", help="禁用 ColBERT 重排")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument(
        "--preset",
        choices=list(HYBRID_WEIGHTS.keys()),
        default=DEFAULT_WEIGHT_PRESET,
        help="权重预设",
    )

    args = parser.parse_args()

    search = HybridSearchManager(weight_preset=args.preset)

    if args.stats:
        print("\n📊 数据库统计")
        print("=" * 60)
        stats = search.get_stats()
        for name, info in stats.items():
            print(f"\n{name}:")
            for k, v in info.items():
                print(f"  {k}: {v}")
        print("=" * 60)

    elif args.query:
        print(f"\n🔍 查询: {args.query}")
        print(f"   类型: {args.type}")
        print(f"   重排: {'禁用' if args.no_rerank else '启用'}")
        print("=" * 60)

        if args.type == "novel":
            results = search.search_novel(
                args.query, top_k=args.top_k, use_rerank=not args.no_rerank
            )
        elif args.type == "technique":
            results = search.search_technique(
                args.query,
                dimension=args.dimension,
                top_k=args.top_k,
                use_rerank=not args.no_rerank,
            )
        else:
            results = search.search_case(
                args.query, top_k=args.top_k, use_rerank=not args.no_rerank
            )

        print(f"\n找到 {len(results)} 条结果:\n")
        for i, r in enumerate(results, 1):
            print(f"[{i}] {r.get('name', r.get('novel_name', '未知'))}")
            print(f"    相似度: {r['score']:.4f}")
            if "dimension" in r:
                print(f"    维度: {r['dimension']}")
            if "writer" in r:
                print(f"    作家: {r['writer']}")
            content = r.get("content", "")[:200]
            if content:
                print(f"    内容: {content}...")
            print()
