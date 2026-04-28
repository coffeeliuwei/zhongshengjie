# core/inspiration/writer_memory_retriever.py
"""作家专属记忆检索

从 config.json writer_mapping + MemoryPointSync 组合召回作家经验。
Embedding 由调用方传入，本模块不负责 BGE-M3 推理。
"""

from typing import Dict, Any, List, Optional

from core.inspiration.memory_point_sync import MemoryPointSync
from core.config_loader import get_project_root, load_config


def retrieve_writer_memory(
    writer_agent: str,
    current_scene_type: str,
    embedding: List[float],
    sync: Optional[MemoryPointSync] = None,
) -> Dict[str, Any]:
    """检索作家专属记忆。

    Args:
        writer_agent: 作家角色（"剑尘"/"墨言"/"云溪"/"玄一"/"苍澜"）
        current_scene_type: 当前场景类型（如 "战斗场景"）
        embedding: 场景描述向量（BGE-M3 1024维）
        sync: 可注入的 MemoryPointSync 实例（测试用）

    Returns:
        {
            "writer": str,
            "scene_type": str,
            "positive_samples": List[dict],   # 正样本
            "negative_samples": List[dict],   # 负样本
            "notes": List[str],               # 正样本中的备注
            "recommended_techniques": List[str],  # 命中的技法约束ID
            "mapping_weight": float,          # 作家权重系数
        }
    """
    if sync is None:
        sync = MemoryPointSync()

    positive = sync.search_by_writer(
        embedding=embedding,
        writer_agent=writer_agent,
        scene_type=current_scene_type,
        polarity="+",
        top_k=3,
    )

    negative = sync.search_by_writer(
        embedding=embedding,
        writer_agent=writer_agent,
        scene_type=current_scene_type,
        polarity="-",
        top_k=2,
    )

    # 从 config.json 读取作家映射配置
    cfg = load_config()
    writer_mapping = cfg.get("writer_mapping", {})
    writer_cfg = writer_mapping.get(writer_agent, {})
    mapping_weight = writer_cfg.get("memory_filter", {}).get("weight", 1.0)

    # 从正样本提取推荐技法（去重、最多取3个）
    seen = set()
    recommended_techniques: List[str] = []
    for p in positive:
        cid = p["payload"].get("used_constraint_id")
        if cid and cid not in seen:
            seen.add(cid)
            recommended_techniques.append(cid)
            if len(recommended_techniques) >= 3:
                break

    def _fmt(items: list) -> List[Dict]:
        return [
            {
                "text": i["payload"].get("segment_text", ""),
                "note": i["payload"].get("note", ""),
                "chapter": i["payload"].get("chapter_ref", ""),
            }
            for i in items
        ]

    return {
        "writer": writer_agent,
        "scene_type": current_scene_type,
        "positive_samples": _fmt(positive),
        "negative_samples": _fmt(negative),
        "notes": [
            p["payload"].get("note", "") for p in positive if p["payload"].get("note")
        ],
        "recommended_techniques": recommended_techniques,
        "mapping_weight": mapping_weight,
    }
