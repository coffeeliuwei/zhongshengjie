# tests/test_workflow_bridge_e_mechanism.py
"""Tests for E mechanism: memory point retrieval into appraisal spec."""

from unittest.mock import MagicMock, patch
import pytest


def test_select_winner_spec_cold_start_no_retrieval():
    """记忆点 < 50 时，不检索参考，返回 phase=cold"""
    from core.inspiration.workflow_bridge import select_winner_spec

    fake_sync = MagicMock()
    fake_sync.count.return_value = 30

    with patch(
        "core.inspiration.workflow_bridge.MemoryPointSync", return_value=fake_sync
    ):
        spec = select_winner_spec(
            candidates=[
                {
                    "id": "v1",
                    "text": "测试文本",
                    "used_constraint_id": None,
                    "writer_agent": "x",
                }
            ],
            scene_context={"scene_type": "打脸"},
        )

    assert spec["phase"] == "cold"
    assert spec["skill_name"] == "novelist-connoisseur"
    fake_sync.search_similar.assert_not_called()


def test_select_winner_spec_growing_retrieves_references():
    """记忆点 >= 50 时，检索参考样本，prompt 中包含参考文本"""
    from core.inspiration.workflow_bridge import select_winner_spec

    fake_sync = MagicMock()
    fake_sync.count.return_value = 100
    fake_sync.search_similar.side_effect = [
        # 正向检索结果
        [
            {
                "id": "mp_1",
                "score": 0.9,
                "payload": {
                    "segment_text": "屋檐滴水",
                    "polarity": "+",
                    "intensity": 3,
                    "note": "",
                },
            }
        ],
        # 负向检索结果
        [
            {
                "id": "mp_2",
                "score": 0.8,
                "payload": {
                    "segment_text": "平淡无奇",
                    "polarity": "-",
                    "intensity": 2,
                    "note": "",
                },
            }
        ],
    ]

    with (
        patch(
            "core.inspiration.workflow_bridge.MemoryPointSync", return_value=fake_sync
        ),
        patch(
            "core.inspiration.workflow_bridge._embed_scene_context",
            return_value=[0.0] * 1024,
        ),
    ):
        spec = select_winner_spec(
            candidates=[
                {
                    "id": "v1",
                    "text": "测试",
                    "used_constraint_id": None,
                    "writer_agent": "x",
                }
            ],
            scene_context={"scene_type": "打脸"},
        )

    assert spec["phase"] == "growing"
    assert "屋檐滴水" in spec["prompt"]
    assert fake_sync.search_similar.call_count == 2


def test_retrieve_references_returns_both_polarities():
    """_retrieve_references_for_appraisal 同时检索正负向记忆点"""
    from core.inspiration.workflow_bridge import _retrieve_references_for_appraisal

    fake_sync = MagicMock()
    fake_sync.search_similar.side_effect = [
        [{"id": "p1", "score": 0.9, "payload": {"polarity": "+"}}],
        [{"id": "n1", "score": 0.7, "payload": {"polarity": "-"}}],
    ]

    refs = _retrieve_references_for_appraisal(
        sync=fake_sync,
        embedding=[0.0] * 1024,
        scene_type="战斗",
        top_k=3,
    )

    polarities = {r["payload"]["polarity"] for r in refs}
    assert "+" in polarities
    assert "-" in polarities
    assert len(refs) == 2
