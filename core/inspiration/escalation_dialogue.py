# core/inspiration/escalation_dialogue.py
"""升级对话格式化器

覆盖四种升级场景的结构化文本输出，供对话层直接呈现给作者。
所有升级都暴露给作者决策，不做静默降级。

设计文档：docs/superpowers/specs/2026-04-14-inspiration-engine-design.md §9
"""

from typing import List, Dict, Any


def format_rater_vs_evaluator_conflict(
    rater_selected_id: str,
    ignition_point: str,
    evaluator_violation: str,
    other_candidates: List[Dict[str, Any]],
) -> str:
    """格式化鉴赏师与评估师冲突的升级对话

    当鉴赏师选中的变体被评估师打回时调用。

    Args:
        rater_selected_id: 鉴赏师选中的变体 ID（如 "var_002"）
        ignition_point: 鉴赏师标注的点火句
        evaluator_violation: 评估师打回的原因（含规则 ID）
        other_candidates: 其余变体信息列表，每项含 id 和 summary

    Returns:
        结构化对话文本，可直接呈现给作者
    """
    others_text = ""
    for c in other_candidates:
        others_text += f"\n  - {c['id']}: {c.get('summary', '(无摘要)')}"

    return (
        f"WARNING: Rater vs Evaluator Conflict\n\n"
        f"  Rater selected: {rater_selected_id}\n"
        f"  Ignition point: {ignition_point}\n"
        f"  Evaluator rejected: {evaluator_violation}\n"
        f"\nOther candidates: {others_text if others_text else '(none)'}\n"
        f"\nOptions:\n"
        f"  A. Accept {rater_selected_id}, relax rule constraints for this case\n"
        f"  B. Choose other candidates that passed evaluation\n"
        f"  C. Adjust constraints and regenerate\n"
        f"  D. Rewrite this scene\n"
        f"  E. Other ideas\n"
    )


def format_all_variants_failed(
    candidate_ids: List[str],
    common_flaw: str,
) -> str:
    """格式化所有变体被评估师打回的升级对话

    Args:
        candidate_ids: 全部变体 ID 列表
        common_flaw: 鉴赏师或系统分析的共因描述

    Returns:
        结构化对话文本
    """
    ids_text = ", ".join(candidate_ids) if candidate_ids else "(none)"
    return (
        f"WARNING: All variants failed evaluation\n\n"
        f"  Generated: {ids_text}\n"
        f"  Common flaw: {common_flaw}\n"
        f"\nSuggested actions:\n"
        f"  A. Modify scene context (power settings,契约 rules) and regenerate\n"
        f"  B. Temporarily disable inspiration engine, use original flow\n"
        f"  C. Manually provide writing direction for this scene\n"
    )


def format_appraisal_audit(
    appraisal_count: int,
    vague_count: int,
    baseline_win_count: int,
) -> str:
    """格式化鉴赏师退化审计报告

    每 10 次鉴赏后自动触发，检查点火点是否笼统、是否反复选基准变体。

    Args:
        appraisal_count: 本轮审计覆盖的鉴赏次数
        vague_count: 点火点包含笼统词的次数
        baseline_win_count: 无约束基准变体被选中的次数

    Returns:
        结构化审计报告，要求作者标定真实点火次数
    """
    vague_ratio = vague_count / appraisal_count if appraisal_count else 0
    baseline_ratio = baseline_win_count / appraisal_count if appraisal_count else 0

    warnings = []
    if vague_ratio >= 0.4:
        warnings.append(
            f"Vague ignition points ({vague_count}/{appraisal_count} contain vague words), may be random selection"
        )
    if baseline_ratio >= 0.6:
        warnings.append(
            f"Repeated baseline selection ({baseline_win_count}/{appraisal_count} times), constraints may not be effective"
        )

    warning_text = (
        "\n  - ".join(warnings) if warnings else "No obvious degradation signs"
    )

    return (
        f"Appraisal Degradation Audit (last {appraisal_count} appraisals)\n\n"
        f"  - {warning_text}\n\n"
        f"Please calibrate: which of these {appraisal_count} appraisals did you actually resonate with?\n"
        f"(Example: 'Appraisals 2, 5, 8 were genuine ignition, others were敷衍')\n"
        f"Your calibration will be written directly to memory point store, used to calibrate rater judgment.\n"
    )


def format_overturn_audit(
    overturn_count: int,
) -> str:
    """格式化推翻事件审计报告

    累计推翻事件达阈值时触发，提示作者两位 Agent 的系统性偏差。

    Args:
        overturn_count: 累计推翻事件数量

    Returns:
        结构化审计报告，提供偏差校正选项
    """
    return (
        f"Overturn Event Audit\n\n"
        f"  You have overturned {overturn_count} times the joint judgment of rater + evaluator.\n"
        f"  This indicates systematic deviation between both Agents' judgment and your aesthetic.\n\n"
        f"How do you want to handle this?\n"
        f"  A. I will summarize deviation direction, inject into rater prompt as 'known deviation calibration'\n"
        f"  B. Adjust relevant dimension weights of evaluator\n"
        f"  C. Continue accumulating, revisit next time\n"
    )
