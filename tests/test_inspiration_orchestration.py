# tests/test_inspiration_orchestration.py
"""灵感引擎编排流程测试"""

import pytest
from unittest.mock import patch, MagicMock


SAMPLE_SPECS = [
    {
        "id": "baseline",
        "writer_agent": "novelist-yunxi",
        "used_constraint_id": None,
        "scene_type": "情感",
        "prompt": "写一段情感场景",
    },
    {
        "id": "variant_1",
        "writer_agent": "novelist-yunxi",
        "used_constraint_id": "CONSTRAINT_001",
        "scene_type": "情感",
        "prompt": "用视角反叛手法写一段情感场景",
    },
]


def test_execute_variants_calls_writer_for_each_spec():
    """execute_variants 为每个 spec 调用 writer_caller"""
    from core.inspiration.workflow_bridge import execute_variants

    call_log = []

    def fake_writer(spec: dict) -> str:
        call_log.append(spec["id"])
        return f"生成文本_{spec['id']}"

    result = execute_variants(specs=SAMPLE_SPECS, writer_caller=fake_writer)

    assert len(call_log) == 2
    assert "baseline" in call_log
    assert "variant_1" in call_log


def test_execute_variants_returns_candidates_with_text():
    """execute_variants 返回含 id/text/used_constraint_id/writer_agent 的列表"""
    from core.inspiration.workflow_bridge import execute_variants

    def fake_writer(spec: dict) -> str:
        return f"文本_{spec['id']}"

    candidates = execute_variants(specs=SAMPLE_SPECS, writer_caller=fake_writer)

    assert len(candidates) == 2
    for c in candidates:
        assert "id" in c
        assert "text" in c
        assert "used_constraint_id" in c
        assert "writer_agent" in c
    assert candidates[0]["text"] == "文本_baseline"
    assert candidates[1]["text"] == "文本_variant_1"


def test_execute_variants_handles_writer_error_gracefully():
    """某个 writer 调用失败时，该变体标记为失败但不中断其他"""
    from core.inspiration.workflow_bridge import execute_variants

    def flaky_writer(spec: dict) -> str:
        if spec["id"] == "variant_1":
            raise RuntimeError("Skill 调用超时")
        return f"文本_{spec['id']}"

    candidates = execute_variants(specs=SAMPLE_SPECS, writer_caller=flaky_writer)

    assert len(candidates) == 2
    baseline = next(c for c in candidates if c["id"] == "baseline")
    failed = next(c for c in candidates if c["id"] == "variant_1")
    assert baseline["text"] == "文本_baseline"
    assert failed["text"] == "[生成失败]"
    assert failed.get("error") is not None
