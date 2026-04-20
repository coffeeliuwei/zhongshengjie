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


def test_record_winner_writes_positive_memory_point():
    """鉴赏师选出赢家时，写入正向记忆点"""
    from core.inspiration.workflow_bridge import record_winner
    from core.inspiration.appraisal_agent import AppraisalResult
    from unittest.mock import patch, MagicMock

    winner = AppraisalResult(
        selected_id="variant_1",
        ignition_point="那句'屋檐滴水'击中了我",
        reason_fragment="结构感与正向参照最近",
        confidence="high",
    )
    candidates = [
        {"id": "baseline", "text": "普通文本", "used_constraint_id": None},
        {"id": "variant_1", "text": "击中文本", "used_constraint_id": "CONSTRAINT_001"},
    ]
    scene_context = {"scene_type": "情感"}

    mock_sync = MagicMock()
    mock_sync.create.return_value = "mp_winner_001"

    with (
        patch(
            "core.inspiration.workflow_bridge.MemoryPointSync", return_value=mock_sync
        ),
        patch(
            "core.inspiration.workflow_bridge._embed_scene_context",
            return_value=[0.1] * 1024,
        ),
    ):
        mp_id = record_winner(
            appraisal=winner,
            candidates=candidates,
            scene_context=scene_context,
        )

    assert mp_id == "mp_winner_001"
    call_kwargs = mock_sync.create.call_args[0][0]  # payload
    assert call_kwargs["polarity"] == "+"
    assert call_kwargs["segment_text"] == "击中文本"
    assert call_kwargs["resonance_type"] == "鉴赏师选中"


def test_record_winner_skips_write_when_none_selected():
    """鉴赏师返回 none（全部平庸）时，不写入记忆点"""
    from core.inspiration.workflow_bridge import record_winner
    from core.inspiration.appraisal_agent import AppraisalResult
    from unittest.mock import patch, MagicMock

    no_winner = AppraisalResult(
        selected_id=None,
        ignition_point=None,
        reason_fragment=None,
        confidence="low",
        common_flaw="三段都是正确但平庸的写法",
    )
    mock_sync = MagicMock()

    with patch(
        "core.inspiration.workflow_bridge.MemoryPointSync", return_value=mock_sync
    ):
        mp_id = record_winner(
            appraisal=no_winner,
            candidates=[],
            scene_context={"scene_type": "情感"},
        )

    assert mp_id is None
    mock_sync.create.assert_not_called()


@pytest.mark.skip(reason="v2 P1-5: variant flow 已移除；v2 Stage 4 全流程待 P2 集成后重写")
def test_stage4_full_flow_with_mocks():
    """Stage 4 完整流程：specs → 变体生成 → 鉴赏师 → 记录"""
    from core.inspiration.workflow_bridge import (
        phase1_dispatch,
        execute_variants,
        select_winner_spec,
        record_winner,
    )
    from core.inspiration.appraisal_agent import parse_appraisal_response
    from unittest.mock import patch, MagicMock

    scene_type = "情感"
    scene_context = {"scene_type": "情感", "chapter_ref": "第一章"}
    config = {"inspiration_engine": {"enabled": True, "variant_count": 2}}

    # Step 1: phase1_dispatch
    with patch("core.inspiration.workflow_bridge.generate_variant_specs") as mock_gen:
        mock_gen.return_value = [
            {
                "id": "baseline",
                "writer_agent": "novelist-yunxi",
                "used_constraint_id": None,
                "scene_type": "情感",
                "prompt": "写情感",
            },
            {
                "id": "v1",
                "writer_agent": "novelist-yunxi",
                "used_constraint_id": "C001",
                "scene_type": "情感",
                "prompt": "写情感（约束）",
            },
        ]
        dispatch = phase1_dispatch(
            scene_type=scene_type,
            scene_context=scene_context,
            original_writers=["云溪"],
            config=config,
        )

    assert dispatch["mode"] == "variants"
    specs = dispatch["variant_specs"]

    # Step 2: execute_variants（mock writer）
    def fake_writer(spec):
        return f"生成内容_{spec['id']}"

    candidates = execute_variants(specs=specs, writer_caller=fake_writer)
    assert len(candidates) == 2
    assert candidates[0]["text"] == "生成内容_baseline"

    # Step 3: select_winner_spec + 鉴赏师调用（mock）
    with (
        patch("core.inspiration.workflow_bridge.MemoryPointSync") as MockSync,
        patch(
            "core.inspiration.workflow_bridge._embed_scene_context",
            return_value=[0.0] * 1024,
        ),
    ):
        MockSync.return_value.count.return_value = 10  # 冷启动
        winner_spec = select_winner_spec(
            candidates=candidates,
            scene_context=scene_context,
        )

    assert winner_spec["skill_name"] == "novelist-connoisseur"
    assert winner_spec["phase"] == "cold"

    # Step 4: parse_appraisal_response（mock Claude 返回）
    fake_response = '{"selected_id": "v1", "ignition_point": "那句话击中了我", "confidence": "high"}'
    appraisal = parse_appraisal_response(fake_response)
    assert appraisal.selected_id == "v1"

    # Step 5: record_winner
    mock_sync = MagicMock()
    mock_sync.create.return_value = "mp_001"
    with (
        patch(
            "core.inspiration.workflow_bridge.MemoryPointSync", return_value=mock_sync
        ),
        patch(
            "core.inspiration.workflow_bridge._embed_scene_context",
            return_value=[0.1] * 1024,
        ),
    ):
        mp_id = record_winner(
            appraisal=appraisal,
            candidates=candidates,
            scene_context=scene_context,
        )

    assert mp_id == "mp_001"
