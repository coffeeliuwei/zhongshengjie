# tests/test_escalation_dialogue.py
"""Tests for escalation dialogue formatters.

四种升级场景：
  1. 鉴赏师选中变体被评估师打回（冲突）
  2. 所有变体被评估师打回（全崩）
  3. 每 10 次鉴赏后的退化审计
  4. 每 10 次推翻后的推翻审计
"""

import pytest


def test_conflict_format_contains_warning_and_violation():
    """冲突格式化：包含警告符号和评估师违规原因"""
    from core.inspiration.escalation_dialogue import format_rater_vs_evaluator_conflict

    result = format_rater_vs_evaluator_conflict(
        rater_selected_id="var_002",
        ignition_point="他抬起的手停在半空",
        evaluator_violation="违反 R006（角色状态转换合理性）",
        other_candidates=[
            {"id": "var_001", "summary": "正常写法，评估通过，鉴赏师评平庸"},
            {"id": "var_003", "summary": "基准写法，评估通过，鉴赏师评平淡"},
        ],
    )
    assert "警告" in result  # N6修复：改为中文
    assert "var_002" in result
    assert "R006" in result
    assert "var_001" in result


def test_conflict_format_contains_options():
    """冲突格式化：包含可选操作"""
    from core.inspiration.escalation_dialogue import format_rater_vs_evaluator_conflict

    result = format_rater_vs_evaluator_conflict(
        rater_selected_id="var_001",
        ignition_point="某句话",
        evaluator_violation="违反 R003",
        other_candidates=[],
    )
    assert "Options" in result or "A" in result


def test_all_variants_failed_format_contains_flaw():
    """全崩格式化：包含共因描述"""
    from core.inspiration.escalation_dialogue import format_all_variants_failed

    result = format_all_variants_failed(
        candidate_ids=["var_001", "var_002", "var_003"],
        common_flaw="三段都用相同的'力量爆发→旁观者惊呼'模板",
    )
    assert "var_001" in result or "var_002" in result
    assert "模板" in result or "flaw" in result.lower()


def test_appraisal_audit_format_contains_count():
    """退化审计：包含鉴赏次数和模糊点火点数量"""
    from core.inspiration.escalation_dialogue import format_appraisal_audit

    result = format_appraisal_audit(
        appraisal_count=10,
        vague_count=4,
        baseline_win_count=7,
    )
    assert "10" in result
    assert "4" in result or "vague" in result.lower() or "笼统" in result


def test_appraisal_audit_format_contains_action_request():
    """退化审计：要求作者标定哪次是真点火"""
    from core.inspiration.escalation_dialogue import format_appraisal_audit

    result = format_appraisal_audit(
        appraisal_count=10, vague_count=3, baseline_win_count=2
    )
    assert "标定" in result  # N6修复：改为中文


def test_overturn_audit_format_contains_count():
    """推翻审计：包含推翻次数"""
    from core.inspiration.escalation_dialogue import format_overturn_audit

    result = format_overturn_audit(overturn_count=10)
    assert "10" in result


def test_overturn_audit_format_contains_options():
    """推翻审计：给出可选操作"""
    from core.inspiration.escalation_dialogue import format_overturn_audit

    result = format_overturn_audit(overturn_count=10)
    assert (
        "deviation" in result.lower()
        or "偏差" in result
        or "Options" in result
        or "A" in result
    )


# ===================== P1-6 追加:阶段 6 三选升级 =====================


def test_stage6_three_choice_contains_warning_header():
    """三选格式化:包含警告头"""
    from core.inspiration.escalation_dialogue import format_stage6_three_choice

    result = format_stage6_three_choice(
        item_summaries=[
            {"item_id": "#1", "summary": "红裙少女的侧脸近景"},
            {"item_id": "#3", "summary": "冰镜倒映回廊"},
        ],
        failed_dimensions=["人物动机连贯性", "情绪一致性"],
        consecutive_fail_count=3,
    )
    assert "警告" in result
    assert "阶段 6" in result or "整章评估" in result


def test_stage6_three_choice_lists_all_items():
    """三选格式化:列出所有 preserve_item 供作者选择撤销"""
    from core.inspiration.escalation_dialogue import format_stage6_three_choice

    result = format_stage6_three_choice(
        item_summaries=[
            {"item_id": "#1", "summary": "A 摘要"},
            {"item_id": "#2", "summary": "B 摘要"},
            {"item_id": "#7", "summary": "C 摘要"},
        ],
        failed_dimensions=["维度X"],
        consecutive_fail_count=3,
    )
    for iid in ("#1", "#2", "#7"):
        assert iid in result
    assert "A 摘要" in result and "B 摘要" in result and "C 摘要" in result


def test_stage6_three_choice_lists_failed_dimensions():
    """三选格式化:列出持续失败维度"""
    from core.inspiration.escalation_dialogue import format_stage6_three_choice

    result = format_stage6_three_choice(
        item_summaries=[{"item_id": "#1", "summary": "x"}],
        failed_dimensions=["节奏", "情绪"],
        consecutive_fail_count=3,
    )
    assert "节奏" in result
    assert "情绪" in result


def test_stage6_three_choice_contains_three_options():
    """三选格式化:三个选项 a/b/c 都在"""
    from core.inspiration.escalation_dialogue import format_stage6_three_choice

    result = format_stage6_three_choice(
        item_summaries=[{"item_id": "#1", "summary": "x"}],
        failed_dimensions=["X"],
        consecutive_fail_count=3,
    )
    assert "[a]" in result and "[b]" in result and "[c]" in result
    assert "撤销" in result
    assert "强制通过" in result
    assert "重协商" in result or "回 5.5" in result


def test_stage6_three_choice_mentions_force_pass_consequence():
    """三选格式化:[b] 强制通过必须提醒'推翻事件回流'"""
    from core.inspiration.escalation_dialogue import format_stage6_three_choice

    result = format_stage6_three_choice(
        item_summaries=[{"item_id": "#1", "summary": "x"}],
        failed_dimensions=["X"],
        consecutive_fail_count=3,
    )
    assert "author_force_pass" in result or "推翻事件" in result


def test_stage6_three_choice_shows_fail_count():
    """三选格式化:显示连续失败次数"""
    from core.inspiration.escalation_dialogue import format_stage6_three_choice

    result = format_stage6_three_choice(
        item_summaries=[{"item_id": "#1", "summary": "x"}],
        failed_dimensions=["X"],
        consecutive_fail_count=3,
    )
    assert "3" in result


def test_stage6_three_choice_empty_items_renders_placeholder():
    """三选格式化:preserve_list 为空时不崩,显示占位"""
    from core.inspiration.escalation_dialogue import format_stage6_three_choice

    result = format_stage6_three_choice(
        item_summaries=[],
        failed_dimensions=["X"],
        consecutive_fail_count=3,
    )
    assert "(无)" in result or "无采纳建议" in result
    assert "[a]" in result and "[b]" in result and "[c]" in result


def test_parse_revoke_with_item_id():
    """解析:'a #2' -> ('revoke', '#2')"""
    from core.inspiration.escalation_dialogue import parse_stage6_choice
    assert parse_stage6_choice("a #2") == ("revoke", "#2")
    assert parse_stage6_choice("A #10") == ("revoke", "#10")
    assert parse_stage6_choice("  a   #7  ") == ("revoke", "#7")


def test_parse_force_pass():
    """解析:'b' / 'B' -> ('force_pass', None)"""
    from core.inspiration.escalation_dialogue import parse_stage6_choice
    assert parse_stage6_choice("b") == ("force_pass", None)
    assert parse_stage6_choice("B") == ("force_pass", None)
    assert parse_stage6_choice("  b\n") == ("force_pass", None)


def test_parse_renegotiate():
    """解析:'c' -> ('renegotiate', None)"""
    from core.inspiration.escalation_dialogue import parse_stage6_choice
    assert parse_stage6_choice("c") == ("renegotiate", None)
    assert parse_stage6_choice("C") == ("renegotiate", None)


def test_parse_revoke_missing_item_id_raises():
    """解析:'a' 缺 #N -> ValueError"""
    import pytest
    from core.inspiration.escalation_dialogue import parse_stage6_choice
    with pytest.raises(ValueError, match="revoke"):
        parse_stage6_choice("a")


def test_parse_revoke_bad_item_id_raises():
    """解析:'a abc' / 'a #' -> ValueError"""
    import pytest
    from core.inspiration.escalation_dialogue import parse_stage6_choice
    for bad in ("a abc", "a #", "a #abc", "a 1", "a ##1"):
        with pytest.raises(ValueError):
            parse_stage6_choice(bad)


def test_parse_unknown_choice_raises():
    """解析:不在 a/b/c -> ValueError"""
    import pytest
    from core.inspiration.escalation_dialogue import parse_stage6_choice
    for bad in ("", "   ", "d", "x y z", "撤销", "abc"):
        with pytest.raises(ValueError):
            parse_stage6_choice(bad)
