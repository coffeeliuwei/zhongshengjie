# core/inspiration/stage5_5.py
"""阶段 5.5 三方协商 — 纯函数编排层 (P2-1)

把 SKILL.md §5.5.1~5.5.3 协议翻译成可测试的纯函数:
  build_connoisseur_prompt()         — 构造发给鉴赏师的 prompt 规格
  parse_connoisseur_response()       — 解析鉴赏师 JSON 输出
  suggestions_to_preserve_candidates() — 建议 → PreserveItem 候选列表
  build_creative_contract()          — 作者采纳后生成 CreativeContract

设计文档: docs/superpowers/specs/2026-04-19-inspiration-engine-design-v2.md
实施计划: docs/计划_P2-1_workflow_stage5.5_20260420.md
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from core.inspiration.creative_contract import (
    Aspects,
    CreativeContract,
    ExemptDimension,
    NegotiationTurn,
    PreserveItem,
    RejectedItem,
    Scope,
    generate_contract_id,
)

__all__ = [
    "ConnoisseurParseError",
    "ConnoisseurSuggestion",
    "ConnoisseurResponse",
    "build_connoisseur_prompt",
    "build_stage5_5_prompt_with_real_data",
    "parse_connoisseur_response",
    "suggestions_to_preserve_candidates",
    "build_creative_contract",
]

SHANGHAI_TZ = timezone(timedelta(hours=8))


class ConnoisseurParseError(ValueError):
    """鉴赏师 JSON 解析失败。"""


# ── 数据类 ──────────────────────────────────────────────────────────────────


@dataclass
class ConnoisseurSuggestion:
    """鉴赏师单条建议（对应 SKILL.md suggestions[i]）。"""
    item_id: str
    scope_paragraph_index: int
    scope_char_start: int
    scope_char_end: int
    scope_excerpt: str
    applied_constraint_id: str
    applied_constraint_text: str
    rationale: str
    memory_point_refs: List[str]
    confidence: str  # "high" / "medium" / "low"
    expected_impact: str


@dataclass
class ConnoisseurResponse:
    """鉴赏师完整响应（对应 SKILL.md §5.5.3 输出结构）。"""
    chapter_ref: str
    suggestions: List[ConnoisseurSuggestion]
    overall_judgment: Optional[str]
    abstain_reason: Optional[str]
    menu_gap: Optional[List[Dict[str, Any]]]


# ── 私有渲染辅助 ─────────────────────────────────────────────────────────────


def _render_menu(menu_items: List[Dict[str, Any]]) -> str:
    """将约束菜单列表渲染为 SKILL.md §5.5.2 要求的分类文本块。"""
    by_cat: Dict[str, list] = defaultdict(list)
    for item in menu_items:
        by_cat[item["category"]].append(item)

    lines = []
    for cat in sorted(by_cat):
        items = by_cat[cat]
        lines.append(f"{cat}({len(items)}):")
        for it in items:
            lines.append(f"  - {it['id']}  {it['constraint_text']}")
    return "\n".join(lines) if lines else "  (约束库为空)"


def _render_samples(samples: List[Dict[str, Any]], label: str) -> str:
    """将记忆点列表渲染为审美指纹文本块。"""
    if not samples:
        return f"  (无{label})"
    lines = []
    for s in samples:
        payload = s.get("payload", {})
        mp_id = payload.get("mp_id", str(s.get("id", "?")))
        text = payload.get("segment_text", "")[:50]
        lines.append(f"  - {mp_id}: {text}")
    return "\n".join(lines)


# ── 公开函数 ─────────────────────────────────────────────────────────────────


def build_connoisseur_prompt(
    chapter_text: str,
    chapter_ref: str,
    menu_items: List[Dict[str, Any]],
    positive_samples: List[Dict[str, Any]],
    negative_samples: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """构造发给 novelist-connoisseur SKILL 的 prompt 规格。

    Args:
        chapter_text:     云溪整章润色完成的完整章节文本
        chapter_ref:      章节标识（例 "第3章")
        menu_items:       constraint_library.as_menu() 的返回值
        positive_samples: memory_point_sync.list_recent("+") 的返回值
        negative_samples: memory_point_sync.list_recent("-") 的返回值

    Returns:
        {"skill_name": "novelist-connoisseur", "prompt": str}
    """
    menu_text = _render_menu(menu_items)
    pos_text = _render_samples(positive_samples, "正样本(击中过)")
    neg_text = _render_samples(negative_samples, "负样本(标过乏味)")
    n_menu = len(menu_items)

    prompt = (
        f"## 完整章节文本\n\n{chapter_text}\n\n"
        f"---\n\n"
        f"## 参考资料\n\n"
        f"【反模板约束库菜单({n_menu}条,按类别)】\n{menu_text}\n\n"
        f"【作者审美指纹 - 正样本(击中过)】\n{pos_text}\n\n"
        f"【作者审美指纹 - 负样本(标过乏味)】\n{neg_text}\n\n"
        f"---\n\n"
        f"请按 SKILL.md §5.5.3 格式输出 JSON。"
        f"chapter_ref 填 \"{chapter_ref}\"。"
    )
    return {"skill_name": "novelist-connoisseur", "prompt": prompt}


def parse_connoisseur_response(raw_json: str) -> ConnoisseurResponse:
    """解析鉴赏师返回的 JSON 字符串为 ConnoisseurResponse。

    Raises:
        ConnoisseurParseError: JSON 格式错误或缺少必要字段。
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise ConnoisseurParseError(f"JSON 解析失败: {e}") from e

    if "chapter_ref" not in data:
        raise ConnoisseurParseError("缺少必要字段 chapter_ref")

    suggestions: List[ConnoisseurSuggestion] = []
    for s in data.get("suggestions", []):
        scope = s.get("scope", {})
        suggestions.append(
            ConnoisseurSuggestion(
                item_id=s["item_id"],
                scope_paragraph_index=scope["paragraph_index"],
                scope_char_start=scope["char_start"],
                scope_char_end=scope["char_end"],
                scope_excerpt=scope.get("excerpt", ""),
                applied_constraint_id=s["applied_constraint_id"],
                applied_constraint_text=s["applied_constraint_text"],
                rationale=s["rationale"],
                memory_point_refs=s.get("memory_point_refs", []),
                confidence=s["confidence"],
                expected_impact=s.get("expected_impact", ""),
            )
        )

    return ConnoisseurResponse(
        chapter_ref=data["chapter_ref"],
        suggestions=suggestions,
        overall_judgment=data.get("overall_judgment"),
        abstain_reason=data.get("abstain_reason"),
        menu_gap=data.get("menu_gap"),
    )


def suggestions_to_preserve_candidates(
    suggestions: List[ConnoisseurSuggestion],
) -> List[PreserveItem]:
    """将鉴赏师建议列表转为 PreserveItem 候选（供作者采纳/驳回）。

    每条建议映射规则:
      - scope           → Scope(paragraph_index, char_start, char_end)
      - applied_constraint_text → Aspects.preserve[0]（Q2 约定）
      - applied_constraint_id + text → ExemptDimension（Q4 子项豁免）
    """
    items: List[PreserveItem] = []
    for s in suggestions:
        scope = Scope(
            paragraph_index=s.scope_paragraph_index,
            char_start=s.scope_char_start,
            char_end=s.scope_char_end,
        )
        aspects = Aspects(
            preserve=[s.applied_constraint_text],
            drop=[],
        )
        exempt = ExemptDimension(
            dimension=s.applied_constraint_id,
            sub_items=[s.applied_constraint_text],
        )
        items.append(
            PreserveItem(
                item_id=s.item_id,
                scope=scope,
                applied_constraint_id=s.applied_constraint_id,
                rationale=s.rationale,
                evaluator_risk=[],
                aspects=aspects,
                exempt_dimensions=[exempt],
            )
        )
    return items


def build_creative_contract(
    accepted_items: List[PreserveItem],
    rejected_items: List[RejectedItem],
    chapter_ref: str,
    negotiation_log: Optional[List[NegotiationTurn]] = None,
    skipped_by_author: bool = False,
) -> CreativeContract:
    """根据作者采纳决策生成并校验 CreativeContract。

    Args:
        accepted_items:    作者采纳的 PreserveItem 列表
        rejected_items:    作者驳回的 RejectedItem 列表
        chapter_ref:       章节标识
        negotiation_log:   三方协商日志（可为 None）
        skipped_by_author: True = 作者确认跳过（Q1）

    Returns:
        已通过 validate() 的 CreativeContract 实例

    Raises:
        ContractValidationError: 契约数据不合法
    """
    now = datetime.now(SHANGHAI_TZ).isoformat()
    contract = CreativeContract(
        contract_id=generate_contract_id(),
        chapter_ref=chapter_ref,
        created_at=now,
        negotiation_log=negotiation_log or [],
        preserve_list=accepted_items,
        rejected_list=rejected_items,
        iteration_count=1,
        skipped_by_author=skipped_by_author,
    )
    contract.validate()
    return contract


def build_stage5_5_prompt_with_real_data(
    chapter_text: str,
    chapter_ref: str,
    scene_type: Optional[str] = None,
    positive_top_k: int = 5,
    negative_top_k: int = 5,
) -> Dict[str, Any]:
    """build_connoisseur_prompt 的集成入口：自动从 ConstraintLibrary 和 MemoryPointSync 加载真实数据。

    解决 as_menu() 未接入问题：直接调用此函数即可获得含完整约束菜单的 prompt 规格，
    无需调用方手动获取 menu_items / positive_samples / negative_samples。

    Args:
        chapter_text:    云溪整章润色完成的完整章节文本
        chapter_ref:     章节标识，例 "第3章"
        scene_type:      场景类型过滤（None = 返回全部活跃约束）
        positive_top_k:  正样本检索数量
        negative_top_k:  负样本检索数量

    Returns:
        {"skill_name": "novelist-connoisseur", "prompt": str}
        与 build_connoisseur_prompt() 返回格式完全一致。
    """
    from core.inspiration.constraint_library import ConstraintLibrary
    from core.inspiration.memory_point_sync import MemoryPointSync

    menu_items = ConstraintLibrary().as_menu(scene_type=scene_type)

    try:
        sync = MemoryPointSync()
        positive_samples = sync.list_recent("+", top_k=positive_top_k)
        negative_samples = sync.list_recent("-", top_k=negative_top_k)
    except Exception:
        positive_samples = []
        negative_samples = []

    return build_connoisseur_prompt(
        chapter_text=chapter_text,
        chapter_ref=chapter_ref,
        menu_items=menu_items,
        positive_samples=positive_samples,
        negative_samples=negative_samples,
    )