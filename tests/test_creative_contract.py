"""core/inspiration/creative_contract.py 的单元测试。

覆盖:
- Scope / Aspects / ExemptDimension / PreserveItem / RejectedItem /
  NegotiationTurn / WriterAssignment / CreativeContract 各 dataclass
- 校验:字段非空 / 子项非空 / preserve 与 drop 不重叠 / iteration <= max_iterations /
  writer_assignments 引用的 item_id 必须在 preserve_list / contract_id 正则
- 序列化:to_json / from_json 往返
- ID 生成器:格式 cc_YYYYMMDD_<6hex>,Shanghai 日期

依据计划:docs/计划_P1-1_creative_contract_20260419.md
"""
from __future__ import annotations

import json
import re
import pytest

from core.inspiration.creative_contract import (
    Scope,
    Aspects,
    ExemptDimension,
    PreserveItem,
    RejectedItem,
    NegotiationTurn,
    WriterAssignment,
    CreativeContract,
    generate_contract_id,
    ContractValidationError,
)


def test_module_importable():
    """冒烟:模块可导入,所有 __all__ 符号已定义。"""
    from core.inspiration import creative_contract as cc
    for name in cc.__all__:
        assert hasattr(cc, name), f"{name} 不在模块中"


# ===================== Scope =====================

def test_scope_basic():
    s = Scope(paragraph_index=3, char_start=234, char_end=567)
    assert s.paragraph_index == 3
    assert s.char_start == 234
    assert s.char_end == 567


def test_scope_rejects_negative_paragraph():
    with pytest.raises(ContractValidationError, match="paragraph_index"):
        Scope(paragraph_index=-1, char_start=0, char_end=10).validate()


def test_scope_rejects_char_start_ge_end():
    with pytest.raises(ContractValidationError, match="char_start"):
        Scope(paragraph_index=0, char_start=10, char_end=10).validate()
    with pytest.raises(ContractValidationError, match="char_start"):
        Scope(paragraph_index=0, char_start=20, char_end=10).validate()


def test_scope_rejects_negative_char_start():
    with pytest.raises(ContractValidationError, match="char_start"):
        Scope(paragraph_index=0, char_start=-1, char_end=5).validate()


# ===================== Aspects (Q2 嵌套核心) =====================

def test_aspects_basic():
    a = Aspects(preserve=["情绪强度", "心理动机"], drop=["具体台词"])
    assert a.preserve == ["情绪强度", "心理动机"]
    assert a.drop == ["具体台词"]


def test_aspects_preserve_non_empty_required():
    with pytest.raises(ContractValidationError, match="preserve.*非空"):
        Aspects(preserve=[], drop=["台词"]).validate()


def test_aspects_drop_may_be_empty():
    Aspects(preserve=["情绪"], drop=[]).validate()


def test_aspects_no_overlap():
    with pytest.raises(ContractValidationError, match="重叠"):
        Aspects(preserve=["情绪", "台词"], drop=["台词"]).validate()


def test_aspects_strips_blank_strings():
    with pytest.raises(ContractValidationError, match="空字符串"):
        Aspects(preserve=["情绪", ""], drop=[]).validate()
    with pytest.raises(ContractValidationError, match="空字符串"):
        Aspects(preserve=["情绪"], drop=["   "]).validate()


# ===================== ExemptDimension (Q4 子项豁免) =====================

def test_exempt_dimension_basic():
    e = ExemptDimension(dimension="视角连贯性", sub_items=["主角一致性"])
    assert e.dimension == "视角连贯性"
    assert e.sub_items == ["主角一致性"]


def test_exempt_dimension_sub_items_non_empty_required():
    with pytest.raises(ContractValidationError, match="sub_items.*非空"):
        ExemptDimension(dimension="视角连贯性", sub_items=[]).validate()


def test_exempt_dimension_rejects_blank_name():
    with pytest.raises(ContractValidationError, match="dimension.*非空"):
        ExemptDimension(dimension="", sub_items=["X"]).validate()
    with pytest.raises(ContractValidationError, match="dimension.*非空"):
        ExemptDimension(dimension="   ", sub_items=["X"]).validate()


def test_exempt_dimension_rejects_blank_sub_item():
    with pytest.raises(ContractValidationError, match="sub_items"):
        ExemptDimension(dimension="D", sub_items=["X", ""]).validate()


# ===================== PreserveItem =====================

def _make_scope():
    return Scope(paragraph_index=3, char_start=234, char_end=567)

def _make_aspects():
    return Aspects(preserve=["情绪强度", "心理动机"], drop=["具体台词"])

def _make_preserve_item(**overrides):
    base = dict(
        item_id="#1",
        scope=_make_scope(),
        applied_constraint_id="ANTI_001",
        rationale="鉴赏师 + 作者共识",
        evaluator_risk=["主角视角连贯性 -0.1"],
        aspects=_make_aspects(),
        exempt_dimensions=[ExemptDimension(dimension="视角连贯性", sub_items=["主角一致性"])],
    )
    base.update(overrides)
    return PreserveItem(**base)


def test_preserve_item_basic():
    p = _make_preserve_item()
    p.validate()
    assert p.item_id == "#1"


def test_preserve_item_id_format():
    _make_preserve_item(item_id="#1").validate()
    _make_preserve_item(item_id="#42").validate()
    with pytest.raises(ContractValidationError, match="item_id"):
        _make_preserve_item(item_id="1").validate()
    with pytest.raises(ContractValidationError, match="item_id"):
        _make_preserve_item(item_id="#abc").validate()


def test_preserve_item_rationale_non_empty():
    with pytest.raises(ContractValidationError, match="rationale"):
        _make_preserve_item(rationale="").validate()


def test_preserve_item_propagates_sub_validation():
    with pytest.raises(ContractValidationError, match="preserve"):
        _make_preserve_item(aspects=Aspects(preserve=[], drop=["台词"])).validate()


def test_preserve_item_exempt_dimensions_may_be_empty():
    p = _make_preserve_item(exempt_dimensions=[])
    p.validate()


# ===================== RejectedItem =====================

def test_rejected_item_basic():
    r = RejectedItem(item_id="#2", reason="评估师违规")
    r.validate()


def test_rejected_item_id_format():
    with pytest.raises(ContractValidationError, match="item_id"):
        RejectedItem(item_id="2", reason="x").validate()


def test_rejected_item_reason_non_empty():
    with pytest.raises(ContractValidationError, match="reason"):
        RejectedItem(item_id="#2", reason="").validate()


# ===================== NegotiationTurn =====================

def test_negotiation_turn_speakers():
    for sp in ("connoisseur", "evaluator", "author"):
        t = NegotiationTurn(speaker=sp, msg="x", timestamp="2026-04-19T12:00:00+08:00")
        t.validate()


def test_negotiation_turn_rejects_unknown_speaker():
    with pytest.raises(ContractValidationError, match="speaker"):
        NegotiationTurn(speaker="writer", msg="x", timestamp="2026-04-19T12:00:00+08:00").validate()


def test_negotiation_turn_msg_non_empty():
    with pytest.raises(ContractValidationError, match="msg"):
        NegotiationTurn(speaker="author", msg="", timestamp="2026-04-19T12:00:00+08:00").validate()


# ===================== WriterAssignment =====================

def test_writer_assignment_basic():
    w = WriterAssignment(item_id="#1", writer="novelist-jianchen", task="rewrite")
    w.validate()


def test_writer_assignment_writer_whitelist():
    valid = ["novelist-jianchen", "novelist-canglan", "novelist-moyan", "novelist-xuanyi", "novelist-yunxi"]
    for wr in valid:
        WriterAssignment(item_id="#1", writer=wr, task="rewrite").validate()
    with pytest.raises(ContractValidationError, match="writer"):
        WriterAssignment(item_id="#1", writer="novelist-wrong", task="x").validate()


def test_writer_assignment_task_non_empty():
    with pytest.raises(ContractValidationError, match="task"):
        WriterAssignment(item_id="#1", writer="novelist-jianchen", task="").validate()


# ===================== generate_contract_id =====================

def test_generate_contract_id_format():
    cid = generate_contract_id()
    assert re.match(r"^cc_\d{8}_[0-9a-f]{6}$", cid), f"格式不符:{cid}"


def test_generate_contract_id_uniqueness():
    ids = {generate_contract_id() for _ in range(100)}
    assert len(ids) == 100


# ===================== CreativeContract =====================

def _make_contract(**overrides):
    base = dict(
        contract_id=generate_contract_id(),
        chapter_ref="第3章",
        created_at="2026-04-19T12:00:00+08:00",
        negotiation_log=[NegotiationTurn(speaker="connoisseur", msg="建议", timestamp="2026-04-19T12:00:00+08:00")],
        preserve_list=[_make_preserve_item()],
        rejected_list=[RejectedItem(item_id="#2", reason="违规")],
        writer_assignments=[WriterAssignment(item_id="#1", writer="novelist-jianchen", task="rewrite")],
        iteration_count=0,
        max_iterations=3,
    )
    base.update(overrides)
    return CreativeContract(**base)


def test_contract_basic():
    c = _make_contract()
    c.validate()
    assert c.skipped_by_author is False


def test_contract_chapter_ref_non_empty():
    with pytest.raises(ContractValidationError, match="chapter_ref"):
        _make_contract(chapter_ref="").validate()


def test_contract_rejects_bad_contract_id():
    with pytest.raises(ContractValidationError, match="contract_id"):
        _make_contract(contract_id="bad_id").validate()


def test_contract_iteration_count_bounds():
    with pytest.raises(ContractValidationError, match="iteration_count"):
        _make_contract(iteration_count=-1).validate()
    with pytest.raises(ContractValidationError, match="iteration_count"):
        _make_contract(iteration_count=5, max_iterations=3).validate()


def test_contract_skipped_by_author_requires_empty_lists():
    _make_contract(preserve_list=[], rejected_list=[], writer_assignments=[], skipped_by_author=True).validate()
    with pytest.raises(ContractValidationError, match="skipped_by_author"):
        _make_contract(skipped_by_author=True).validate()


# ===================== 序列化 =====================

def test_contract_roundtrip_minimal():
    c = CreativeContract(
        contract_id=generate_contract_id(),
        chapter_ref="第1章",
        created_at="2026-04-19T00:00:00+08:00",
    )
    s = c.to_json()
    assert isinstance(s, str)
    c2 = CreativeContract.from_json(s)
    assert c2.contract_id == c.contract_id


def test_contract_roundtrip_full():
    c = _make_contract()
    s = c.to_json()
    parsed = json.loads(s)
    assert parsed["preserve_list"][0]["aspects"]["preserve"] == ["情绪强度", "心理动机"]
    c2 = CreativeContract.from_json(s)
    assert c2.contract_id == c.contract_id


def test_contract_from_json_invalid_raises():
    with pytest.raises(ContractValidationError, match="JSON"):
        CreativeContract.from_json("not a json")


def test_contract_preserve_list_ascii_false():
    c = _make_contract()
    s = c.to_json()
    assert "情绪强度" in s