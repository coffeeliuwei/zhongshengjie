# core/inspiration/escalation_dialogue.py
"""升级对话格式化器

覆盖四种升级场景的结构化文本输出，供对话层直接呈现给作者。
所有升级都暴露给作者决策，不做静默降级。

设计文档：docs/superpowers/specs/2026-04-14-inspiration-engine-design.md §9
"""

import re
from typing import List, Dict, Any, Tuple, Optional


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
        f"⚠️ 警告：鉴赏师与评估师冲突\n\n"
        f"  鉴赏师选中: {rater_selected_id}\n"
        f"  点火句: {ignition_point}\n"
        f"  评估师打回: {evaluator_violation}\n"
        f"\n其他候选: {others_text if others_text else '(无)'}\n"
        f"\n可选操作:\n"
        f"  A. 接受 {rater_selected_id}，放宽此场景的规则约束\n"
        f"  B. 选择通过评估的其他候选\n"
        f"  C. 调整约束条件后重新生成\n"
        f"  D. 重写此场景\n"
        f"  E. 其他想法\n"
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
    ids_text = ", ".join(candidate_ids) if candidate_ids else "(无)"
    return (
        f"⚠️ 警告：所有变体未通过评估\n\n"
        f"  生成的变体: {ids_text}\n"
        f"  共性问题: {common_flaw}\n"
        f"\n建议操作:\n"
        f"  A. 修改场景上下文（力量设定、契约规则）后重新生成\n"
        f"  B. 暂时关闭灵感引擎，使用原流程\n"
        f"  C. 手动提供此场景的写作方向\n"
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
            f"点火点笼统 ({vague_count}/{appraisal_count} 次包含笼统词)，可能为随机选择"
        )
    if baseline_ratio >= 0.6:
        warnings.append(
            f"反复选择基准变体 ({baseline_win_count}/{appraisal_count} 次)，约束可能失效"
        )

    warning_text = "\n  - ".join(warnings) if warnings else "无明显退化迹象"

    return (
        f"鉴赏师退化审计（最近 {appraisal_count} 次鉴赏）\n\n"
        f"  - {warning_text}\n\n"
        f"请标定：这 {appraisal_count} 次鉴赏中，哪些是你真正共鸣的？\n"
        f"（示例：'第 2、5、8 次是真点火，其他是敷衍'）\n"
        f"你的标定将直接写入记忆点库，用于校准鉴赏师判断。\n"
    )


def format_overturn_audit(
    overturn_count: int,
) -> str:
    """格式化推翻事件审计报告

    累计推翻事件达阈值时触发，提示作者两位 Agent 的系统性偏差。

    Args:
        overturn_count: 紧计推翻事件数量

    Returns:
        结构化审计报告，提供偏差校正选项
    """
    return (
        f"推翻事件审计\n\n"
        f"  你已累计 {overturn_count} 次推翻鉴赏师+评估师的联合判断。\n"
        f"  这表明两位 Agent 的判断与你的审美存在系统性偏差。\n\n"
        f"如何处理？\n"
        f"  A. 我将总结偏差方向，注入鉴赏师 Prompt 作为'已知偏差校准'\n"
        f"  B. 调整评估师相关维度的权重\n"
        f"  C. 继续积累，下次再处理\n"
    )


# ===================== P1-6 追加:阶段 6 三选升级 =====================


def format_stage6_three_choice(
    item_summaries: List[Dict[str, str]],
    failed_dimensions: List[str],
    consecutive_fail_count: int,
) -> str:
    """格式化阶段 6 整章评估连续失败触发的三选升级对话。

    v2 设计 §1 阶段 6 `<0.8 第 3 次 → 触发对话升级`:
      [a] 撤销某条采纳建议(进 rejected_list)
      [b] 强制通过(标 author_force_pass,推翻事件回流)
      [c] 整章重协商(回 5.5)

    Args:
        item_summaries: preserve_list 摘要,每项 {"item_id": "#N", "summary": "..."}
        failed_dimensions: 持续 <0.8 的评估维度名
        consecutive_fail_count: 连续失败次数(触发时通常为 3)

    Returns:
        可直接呈现给作者的结构化三选文本
    """
    if item_summaries:
        items_text = "\n".join(
            f"  - {it['item_id']}: {it.get('summary', '(无摘要)')}"
            for it in item_summaries
        )
    else:
        items_text = "  (无采纳建议)"

    dims_text = "、".join(failed_dimensions) if failed_dimensions else "(未列出)"

    return (
        f"⚠️ 警告:阶段 6 整章评估连续 {consecutive_fail_count} 次 <0.8\n\n"
        f"  持续不过的维度:{dims_text}\n\n"
        f"  当前采纳建议(preserve_list):\n"
        f"{items_text}\n\n"
        f"请选择处理方式:\n"
        f"  [a] 撤销某条采纳建议(进 rejected_list,回 5.6 再改写)\n"
        f"      用法示例:`a #1`\n"
        f"  [b] 强制通过(标 author_force_pass,推翻事件回流,触发审计)\n"
        f"      用法示例:`b`\n"
        f"  [c] 整章重协商(丢弃本次契约,回阶段 5.5 重来)\n"
        f"      用法示例:`c`\n"
    )


_STAGE6_REVOKE_RE = re.compile(r"^a\s+(#\d+)$", re.IGNORECASE)


def parse_stage6_choice(user_input: str) -> Tuple[str, Optional[str]]:
    """解析作者对 format_stage6_three_choice 的回复。

    语法:
      'a #N'  -> ('revoke', '#N')         撤销第 N 条采纳建议
      'b'     -> ('force_pass', None)     强制通过
      'c'     -> ('renegotiate', None)    整章重协商

    允许前后空白、字母大小写不敏感。其余一律 ValueError。
    """
    if user_input is None:
        raise ValueError("user_input 不得为 None")
    stripped = user_input.strip()
    if not stripped:
        raise ValueError("user_input 不得为空白")

    lower = stripped.lower()
    if lower == "b":
        return ("force_pass", None)
    if lower == "c":
        return ("renegotiate", None)

    # revoke 必须形如 "a #N"
    if lower == "a" or lower.startswith("a ") or lower.startswith("a\t"):
        m = _STAGE6_REVOKE_RE.match(lower)
        if not m:
            raise ValueError(
                f"revoke 格式错误,须 'a #N'(N 为正整数),实得 {user_input!r}"
            )
        return ("revoke", m.group(1))

    raise ValueError(
        f"无法识别的选择 {user_input!r};合法:'a #N' / 'b' / 'c'"
    )
