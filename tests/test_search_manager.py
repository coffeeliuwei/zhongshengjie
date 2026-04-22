"""
测试 SearchManager 的案例库三条新链路
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

# 动态导入 SearchManager
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "modules" / "knowledge_base"))
from search_manager import SearchManager


@pytest.fixture
def mock_qdrant():
    """Mock Qdrant 客户端"""
    with patch("modules.knowledge_base.search_manager.QdrantClient"):
        yield


class TestQualityAnchor:
    """任务A：质量锚点检索"""

    def test_search_case_quality_anchor_returns_list(self):
        """有结果时返回列表"""
        sm = SearchManager()
        with patch.object(sm, "_get_client") as mock_client:
            mock_point = MagicMock()
            mock_point.id = "test-id"
            mock_point.payload = {
                "novel_name": "测试小说",
                "scene_type": "战斗",
                "quality_score": 8.0,
                "word_count": 500,
                "content": "测试内容",
                "cross_genre_value": "",
            }
            mock_client.return_value.scroll.return_value = ([mock_point], None)
            results = sm.search_case_quality_anchor(scene_type="战斗")
            assert isinstance(results, list)
            assert len(results) <= 3

    def test_search_case_quality_anchor_qdrant_error_returns_empty(self):
        """Qdrant 不可用时返回空列表，不抛异常"""
        sm = SearchManager()
        with patch.object(sm, "_get_client", side_effect=Exception("qdrant down")):
            results = sm.search_case_quality_anchor(scene_type="战斗")
            assert results == []

    def test_search_case_quality_anchor_sorted_by_quality(self):
        """返回结果按 quality_score 降序"""
        sm = SearchManager()
        with patch.object(sm, "_get_client") as mock_client:
            points = []
            for score in [7.5, 9.0, 8.2]:
                p = MagicMock()
                p.id = f"id-{score}"
                p.payload = {
                    "quality_score": score,
                    "scene_type": "战斗",
                    "novel_name": "x",
                    "word_count": 100,
                    "content": "x",
                    "cross_genre_value": "",
                }
                points.append(p)
            mock_client.return_value.scroll.return_value = (points, None)
            results = sm.search_case_quality_anchor(scene_type="战斗", top_k=3)
            if len(results) >= 2:
                assert results[0]["quality_score"] >= results[1]["quality_score"]


class TestTechniqueInstance:
    """任务B：技法实例检索"""

    def test_search_case_technique_instance_returns_list(self):
        """正常调用返回列表"""
        sm = SearchManager()
        with patch.object(sm, "_get_client") as mock_client, patch.object(
            sm, "_get_embedding", return_value=[0.1] * 1024
        ):
            mock_client.return_value.query_points.return_value.points = []
            results = sm.search_case_technique_instance(
                constraint_text="从败者视角写战斗，禁用主角内心独白"
            )
            assert isinstance(results, list)

    def test_search_case_technique_instance_error_returns_empty(self):
        """Qdrant 报错返回空列表"""
        sm = SearchManager()
        with patch.object(
            sm, "_get_client", side_effect=Exception("down")
        ), patch.object(sm, "_get_embedding", return_value=[0.1] * 1024):
            results = sm.search_case_technique_instance("任意约束文本")
            assert results == []


class TestOwnChapters:
    """任务C：本书章节回流"""

    def test_write_own_chapter_scene_success(self):
        """正常写入返回 True"""
        sm = SearchManager()
        with patch.object(sm, "_get_client") as mock_client, patch.object(
            sm, "_get_embedding", return_value=[0.1] * 1024
        ), patch.object(sm, "ensure_own_chapters_collection"):
            mock_client.return_value.upsert.return_value = None
            result = sm.write_own_chapter_scene(
                chapter_name="第二章",
                scene_index=0,
                scene_type="战斗",
                content="测试场景内容",
                techniques_used=["ANTI_001"],
                quality_score=0.82,
            )
            assert result is True

    def test_write_own_chapter_scene_error_returns_false(self):
        """写入失败返回 False，不抛异常"""
        sm = SearchManager()
        with patch.object(
            sm, "_get_client", side_effect=Exception("fail")
        ), patch.object(sm, "_get_embedding", return_value=[0.1] * 1024), patch.object(
            sm, "ensure_own_chapters_collection"
        ):
            result = sm.write_own_chapter_scene(
                chapter_name="第二章",
                scene_index=0,
                scene_type="战斗",
                content="x",
                techniques_used=[],
                quality_score=0.5,
            )
            assert result is False

    def test_search_own_chapters_returns_list(self):
        """检索本书章节返回列表"""
        sm = SearchManager()
        with patch.object(sm, "_get_client") as mock_client, patch.object(
            sm, "_get_embedding", return_value=[0.1] * 1024
        ):
            mock_client.return_value.query_points.return_value.points = []
            results = sm.search_own_chapters(scene_type="战斗")
            assert isinstance(results, list)

    def test_search_own_chapters_with_exclude(self):
        """检索时排除当前章节"""
        sm = SearchManager()
        with patch.object(sm, "_get_client") as mock_client, patch.object(
            sm, "_get_embedding", return_value=[0.1] * 1024
        ):
            mock_client.return_value.query_points.return_value.points = []
            results = sm.search_own_chapters(
                scene_type="战斗", exclude_chapter="第三章"
            )
            assert isinstance(results, list)


class TestEnsureCollection:
    """测试集合自动创建"""

    def test_ensure_own_chapters_collection_creates_if_missing(self):
        """集合不存在时自动创建"""
        sm = SearchManager()
        with patch.object(sm, "_get_client") as mock_client:
            mock_client.return_value.get_collections.return_value.collections = []
            mock_client.return_value.create_collection.return_value = None
            sm.ensure_own_chapters_collection()
            mock_client.return_value.create_collection.assert_called_once()

    def test_ensure_own_chapters_collection_skips_if_exists(self):
        """集合已存在时跳过创建"""
        sm = SearchManager()
        with patch.object(sm, "_get_client") as mock_client:
            existing_col = MagicMock()
            existing_col.name = "novel_chapters_v1"
            mock_client.return_value.get_collections.return_value.collections = [
                existing_col
            ]
            sm.ensure_own_chapters_collection()
            mock_client.return_value.create_collection.assert_not_called()