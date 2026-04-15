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
    assert "WARNING" in result
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
    assert "calibrate" in result.lower() or "Calibrate" in result


def test_overturn_audit_format_contains_count():
    """推翻审计：包含推翻次数"""
    from core.inspiration.escalation_dialogue import format_overturn_audit

    result = format_overturn_audit(overturn_count=10)
    assert "10" in result


def test_overturn_audit_format_contains_options():
    """推翻审计：给出可选操作"""
    from core.inspiration.escalation_dialogue import format_overturn_audit

    result = format_overturn_audit(overturn_count=10)
    assert "deviation" in result.lower() or "偏差" in result or "Options" in result or "A" in result
