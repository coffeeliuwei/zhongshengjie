# core/inspiration/appraisal_agent.py
"""鉴赏 Agent 调用层

负责：
1. 根据记忆点数量选择 prompt 模板（冷启动/成长期/成熟期）
2. 构造调用规格（Claude 对话层据此调用 novelist-connoisseur）
3. 解析 Skill 返回的 JSON 为 AppraisalResult

设计：附录 A 鉴赏师 SKILL.md 与本模块互相对照。

设计文档：docs/superpowers/specs/2026-04-14-inspiration-engine-design.md §4
"""

import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


SKILL_NAME = "novelist-connoisseur"


@dataclass
class AppraisalResult:
    selected_id: Optional[str]  # None 表示 "无一可选"
    ignition_point: Optional[str]
    reason_fragment: Optional[str]
    confidence: str  # "high"/"medium"/"low"
    common_flaw: Optional[str] = None
    raw: Optional[str] = None


class AppraisalParseError(Exception):
    pass


def build_appraisal_spec(
    candidates: List[Dict[str, Any]],
    scene_context: Dict[str, Any],
    memory_point_count: int,
    retrieved_references: Optional[List[Dict[str, Any]]] = None,
    structural_summary: Optional[str] = None,
    cold_threshold: int = 50,
    growing_threshold: int = 300,
) -> Dict[str, Any]:
    """构造鉴赏师调用规格

    Returns:
        {"skill_name": str, "prompt": str, "phase": "cold"|"growing"|"mature"}
    """
    if memory_point_count < cold_threshold:
        phase = "cold"
        prompt = _build_cold_prompt(candidates, scene_context)
    elif memory_point_count < growing_threshold:
        phase = "growing"
        prompt = _build_growing_prompt(
            candidates, scene_context, retrieved_references or []
        )
    else:
        phase = "mature"
        prompt = _build_mature_prompt(
            candidates,
            scene_context,
            retrieved_references or [],
            structural_summary or "",
        )

    return {
        "skill_name": SKILL_NAME,
        "prompt": prompt,
        "phase": phase,
    }


def _candidates_block(candidates: List[Dict[str, Any]]) -> str:
    lines = ["【候选文本】"]
    for c in candidates:
        text = c.get("text", "[未生成]")
        constraint = c.get("used_constraint_id") or "BASELINE"
        lines.append(f"\n【{c['id']}】（约束: {constraint}）")
        lines.append(text)
    return "\n".join(lines)


def _scene_block(scene_context: Dict[str, Any]) -> str:
    lines = ["【场景上下文】"]
    for k, v in scene_context.items():
        lines.append(f"{k}: {v}")
    return "\n".join(lines)


def _build_cold_prompt(candidates, scene_context) -> str:
    return f"""{_scene_block(scene_context)}

{_candidates_block(candidates)}

【你的任务】
读完这 {len(candidates)} 段候选，告诉我哪一段是活的。

不要打分，不要列维度，不要写评审意见。
只指出哪一段击中了你，是在哪一句/哪个字上击中的，用一句话说那个瞬间的感觉。

如果三段都是正确但平庸，返回 selected_id="none" 并说出共同问题。

按 SKILL.md 规定的 JSON 格式输出。"""


def _build_growing_prompt(candidates, scene_context, refs) -> str:
    refs_block = ["【你过去被击中的参照段落】"]
    for r in refs:
        p = r.get("payload", {})
        polarity = p.get("polarity", "?")
        intensity = p.get("intensity", "?")
        note = p.get("note", "")
        refs_block.append(f"\n[{polarity}{intensity}] {p.get('segment_text', '')}")
        if note:
            refs_block.append(f"  作者备注：{note}")
    return f"""{_scene_block(scene_context)}

{_candidates_block(candidates)}

{chr(10).join(refs_block)}

【你的任务】
对比 {len(candidates)} 个候选与上述参照段落。
正向参照（+1/+2/+3）是作者过去被击中的结构感，负向参照（-1/-2/-3）是作者觉得乏味/出戏的结构。

哪个候选最接近正向参照的结构感（不是内容，是结构）？
哪个候选要警惕——结构上像负向参照？

按 SKILL.md 规定的 JSON 格式输出。必须指出 ignition_point 到具体字句。"""


def _build_mature_prompt(candidates, scene_context, refs, structural_summary) -> str:
    return f"""{_scene_block(scene_context)}

【作者的审美指纹（基于历史反馈聚类）】
{structural_summary}

{_candidates_block(candidates)}

【你过去被击中的参照（top {len(refs)}）】
{chr(10).join(_format_ref(r) for r in refs)}

【你的任务】
优先按上述结构偏好筛选。两个候选都符合时，靠你的直觉选最活的。

按 SKILL.md 规定的 JSON 格式输出。"""


def _format_ref(r: Dict[str, Any]) -> str:
    p = r.get("payload", {})
    return f"[{p.get('polarity', '?')}{p.get('intensity', '?')}] {p.get('segment_text', '')}"


def parse_appraisal_response(raw: str) -> AppraisalResult:
    """解析鉴赏师 Skill 输出"""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise AppraisalParseError(f"Invalid JSON: {e}") from e

    if not isinstance(data, dict):
        raise AppraisalParseError("Response must be a JSON object")

    selected = data.get("selected_id")
    if selected == "none":
        if not data.get("common_flaw"):
            raise AppraisalParseError("selected_id='none' must include common_flaw")
        return AppraisalResult(
            selected_id=None,
            ignition_point=None,
            reason_fragment=None,
            confidence=data.get("confidence", "low"),
            common_flaw=data["common_flaw"],
            raw=raw,
        )

    if not selected:
        raise AppraisalParseError("Missing selected_id")
    if not data.get("ignition_point"):
        raise AppraisalParseError("Missing ignition_point for selected variant")

    return AppraisalResult(
        selected_id=selected,
        ignition_point=data["ignition_point"],
        reason_fragment=data.get("reason_fragment"),
        confidence=data.get("confidence", "medium"),
        raw=raw,
    )
