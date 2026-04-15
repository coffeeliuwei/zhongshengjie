# tests/test_feedback_collector_connection.py
"""Tests for FeedbackCollector connection to conversation flow."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_has_feedback_signal_true():
    from core.feedback.feedback_collector import FeedbackCollector

    assert FeedbackCollector.has_feedback_signal("重写这段，节奏太慢") is True
    assert FeedbackCollector.has_feedback_signal("这段风格不对") is True
    assert FeedbackCollector.has_feedback_signal("太啰嗦了") is True


def test_has_feedback_signal_false():
    from core.feedback.feedback_collector import FeedbackCollector

    assert FeedbackCollector.has_feedback_signal("帮我写第三章") is False
    assert FeedbackCollector.has_feedback_signal("今天天气不错") is False


def test_save_and_load_history(tmp_path):
    from core.feedback.feedback_collector import FeedbackCollector

    path = tmp_path / "feedback_history.json"
    collector = FeedbackCollector()
    collector.feedback_history = [
        {"feedback_type": "rewrite_request", "issue": "节奏太慢"}
    ]
    collector.save_history(path)

    collector2 = FeedbackCollector()
    collector2.load_history(path)
    assert len(collector2.feedback_history) == 1
    assert collector2.feedback_history[0]["issue"] == "节奏太慢"


def test_load_history_missing_file(tmp_path):
    """文件不存在时 load_history 不报错"""
    from core.feedback.feedback_collector import FeedbackCollector

    collector = FeedbackCollector()
    collector.load_history(tmp_path / "nonexistent.json")
    assert collector.feedback_history == []


def test_save_history_creates_parent_dir(tmp_path):
    from core.feedback.feedback_collector import FeedbackCollector

    path = tmp_path / "subdir" / "feedback_history.json"
    collector = FeedbackCollector()
    collector.feedback_history = [{"feedback_type": "quality_feedback"}]
    collector.save_history(path)
    assert path.exists()


def test_inject_feedback_context_adds_to_result_data():
    from core.conversation.conversation_entry_layer import (
        ConversationEntryLayer,
        ProcessingResult,
        ProcessingStatus,
    )

    layer = ConversationEntryLayer.__new__(ConversationEntryLayer)
    layer._pending_feedback_context = {
        "feedback_type": "rewrite_request",
        "issue": "节奏太慢",
        "severity": "high",
        "scene_type": None,
    }

    result = ProcessingResult(
        status=ProcessingStatus.SUCCESS,
        intent="test_intent",
        entities={},
        message="ok",
        data=None,
    )
    result = layer._inject_feedback_context(result)

    assert result.data is not None
    assert result.data["feedback_context"]["feedback_type"] == "rewrite_request"
    assert result.data["feedback_context"]["issue"] == "节奏太慢"


def test_inject_feedback_context_no_pending():
    from core.conversation.conversation_entry_layer import (
        ConversationEntryLayer,
        ProcessingResult,
        ProcessingStatus,
    )

    layer = ConversationEntryLayer.__new__(ConversationEntryLayer)
    layer._pending_feedback_context = None

    result = ProcessingResult(
        status=ProcessingStatus.SUCCESS,
        intent="test_intent",
        entities={},
        message="ok",
        data={"existing": "value"},
    )
    result = layer._inject_feedback_context(result)
    assert "feedback_context" not in result.data
    assert result.data["existing"] == "value"


def test_inject_feedback_context_merges_existing_data():
    from core.conversation.conversation_entry_layer import (
        ConversationEntryLayer,
        ProcessingResult,
        ProcessingStatus,
    )

    layer = ConversationEntryLayer.__new__(ConversationEntryLayer)
    layer._pending_feedback_context = {
        "feedback_type": "style_feedback",
        "issue": "文风太正式",
    }

    result = ProcessingResult(
        status=ProcessingStatus.SUCCESS,
        intent="test_intent",
        entities={},
        message="ok",
        data={"mode": "incremental"},
    )
    result = layer._inject_feedback_context(result)
    assert result.data["mode"] == "incremental"
    assert result.data["feedback_context"]["feedback_type"] == "style_feedback"
