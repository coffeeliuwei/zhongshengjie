"""
检索管理器 - 从向量库检索数据
整合 knowledge_search.py、technique_search.py、case_search_qdrant.py 的核心逻辑
"""

from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
except ImportError:
    raise ImportError("请安装 qdrant-client: pip install qdrant-client")

# 配置导入
try:
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".vectorstore"))
    from config_loader import get_project_root, get_qdrant_url
except ImportError:
    # 兼容独立运行场景
    def get_project_root():
        return Path.cwd()

    def get_qdrant_url():
        return "http://localhost:6333"


class SearchManager:
    """
    检索管理器

    支持从三大向量库检索数据：
    - novel_settings: 小说设定（角色、势力、力量体系）
    - writing_techniques: 创作技法（11维度技法）
    - case_library: 标杆案例（跨题材案例）
    """

    # 集合名称常量
    NOVEL_COLLECTION = "novel_settings"
    TECHNIQUE_COLLECTION = "writing_techniques"
    CASE_COLLECTION = "case_library"

    # 向量维度
    VECTOR_SIZE = 1024  # BGE-M3 dense 向量维度

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
    ):
        """
        初始化检索管理器

        Args:
            project_dir: 项目根目录，默认从配置自动获取
            use_docker: 是否使用Docker Qdrant
            docker_url: Docker Qdrant URL，默认从配置自动获取
        """
        self.project_dir = project_dir or get_project_root()
        self.vectorstore_dir = self.project_dir / ".vectorstore"
        self.qdrant_dir = self.vectorstore_dir / "qdrant"

        # Qdrant客户端
        self._client = None
        self._model = None
        self.use_docker = use_docker
        self.docker_url = docker_url or get_qdrant_url()

    def _get_client(self) -> QdrantClient:
        """获取Qdrant客户端"""
        if self._client is None:
            if self.use_docker:
                try:
                    self._client = QdrantClient(url=self.docker_url)
                    self._client.get_collections()  # 测试连接
                except Exception:
                    # 回退到本地
                    self._client = QdrantClient(path=str(self.qdrant_dir))
            else:
                self._client = QdrantClient(path=str(self.qdrant_dir))
        return self._client

    def _load_model(self):
        """懒加载嵌入模型"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(
                    "paraphrase-multilingual-MiniLM-L12-v2"
                )
            except ImportError:
                pass
        return self._model

    def _get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入向量"""
        model = self._load_model()
        if model is None:
            return [0.0] * self.VECTOR_SIZE
        return model.encode(text, show_progress_bar=False).tolist()

    # ==================== 小说设定检索 ====================

    def search_novel(
        self,
        query: str,
        entity_type: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        检索小说设定

        Args:
            query: 查询文本
            entity_type: 实体类型过滤（角色、势力、力量体系等）
            top_k: 返回数量

        Returns:
            检索结果列表
        """
        client = self._get_client()
        query_vector = self._get_embedding(query)

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

        try:
            results = client.query_points(
                collection_name=self.NOVEL_COLLECTION,
                query=query_vector,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
        except Exception:
            return []

        formatted = []
        for p in results.points:
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
        """
        获取角色设定

        Args:
            name: 角色名称

        Returns:
            角色设定字典，若未找到则返回None
        """
        results = self.search_novel(name, entity_type="角色", top_k=10)
        for r in results:
            if name in r.get("name", ""):
                return r
        return None

    def get_faction(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取势力设定

        Args:
            name: 势力名称

        Returns:
            势力设定字典，若未找到则返回None
        """
        results = self.search_novel(name, entity_type="势力", top_k=10)
        for r in results:
            if name in r.get("name", ""):
                return r
        return None

    def get_power_branch(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取力量派别

        Args:
            name: 力量派别名称

        Returns:
            力量派别设定字典，若未找到则返回None
        """
        results = self.search_novel(name, entity_type="力量派别", top_k=10)
        for r in results:
            if name in r.get("name", ""):
                return r
        return None

    def list_characters(self) -> List[str]:
        """列出所有角色名称"""
        client = self._get_client()
        try:
            results = client.scroll(
                collection_name=self.NOVEL_COLLECTION,
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
        try:
            results = client.scroll(
                collection_name=self.NOVEL_COLLECTION,
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

    # ==================== 创作技法检索 ====================

    def search_technique(
        self,
        query: str,
        dimension: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        检索创作技法

        Args:
            query: 查询文本
            dimension: 维度过滤（世界观维度、剧情维度等）
            top_k: 返回数量
            min_score: 最低相似度

        Returns:
            检索结果列表
        """
        client = self._get_client()
        query_vector = self._get_embedding(query)

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

        try:
            results = client.query_points(
                collection_name=self.TECHNIQUE_COLLECTION,
                query=query_vector,
                query_filter=query_filter,
                limit=top_k,
                score_threshold=min_score,
                with_payload=True,
            )
        except Exception:
            return []

        formatted = []
        for p in results.points:
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

    def get_techniques_by_dimension(
        self, dimension: str, top_k: int = 50
    ) -> List[Dict[str, Any]]:
        """
        按维度获取所有技法

        Args:
            dimension: 维度名称
            top_k: 返回数量

        Returns:
            技法列表
        """
        client = self._get_client()
        try:
            results = client.scroll(
                collection_name=self.TECHNIQUE_COLLECTION,
                with_payload=True,
                with_vectors=False,
                limit=1000,
            )[0]

            formatted = []
            for p in results:
                if p.payload.get("dimension") == dimension:
                    formatted.append(
                        {
                            "id": p.id,
                            "name": p.payload.get("name", "未知"),
                            "dimension": p.payload.get("dimension", "未知"),
                            "writer": p.payload.get("writer", "未知"),
                            "content": p.payload.get("content", ""),
                            "source_file": p.payload.get("source_file", ""),
                        }
                    )
                    if len(formatted) >= top_k:
                        break

            return formatted
        except Exception:
            return []

    # ==================== 案例检索 ====================

    def search_case(
        self,
        query: str,
        scene_type: Optional[str] = None,
        genre: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        检索标杆案例

        Args:
            query: 查询文本
            scene_type: 场景类型过滤
            genre: 题材类型过滤
            top_k: 返回数量
            min_score: 最低相似度

        Returns:
            检索结果列表
        """
        client = self._get_client()
        query_vector = self._get_embedding(query)

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

        try:
            results = client.query_points(
                collection_name=self.CASE_COLLECTION,
                query=query_vector,
                query_filter=query_filter,
                limit=top_k * 2,
                score_threshold=min_score,
                with_payload=True,
            )
        except Exception:
            return []

        formatted = []
        for p in results.points:
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

            if len(formatted) >= top_k:
                break

        return formatted

    # ==================== 统计 ====================

    def get_stats(self) -> Dict[str, Any]:
        """
        获取数据库统计信息

        Returns:
            统计信息字典
        """
        client = self._get_client()
        stats = {}

        collections = [c.name for c in client.get_collections().collections]

        # 小说设定库
        if self.NOVEL_COLLECTION in collections:
            info = client.get_collection(self.NOVEL_COLLECTION)
            stats["小说设定库"] = {
                "总数": info.points_count,
                "状态": info.status.value,
            }
        else:
            stats["小说设定库"] = {"总数": 0, "状态": "未创建"}

        # 创作技法库
        if self.TECHNIQUE_COLLECTION in collections:
            info = client.get_collection(self.TECHNIQUE_COLLECTION)
            stats["创作技法库"] = {
                "总数": info.points_count,
                "状态": info.status.value,
            }
        else:
            stats["创作技法库"] = {"总数": 0, "状态": "未创建"}

        # 案例库
        if self.CASE_COLLECTION in collections:
            info = client.get_collection(self.CASE_COLLECTION)
            stats["案例库"] = {
                "总数": info.points_count,
                "状态": info.status.value,
            }
        else:
            stats["案例库"] = {"总数": 0, "状态": "未创建"}

        return stats

    def count_novel(self) -> int:
        """获取小说设定总数"""
        client = self._get_client()
        try:
            info = client.get_collection(self.NOVEL_COLLECTION)
            return info.points_count
        except Exception:
            return 0

    def count_technique(self) -> int:
        """获取创作技法总数"""
        client = self._get_client()
        try:
            info = client.get_collection(self.TECHNIQUE_COLLECTION)
            return info.points_count
        except Exception:
            return 0

    def count_case(self) -> int:
        """获取案例总数"""
        client = self._get_client()
        try:
            info = client.get_collection(self.CASE_COLLECTION)
            return info.points_count
        except Exception:
            return 0
