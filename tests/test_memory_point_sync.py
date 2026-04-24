# tests/test_memory_point_sync.py
"""Tests for memory point library sync operations."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_qdrant():
    """Mock QdrantClient"""
    with patch("core.inspiration.memory_point_sync.QdrantClient") as mock_cls:
        instance = MagicMock()
        mock_cls.return_value = instance
        instance.search.return_value = []
        yield instance


def test_create_memory_point_returns_id(mock_qdrant):
    """创建记忆点返回 ID"""
    from core.inspiration.memory_point_sync import MemoryPointSync

    sync = MemoryPointSync(client=mock_qdrant)
    mp_id = sync.create(
        {
            "segment_text": "屋檐在滴水",
            "resonance_type": "爽快",
            "polarity": "+",
            "intensity": 3,
            "scene_type": "打脸",
            "writer_agent": "novelist-jianchen",
        }
    )
    assert mp_id.startswith("mp_")
    mock_qdrant.upsert.assert_called_once()


def test_create_assigns_default_reader_fields(mock_qdrant):
    """创建时自动填充 reader_id 和 reader_cluster"""
    from core.inspiration.memory_point_sync import MemoryPointSync

    sync = MemoryPointSync(client=mock_qdrant)
    sync.create(
        {
            "segment_text": "X",
            "resonance_type": "爽快",
            "polarity": "+",
            "intensity": 2,
            "scene_type": "战斗",
        }
    )
    call = mock_qdrant.upsert.call_args
    points = call.kwargs.get("points") or call.args[1]
    payload = points[0].payload
    assert payload["reader_id"] == "author"
    assert payload["reader_cluster"] == "default"


def test_create_with_overturn_event_sets_weight_2(mock_qdrant):
    """推翻事件的 retrieval_weight=2"""
    from core.inspiration.memory_point_sync import MemoryPointSync

    sync = MemoryPointSync(client=mock_qdrant)
    sync.create(
        {
            "segment_text": "X",
            "resonance_type": "出戏",
            "polarity": "-",
            "intensity": 2,
            "scene_type": "战斗",
            "overturn_event": {
                "rater_selected": True,
                "evaluator_approved": True,
                "conflict_type": "rater+evaluator_vs_user",
            },
        }
    )
    call = mock_qdrant.upsert.call_args
    points = call.kwargs.get("points") or call.args[1]
    payload = points[0].payload
    assert payload["retrieval_weight"] == 2


def test_create_normal_feedback_weight_1(mock_qdrant):
    """普通反馈的 retrieval_weight=1"""
    from core.inspiration.memory_point_sync import MemoryPointSync

    sync = MemoryPointSync(client=mock_qdrant)
    sync.create(
        {
            "segment_text": "X",
            "resonance_type": "爽快",
            "polarity": "+",
            "intensity": 3,
            "scene_type": "战斗",
        }
    )
    call = mock_qdrant.upsert.call_args
    points = call.kwargs.get("points") or call.args[1]
    payload = points[0].payload
    assert payload["retrieval_weight"] == 1


def test_count_returns_total(mock_qdrant):
    """count 返回总数"""
    from core.inspiration.memory_point_sync import MemoryPointSync

    sync = MemoryPointSync(client=mock_qdrant)
    mock_qdrant.count.return_value = MagicMock(count=42)
    assert sync.count() == 42


def test_search_similar_uses_filters(mock_qdrant):
    """search_similar 使用过滤器"""
    from core.inspiration.memory_point_sync import MemoryPointSync

    sync = MemoryPointSync(client=mock_qdrant)
    sync.search_similar(
        embedding=[0.0] * 1024,
        scene_type="战斗",
        top_k=3,
    )
    mock_qdrant.search.assert_called_once()


def test_count_overturn_events(mock_qdrant):
    """count_overturn_events 统计推翻事件"""
    from core.inspiration.memory_point_sync import MemoryPointSync

    sync = MemoryPointSync(client=mock_qdrant)
    mock_qdrant.count.return_value = MagicMock(count=5)
    assert sync.count_overturn_events() == 5


def test_get_stats_returns_phase(mock_qdrant):
    """get_stats 返回阶段信息"""
    from core.inspiration.memory_point_sync import MemoryPointSync

    sync = MemoryPointSync(client=mock_qdrant)
    mock_qdrant.count.return_value = MagicMock(count=100)
    stats = sync.get_stats()
    assert "total_count" in stats
    assert "phase" in stats
    assert stats["total_count"] == 100
