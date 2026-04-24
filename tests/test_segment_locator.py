# tests/test_segment_locator.py
"""Tests for natural-language segment locator."""

import sys
from pathlib import Path
import pytest

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


SAMPLE_CHAPTER_2 = """苍山如海，残阳如血。

他立在风口，身后是三千铁骑。

他抬手时，屋檐在滴水。
"""


@pytest.fixture
def fake_chapter_file(tmp_path):
    """创建临时章节文件"""
    chapter_file = tmp_path / "第2章.md"
    chapter_file.write_text(SAMPLE_CHAPTER_2, encoding="utf-8")
    return chapter_file


def test_locate_by_location_hint_end(fake_chapter_file):
    """'末尾' 定位到最后一段"""
    from core.inspiration.segment_locator import locate_segment

    result = locate_segment(
        chapter_file=fake_chapter_file,
        location_hint="末尾",
        keyword=None,
    )
    assert result is not None
    assert "屋檐在滴水" in result["segment_text"]
    assert result["segment_scope"] == "paragraph"


def test_locate_by_keyword_found_in_text(fake_chapter_file):
    """关键词定位到含该词的段"""
    from core.inspiration.segment_locator import locate_segment

    result = locate_segment(
        chapter_file=fake_chapter_file,
        location_hint=None,
        keyword="屋檐",  # 使用实际存在的关键词
    )
    assert result is not None
    assert "屋檐" in result["segment_text"]


def test_locate_by_position_hint_beginning(fake_chapter_file):
    """'开头' 定位到第一段"""
    from core.inspiration.segment_locator import locate_segment

    result = locate_segment(
        chapter_file=fake_chapter_file,
        location_hint="开头",
        keyword=None,
    )
    assert result is not None
    assert "苍山如海" in result["segment_text"]


def test_locate_by_position_hint_middle(fake_chapter_file):
    """'中间' 定位到中间段"""
    from core.inspiration.segment_locator import locate_segment

    result = locate_segment(
        chapter_file=fake_chapter_file,
        location_hint="中间",
        keyword=None,
    )
    assert result is not None
    # 中间段应在第2-3段之间
    assert "立在风口" in result["segment_text"] or "三千铁骑" in result["segment_text"]


def test_locate_returns_none_when_not_found(fake_chapter_file):
    """找不到时返回 None"""
    from core.inspiration.segment_locator import locate_segment

    result = locate_segment(
        chapter_file=fake_chapter_file,
        location_hint=None,
        keyword="不存在的词xxxxx",
    )
    assert result is None


def test_locate_position_hint_with_keyword_combined(fake_chapter_file):
    """'末尾屋檐' 同时使用位置和关键词"""
    from core.inspiration.segment_locator import locate_segment

    result = locate_segment(
        chapter_file=fake_chapter_file,
        location_hint="末尾",
        keyword="屋檐",  # 使用实际存在的关键词
    )
    assert result is not None
    assert "屋檐" in result["segment_text"]
    assert result["position_hint"]["paragraph_index"] == 2  # 0-based


def test_locate_file_not_exists():
    """文件不存在返回 None"""
    from core.inspiration.segment_locator import locate_segment

    result = locate_segment(
        chapter_file=Path("/nonexistent/file.md"),
        location_hint=None,
        keyword="test",
    )
    assert result is None
