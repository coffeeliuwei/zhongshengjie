"""
数据库连接管理器
统一管理向量数据库连接，支持自动检测、降级处理、本地缓存
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# 导入统一配置
try:
    from core.config_loader import get_qdrant_url
    HAS_CONFIG_LOADER = True
except ImportError:
    HAS_CONFIG_LOADER = False

# 导入日志工具
try:
    from core.logging_utils import get_logger
    _db_logger = get_logger("db_connection")
except ImportError:
    _db_logger = None

# 导入 Qdrant 异常类型（用于重试）
try:
    from qdrant_client.http.exceptions import UnexpectedResponse
    _HAS_UNEXPECTED_RESPONSE = True
except ImportError:
    _HAS_UNEXPECTED_RESPONSE = False


class DatabaseStatus(Enum):
    """数据库状态"""

    AVAILABLE = "available"  # 可用
    UNAVAILABLE = "unavailable"  # 不可用
    DEGRADED = "degraded"  # 降级模式（使用本地缓存）
    UNKNOWN = "unknown"  # 未知


@dataclass
class ConnectionInfo:
    """连接信息"""

    status: DatabaseStatus
    host: str
    port: int
    message: str
    latency_ms: float = 0.0
    collections: Dict[str, int] = None  # 集合名 -> 条目数


class DatabaseConnectionManager:
    """
    数据库连接管理器

    功能：
    1. 自动检测数据库连接状态
    2. 支持降级模式（本地 JSON 缓存）
    3. 连接健康检查
    4. 自动重连机制

    降级策略：
    - Qdrant 不可用时 → 使用本地 JSON 文件
    - 同步功能 → 写入本地 JSON
    - 检索功能 → 从本地 JSON 搜索（文本匹配）
    """

    def __init__(
        self,
        qdrant_url: Optional[str] = None,
        cache_dir: Path = None,
        auto_check: bool = True,
    ):
        """
        初始化数据库连接管理器

        Args:
            qdrant_url: Qdrant 服务 URL（默认从 get_qdrant_url() 获取）
            cache_dir: 本地缓存目录（降级模式使用）
            auto_check: 是否自动检测连接
        """
        if qdrant_url is None:
            if HAS_CONFIG_LOADER:
                qdrant_url = get_qdrant_url()
            else:
                import os
                qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
        self.qdrant_url = qdrant_url
        self.cache_dir = cache_dir or Path(".cache/db_cache")

        # 状态
        self._status = DatabaseStatus.UNKNOWN
        self._last_check_time = 0
        self._check_interval = 60  # 60秒检测一次

        # Qdrant 客户端（延迟初始化）
        self._client = None
        self._embedder = None

        # 本地缓存
        self._cache: Dict[str, Dict[str, Any]] = {}  # collection -> {id: data}

        # 自动检测
        if auto_check:
            self.check_connection()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type(
            (ConnectionError, TimeoutError, OSError)
            + ((UnexpectedResponse,) if _HAS_UNEXPECTED_RESPONSE else ())
        ),
        before_sleep=lambda retry_state: (
            _db_logger.warning(
                "Qdrant 连接失败，重试中",
                attempt=retry_state.attempt_number,
            ) if _db_logger else print(
                f"Qdrant 连接失败，第 {retry_state.attempt_number} 次重试..."
            )
        ),
    )
    def _create_qdrant_client(self) -> "QdrantClient":
        """创建 Qdrant 客户端（带重试）"""
        from qdrant_client import QdrantClient

        return QdrantClient(url=self.qdrant_url, timeout=5)

    def check_connection(self) -> ConnectionInfo:
        """
        检测数据库连接

        Returns:
            连接信息
        """
        start_time = time.time()

        try:
            # 尝试连接 Qdrant（带重试）
            client = self._create_qdrant_client()

            # 获取集合列表
            collections = client.get_collections().collections
            collection_names = [c.name for c in collections]

            # 获取各集合的条目数
            collection_counts = {}
            for name in collection_names:
                try:
                    info = client.get_collection(name)
                    collection_counts[name] = info.points_count
                except Exception:
                    collection_counts[name] = 0

            latency = (time.time() - start_time) * 1000

            self._status = DatabaseStatus.AVAILABLE
            self._client = client
            self._last_check_time = time.time()

            return ConnectionInfo(
                status=DatabaseStatus.AVAILABLE,
                host=self.qdrant_url,
                port=0,
                message="数据库连接正常",
                latency_ms=latency,
                collections=collection_counts,
            )

        except ImportError:
            self._status = DatabaseStatus.UNAVAILABLE
            self._last_check_time = time.time()

            return ConnectionInfo(
                status=DatabaseStatus.UNAVAILABLE,
                host=self.qdrant_url,
                port=0,
                message="qdrant-client 未安装，请运行: pip install qdrant-client",
            )

        except Exception as e:
            self._status = DatabaseStatus.DEGRADED
            self._last_check_time = time.time()

            # 加载本地缓存
            self._load_local_cache()

            return ConnectionInfo(
                status=DatabaseStatus.DEGRADED,
                host=self.qdrant_url,
                port=0,
                message=f"数据库不可用，使用本地缓存模式: {str(e)}",
            )

    @property
    def is_available(self) -> bool:
        """是否可用（Qdrant 连接正常）"""
        return self._status == DatabaseStatus.AVAILABLE

    def get_client(self):
        """
        获取 Qdrant 客户端

        Returns:
            Qdrant 客户端，不可用时返回 None
        """
        if self._status == DatabaseStatus.AVAILABLE:
            return self._client
        return None

    def get_embedder(self):
        """
        获取嵌入模型

        Returns:
            SentenceTransformer 模型
        """
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._embedder = SentenceTransformer(
                    "paraphrase-multilingual-MiniLM-L12-v2"
                )
            except ImportError:
                pass
        return self._embedder

    # ==================== 降级模式：本地缓存操作 ====================

    def _load_local_cache(self) -> None:
        """加载本地缓存"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        for collection in [
            "novel_settings",
            "writing_techniques",
            "case_library",
            "creation_context",
        ]:
            cache_file = self.cache_dir / f"{collection}.json"
            if cache_file.exists():
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        self._cache[collection] = json.load(f)
                except Exception:
                    self._cache[collection] = {}
            else:
                self._cache[collection] = {}

    def _save_local_cache(self, collection: str) -> None:
        """保存本地缓存"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self.cache_dir / f"{collection}.json"

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(self._cache.get(collection, {}), f, ensure_ascii=False, indent=2)

    def save_to_cache(
        self, collection: str, item_id: str, data: Dict[str, Any]
    ) -> bool:
        """
        保存数据到缓存（降级模式使用）

        Args:
            collection: 集合名称
            item_id: 数据ID
            data: 数据内容

        Returns:
            是否成功
        """
        if collection not in self._cache:
            self._cache[collection] = {}

        self._cache[collection][item_id] = data
        self._save_local_cache(collection)

        return True

    def search_in_cache(
        self,
        collection: str,
        query: str,
        top_k: int = 5,
        filters: Dict[str, str] = None,
    ) -> List[Dict[str, Any]]:
        """
        从缓存搜索（降级模式使用）

        Args:
            collection: 集合名称
            query: 查询文本
            top_k: 返回数量
            filters: 过滤条件

        Returns:
            搜索结果列表
        """
        if collection not in self._cache:
            return []

        results = []
        query_lower = query.lower()

        for item_id, data in self._cache[collection].items():
            # 检查过滤条件
            if filters:
                match = True
                for key, value in filters.items():
                    if data.get(key) != value:
                        match = False
                        break
                if not match:
                    continue

            # 简单文本匹配
            content = str(data).lower()
            if query_lower in content:
                # 计算简单相关性分数
                score = content.count(query_lower) / max(len(content), 1)
                results.append({"id": item_id, "score": score, "payload": data})

        # 按分数排序
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:top_k]

    def get_from_cache(self, collection: str, item_id: str) -> Optional[Dict[str, Any]]:
        """
        从缓存获取单个数据

        Args:
            collection: 集合名称
            item_id: 数据ID

        Returns:
            数据内容，不存在返回 None
        """
        return self._cache.get(collection, {}).get(item_id)

    def list_cache(self, collection: str) -> List[Dict[str, Any]]:
        """
        列出缓存中的所有数据

        Args:
            collection: 集合名称

        Returns:
            数据列表
        """
        return list(self._cache.get(collection, {}).values())

    def get_cache_stats(self) -> Dict[str, int]:
        """
        获取缓存统计

        Returns:
            各集合的缓存条目数
        """
        return {collection: len(items) for collection, items in self._cache.items()}

    # ==================== 统一接口 ====================

    def upsert(
        self,
        collection: str,
        item_id: str,
        vector: List[float],
        payload: Dict[str, Any],
    ) -> bool:
        """
        插入或更新数据（自动选择模式）

        Args:
            collection: 集合名称
            item_id: 数据ID
            vector: 向量
            payload: 数据内容

        Returns:
            是否成功
        """
        if self.is_available:
            try:
                from qdrant_client.models import PointStruct

                self._client.upsert(
                    collection_name=collection,
                    points=[PointStruct(id=item_id, vector=vector, payload=payload)],
                )
                return True
            except Exception:
                pass

        # 降级模式：保存到缓存
        return self.save_to_cache(collection, item_id, payload)

    def search(
        self,
        collection: str,
        query: str,
        top_k: int = 5,
        filters: Dict[str, str] = None,
    ) -> List[Dict[str, Any]]:
        """
        搜索数据（自动选择模式）

        Args:
            collection: 集合名称
            query: 查询文本
            top_k: 返回数量
            filters: 过滤条件

        Returns:
            搜索结果列表
        """
        if self.is_available:
            try:
                embedder = self.get_embedder()
                if embedder is None:
                    return self.search_in_cache(collection, query, top_k, filters)

                query_vector = embedder.encode(query).tolist()

                # 构建过滤条件
                from qdrant_client.models import Filter, FieldCondition, MatchValue

                filter_obj = None
                if filters:
                    conditions = [
                        FieldCondition(key=k, match=MatchValue(value=v))
                        for k, v in filters.items()
                    ]
                    filter_obj = Filter(must=conditions)

                results = self._client.search(
                    collection_name=collection,
                    query_vector=query_vector,
                    filter=filter_obj,
                    limit=top_k,
                    with_payload=True,
                )

                return [
                    {"id": str(r.id), "score": r.score, "payload": r.payload}
                    for r in results
                ]
            except Exception:
                pass

        # 降级模式：从缓存搜索
        return self.search_in_cache(collection, query, top_k, filters)

    def get_stats(self) -> Dict[str, Any]:
        """
        获取数据库统计信息

        Returns:
            统计信息
        """
        if self.is_available:
            try:
                collections = self._client.get_collections().collections
                stats = {
                    "status": "available",
                    "url": self.qdrant_url,
                    "collections": {},
                }

                for c in collections:
                    info = self._client.get_collection(c.name)
                    stats["collections"][c.name] = info.points_count

                return stats
            except Exception:
                pass

        # 降级模式：返回缓存统计
        return {
            "status": "degraded",
            "url": self.qdrant_url,
            "message": "使用本地缓存模式",
            "collections": self.get_cache_stats(),
        }


# 全局数据库连接管理器（延迟初始化）
_global_db_manager: Optional[DatabaseConnectionManager] = None


def get_db_manager(
    qdrant_url: Optional[str] = None,
    cache_dir: Path = None,
    auto_check: bool = True,
) -> DatabaseConnectionManager:
    """
    获取全局数据库连接管理器

    Args:
        qdrant_url: Qdrant 服务 URL（默认从 get_qdrant_url() 获取）
        cache_dir: 本地缓存目录
        auto_check: 是否自动检测连接

    Returns:
        DatabaseConnectionManager 实例
    """
    global _global_db_manager

    if _global_db_manager is None:
        _global_db_manager = DatabaseConnectionManager(
            qdrant_url=qdrant_url, cache_dir=cache_dir, auto_check=auto_check
        )

    return _global_db_manager
