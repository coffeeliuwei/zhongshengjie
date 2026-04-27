# core/inspiration/memory_point_sync.py
"""记忆点库（memory_points_v1）同步操作

封装 Qdrant 增删查。Embedding 由调用方传入（本模块不负责 BGE-M3 调用）。

设计文档：docs/superpowers/specs/2026-04-14-inspiration-engine-design.md §8
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

try:
    from core.config_loader import get_qdrant_url
except ImportError:
    import os

    def get_qdrant_url():
        return os.environ.get("QDRANT_URL", "http://localhost:6333")


COLLECTION_NAME = "memory_points_v1"
_VECTOR_SIZE = 1024  # BGE-M3 向量维度


class MemoryPointSync:
    """记忆点库 CRUD"""

    def __init__(
        self, client: Optional[QdrantClient] = None, qdrant_path: Optional[str] = None
    ):
        if client is not None:
            self.client = client
        elif qdrant_path:
            self.client = QdrantClient(path=qdrant_path)
        else:
            self.client = QdrantClient(url=get_qdrant_url())

    def ensure_collection(self) -> None:
        """确保 memory_points_v1 collection 存在，不存在则自动创建。

        create() 在写入前自动调用此方法，无需外部手动初始化。
        """
        from qdrant_client.http.models import Distance, VectorParams

        existing = {c.name for c in self.client.get_collections().collections}
        if COLLECTION_NAME not in existing:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=_VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )

    def create(
        self, payload: Dict[str, Any], embedding: Optional[List[float]] = None
    ) -> str:
        """创建记忆点

        Args:
            payload: 记忆点 payload，必含
                segment_text, resonance_type, polarity, intensity, scene_type
            embedding: 1024 维向量；为 None 时使用零向量占位（待后续补充）

        Returns:
            生成的记忆点 ID
        """
        self.ensure_collection()
        # 默认字段
        now = datetime.now(timezone.utc)
        mp_id = f"mp_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        full_payload = {
            "id": mp_id,
            "created_at": now.isoformat(),
            "chapter_ref": payload.get("chapter_ref"),
            "segment_text": payload["segment_text"],
            "segment_scope": payload.get("segment_scope", "paragraph"),
            "position_hint": payload.get("position_hint", {}),
            "resonance_type": payload["resonance_type"],
            "polarity": payload["polarity"],
            "intensity": payload["intensity"],
            "note": payload.get("note"),
            "reader_id": payload.get("reader_id", "author"),
            "reader_cluster": payload.get("reader_cluster", "default"),
            "scene_type": payload["scene_type"],
            "writer_agent": payload.get("writer_agent"),
            "used_constraint_id": payload.get("used_constraint_id"),
            "overturn_event": payload.get("overturn_event"),
            "structural_features": payload.get("structural_features", {}),
            # 存为整数便于 Qdrant MatchValue 过滤
            "retrieval_weight": 2 if payload.get("overturn_event") else 1,
        }

        vector = embedding if embedding is not None else [0.0] * 1024

        point = PointStruct(
            id=mp_id,
            vector=vector,
            payload=full_payload,
        )
        self.client.upsert(collection_name=COLLECTION_NAME, points=[point])
        return mp_id

    def count(self) -> int:
        """记忆点总数"""
        result = self.client.count(collection_name=COLLECTION_NAME, exact=True)
        return result.count

    def count_overturn_events(self) -> int:
        """推翻事件数"""
        # Qdrant 没有 "is not null" 直接过滤；用 retrieval_weight=2 作为代理
        flt = Filter(
            must=[
                FieldCondition(
                    key="retrieval_weight",
                    match=MatchValue(value=2),
                )
            ]
        )
        result = self.client.count(
            collection_name=COLLECTION_NAME,
            count_filter=flt,
            exact=True,
        )
        return result.count

    def search_similar(
        self,
        embedding: List[float],
        scene_type: Optional[str] = None,
        polarity: Optional[str] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """检索相似记忆点

        Args:
            embedding: 查询向量
            scene_type: 可选，限定场景类型
            polarity: 可选，"+" 或 "-"
            top_k: 返回数量
        """
        filter_conditions = []
        if scene_type:
            filter_conditions.append(
                FieldCondition(key="scene_type", match=MatchValue(value=scene_type))
            )
        if polarity:
            filter_conditions.append(
                FieldCondition(key="polarity", match=MatchValue(value=polarity))
            )

        flt = Filter(must=filter_conditions) if filter_conditions else None

        results = self.client.search(
            collection_name=COLLECTION_NAME,
            query_vector=embedding,
            query_filter=flt,
            limit=top_k,
        )
        return [{"id": r.id, "score": r.score, "payload": r.payload} for r in results]

    def list_recent(
        self,
        polarity: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """按极性列出最近的记忆点（按 created_at 降序，不需要 embedding）。

        Args:
            polarity: "+" 为正样本（击中过），"-" 为负样本（标过乏味）
            top_k:    返回条数上限

        Returns:
            List of {"id": str, "payload": dict}，按 created_at 降序
        """
        flt = Filter(
            must=[FieldCondition(key="polarity", match=MatchValue(value=polarity))]
        )
        results, _ = self.client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=flt,
            limit=top_k * 3,  # 取多一些再在内存中排序
            with_payload=True,
        )
        points = [{"id": str(p.id), "payload": p.payload} for p in results]
        points.sort(
            key=lambda x: x["payload"].get("created_at", ""),
            reverse=True,
        )
        return points[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        """获取记忆点库统计"""
        total = self.count()
        overturn = self.count_overturn_events()
        return {
            "total_count": total,
            "overturn_count": overturn,
            "normal_count": total - overturn,
            "phase": self._determine_phase(total),
        }

    def _determine_phase(self, count: int) -> str:
        """根据记忆点数判断鉴赏师阶段"""
        from core.config_loader import get_inspiration_engine_config

        cfg = get_inspiration_engine_config()
        cold_start = cfg.get("appraisal_cold_start_threshold", 50)
        growing = cfg.get("appraisal_growing_threshold", 300)

        if count < cold_start:
            return "cold_start"
        elif count < growing:
            return "growing"
        else:
            return "mature"
