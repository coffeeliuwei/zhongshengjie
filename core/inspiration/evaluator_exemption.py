# core/inspiration/evaluator_exemption.py
"""评估师豁免数据层(Q4 子项粒度)。

把 CreativeContract.preserve_list 中的 exempt_dimensions 展成段落级查询索引:
    { paragraph_index: { dimension: { sub_item1, sub_item2, ... } } }

仅做纯数据转换,不涉及评估师 prompt / LLM / 磁盘 I/O。
Q4 硬约束:sub_items 非空;空值一律 ExemptionBuildError(禁止整维度豁免)。

设计文档:docs/superpowers/specs/2026-04-19-inspiration-engine-design-v2.md §1 阶段 6
实施计划:docs/计划_P1-7_evaluator_exemption_20260420.md
"""
from __future__ import annotations

from typing import Dict, Set

from core.inspiration.creative_contract import CreativeContract

__all__ = [
    "ExemptionMap",
    "ExemptionBuildError",
    "build_exemption_map",
    "is_exempt",
    "format_exemption_report",
]

# 类型别名:{paragraph_index: {dimension: {sub_items}}}
ExemptionMap = Dict[int, Dict[str, Set[str]]]


class ExemptionBuildError(ValueError):
    """构建豁免索引时发现不合法数据(通常是 Q4 违反)。"""


def build_exemption_map(contract: CreativeContract) -> ExemptionMap:
    """从契约抽取段落级豁免索引。"""
    if not isinstance(contract, CreativeContract):
        raise TypeError(
            f"contract 必须是 CreativeContract,实得 {type(contract).__name__}"
        )

    result: ExemptionMap = {}
    for item in contract.preserve_list:
        para = item.scope.paragraph_index
        for ed in item.exempt_dimensions:
            if not ed.sub_items:
                raise ExemptionBuildError(
                    f"item {item.item_id} 维度 {ed.dimension!r} 的 sub_items 为空 — "
                    "Q4 禁止整维度豁免"
                )
            bucket = result.setdefault(para, {}).setdefault(ed.dimension, set())
            for sub in ed.sub_items:
                if not sub or not sub.strip():
                    raise ExemptionBuildError(
                        f"item {item.item_id} 维度 {ed.dimension!r} 含空白 sub_item"
                    )
                bucket.add(sub)
    return result


def is_exempt(
    exemption_map: ExemptionMap,
    paragraph_index: int,
    dimension: str,
    sub_item: str,
) -> bool:
    """查询 (段落, 维度, 子项) 是否被豁免。

    任一 key 不存在 -> False(未豁免,评估师照常打分)。
    """
    dims = exemption_map.get(paragraph_index)
    if not dims:
        return False
    subs = dims.get(dimension)
    if not subs:
        return False
    return sub_item in subs


def format_exemption_report(exemption_map: ExemptionMap) -> str:
    """生成可读的中文豁免报告。段落升序,维度按名称升序,子项按名称升序。"""
    if not exemption_map:
        return "(本章无豁免)"

    lines = ["本章评估师豁免清单:"]
    for para in sorted(exemption_map.keys()):
        lines.append(f"  段落 {para}:")
        dims = exemption_map[para]
        for dim in sorted(dims.keys()):
            subs = sorted(dims[dim])
            lines.append(f"    - {dim}:{', '.join(subs)}")
    return "\n".join(lines)