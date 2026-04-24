"""派单器(Dispatcher)— v2 阶段 5.6 核心纯函数层。

输入:一份已校验的 CreativeContract
输出:List[DispatchPackage],每个包含某一位写手需要承接的全部 item_ids、
      任务列表、对应的 PreserveItem 引用、以及渲染好的
      【创意契约约束】prompt 增量(v2 §5 模板)。

dispatcher 不做 I/O、不调 LLM、不查 Qdrant。
真正的写手调用由 workflow(P2-2)接收本层输出后实施。

设计文档:docs/superpowers/specs/2026-04-19-inspiration-engine-design-v2.md §1 阶段 5.6 + §5
实施计划:docs/计划_P1-2_dispatcher_20260419.md

【关键决策贯彻】
- Q1 skipped_by_author=True → dispatch 返回空列表
- Q2 嵌套 aspects → prompt 分块渲染【必须保留】与【可放开】;drop 为空时降级为"仅优化字词/语流"
- Q3 不回流权重 → 本模块与权重无关,自然贯彻
- Q4 豁免按子项 → prompt 中透传 exempt_dimensions 提示,但不改变豁免决策(由 P1-7 评估师执行)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from core.inspiration.creative_contract import (
    CreativeContract,
    ContractValidationError,
    PreserveItem,
    WriterAssignment,
)

__all__ = [
    "DispatchPackage",
    "dispatch",
    "DispatcherError",
]


class DispatcherError(ContractValidationError):
    """派单器特有的错误(复用 ContractValidationError 的 ValueError 血统)。

    目前用于:dispatch 在入口发现契约字段被调用方伪造绕过 validate 时抛出。
    """


# ===================== DispatchPackage =====================


@dataclass
class DispatchPackage:
    """某位写手在本次契约中的派单包。

    一个 DispatchPackage 对应 一位写手 × 本契约的 1..N 条 writer_assignments。
    workflow(P2-2)消费本包时:
      - 用 writer 作为目标 skill 名
      - 把 prompt_increment 追加到该写手的标准 prompt 尾部
      - tasks[i] / preserve_items[i] / item_ids[i] 三列表并行,表示第 i 条任务
    """

    contract_id: str
    writer: str                               # novelist-xxx 全名
    item_ids: List[str]                       # 顺序 = WriterAssignment 在契约中的出现顺序
    tasks: List[str]                          # 与 item_ids 并行
    preserve_items: List[PreserveItem]        # 与 item_ids 并行,同 item_id
    prompt_increment: str                     # 渲染好的【创意契约约束】整块 Chinese prompt

    def validate(self) -> None:
        if not self.contract_id or not self.contract_id.strip():
            raise DispatcherError("DispatchPackage.contract_id 必须非空")
        if not self.writer or not self.writer.strip():
            raise DispatcherError("DispatchPackage.writer 必须非空")
        if not self.item_ids:
            raise DispatcherError(
                "DispatchPackage.item_ids 必须非空(无任务的写手不应产出派单包)"
            )
        if len(self.item_ids) != len(self.tasks):
            raise DispatcherError(
                f"DispatchPackage.item_ids 与 tasks 长度必须一致,"
                f"实得 {len(self.item_ids)} vs {len(self.tasks)}"
            )
        if len(self.item_ids) != len(self.preserve_items):
            raise DispatcherError(
                f"DispatchPackage.preserve_items 长度必须等于 item_ids,"
                f"实得 {len(self.preserve_items)} vs {len(self.item_ids)}"
            )
        for i, (iid, pi) in enumerate(zip(self.item_ids, self.preserve_items)):
            if pi.item_id != iid:
                raise DispatcherError(
                    f"DispatchPackage.preserve_items[{i}].item_id "
                    f"({pi.item_id!r}) 不等于 item_ids[{i}] ({iid!r})"
                )
        if not self.prompt_increment or not self.prompt_increment.strip():
            raise DispatcherError("DispatchPackage.prompt_increment 必须非空")


# ===================== dispatch 顶层 =====================


def dispatch(contract: CreativeContract) -> List[DispatchPackage]:
    """把一份已校验契约转成每位写手的派单包列表。

    规则:
      - contract.skipped_by_author=True → 返回 [](Q1)
      - contract.writer_assignments 为空 → 返回 []
      - 正常路径:按 writer 分组,每组渲染 prompt 增量,产出 DispatchPackage
    """
    # 内部 re-validate,不信任调用方
    contract.validate()

    if contract.skipped_by_author:
        return []
    if not contract.writer_assignments:
        return []

    # item_id → PreserveItem 反查表
    items_by_id: Dict[str, PreserveItem] = {
        p.item_id: p for p in contract.preserve_list
    }

    groups = _group_assignments_by_writer(contract.writer_assignments)

    packages: List[DispatchPackage] = []
    for writer, assignments in groups.items():
        item_ids = [wa.item_id for wa in assignments]
        tasks = [wa.task for wa in assignments]
        preserve_items = [items_by_id[iid] for iid in item_ids]
        pairs = list(zip(preserve_items, tasks))
        prompt = _build_prompt_increment(
            contract_id=contract.contract_id,
            writer=writer,
            pairs=pairs,
        )
        pkg = DispatchPackage(
            contract_id=contract.contract_id,
            writer=writer,
            item_ids=item_ids,
            tasks=tasks,
            preserve_items=preserve_items,
            prompt_increment=prompt,
        )
        pkg.validate()
        packages.append(pkg)
    return packages


# ===================== prompt 模板 =====================

_BLOCK_SEPARATOR = "───────────── 项目 {item_id} ─────────────"
_BLOCK_CLOSER = "─────────────────────────────────────"


def _format_preserve_block(*, preserve_item: PreserveItem, task: str) -> str:
    """为单条 PreserveItem 渲染 v2 §5 模板中"项目"块(Chinese,Q2 嵌套)。"""
    p = preserve_item
    lines: List[str] = []
    lines.append(_BLOCK_SEPARATOR.format(item_id=p.item_id))
    lines.append(
        f"区域:第 {p.scope.paragraph_index} 段,"
        f"字符 [{p.scope.char_start}, {p.scope.char_end})"
    )
    if p.applied_constraint_id:
        lines.append(f"应用约束:{p.applied_constraint_id}")
    else:
        lines.append("应用约束:无(非约束库触发)")
    lines.append(f"采纳理由:{p.rationale}")

    # evaluator_risk(可选)
    if p.evaluator_risk:
        lines.append("评估师风险提示:")
        for risk in p.evaluator_risk:
            lines.append(f"  - {risk}")

    # Q2 嵌套 aspects
    lines.append("【必须保留】(preserve):")
    for s in p.aspects.preserve:
        lines.append(f"  - {s}")
    if p.aspects.drop:
        lines.append("【可放开】(drop,可在此范围内优化):")
        for s in p.aspects.drop:
            lines.append(f"  - {s}")
    else:
        lines.append("【可放开】:(无)— 仅可优化字词/语流,不改任何子面")

    # Q4 豁免透传(可选)
    if p.exempt_dimensions:
        lines.append("涉及豁免维度(评估师将跳过以下子项打分):")
        for ed in p.exempt_dimensions:
            subs = " / ".join(ed.sub_items)
            lines.append(f"  - {ed.dimension}:{subs}")

    lines.append(f"任务指令:{task}")
    lines.append(_BLOCK_CLOSER)
    return "\n".join(lines)


# ===================== _build_prompt_increment =====================

_PROMPT_HEADER = (
    "【创意契约约束】\n"
    "本次重写涉及创意契约 ID:{contract_id}\n"
    "承接写手:{writer}\n"
    "你负责以下 {n} 条采纳项的重写,每条均有标注区域与约束细则,"
    "**区域外**保持原文不动:"
)

_PROMPT_FOOTER = (
    "【重写守则】\n"
    "- 你只能在每个'项目'块标注的区域内修改,区域外保持原文\n"
    "- 标注为【必须保留】的子面禁止改动(否则触发评估师 MUST_PRESERVE 检查)\n"
    "- 标注为【可放开】的子面可根据'任务指令'重写\n"
    "- 若某项【可放开】为空,仅可优化字词/语流,不改核心手法\n"
    "- '涉及豁免维度'仅为知情提示,写手不得据此扩大修改范围"
)


def _build_prompt_increment(
    *,
    contract_id: str,
    writer: str,
    pairs: List,  # List[Tuple[PreserveItem, str]]
) -> str:
    """拼接整块派单 prompt:header + 多个项目块 + footer。"""
    if not pairs:
        raise DispatcherError(
            "_build_prompt_increment.pairs 必须非空(无任务的写手不应进入派单流程)"
        )
    parts: List[str] = []
    parts.append(
        _PROMPT_HEADER.format(
            contract_id=contract_id, writer=writer, n=len(pairs)
        )
    )
    for item, task in pairs:
        parts.append(_format_preserve_block(preserve_item=item, task=task))
    parts.append(_PROMPT_FOOTER)
    return "\n\n".join(parts)


# ===================== 分组辅助 =====================


def _group_assignments_by_writer(
    assignments: List[WriterAssignment],
) -> Dict[str, List[WriterAssignment]]:
    """按 writer 分组并保持原列表中的相对顺序。"""
    groups: Dict[str, List[WriterAssignment]] = {}
    for wa in assignments:
        groups.setdefault(wa.writer, []).append(wa)
    return groups