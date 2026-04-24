"""两套反馈系统统一测试"""

import pytest
from unittest.mock import patch, MagicMock


def test_dispatcher_routes_inspiration_feedback_to_resonance():
    """灵感引擎类反馈 → resonance_feedback"""
    from core.feedback.feedback_dispatcher import FeedbackDispatcher

    mock_resonance = MagicMock(
        return_value={
            "status": "ok",
            "memory_point_ids": ["mp_001"],
            "message": "已记录",
        }
    )

    with patch(
        "core.feedback.feedback_dispatcher.handle_reader_feedback", mock_resonance
    ):
        dispatcher = FeedbackDispatcher()
        result = dispatcher.dispatch(
            feedback_category="inspiration",
            user_input="第二章那句话很震撼",
            scene_type_lookup=lambda ch: "情感",
        )

    mock_resonance.assert_called_once()
    assert result["source"] == "resonance"


def test_dispatcher_routes_quality_feedback_to_collector():
    """写作质量类反馈 → feedback_collector"""
    from core.feedback.feedback_dispatcher import FeedbackDispatcher
    from pathlib import Path

    mock_collector = MagicMock()
    mock_collector.collect_from_explicit.return_value = {
        "feedback_type": "rewrite_request",
        "issue": "节奏太慢",
        "severity": "high",
    }
    mock_collector.save_history = MagicMock()

    with patch(
        "core.feedback.feedback_dispatcher.FeedbackCollector",
        return_value=mock_collector,
    ):
        dispatcher = FeedbackDispatcher(history_path=Path("/tmp/fb.json"))
        result = dispatcher.dispatch(
            feedback_category="quality",
            user_input="重写，节奏太慢",
        )

    mock_collector.collect_from_explicit.assert_called_once_with("重写，节奏太慢")
    assert result["source"] == "collector"
    assert result["feedback_type"] == "rewrite_request"


def test_dispatcher_returns_combined_summary():
    """dispatch 结果包含统一格式的 summary"""
    from core.feedback.feedback_dispatcher import FeedbackDispatcher
    from pathlib import Path

    mock_collector = MagicMock()
    mock_collector.collect_from_explicit.return_value = {
        "feedback_type": "style_feedback",
        "issue": "文风太正式",
        "severity": "medium",
        "scene_type": None,
    }
    mock_collector.save_history = MagicMock()

    with patch(
        "core.feedback.feedback_dispatcher.FeedbackCollector",
        return_value=mock_collector,
    ):
        dispatcher = FeedbackDispatcher(history_path=Path("/tmp/fb.json"))
        result = dispatcher.dispatch(
            feedback_category="quality",
            user_input="风格不对，太正式了",
        )

    assert "summary" in result
    assert result["summary"]["polarity"] in ("+", "-", "?")
    assert "issue" in result["summary"]


def test_feedback_processor_can_read_history_json(tmp_path):
    """FeedbackProcessor 能从 feedback_history.json 读取历史并分析"""
    import json

    history_file = tmp_path / "feedback_history.json"
    history_file.write_text(
        json.dumps(
            [
                {
                    "feedback_type": "rewrite_request",
                    "issue": "节奏太慢",
                    "severity": "high",
                    "feedback_category": "negative",
                    "scene_type": "战斗",
                    "raw_input": "重写，节奏太慢",
                },
                {
                    "feedback_type": "rewrite_request",
                    "issue": "节奏太慢",
                    "severity": "high",
                    "feedback_category": "negative",
                    "scene_type": "战斗",
                    "raw_input": "又是节奏太慢",
                },
                {
                    "feedback_type": "style_feedback",
                    "issue": "文风太正式",
                    "severity": "medium",
                    "feedback_category": "style",
                    "scene_type": None,
                    "raw_input": "风格不对",
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    from core.feedback.feedback_processor import FeedbackProcessor

    fp = FeedbackProcessor()
    summary = fp.analyze_history_file(history_file)

    assert summary["total"] == 3
    assert summary["most_common_type"] == "rewrite_request"
    assert summary["negative_count"] >= 2
