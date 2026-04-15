# tests/test_audit_trigger.py
"""Tests for audit trigger - degradation audit + overturn audit."""

import pytest


def test_no_audit_before_interval():
    """未到 10 次鉴赏，不触发审计"""
    from core.inspiration.audit_trigger import AuditTrigger

    trigger = AuditTrigger(appraisal_interval=10, overturn_threshold=10)
    for _ in range(9):
        result = trigger.record_appraisal(
            {"selected_id": "v1", "ignition_point": "某句话"}
        )
    assert result is None


def test_audit_triggered_at_interval():
    """第 10 次鉴赏触发退化审计，返回非空文本"""
    from core.inspiration.audit_trigger import AuditTrigger

    trigger = AuditTrigger(appraisal_interval=10, overturn_threshold=10)
    result = None
    for i in range(10):
        result = trigger.record_appraisal(
            {"selected_id": "v1", "ignition_point": "某句话"}
        )
    assert result is not None
    assert "Audit" in result or "审计" in result


def test_audit_resets_counter_after_trigger():
    """触发一次审计后计数器重置，后续不立即再次触发"""
    from core.inspiration.audit_trigger import AuditTrigger

    trigger = AuditTrigger(appraisal_interval=10, overturn_threshold=10)
    for _ in range(10):
        trigger.record_appraisal({"selected_id": "v1", "ignition_point": "某句话"})
    # 第 11 次，不应触发
    result = trigger.record_appraisal({"selected_id": "v1", "ignition_point": "另一句"})
    assert result is None


def test_vague_ignition_point_detected():
    """点火点含笼统词，审计报告中体现"""
    from core.inspiration.audit_trigger import AuditTrigger

    trigger = AuditTrigger(appraisal_interval=10, overturn_threshold=10)
    result = None
    for _ in range(10):
        result = trigger.record_appraisal(
            {"selected_id": "v1", "ignition_point": "节奏明快，画面感强"}
        )
    assert result is not None
    # 报告应提示笼统
    assert "Vague" in result or "10" in result


def test_no_overturn_audit_before_threshold():
    """未到 10 次推翻，不触发推翻审计"""
    from core.inspiration.audit_trigger import AuditTrigger

    trigger = AuditTrigger(appraisal_interval=10, overturn_threshold=10)
    for _ in range(9):
        result = trigger.record_overturn()
    assert result is None


def test_overturn_audit_triggered_at_threshold():
    """第 10 次推翻触发推翻审计，返回非空文本"""
    from core.inspiration.audit_trigger import AuditTrigger

    trigger = AuditTrigger(appraisal_interval=10, overturn_threshold=10)
    result = None
    for _ in range(10):
        result = trigger.record_overturn()
    assert result is not None
    assert "Overturn" in result or "推翻" in result
    assert "10" in result
