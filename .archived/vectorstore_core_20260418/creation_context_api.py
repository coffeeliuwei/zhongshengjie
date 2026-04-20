"""创作上下文缓存 API

将每个阶段的关键产出存入 Qdrant creation_context collection，
供后续阶段按需检索，替代对对话历史的依赖。
"""

import json
import uuid
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path

# 确保项目根目录在 path 中
_here = Path(__file__).parent
sys.path.insert(0, str(_here.parent.parent))

from core.config_loader import get_qdrant_url, get_config

# 从 config.json 读取 collection 名
_cfg = get_config()
COLLECTION_NAME = (
    _cfg.get("database", {})
    .get("collections", {})
    .get("creation_context", "creation_context")
)
VECTOR_SIZE = 1024


def _get_client():
    """获取 Qdrant 客户端（懒加载）"""
    from qdrant_client import QdrantClient

    return QdrantClient(url=get_qdrant_url())


def _get_embedder():
    """获取 BGE-M3 嵌入模型（懒加载）"""
    from FlagEmbedding import FlagModel

    model_path = get_config().get("model", {}).get("model_path", "")
    return FlagModel(model_path, use_fp16=True)


def ensure_collection() -> None:
    """确保 creation_context collection 存在，不存在则自动创建"""
    from qdrant_client.http import models

    client = _get_client()
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=VECTOR_SIZE,
                distance=models.Distance.COSINE,
            ),
        )


def save_stage_output(
    chapter: str,
    stage: str,
    content: Dict[str, Any],
) -> str:
    """将阶段产出向量化存入 creation_context

    Args:
        chapter: 章节标识，如"第1章"
        stage: 阶段标识，如"stage0_goal"、"scene_001_result"
        content: 要存储的内容字典

    Returns:
        存储的点 ID（UUID 字符串）
    """
    ensure_collection()
    client = _get_client()
    embedder = _get_embedder()

    text = json.dumps(content, ensure_ascii=False)
    embedding = embedder.encode(text).tolist()

    point_id = str(uuid.uuid4())
    from qdrant_client.http import models

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            models.PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "chapter": chapter,
                    "stage": stage,
                    "content": content,
                    "text_preview": text[:200],
                },
            )
        ],
    )
    return point_id


def query_context(
    chapter: str,
    query: str,
    top_k: int = 5,
    stage_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """检索与 query 最相关的上下文片段

    Args:
        chapter: 只检索该章节的上下文
        query: 语义查询文本，如"血牙的情感状态"
        top_k: 返回条数
        stage_filter: 可选，只检索特定阶段产出，如"stage0_goal"

    Returns:
        按相关度排序的 content 字典列表
    """
    ensure_collection()
    client = _get_client()
    embedder = _get_embedder()

    from qdrant_client.http import models

    embedding = embedder.encode(query).tolist()

    must_filters = [
        models.FieldCondition(
            key="chapter",
            match=models.MatchValue(value=chapter),
        )
    ]
    if stage_filter:
        must_filters.append(
            models.FieldCondition(
                key="stage",
                match=models.MatchValue(value=stage_filter),
            )
        )

    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=embedding,
        limit=top_k,
        query_filter=models.Filter(must=must_filters),
    )
    return [r.payload["content"] for r in results]


def clear_chapter_context(chapter: str) -> None:
    """章节定稿后清理该章节的所有缓存

    Args:
        chapter: 章节标识，如"第1章"
    """
    from qdrant_client.http import models

    client = _get_client()
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="chapter",
                        match=models.MatchValue(value=chapter),
                    )
                ]
            )
        ),
    )
