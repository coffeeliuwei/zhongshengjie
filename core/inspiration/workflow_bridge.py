# core/inspiration/workflow_bridge.py
"""灵感引擎与 workflow.py 的桥接层

workflow.py 的 Stage 4 Phase 1 调用此处的 phase1_dispatch。
根据 inspiration_engine.enabled 决定走原流程还是灵感引擎。

把 workflow 与 inspiration 子系统解耦——
workflow 只调用 phase1_dispatch，无需知道灵感引擎内部。

设计文档：docs/superpowers/specs/2026-04-14-inspiration-engine-design.md §11
"""

from typing import Dict, Any, List, Optional

from core.inspiration.constraint_library import ConstraintLibrary
from core.inspiration.variant_generator import generate_variant_specs
from core.inspiration.memory_point_sync import MemoryPointSync
from core.inspiration.appraisal_agent import build_appraisal_spec
from core.inspiration.embedder import embed_scene_context as _embed_scene_ctx


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
    """Stage 4 Phase 1 分发器

    Returns:
        {
            "mode": "original" | "variants",
            # mode=original 时：
            "writers": List[str],          # 中文作家名列表
            # mode=variants 时：
            "variant_specs": List[dict],   # 变体任务规格
        }
    """
    inspiration_cfg = config.get("inspiration_engine", {})
    enabled = inspiration_cfg.get("enabled", True)

    if not enabled:
        return {"mode": "original", "writers": original_writers}

    # 灵感引擎模式：选第一个原作家作为本场主作家
    primary_writer_cn = original_writers[0] if original_writers else "云溪"
    writer_skill = _resolve_writer_skill(primary_writer_cn)

    n = inspiration_cfg.get("variant_count", 3)
    lib = ConstraintLibrary()
    specs = generate_variant_specs(
        scene_type=scene_type,
        scene_context=scene_context,
        writer_agent=writer_skill,
        n=n,
        constraint_library=lib,
        seed=seed,
    )

    return {"mode": "variants", "variant_specs": specs}


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
        if memory_point_count >= 50:
            embedding = _embed_scene_context(scene_context)
            top_k = 3 if memory_point_count < 300 else 5
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
