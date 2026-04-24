# .vectorstore/memory_points_v1_config.py
"""memory_points_v1 Qdrant Collection 定义与初始化

记忆点库——存储作者审美指纹（段落+情绪信号+结构特征）。
作者反馈通过自然语言对话回流，由意图层识别后自动入库。

设计文档：docs/superpowers/specs/2026-04-14-inspiration-engine-design.md §8
"""

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

COLLECTION_NAME = "memory_points_v1"
VECTOR_SIZE = 1024  # BGE-M3 dense
DISTANCE = Distance.COSINE


def init_collection(client: QdrantClient) -> bool:
    """初始化 memory_points_v1 Collection。

    若已存在则跳过。返回 True 表示新建，False 表示已存在。
    """
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]

    if COLLECTION_NAME in collection_names:
        return False

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=DISTANCE,
        ),
    )
    return True


# Schema 文档（payload 字段说明，非代码强制约束）
SCHEMA_FIELDS = {
    "id": "str, mp_YYYYMMDD_NNN",
    "created_at": "ISO 8601 timestamp",
    "chapter_ref": "str | null, 来源章节",
    "segment_text": "str, 原文片段",
    "segment_scope": "sentence | paragraph | span",
    "position_hint": "dict, 段号/字符偏移",
    "resonance_type": "震撼/感动/爽快/好笑/出戏/乏味",
    "polarity": "+ | -",
    "intensity": "1 | 2 | 3",
    "note": "str | null, 作者备注",
    "reader_id": "str, 当前恒为 author（dormant interface）",
    "reader_cluster": "str, 当前恒为 default（dormant interface）",
    "scene_type": "str, 28 种场景之一",
    "writer_agent": "str, 作家 Skill 名称",
    "used_constraint_id": "str | null, 若是变体产出",
    "overturn_event": "dict | null, 推翻事件结构",
    "structural_features": "dict, 自动提取的结构特征",
    "retrieval_weight": "float, 普通 1.0 / overturn 2.0",
}
