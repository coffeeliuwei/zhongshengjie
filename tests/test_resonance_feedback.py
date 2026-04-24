# tests/test_resonance_feedback.py
"""Tests for resonance feedback handler."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def test_extract_polarity_from_positive_words():
    from core.inspiration.resonance_feedback import _extract_signal

    sig = _extract_signal("第2章末尾那段反打写得很解气")
    assert sig["polarity"] == "+"
    assert sig["resonance_type"] == "爽快"
    assert sig["intensity"] >= 2


def test_extract_polarity_from_negative_words():
    from core.inspiration.resonance_feedback import _extract_signal

    sig = _extract_signal("那段有点出戏")
    assert sig["polarity"] == "-"
    assert sig["resonance_type"] == "出戏"
    assert sig["intensity"] == 1


def test_extract_chapter_ref():
    from core.inspiration.resonance_feedback import _extract_signal

    sig = _extract_signal("第3章开头写得震撼")
    assert sig["chapter_ref"] == "第3章"


def test_extract_location_hint():
    from core.inspiration.resonance_feedback import _extract_signal

    sig = _extract_signal("第2章末尾那段很燃")
    assert sig["location_hint"] == "末尾"


def test_extract_intensity_very_strong():
    from core.inspiration.resonance_feedback import _extract_signal

    sig = _extract_signal("那段非常太震撼了")
    assert sig["intensity"] == 3


def test_handle_feedback_missing_chapter_ref():
    from core.inspiration.resonance_feedback import handle_reader_feedback

    mock_sync = MagicMock()
    result = handle_reader_feedback(
        user_input="那段写得很好",
        scene_type_lookup=lambda ch: "打脸",
        sync=mock_sync,
    )
    assert result["status"] == "needs_clarification"
    mock_sync.create.assert_not_called()


def test_handle_feedback_creates_memory_point(tmp_path):
    """成功处理反馈时创建记忆点"""
    from core.inspiration.resonance_feedback import handle_reader_feedback

    # 创建临时章节文件
    chapter_file = tmp_path / "正文" / "第2章.md"
    chapter_file.parent.mkdir(parents=True, exist_ok=True)
    chapter_file.write_text("苍山如海。他立在风口。屋檐在滴水。", encoding="utf-8")

    mock_sync = MagicMock()
    mock_sync.create.return_value = "mp_20260415_001"

    # Mock _resolve_chapter_path
    with patch(
        "core.inspiration.resonance_feedback._resolve_chapter_path",
        return_value=chapter_file,
    ):
        result = handle_reader_feedback(
            user_input="第2章末尾那段很震撼",
            scene_type_lookup=lambda ch: "高潮",
            sync=mock_sync,
        )

    assert result["status"] == "ok"
    assert len(result["memory_point_ids"]) >= 1
    mock_sync.create.assert_called()


def test_extract_signal_default_resonance():
    """无法识别具体情绪时默认为震撼"""
    from core.inspiration.resonance_feedback import _extract_signal

    sig = _extract_signal("第5章那段写得不错")
    assert sig["polarity"] == "+"
