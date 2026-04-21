"""创意契约(Creative Contract)数据模型。

由鉴赏师 + 评估师 + 作者三方协商产出的本章创意锁定契约。
阶段 5.5 生成 → 阶段 5.6 派单写手使用 → 阶段 6 评估师按 exempt_dimensions 豁免 →
阶段 7 作者可撤销某条(进 rejected_list)或强制通过。

设计文档:docs/superpowers/specs/2026-04-19-inspiration-engine-design-v2.md §4
实施计划:docs/计划_P1-1_creative_contract_20260419.md

【关键决策贯彻】
- Q1 鉴赏师 0 条建议时由作者决定跳过:见 `CreativeContract.skipped_by_author`
- Q2 preserve_list 支持嵌套 aspects:见 `PreserveItem.aspects`
- Q3 author_force_pass 不回流权重:本模块**不持有**权重字段,归档即止
- Q4 评估师豁免按子项:见 `ExemptDimension.sub_items`(非空)
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import List, Literal, Optional
import json
import re
import secrets

__all__ = [
    "Scope",
    "Aspects",
    "ExemptDimension",
    "PreserveItem",
    "RejectedItem",
    "NegotiationTurn",
    "WriterAssignment",
    "CreativeContract",
    "generate_contract_id",
    "ContractValidationError",
]

SHANGHAI_TZ = timezone(timedelta(hours=8))
_CONTRACT_ID_PATTERN = re.compile(r"^cc_\d{8}_[0-9a-f]{6}$")


class ContractValidationError(ValueError):
    """契约数据校验失败。"""


# ===================== Scope =====================

@dataclass
class Scope:
    """段落内字符偏移区间 [char_start, char_end)。"""
    paragraph_index: int
    char_start: int
    char_end: int

    def validate(self) -> None:
        if self.paragraph_index < 0:
            raise ContractValidationError(
                f"paragraph_index 必须 >= 0,实得 {self.paragraph_index}"
            )
        if self.char_start < 0:
            raise ContractValidationError(
                f"char_start 必须 >= 0,实得 {self.char_start}"
            )
        if self.char_start >= self.char_end:
            raise ContractValidationError(
                f"char_start ({self.char_start}) 必须 < char_end ({self.char_end})"
            )


# ===================== Aspects (Q2 嵌套核心) =====================

@dataclass
class Aspects:
    """preserve_list[i] 内部的细粒度面切分(Q2 嵌套)。

    preserve: 必须锁定的子面(例:"情绪强度", "心理动机")
    drop:     可放开给写手重写的子面(例:"具体台词", "肢体表现")
    """
    preserve: List[str]
    drop: List[str] = field(default_factory=list)

    def validate(self) -> None:
        if not self.preserve:
            raise ContractValidationError(
                "Aspects.preserve 必须非空(否则失去契约意义,整体弃用请用 rejected_list)"
            )
        for s in self.preserve + self.drop:
            if not s or not s.strip():
                raise ContractValidationError(
                    f"Aspects 不允许空字符串或纯空白项,实得 {s!r}"
                )
        overlap = set(self.preserve) & set(self.drop)
        if overlap:
            raise ContractValidationError(
                f"Aspects.preserve 与 drop 不得重叠,冲突项:{sorted(overlap)}"
            )


# ===================== ExemptDimension (Q4 子项豁免) =====================

@dataclass
class ExemptDimension:
    """评估师豁免项(Q4 子项粒度)。

    sub_items 必须非空 — 整维度豁免已证明会导致整体偏离,禁止。
    如需豁免"某维度的所有子项",请显式列出全部子项名称。
    """
    dimension: str
    sub_items: List[str]

    def validate(self) -> None:
        if not self.dimension or not self.dimension.strip():
            raise ContractValidationError("ExemptDimension.dimension 必须非空")
        if not self.sub_items:
            raise ContractValidationError(
                f"ExemptDimension.sub_items 必须非空(维度 {self.dimension!r})— "
                "Q4 禁止整维度豁免,请显式列出子项"
            )
        for s in self.sub_items:
            if not s or not s.strip():
                raise ContractValidationError(
                    f"ExemptDimension.sub_items 不允许空字符串(维度 {self.dimension!r})"
                )


# ===================== PreserveItem =====================

_ITEM_ID_PATTERN = re.compile(r"^#\d+$")


@dataclass
class PreserveItem:
    """preserve_list 中的一条:采纳的创意手法,带嵌套 aspects + 子项豁免。"""
    item_id: str
    scope: Scope
    applied_constraint_id: Optional[str]
    rationale: str
    evaluator_risk: List[str]
    aspects: Aspects
    exempt_dimensions: List[ExemptDimension] = field(default_factory=list)

    def validate(self) -> None:
        if not _ITEM_ID_PATTERN.match(self.item_id or ""):
            raise ContractValidationError(
                f"item_id 必须匹配 /^#\\d+$/,实得 {self.item_id!r}"
            )
        if not self.rationale or not self.rationale.strip():
            raise ContractValidationError("PreserveItem.rationale 必须非空")
        self.scope.validate()
        self.aspects.validate()
        for ed in self.exempt_dimensions:
            ed.validate()


# ===================== RejectedItem =====================

@dataclass
class RejectedItem:
    """被驳回的鉴赏师建议。"""
    item_id: str
    reason: str

    def validate(self) -> None:
        if not _ITEM_ID_PATTERN.match(self.item_id or ""):
            raise ContractValidationError(
                f"RejectedItem.item_id 必须匹配 /^#\\d+$/,实得 {self.item_id!r}"
            )
        if not self.reason or not self.reason.strip():
            raise ContractValidationError("RejectedItem.reason 必须非空")


# ===================== NegotiationTurn =====================

_VALID_SPEAKERS = ("connoisseur", "evaluator", "author")


@dataclass
class NegotiationTurn:
    """三方协商的一轮发言。"""
    speaker: str  # Literal["connoisseur", "evaluator", "author"]
    msg: str
    timestamp: str  # ISO 8601

    def validate(self) -> None:
        if self.speaker not in _VALID_SPEAKERS:
            raise ContractValidationError(
                f"NegotiationTurn.speaker 必须在 {_VALID_SPEAKERS},实得 {self.speaker!r}"
            )
        if not self.msg or not self.msg.strip():
            raise ContractValidationError("NegotiationTurn.msg 必须非空")
        if not self.timestamp or not self.timestamp.strip():
            raise ContractValidationError("NegotiationTurn.timestamp 必须非空")


# ===================== WriterAssignment =====================

_VALID_WRITERS = (
    "novelist-jianchen",
    "novelist-canglan",
    "novelist-moyan",
    "novelist-xuanyi",
    "novelist-yunxi",
)


@dataclass
class WriterAssignment:
    """派单:把某 preserve_item 指派给某写手。"""
    item_id: str
    writer: str
    task: str

    def validate(self) -> None:
        if not _ITEM_ID_PATTERN.match(self.item_id or ""):
            raise ContractValidationError(
                f"WriterAssignment.item_id 必须匹配 /^#\\d+$/,实得 {self.item_id!r}"
            )
        if self.writer not in _VALID_WRITERS:
            raise ContractValidationError(
                f"WriterAssignment.writer 必须在 {_VALID_WRITERS},实得 {self.writer!r}"
            )
        if not self.task or not self.task.strip():
            raise ContractValidationError("WriterAssignment.task 必须非空")


# ===================== ID 生成器 =====================

def generate_contract_id() -> str:
    """生成 contract_id,格式 cc_YYYYMMDD_<6hex>,日期用 Shanghai 时区。"""
    date = datetime.now(SHANGHAI_TZ).strftime("%Y%m%d")
    suffix = secrets.token_hex(3)  # 3 bytes = 6 hex chars
    return f"cc_{date}_{suffix}"


# ===================== CreativeContract 顶层 =====================

@dataclass
class CreativeContract:
    """本章创意契约:阶段 5.5 产出,阶段 5.6 / 6 / 7 消费。"""
    contract_id: str
    chapter_ref: str
    created_at: str  # ISO 8601 (Shanghai tz)
    negotiation_log: List[NegotiationTurn] = field(default_factory=list)
    preserve_list: List[PreserveItem] = field(default_factory=list)
    rejected_list: List[RejectedItem] = field(default_factory=list)
    writer_assignments: List[WriterAssignment] = field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 3
    skipped_by_author: bool = False  # Q1:鉴赏师 0 条 + 作者确认跳过

    def validate(self) -> None:
        """跨字段 + 级联校验。"""
        if not _CONTRACT_ID_PATTERN.match(self.contract_id or ""):
            raise ContractValidationError(
                f"contract_id 必须匹配 /^cc_\\d{{8}}_[0-9a-f]{{6}}$/,实得 {self.contract_id!r}"
            )
        if not self.chapter_ref or not self.chapter_ref.strip():
            raise ContractValidationError("chapter_ref 必须非空")
        if not self.created_at or not self.created_at.strip():
            raise ContractValidationError("created_at 必须非空")
        if self.max_iterations <= 0:
            raise ContractValidationError(
                f"max_iterations 必须 > 0,实得 {self.max_iterations}"
            )
        if self.iteration_count < 0 or self.iteration_count > self.max_iterations:
            raise ContractValidationError(
                f"iteration_count ({self.iteration_count}) 必须在 "
                f"[0, max_iterations={self.max_iterations}] 区间"
            )

        # 级联校验
        for t in self.negotiation_log:
            t.validate()
        for p in self.preserve_list:
            p.validate()
        for r in self.rejected_list:
            r.validate()
        for w in self.writer_assignments:
            w.validate()

        # item_id 唯一性 + 不与 rejected 重叠
        preserve_ids = [p.item_id for p in self.preserve_list]
        if len(preserve_ids) != len(set(preserve_ids)):
            dup = [i for i in set(preserve_ids) if preserve_ids.count(i) > 1]
            raise ContractValidationError(f"preserve_list 中 item_id 重复:{dup}")
        rejected_ids = {r.item_id for r in self.rejected_list}
        overlap = set(preserve_ids) & rejected_ids
        if overlap:
            raise ContractValidationError(
                f"item_id 同时出现在 preserve 与 rejected:{sorted(overlap)}"
            )

        # writer_assignments 必须引用 preserve_list 中的 item_id
        preserve_id_set = set(preserve_ids)
        for w in self.writer_assignments:
            if w.item_id not in preserve_id_set:
                raise ContractValidationError(
                    f"writer_assignments 引用了 preserve_list 中不存在的 "
                    f"item_id {w.item_id!r}"
                )

        # Q1:skipped_by_author=True 要求三列表全空
        if self.skipped_by_author and (
            self.preserve_list or self.rejected_list or self.writer_assignments
        ):
            raise ContractValidationError(
                "skipped_by_author=True 要求 preserve_list / rejected_list / "
                "writer_assignments 三个列表全空(Q1:鉴赏师 0 条建议 + 作者确认跳过)"
            )

    def to_json(self, *, indent: Optional[int] = None) -> str:
        """序列化为 JSON 字符串,中文不转义。"""
        return json.dumps(asdict(self), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, s: str) -> "CreativeContract":
        """从 JSON 字符串反序列化并校验。"""
        try:
            raw = json.loads(s)
        except json.JSONDecodeError as e:
            raise ContractValidationError(f"输入不是合法 JSON: {e}") from e
        if not isinstance(raw, dict):
            raise ContractValidationError("JSON 顶层必须是对象")
        try:
            obj = cls(
                contract_id=raw["contract_id"],
                chapter_ref=raw["chapter_ref"],
                created_at=raw["created_at"],
                negotiation_log=[
                    NegotiationTurn(**t) for t in raw.get("negotiation_log", [])
                ],
                preserve_list=[
                    PreserveItem(
                        item_id=p["item_id"],
                        scope=Scope(**p["scope"]),
                        applied_constraint_id=p.get("applied_constraint_id"),
                        rationale=p["rationale"],
                        evaluator_risk=list(p.get("evaluator_risk", [])),
                        aspects=Aspects(
                            preserve=list(p["aspects"]["preserve"]),
                            drop=list(p["aspects"].get("drop", [])),
                        ),
                        exempt_dimensions=[
                            ExemptDimension(
                                dimension=ed["dimension"],
                                sub_items=list(ed["sub_items"]),
                            )
                            for ed in p.get("exempt_dimensions", [])
                        ],
                    )
                    for p in raw.get("preserve_list", [])
                ],
                rejected_list=[
                    RejectedItem(**r) for r in raw.get("rejected_list", [])
                ],
                writer_assignments=[
                    WriterAssignment(**w) for w in raw.get("writer_assignments", [])
                ],
                iteration_count=raw.get("iteration_count", 0),
                max_iterations=raw.get("max_iterations", 3),
                skipped_by_author=raw.get("skipped_by_author", False),
            )
        except KeyError as e:
            raise ContractValidationError(f"JSON 缺必需字段:{e}") from e
        except TypeError as e:
            raise ContractValidationError(f"JSON 字段类型不匹配:{e}") from e
        obj.validate()
        return obj