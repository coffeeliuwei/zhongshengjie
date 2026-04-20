# tests/test_evaluator_exemption.py
"""Tests for core.inspiration.evaluator_exemption.

仅测试纯数据转换 -- 不涉及任何评估师 prompt / LLM / 磁盘 I/O。
Q4 硬约束:sub_items 非空,否则 ExemptionBuildError。
"""
from __future__ import annotations

import pytest

from core.inspiration.creative_contract import (
    Aspects,
    CreativeContract,
    ExemptDimension,
    PreserveItem,
    Scope,
)


# ----------------- fixtures -----------------

def _make_item(
    item_id: str,
    paragraph_index: int,
    exempts: list[tuple[str, list[str]]],
    char_start: int = 0,
    char_end: int = 10,
) -> PreserveItem:
    """便捷构造 PreserveItem。exempts = [(dim, [sub,...]), ...]"""
    return PreserveItem(
        item_id=item_id,
        scope=Scope(
            paragraph_index=paragraph_index,
            char_start=char_start,
            char_end=char_end,
        ),
        applied_constraint_id=None,
        rationale="test",
        evaluator_risk=[],
        aspects=Aspects(preserve=["情绪强度"]),
        exempt_dimensions=[
            ExemptDimension(dimension=d, sub_items=list(s)) for d, s in exempts
        ],
    )


def _make_contract(preserve_list):
    return CreativeContract(
        contract_id="cc_20260420_abcdef",
        chapter_ref="test_ch",
        created_at="2026-04-20T03:30:00+08:00",
        preserve_list=preserve_list,
    )


# ===================== build_exemption_map 基础 =====================

def test_build_empty_contract_returns_empty_map():
    """空 preserve_list -> 空 map"""
    from core.inspiration.evaluator_exemption import build_exemption_map

    m = build_exemption_map(_make_contract([]))
    assert m == {}


def test_build_single_item_single_dimension():
    """单 item 单维度 -> {para: {dim: {subs...}}}"""
    from core.inspiration.evaluator_exemption import build_exemption_map

    c = _make_contract(
        [_make_item("#1", paragraph_index=3,
                    exempts=[("视角连贯性", ["人称切换", "焦点切换"])])]
    )
    m = build_exemption_map(c)
    assert set(m.keys()) == {3}
    assert set(m[3].keys()) == {"视角连贯性"}
    assert m[3]["视角连贯性"] == {"人称切换", "焦点切换"}


def test_build_multiple_items_same_paragraph_merge():
    """两 item 同段同维度 -> sub_items 并集"""
    from core.inspiration.evaluator_exemption import build_exemption_map

    c = _make_contract([
        _make_item("#1", paragraph_index=2, char_start=0, char_end=10,
                   exempts=[("节奏", ["重复句"])]),
        _make_item("#2", paragraph_index=2, char_start=20, char_end=30,
                   exempts=[("节奏", ["短句密集"])]),
    ])
    m = build_exemption_map(c)
    assert m[2]["节奏"] == {"重复句", "短句密集"}


def test_build_multiple_paragraphs_isolated():
    """不同 paragraph 互不干扰"""
    from core.inspiration.evaluator_exemption import build_exemption_map

    c = _make_contract([
        _make_item("#1", paragraph_index=0,
                   exempts=[("X", ["a"])]),
        _make_item("#2", paragraph_index=5,
                   exempts=[("X", ["b"])]),
    ])
    m = build_exemption_map(c)
    assert m[0]["X"] == {"a"}
    assert m[5]["X"] == {"b"}


# ===================== build_exemption_map 校验 =====================

def test_build_rejects_non_contract():
    """非 CreativeContract -> TypeError"""
    from core.inspiration.evaluator_exemption import build_exemption_map

    with pytest.raises(TypeError):
        build_exemption_map({"preserve_list": []})  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        build_exemption_map(None)  # type: ignore[arg-type]


def test_build_item_no_exempt_dimensions_contributes_nothing():
    """preserve_item 未声明任何豁免 -> map 不含该段落键"""
    from core.inspiration.evaluator_exemption import build_exemption_map

    c = _make_contract([
        _make_item("#1", paragraph_index=4, exempts=[]),
    ])
    m = build_exemption_map(c)
    assert 4 not in m
    assert m == {}


def test_build_multiple_dimensions_same_item():
    """同 item 多维度 -> 各自独立"""
    from core.inspiration.evaluator_exemption import build_exemption_map

    c = _make_contract([
        _make_item("#1", paragraph_index=1, exempts=[
            ("维度A", ["a1", "a2"]),
            ("维度B", ["b1"]),
        ]),
    ])
    m = build_exemption_map(c)
    assert m[1]["维度A"] == {"a1", "a2"}
    assert m[1]["维度B"] == {"b1"}


def test_build_duplicate_sub_items_deduped():
    """同 (para, dim) 重复 sub_item -> 集合去重"""
    from core.inspiration.evaluator_exemption import build_exemption_map

    c = _make_contract([
        _make_item("#1", paragraph_index=0, char_start=0, char_end=5,
                   exempts=[("X", ["共同项"])]),
        _make_item("#2", paragraph_index=0, char_start=10, char_end=15,
                   exempts=[("X", ["共同项"])]),
    ])
    m = build_exemption_map(c)
    assert m[0]["X"] == {"共同项"}


# ===================== is_exempt 查询 =====================

def test_is_exempt_hit():
    """命中 (para, dim, sub) -> True"""
    from core.inspiration.evaluator_exemption import build_exemption_map, is_exempt

    c = _make_contract([
        _make_item("#1", paragraph_index=2, exempts=[("情绪一致性", ["心理旁白"])])
    ])
    m = build_exemption_map(c)
    assert is_exempt(m, paragraph_index=2, dimension="情绪一致性", sub_item="心理旁白") is True


def test_is_exempt_paragraph_miss():
    """段落未豁免 -> False"""
    from core.inspiration.evaluator_exemption import build_exemption_map, is_exempt

    c = _make_contract([
        _make_item("#1", paragraph_index=2, exempts=[("X", ["a"])])
    ])
    m = build_exemption_map(c)
    assert is_exempt(m, paragraph_index=5, dimension="X", sub_item="a") is False


def test_is_exempt_dimension_miss():
    """段落命中但维度未豁免 -> False"""
    from core.inspiration.evaluator_exemption import build_exemption_map, is_exempt

    c = _make_contract([
        _make_item("#1", paragraph_index=2, exempts=[("X", ["a"])])
    ])
    m = build_exemption_map(c)
    assert is_exempt(m, 2, "Y", "a") is False


def test_is_exempt_sub_item_miss():
    """段落+维度命中但 sub_item 未列 -> False"""
    from core.inspiration.evaluator_exemption import build_exemption_map, is_exempt

    c = _make_contract([
        _make_item("#1", paragraph_index=2, exempts=[("X", ["a"])])
    ])
    m = build_exemption_map(c)
    assert is_exempt(m, 2, "X", "b") is False


def test_is_exempt_on_empty_map():
    """空 map -> 恒 False"""
    from core.inspiration.evaluator_exemption import is_exempt

    assert is_exempt({}, 0, "X", "a") is False


# ===================== format_exemption_report =====================

def test_format_empty_map():
    """空 map -> 明示无豁免"""
    from core.inspiration.evaluator_exemption import format_exemption_report

    t = format_exemption_report({})
    assert "本章无豁免" in t


def test_format_contains_all_keys():
    """报告应包含所有 paragraph / dimension / sub_item 标识"""
    from core.inspiration.evaluator_exemption import build_exemption_map, format_exemption_report

    c = _make_contract([
        _make_item("#1", paragraph_index=3, exempts=[("视角", ["切焦"])]),
        _make_item("#2", paragraph_index=7, exempts=[("节奏", ["短句", "停顿"])]),
    ])
    t = format_exemption_report(build_exemption_map(c))
    for s in ("3", "7", "视角", "切焦", "节奏", "短句", "停顿"):
        assert s in t, f"报告缺 {s!r}"


def test_format_paragraphs_sorted_ascending():
    """段落按 index 升序输出,利于作者阅读"""
    from core.inspiration.evaluator_exemption import build_exemption_map, format_exemption_report

    c = _make_contract([
        _make_item("#1", paragraph_index=9, exempts=[("A", ["x"])]),
        _make_item("#2", paragraph_index=2, exempts=[("B", ["y"])]),
    ])
    t = format_exemption_report(build_exemption_map(c))
    idx_2 = t.find("段落 2")
    idx_9 = t.find("段落 9")
    assert idx_2 != -1 and idx_9 != -1
    assert idx_2 < idx_9, "段落 2 应在段落 9 之前出现"


# ===================== 端到端 smoke =====================

def test_end_to_end_contract_to_report():
    """契约 -> build -> is_exempt -> format,全链路贯通"""
    from core.inspiration.evaluator_exemption import (
        build_exemption_map,
        is_exempt,
        format_exemption_report,
    )

    c = _make_contract([
        _make_item("#1", paragraph_index=4, char_start=10, char_end=50,
                   exempts=[("人物动机连贯性", ["突兀转折"])]),
        _make_item("#2", paragraph_index=4, char_start=60, char_end=90,
                   exempts=[("人物动机连贯性", ["情绪跳脱"]),
                            ("节奏", ["停顿不足"])]),
    ])
    m = build_exemption_map(c)

    assert is_exempt(m, 4, "人物动机连贯性", "突兀转折") is True
    assert is_exempt(m, 4, "人物动机连贯性", "情绪跳脱") is True
    assert is_exempt(m, 4, "节奏", "停顿不足") is True
    assert is_exempt(m, 4, "节奏", "过长铺陈") is False
    assert is_exempt(m, 5, "节奏", "停顿不足") is False

    text = format_exemption_report(m)
    assert "段落 4" in text
    assert "突兀转折" in text and "情绪跳脱" in text
    assert "停顿不足" in text