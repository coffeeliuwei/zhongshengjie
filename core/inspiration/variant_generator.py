# core/inspiration/variant_generator.py
"""变体生成器（任务规格构造）

本模块不直接调用作家 Skill。Claude 对话层按生成的任务规格调用 Skills。
每个变体规格包含：变体 ID、目标作家、注入约束后的 prompt、所用约束 ID。

一个无约束基准始终保留——保证至少有"正常写法"可选。

设计文档：docs/superpowers/specs/2026-04-14-inspiration-engine-design.md §4
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from core.inspiration.constraint_library import ConstraintLibrary


def generate_variant_specs(
    scene_type: str,
    scene_context: Dict[str, Any],
    writer_agent: str,
    n: int,
    constraint_library: ConstraintLibrary,
    seed: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """生成 N 个变体任务规格

    策略：
    - 1 个基准（无约束）
    - N-1 个约束变体（不同类别优先）
    - 若约束池不足，剩余位置全部为基准

    Args:
        scene_type: 场景类型（如"战斗"、"打脸"）
        scene_context: 场景上下文（大纲、角色、设定约束等）
        writer_agent: 目标作家 Skill 名称
        n: 变体数量（最小 2）
        constraint_library: 约束库实例
        seed: 随机种子（测试用）

    Returns:
        list of dicts: [{id, writer_agent, prompt, used_constraint_id}, ...]
    """
    if n < 2:
        n = 2

    # 抽取 N-1 条约束（保留 1 个基准位）
    constraints = constraint_library.pick_for_variants(
        scene_type=scene_type,
        n=n - 1,
        seed=seed,
    )

    specs: List[Dict[str, Any]] = []
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    # 基准变体（始终第一个）
    specs.append(
        {
            "id": f"var_{timestamp}_001",
            "writer_agent": writer_agent,
            "prompt": _build_prompt(scene_context, constraint=None),
            "used_constraint_id": None,
        }
    )

    # 约束变体
    for i, constraint in enumerate(constraints, start=2):
        specs.append(
            {
                "id": f"var_{timestamp}_{i:03d}",
                "writer_agent": writer_agent,
                "prompt": _build_prompt(scene_context, constraint=constraint),
                "used_constraint_id": constraint["id"],
            }
        )

    # 若约束不足，补足基准（场景无可用约束时全是基准）
    while len(specs) < n:
        idx = len(specs) + 1
        specs.append(
            {
                "id": f"var_{timestamp}_{idx:03d}",
                "writer_agent": writer_agent,
                "prompt": _build_prompt(scene_context, constraint=None),
                "used_constraint_id": None,
            }
        )

    return specs


def _build_prompt(
    scene_context: Dict[str, Any],
    constraint: Optional[Dict[str, Any]],
) -> str:
    """构造作家 Skill 的输入 prompt

    Format:
        【场景上下文】
        outline: ...
        characters: ...
        ...

        【创作约束】（可选）
        类型：XXX
        要求：YYY
    """
    context_lines = ["【场景上下文】"]
    for key, value in scene_context.items():
        context_lines.append(f"{key}: {value}")
    prompt = "\n".join(context_lines)

    if constraint:
        prompt += "\n\n【本次创作约束】\n"
        prompt += f"类型：{constraint['category']}\n"
        prompt += f"强度：{constraint['intensity']}\n"
        prompt += f"要求：{constraint['constraint_text']}\n"
        prompt += "\n请在此约束下完成本场景的创作。"

    return prompt


def get_variant_count_from_config() -> int:
    """从配置获取默认变体数量"""
    from core.config_loader import get_config

    config = get_config()
    return config.get("inspiration_engine", {}).get("variant_count", 3)
