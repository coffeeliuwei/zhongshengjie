# core/inspiration/workflow_bridge.py
"""灵感引擎与 workflow.py 的桥接层

workflow.py 的 Stage 4 Phase 1 调用此处的 phase1_dispatch。
根据 inspiration_engine.enabled 决定走原流程还是灵感引擎。

把 workflow 与 inspiration 子系统解耦——
workflow 只调用 phase1_dispatch，无需知道灵感引擎内部。

设计文档：docs/superpowers/specs/2026-04-14-inspiration-engine-design.md §11
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from core.inspiration.memory_point_sync import MemoryPointSync
from core.inspiration.appraisal_agent import build_appraisal_spec
from core.inspiration.embedder import embed_scene_context as _embed_scene_ctx

# N5修复：导入配置读取
from core.config_loader import get_config


# 中文作家名 → Skill 名称映射
WRITER_NAME_TO_SKILL = {
    "苍澜": "novelist-canglan",
    "玄一": "novelist-xuanyi",
    "墨言": "novelist-moyan",
    "剑尘": "novelist-jianchen",
    "云溪": "novelist-yunxi",
}


def _resolve_writer_skill(chinese_name: str) -> str:
    """中文作家名映射为 Skill 名"""
    return WRITER_NAME_TO_SKILL.get(chinese_name, chinese_name)


def phase1_dispatch(
    scene_type: str,
    scene_context: Dict[str, Any],
    original_writers: List[str],
    config: Dict[str, Any],
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """Stage 4 Phase 1 分发器（v2：变体模式已移除，始终返回原始写手列表）

    v1 多变体生成逻辑已由 P1-5 删除（variant_generator.py 已归档至 .archived/）。
    v2 创意注入由阶段 5.5 三方协商完成（P2-1 接入）。

    Args:
        scene_type: 场景类型（保留参数兼容旧调用方，暂未使用）
        scene_context: 场景上下文（保留参数兼容旧调用方，暂未使用）
        original_writers: 原始写手列表（中文名）
        config: 配置字典（保留参数兼容旧调用方，暂未使用）
        seed: 随机种子（保留参数兼容旧调用方，暂未使用）

    Returns:
        {"mode": "original", "writers": original_writers}
    """
    return {"mode": "original", "writers": original_writers}


def _embed_scene_context(scene_context: Dict[str, Any]) -> List[float]:
    """将场景上下文编码为向量（调用 BGE-M3）

    降级：模型不可用时返回零向量（不影响流程跑通，只影响检索质量）。
    """
    try:
        return _embed_scene_ctx(scene_context)
    except Exception:
        return [0.0] * 1024


def _retrieve_references_for_appraisal(
    sync: MemoryPointSync,
    embedding: List[float],
    scene_type: str,
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """检索正负向记忆点，供鉴赏师 prompt 注入

    正向（+）：作者过去被击中的段落，鉴赏师应向其靠近
    负向（-）：作者觉得乏味/出戏的段落，鉴赏师应避开

    Args:
        sync: MemoryPointSync 实例
        embedding: 场景上下文向量
        scene_type: 当前场景类型，用于过滤
        top_k: 正向检索数量（负向取 max(1, top_k//2)）
    """
    pos = sync.search_similar(
        embedding=embedding,
        scene_type=scene_type,
        polarity="+",
        top_k=top_k,
    )
    neg = sync.search_similar(
        embedding=embedding,
        scene_type=scene_type,
        polarity="-",
        top_k=max(1, top_k // 2),
    )
    return pos + neg


def select_winner_spec(
    candidates: List[Dict[str, Any]],
    scene_context: Dict[str, Any],
    memory_point_count: Optional[int] = None,
    retrieved_references: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """构造鉴赏师选择规格（含 E 机制记忆点注入）

    根据记忆点数量自动切换判准阶段：
    - < 50：冷启动，纯 LLM 直感
    - 50-300：成长期，注入 top 3 正负记忆点
    - >= 300：成熟期，注入 top 5 正负记忆点

    Args:
        candidates: 变体列表，每项含 id / text / used_constraint_id / writer_agent
        scene_context: 场景上下文（含 scene_type 等字段）
        memory_point_count: 可注入以避免真实 Qdrant 调用（测试用）
        retrieved_references: 可注入以避免真实检索（测试用）

    Returns:
        {"skill_name": str, "prompt": str, "phase": "cold"|"growing"|"mature"}
    """
    sync = MemoryPointSync()

    if memory_point_count is None:
        try:
            memory_point_count = sync.count()
        except Exception:
            memory_point_count = 0

    if retrieved_references is None:
        # N5修复：从配置读取阈值，而非硬编码
        cfg = get_config()
        inspiration_cfg = cfg.get("inspiration_engine", {})
        cold_threshold = inspiration_cfg.get("appraisal_cold_start_threshold", 50)
        growing_threshold = inspiration_cfg.get("appraisal_growing_threshold", 300)

        if memory_point_count >= cold_threshold:
            embedding = _embed_scene_context(scene_context)
            top_k = 3 if memory_point_count < growing_threshold else 5
            retrieved_references = _retrieve_references_for_appraisal(
                sync=sync,
                embedding=embedding,
                scene_type=scene_context.get("scene_type", ""),
                top_k=top_k,
            )
        else:
            retrieved_references = []

    return build_appraisal_spec(
        candidates=candidates,
        scene_context=scene_context,
        memory_point_count=memory_point_count,
        retrieved_references=retrieved_references,
    )


def execute_variants(
    specs: List[Dict[str, Any]],
    writer_caller: Any,
) -> List[Dict[str, Any]]:
    """将变体规格列表执行为带文本的候选列表

    Args:
        specs: phase1_dispatch 返回的 variant_specs
        writer_caller: 可调用对象，接收一个 spec dict，返回生成文本 str
                       （由 workflow.py 提供，内部调用相应 novelist Skill）

    Returns:
        候选列表，每项：
        {
            "id": str,
            "text": str,          # 生成文本，失败时为 "[生成失败]"
            "used_constraint_id": str | None,
            "writer_agent": str,
            "error": str | None,  # 仅在失败时存在
        }
    """
    candidates = []
    for spec in specs:
        try:
            text = writer_caller(spec)
            candidates.append(
                {
                    "id": spec["id"],
                    "text": text,
                    "used_constraint_id": spec.get("used_constraint_id"),
                    "writer_agent": spec.get("writer_agent", ""),
                }
            )
        except Exception as e:
            candidates.append(
                {
                    "id": spec["id"],
                    "text": "[生成失败]",
                    "used_constraint_id": spec.get("used_constraint_id"),
                    "writer_agent": spec.get("writer_agent", ""),
                    "error": str(e),
                }
            )
    return candidates


def record_winner(
    appraisal: Any,
    candidates: List[Dict[str, Any]],
    scene_context: Dict[str, Any],
    sync: Optional[Any] = None,
) -> Optional[str]:
    """将鉴赏师选择结果写入记忆点库

    Args:
        appraisal: AppraisalResult 实例
        candidates: execute_variants 返回的候选列表
        scene_context: 场景上下文
        sync: MemoryPointSync 实例（测试可注入）

    Returns:
        写入的记忆点 ID，或 None（无赢家时）
    """
    if appraisal.selected_id is None:
        return None  # 全部平庸，不写入

    # 找到赢家候选文本
    winner_candidate = next(
        (c for c in candidates if c["id"] == appraisal.selected_id), None
    )
    if not winner_candidate:
        return None

    if sync is None:
        sync = MemoryPointSync()

    embedding = _embed_scene_context(scene_context)

    payload = {
        "segment_text": winner_candidate["text"],
        "segment_scope": "paragraph",
        "position_hint": None,
        "chapter_ref": scene_context.get("chapter_ref"),
        "resonance_type": "鉴赏师选中",
        "polarity": "+",
        "intensity": 2 if appraisal.confidence == "high" else 1,
        "note": appraisal.ignition_point or "",
        "scene_type": scene_context.get("scene_type", ""),
        "structural_features": {},
        "used_constraint_id": winner_candidate.get("used_constraint_id"),
        "writer_agent": winner_candidate.get("writer_agent", ""),
        "appraisal_reason": appraisal.reason_fragment,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

    return sync.create(payload, embedding=embedding)
