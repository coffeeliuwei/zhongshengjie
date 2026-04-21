"""core/inspiration/dispatcher.py 的单元测试。

覆盖:
- dispatch 对 skipped_by_author=True / 空 writer_assignments / 正常多写手派单的处理
- DispatchPackage 字段 / 校验
- prompt 增量:v2 §5 模板、Q2 嵌套 aspects 分块、drop 空降级、多 item 拼接、
  evaluator_risk 透传、exempt_dimensions 透传
- 保持 WriterAssignment 原始顺序(同一写手多 item 的 task 顺序稳定)
- 在契约未经 validate 时 dispatch 内部仍会 validate(不信任调用方)

依据计划:docs/计划_P1-2_dispatcher_20260419.md
"""
from __future__ import annotations

import pytest

from core.inspiration.creative_contract import (
    Aspects,
    CreativeContract,
    ContractValidationError,
    ExemptDimension,
    NegotiationTurn,
    PreserveItem,
    RejectedItem,
    Scope,
    WriterAssignment,
    generate_contract_id,
)
from core.inspiration.dispatcher import (
    DispatchPackage,
    DispatcherError,
    dispatch,
)


def test_module_importable():
    """冒烟:模块可导入,所有 __all__ 符号已定义。"""
    from core.inspiration import dispatcher as d
    for name in d.__all__:
        assert hasattr(d, name), f"{name} 不在模块中"


# ===================== DispatchPackage =====================


def _make_preserve_item(**overrides) -> PreserveItem:
    base = dict(
        item_id="#1",
        scope=Scope(paragraph_index=3, char_start=234, char_end=567),
        applied_constraint_id="ANTI_001",
        rationale="鉴赏师 + 作者共识:败者视角 +3 爽快累计 7 条",
        evaluator_risk=["主角视角连贯性 -0.1"],
        aspects=Aspects(preserve=["情绪强度", "心理动机"], drop=["具体台词"]),
        exempt_dimensions=[
            ExemptDimension(dimension="视角连贯性", sub_items=["主角一致性"]),
        ],
    )
    base.update(overrides)
    return PreserveItem(**base)


def test_dispatch_package_basic():
    p = DispatchPackage(
        contract_id="cc_20260419_abcdef",
        writer="novelist-jianchen",
        item_ids=["#1"],
        tasks=["rewrite_paragraph"],
        preserve_items=[_make_preserve_item()],
        prompt_increment="【创意契约约束】...",
    )
    p.validate()
    assert p.writer == "novelist-jianchen"
    assert p.item_ids == ["#1"]


def test_dispatch_package_item_ids_tasks_parallel():
    """item_ids 与 tasks 必须同长。"""
    with pytest.raises(DispatcherError, match="item_ids.*tasks"):
        DispatchPackage(
            contract_id="cc_20260419_abcdef",
            writer="novelist-jianchen",
            item_ids=["#1", "#2"],
            tasks=["rewrite_paragraph"],
            preserve_items=[_make_preserve_item()],
            prompt_increment="x",
        ).validate()


def test_dispatch_package_rejects_empty_writer():
    with pytest.raises(DispatcherError, match="writer"):
        DispatchPackage(
            contract_id="cc_20260419_abcdef",
            writer="",
            item_ids=["#1"],
            tasks=["rewrite_paragraph"],
            preserve_items=[_make_preserve_item()],
            prompt_increment="x",
        ).validate()


def test_dispatch_package_rejects_empty_item_ids():
    with pytest.raises(DispatcherError, match="item_ids"):
        DispatchPackage(
            contract_id="cc_20260419_abcdef",
            writer="novelist-jianchen",
            item_ids=[],
            tasks=[],
            preserve_items=[],
            prompt_increment="x",
        ).validate()


def test_dispatch_package_rejects_empty_prompt_increment():
    with pytest.raises(DispatcherError, match="prompt_increment"):
        DispatchPackage(
            contract_id="cc_20260419_abcdef",
            writer="novelist-jianchen",
            item_ids=["#1"],
            tasks=["rewrite_paragraph"],
            preserve_items=[_make_preserve_item()],
            prompt_increment="",
        ).validate()


def test_dispatch_package_preserve_items_cardinality():
    """preserve_items 数量必须等于 item_ids 数量(且 item_id 一一对应)。"""
    p1 = _make_preserve_item(item_id="#1")
    p2 = _make_preserve_item(item_id="#2")
    with pytest.raises(DispatcherError, match="preserve_items"):
        DispatchPackage(
            contract_id="cc_20260419_abcdef",
            writer="novelist-jianchen",
            item_ids=["#1", "#2"],
            tasks=["t1", "t2"],
            preserve_items=[p1],  # 少一个
            prompt_increment="x",
        ).validate()
    # id 对应不上
    with pytest.raises(DispatcherError, match="preserve_items"):
        DispatchPackage(
            contract_id="cc_20260419_abcdef",
            writer="novelist-jianchen",
            item_ids=["#1", "#2"],
            tasks=["t1", "t2"],
            preserve_items=[p1, _make_preserve_item(item_id="#3")],
            prompt_increment="x",
        ).validate()


# ===================== _format_preserve_block =====================


def _get_block(*, aspects=None, exempt_dimensions=None, evaluator_risk=None,
               task="rewrite_paragraph"):
    """构造一个 block + 调用内部渲染函数的便捷封装。"""
    from core.inspiration.dispatcher import _format_preserve_block
    p = _make_preserve_item(
        aspects=aspects or Aspects(preserve=["情绪强度", "心理动机"],
                                   drop=["具体台词"]),
        exempt_dimensions=exempt_dimensions if exempt_dimensions is not None else [
            ExemptDimension(dimension="视角连贯性", sub_items=["主角一致性"]),
        ],
        evaluator_risk=evaluator_risk if evaluator_risk is not None else ["主角视角连贯性 -0.1"],
    )
    return _format_preserve_block(preserve_item=p, task=task)


def test_format_preserve_block_contains_scope():
    text = _get_block()
    assert "第 3 段" in text
    assert "[234, 567)" in text or "234" in text and "567" in text


def test_format_preserve_block_contains_item_id_and_constraint():
    text = _get_block()
    assert "#1" in text
    assert "ANTI_001" in text


def test_format_preserve_block_contains_rationale():
    text = _get_block()
    assert "鉴赏师 + 作者共识" in text


def test_format_preserve_block_q2_renders_preserve_and_drop():
    """Q2:preserve 与 drop 必须分段出现。"""
    text = _get_block()
    assert "【必须保留】" in text
    assert "情绪强度" in text
    assert "心理动机" in text
    assert "【可放开】" in text
    assert "具体台词" in text


def test_format_preserve_block_q2_drop_empty_degrades():
    """drop 为空时,改为"仅可优化字词/语流"提示,不输出空的【可放开】块。"""
    text = _get_block(aspects=Aspects(preserve=["情绪强度"], drop=[]))
    assert "【必须保留】" in text
    assert "情绪强度" in text
    # 不应出现空块
    assert "【可放开】:\n  -" not in text
    # 应出现降级提示
    assert "仅可优化字词" in text or "仅优化字词" in text


def test_format_preserve_block_evaluator_risk_listed():
    text = _get_block(evaluator_risk=["主角视角连贯性 -0.1", "节奏打断风险"])
    assert "评估师风险" in text
    assert "主角视角连贯性 -0.1" in text
    assert "节奏打断风险" in text


def test_format_preserve_block_evaluator_risk_empty_section_absent():
    """evaluator_risk 为空时不渲染该段落,避免空表格。"""
    text = _get_block(evaluator_risk=[])
    assert "评估师风险" not in text


def test_format_preserve_block_exempt_dimensions_transparent():
    """Q4:豁免按子项透传到 prompt,便于写手知晓约束边界。"""
    text = _get_block(exempt_dimensions=[
        ExemptDimension(dimension="视角连贯性", sub_items=["主角一致性", "叙述人称一致性"]),
    ])
    assert "涉及豁免维度" in text or "豁免维度" in text
    assert "视角连贯性" in text
    assert "主角一致性" in text
    assert "叙述人称一致性" in text


def test_format_preserve_block_exempt_dimensions_empty_section_absent():
    text = _get_block(exempt_dimensions=[])
    assert "豁免维度" not in text


def test_format_preserve_block_applied_constraint_none():
    """applied_constraint_id 可为 None(非约束库触发)。"""
    from core.inspiration.dispatcher import _format_preserve_block
    p = _make_preserve_item(applied_constraint_id=None)
    text = _format_preserve_block(preserve_item=p, task="rewrite_paragraph")
    assert "ANTI_001" not in text
    assert "非约束库" in text or "无(" in text or "无约束" in text


def test_format_preserve_block_contains_task():
    text = _get_block(task="整章再润色,不得修改 preserve 区域")
    assert "整章再润色" in text


# ===================== _build_prompt_increment =====================


def test_build_prompt_increment_header_and_footer():
    from core.inspiration.dispatcher import _build_prompt_increment
    p = _make_preserve_item(item_id="#1")
    text = _build_prompt_increment(
        contract_id="cc_20260419_abcdef",
        writer="novelist-jianchen",
        pairs=[(p, "rewrite_paragraph")],
    )
    assert "【创意契约约束】" in text
    assert "cc_20260419_abcdef" in text
    assert "novelist-jianchen" in text
    # 守则尾部
    assert "重写守则" in text
    assert "区域外保持原文" in text or "区域外正常修改" in text or "区域外可" in text


def test_build_prompt_increment_concatenates_multiple_items():
    """一位写手承接多 item 时,prompt 中出现多个"项目"块。"""
    from core.inspiration.dispatcher import _build_prompt_increment
    p1 = _make_preserve_item(item_id="#1")
    p3 = _make_preserve_item(
        item_id="#3",
        scope=Scope(paragraph_index=5, char_start=10, char_end=99),
    )
    text = _build_prompt_increment(
        contract_id="cc_20260419_abcdef",
        writer="novelist-jianchen",
        pairs=[(p1, "rewrite_paragraph"), (p3, "tighten_rhythm")],
    )
    # 两个项目都出现
    assert "项目 #1" in text
    assert "项目 #3" in text
    # 第 5 段信息来自 #3
    assert "第 5 段" in text


def test_build_prompt_increment_preserves_pair_order():
    """pairs 顺序 = 项目块顺序。"""
    from core.inspiration.dispatcher import _build_prompt_increment
    p1 = _make_preserve_item(item_id="#1")
    p2 = _make_preserve_item(
        item_id="#2",
        scope=Scope(paragraph_index=7, char_start=0, char_end=10),
    )
    text_a = _build_prompt_increment(
        contract_id="cc_20260419_abcdef",
        writer="novelist-jianchen",
        pairs=[(p1, "t1"), (p2, "t2")],
    )
    text_b = _build_prompt_increment(
        contract_id="cc_20260419_abcdef",
        writer="novelist-jianchen",
        pairs=[(p2, "t2"), (p1, "t1")],
    )
    assert text_a.index("项目 #1") < text_a.index("项目 #2")
    assert text_b.index("项目 #2") < text_b.index("项目 #1")


def test_build_prompt_increment_rejects_empty_pairs():
    from core.inspiration.dispatcher import _build_prompt_increment
    with pytest.raises(DispatcherError, match="pairs"):
        _build_prompt_increment(
            contract_id="cc_20260419_abcdef",
            writer="novelist-jianchen",
            pairs=[],
        )


# ===================== _group_assignments_by_writer =====================


def _wa(item_id: str, writer: str, task: str = "rewrite_paragraph") -> WriterAssignment:
    return WriterAssignment(item_id=item_id, writer=writer, task=task)


def test_group_assignments_single_writer_multi_items():
    from core.inspiration.dispatcher import _group_assignments_by_writer
    groups = _group_assignments_by_writer([
        _wa("#1", "novelist-jianchen"),
        _wa("#2", "novelist-jianchen", task="tighten_rhythm"),
    ])
    assert list(groups.keys()) == ["novelist-jianchen"]
    assert [w.item_id for w in groups["novelist-jianchen"]] == ["#1", "#2"]
    assert groups["novelist-jianchen"][1].task == "tighten_rhythm"


def test_group_assignments_multi_writers_preserves_insertion_order():
    """dict 按写手首次出现的顺序排列;同一写手的 task 按原 list 顺序。"""
    from core.inspiration.dispatcher import _group_assignments_by_writer
    groups = _group_assignments_by_writer([
        _wa("#1", "novelist-yunxi"),
        _wa("#2", "novelist-jianchen"),
        _wa("#3", "novelist-yunxi"),
    ])
    assert list(groups.keys()) == ["novelist-yunxi", "novelist-jianchen"]
    assert [w.item_id for w in groups["novelist-yunxi"]] == ["#1", "#3"]
    assert [w.item_id for w in groups["novelist-jianchen"]] == ["#2"]


def test_group_assignments_empty_returns_empty_dict():
    from core.inspiration.dispatcher import _group_assignments_by_writer
    assert _group_assignments_by_writer([]) == {}


# ===================== dispatch: 正常路径 =====================


def _make_contract(**overrides) -> CreativeContract:
    base = dict(
        contract_id=generate_contract_id(),
        chapter_ref="第3章",
        created_at="2026-04-19T12:00:00+08:00",
        negotiation_log=[
            NegotiationTurn(speaker="connoisseur", msg="建议 #1",
                            timestamp="2026-04-19T12:00:00+08:00"),
            NegotiationTurn(speaker="author", msg="采纳 #1",
                            timestamp="2026-04-19T12:05:00+08:00"),
        ],
        preserve_list=[_make_preserve_item()],
        rejected_list=[RejectedItem(item_id="#2", reason="12 一致性规则 #7 违规")],
        writer_assignments=[
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="rewrite_paragraph")
        ],
        iteration_count=0,
        max_iterations=3,
    )
    base.update(overrides)
    return CreativeContract(**base)


def test_dispatch_returns_list_of_dispatch_packages():
    c = _make_contract()
    packages = dispatch(c)
    assert isinstance(packages, list)
    assert len(packages) == 1
    assert isinstance(packages[0], DispatchPackage)


def test_dispatch_package_fields_populated():
    c = _make_contract()
    pkg = dispatch(c)[0]
    assert pkg.contract_id == c.contract_id
    assert pkg.writer == "novelist-jianchen"
    assert pkg.item_ids == ["#1"]
    assert pkg.tasks == ["rewrite_paragraph"]
    assert len(pkg.preserve_items) == 1
    assert pkg.preserve_items[0].item_id == "#1"
    assert "【创意契约约束】" in pkg.prompt_increment
    assert c.contract_id in pkg.prompt_increment


def test_dispatch_package_self_validates():
    """dispatch 返回的每个包必然通过自身 validate()。"""
    c = _make_contract()
    for pkg in dispatch(c):
        pkg.validate()  # 不应抛


def test_dispatch_multi_writers_produces_multi_packages():
    """两位写手各自拿到一个 package,顺序 = 首次出现顺序。"""
    p1 = _make_preserve_item(item_id="#1")
    p3 = _make_preserve_item(
        item_id="#3",
        scope=Scope(paragraph_index=5, char_start=10, char_end=99),
    )
    c = _make_contract(
        preserve_list=[p1, p3],
        rejected_list=[],
        writer_assignments=[
            WriterAssignment(item_id="#3", writer="novelist-yunxi",
                             task="chapter_polish_with_preserve"),
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="rewrite_paragraph"),
        ],
    )
    pkgs = dispatch(c)
    assert [p.writer for p in pkgs] == ["novelist-yunxi", "novelist-jianchen"]
    yunxi = pkgs[0]
    assert yunxi.item_ids == ["#3"]
    assert yunxi.tasks == ["chapter_polish_with_preserve"]


def test_dispatch_single_writer_multi_items_keeps_order():
    """一位写手承接多 item 时,顺序与 writer_assignments 原顺序一致。"""
    p1 = _make_preserve_item(item_id="#1")
    p3 = _make_preserve_item(
        item_id="#3",
        scope=Scope(paragraph_index=7, char_start=0, char_end=50),
    )
    c = _make_contract(
        preserve_list=[p1, p3],
        rejected_list=[],
        writer_assignments=[
            WriterAssignment(item_id="#3", writer="novelist-jianchen",
                             task="second_task"),
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="first_task"),
        ],
    )
    pkgs = dispatch(c)
    assert len(pkgs) == 1
    pkg = pkgs[0]
    assert pkg.item_ids == ["#3", "#1"]
    assert pkg.tasks == ["second_task", "first_task"]
    # prompt 中项目顺序一致
    assert pkg.prompt_increment.index("项目 #3") < pkg.prompt_increment.index("项目 #1")


# ===================== dispatch: Q1 跳过 / 空契约 =====================


def test_dispatch_skipped_by_author_returns_empty():
    """Q1:鉴赏师 0 条 + 作者确认跳过 → 空契约 → dispatch 返回 []。"""
    c = CreativeContract(
        contract_id=generate_contract_id(),
        chapter_ref="第5章",
        created_at="2026-04-19T13:00:00+08:00",
        skipped_by_author=True,
    )
    assert dispatch(c) == []


def test_dispatch_no_assignments_returns_empty():
    """writer_assignments 空(但契约本身合法,未 skip)→ dispatch 返回 []。

    语义:鉴赏师虽然有建议,但派单决定没落到任何写手头上
    (如:preserve_list 全靠 P2-2 的云溪兜底整章润色流程处理,
    不在 writer_assignments 表达)。
    """
    c = CreativeContract(
        contract_id=generate_contract_id(),
        chapter_ref="第5章",
        created_at="2026-04-19T13:00:00+08:00",
        preserve_list=[_make_preserve_item()],
        rejected_list=[],
        writer_assignments=[],
    )
    assert dispatch(c) == []


def test_dispatch_rejects_unvalidated_tampered_contract():
    """调用方若绕过 validate 手动改坏字段,dispatch 入口会重新 validate 并抛错。"""
    c = _make_contract()
    # 后门伪造:插入指向不存在 item 的 assignment
    c.writer_assignments = [
        WriterAssignment(item_id="#1", writer="novelist-jianchen",
                         task="rewrite_paragraph"),
        WriterAssignment(item_id="#99", writer="novelist-jianchen",
                         task="bogus"),
    ]
    with pytest.raises(ContractValidationError, match="writer_assignments"):
        dispatch(c)


# ===================== dispatch: Q2 嵌套端到端 =====================


def test_dispatch_prompt_contains_q2_preserve_and_drop():
    p = _make_preserve_item(
        aspects=Aspects(
            preserve=["情绪强度", "心理动机"],
            drop=["具体台词", "肢体表现"],
        ),
    )
    c = _make_contract(
        preserve_list=[p],
        rejected_list=[],
        writer_assignments=[
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="rewrite_paragraph"),
        ],
    )
    pkg = dispatch(c)[0]
    prompt = pkg.prompt_increment
    assert "【必须保留】" in prompt
    assert "情绪强度" in prompt
    assert "心理动机" in prompt
    assert "【可放开】" in prompt
    assert "具体台词" in prompt
    assert "肢体表现" in prompt


def test_dispatch_prompt_q2_empty_drop_degrades():
    p = _make_preserve_item(
        aspects=Aspects(preserve=["节奏张力"], drop=[]),
    )
    c = _make_contract(
        preserve_list=[p],
        rejected_list=[],
        writer_assignments=[
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="rewrite_paragraph"),
        ],
    )
    prompt = dispatch(c)[0].prompt_increment
    assert "节奏张力" in prompt
    assert "仅可优化字词" in prompt or "仅优化字词" in prompt


# ===================== dispatch: 多写手真实场景 =====================


def test_dispatch_three_writers_scenario():
    """v2 §1 阶段 5.6 典型场景:
    - #1 改第3段视角 → 剑尘 rewrite_paragraph
    - #2 整章节奏调整 → 云溪 chapter_polish
    - #3 对话打磨     → 墨言 tighten_dialogue
    """
    p1 = _make_preserve_item(
        item_id="#1",
        scope=Scope(paragraph_index=3, char_start=234, char_end=567),
        aspects=Aspects(preserve=["败者视角主导"], drop=["具体用词"]),
    )
    p2 = _make_preserve_item(
        item_id="#2",
        scope=Scope(paragraph_index=0, char_start=0, char_end=9999),
        applied_constraint_id=None,
        aspects=Aspects(preserve=["整章节奏: 紧-紧-松-紧"], drop=[]),
    )
    p3 = _make_preserve_item(
        item_id="#3",
        scope=Scope(paragraph_index=7, char_start=10, char_end=250),
        applied_constraint_id="ANTI_007",
        aspects=Aspects(preserve=["反派口语色调"], drop=["具体词汇"]),
    )
    c = _make_contract(
        preserve_list=[p1, p2, p3],
        rejected_list=[],
        writer_assignments=[
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="rewrite_paragraph"),
            WriterAssignment(item_id="#2", writer="novelist-yunxi",
                             task="chapter_polish_with_preserve"),
            WriterAssignment(item_id="#3", writer="novelist-moyan",
                             task="tighten_dialogue"),
        ],
    )
    pkgs = dispatch(c)
    # 3 个 package,顺序 = 出现顺序
    assert [p.writer for p in pkgs] == [
        "novelist-jianchen", "novelist-yunxi", "novelist-moyan"
    ]
    # 每个 package 只承接本写手的项目
    assert pkgs[0].item_ids == ["#1"]
    assert pkgs[1].item_ids == ["#2"]
    assert pkgs[2].item_ids == ["#3"]
    # prompt 中不混入他人的 item
    assert "项目 #2" not in pkgs[0].prompt_increment
    assert "项目 #1" not in pkgs[1].prompt_increment
    assert "项目 #2" not in pkgs[2].prompt_increment


def test_dispatch_integrity_total_assignments_conserved():
    """所有 package 的 item_ids 总数 = 契约 writer_assignments 总数。"""
    p1 = _make_preserve_item(item_id="#1")
    p2 = _make_preserve_item(
        item_id="#2",
        scope=Scope(paragraph_index=4, char_start=0, char_end=100),
    )
    p3 = _make_preserve_item(
        item_id="#3",
        scope=Scope(paragraph_index=5, char_start=0, char_end=100),
    )
    c = _make_contract(
        preserve_list=[p1, p2, p3],
        rejected_list=[],
        writer_assignments=[
            WriterAssignment(item_id="#1", writer="novelist-jianchen", task="t1"),
            WriterAssignment(item_id="#2", writer="novelist-jianchen", task="t2"),
            WriterAssignment(item_id="#3", writer="novelist-yunxi", task="t3"),
        ],
    )
    pkgs = dispatch(c)
    total = sum(len(p.item_ids) for p in pkgs)
    assert total == len(c.writer_assignments) == 3


# ===================== dispatch: Q4 豁免透传 / evaluator_risk =====================


def test_dispatch_prompt_exempt_dimensions_transparent():
    p = _make_preserve_item(
        exempt_dimensions=[
            ExemptDimension(dimension="视角连贯性",
                            sub_items=["主角一致性", "叙述人称一致性"]),
            ExemptDimension(dimension="情绪节奏",
                            sub_items=["爽快度曲线"]),
        ],
    )
    c = _make_contract(
        preserve_list=[p],
        rejected_list=[],
        writer_assignments=[
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="rewrite_paragraph"),
        ],
    )
    prompt = dispatch(c)[0].prompt_increment
    assert "视角连贯性" in prompt
    assert "主角一致性" in prompt
    assert "叙述人称一致性" in prompt
    assert "情绪节奏" in prompt
    assert "爽快度曲线" in prompt


def test_dispatch_prompt_evaluator_risk_transparent():
    p = _make_preserve_item(
        evaluator_risk=["主角视角连贯性 -0.1", "节奏打断风险", "读者代入感降低"],
    )
    c = _make_contract(
        preserve_list=[p],
        rejected_list=[],
        writer_assignments=[
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="rewrite_paragraph"),
        ],
    )
    prompt = dispatch(c)[0].prompt_increment
    assert "评估师风险" in prompt
    assert "主角视角连贯性 -0.1" in prompt
    assert "节奏打断风险" in prompt
    assert "读者代入感降低" in prompt


# ===================== dispatch: 入口再校验 =====================


def test_dispatch_calls_validate_on_entry():
    """契约的 contract_id 伪造成非法格式,dispatch 必须抛 ContractValidationError。"""
    # 直接构造一个 contract_id 格式非法的契约,绕过 generate_contract_id
    c = CreativeContract(
        contract_id="not-a-valid-id",
        chapter_ref="第3章",
        created_at="2026-04-19T12:00:00+08:00",
        preserve_list=[_make_preserve_item()],
        writer_assignments=[
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="rewrite_paragraph"),
        ],
    )
    with pytest.raises(ContractValidationError, match="contract_id"):
        dispatch(c)


# ===================== 综合冒烟 =====================


def test_end_to_end_smoke_full_v2_stage_5_6():
    """v2 §1 阶段 5.6 端到端冒烟:
    契约构造 → dispatch → 检查 prompt 含全部关键字段 → 每包自校验。
    """
    p1 = _make_preserve_item(
        item_id="#1",
        scope=Scope(paragraph_index=3, char_start=234, char_end=567),
        aspects=Aspects(
            preserve=["败者视角主导", "情绪强度"],
            drop=["具体用词", "肢体细节"],
        ),
        exempt_dimensions=[
            ExemptDimension(dimension="视角连贯性",
                            sub_items=["主角一致性"]),
        ],
        evaluator_risk=["主角视角连贯性 -0.1"],
    )
    p2 = _make_preserve_item(
        item_id="#2",
        scope=Scope(paragraph_index=0, char_start=0, char_end=9999),
        applied_constraint_id=None,
        aspects=Aspects(preserve=["整章节奏"], drop=[]),
        exempt_dimensions=[],
        evaluator_risk=[],
    )
    c = CreativeContract(
        contract_id=generate_contract_id(),
        chapter_ref="第3章",
        created_at="2026-04-19T12:00:00+08:00",
        negotiation_log=[
            NegotiationTurn(speaker="connoisseur",
                            msg="建议 #1:第3段改败者视角;建议 #2:整章节奏",
                            timestamp="2026-04-19T12:00:00+08:00"),
            NegotiationTurn(speaker="evaluator",
                            msg="#1 风险:主角视角连贯性 -0.1;#2 无异议",
                            timestamp="2026-04-19T12:02:00+08:00"),
            NegotiationTurn(speaker="author",
                            msg="采纳 #1 和 #2",
                            timestamp="2026-04-19T12:05:00+08:00"),
        ],
        preserve_list=[p1, p2],
        rejected_list=[],
        writer_assignments=[
            WriterAssignment(item_id="#1", writer="novelist-jianchen",
                             task="rewrite_paragraph"),
            WriterAssignment(item_id="#2", writer="novelist-yunxi",
                             task="chapter_polish_with_preserve"),
        ],
        iteration_count=0,
        max_iterations=3,
    )
    pkgs = dispatch(c)
    # 2 位写手各得一个包
    assert len(pkgs) == 2
    names = [p.writer for p in pkgs]
    assert names == ["novelist-jianchen", "novelist-yunxi"]
    # 每个包自校验 + 关键字段齐全
    for pkg in pkgs:
        pkg.validate()
        assert c.contract_id in pkg.prompt_increment
        assert "【创意契约约束】" in pkg.prompt_increment
        assert "重写守则" in pkg.prompt_increment
    jianchen = pkgs[0]
    assert "败者视角主导" in jianchen.prompt_increment
    assert "情绪强度" in jianchen.prompt_increment
    assert "具体用词" in jianchen.prompt_increment
    assert "肢体细节" in jianchen.prompt_increment
    assert "主角视角连贯性 -0.1" in jianchen.prompt_increment
    assert "主角一致性" in jianchen.prompt_increment
    yunxi = pkgs[1]
    assert "整章节奏" in yunxi.prompt_increment
    # yunxi 的项目 drop 为空 → 降级提示
    assert "仅可优化字词" in yunxi.prompt_increment or "仅优化字词" in yunxi.prompt_increment


def test_public_api_via_package_import():
    """通过 core.inspiration 顶层导入应可达 dispatcher 3 个符号。"""
    from core import inspiration as insp
    for name in ("DispatchPackage", "dispatch", "DispatcherError"):
        assert hasattr(insp, name), f"{name} 未从 core.inspiration 导出"