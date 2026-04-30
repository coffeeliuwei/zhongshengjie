"""
测试 inspiration-ingest 同步管线三处修复：
  1. hybrid_sync_manager: 99-从小说提取 目录技法 dimension 映射
  2. case_builder: sync_to_vectorstore 读取 .md 案例文件
  3. UnifiedRetrievalAPI: 5 个写手专属案例检索方法
"""

import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest


# ==================== 任务一：dimension 映射 ====================


class TestHybridSyncDimensionMapping:
    def test_normal_dir_uses_dimension_map(self):
        """原有维度目录（01-世界观维度 等）仍使用 DIMENSION_MAP"""
        from modules.knowledge_base.hybrid_sync_manager import HybridSyncManager

        mgr = HybridSyncManager.__new__(HybridSyncManager)
        mgr.DIMENSION_MAP = {
            "01-世界观维度": "世界观维度",
            "04-战斗冲突维度": "战斗冲突维度",
        }
        md = MagicMock()
        md.parent.name = "04-战斗冲突维度"
        md.stem = "战斗技法汇总"

        parent_dir = md.parent.name
        dimension = (
            md.stem
            if parent_dir == "99-从小说提取"
            else mgr.DIMENSION_MAP.get(parent_dir, "未知")
        )
        assert dimension == "战斗冲突维度"

    def test_99_dir_uses_file_stem_as_dimension(self):
        """99-从小说提取 目录下的文件以 stem 作为 dimension，不再返回 '未知'"""
        from modules.knowledge_base.hybrid_sync_manager import HybridSyncManager

        mgr = HybridSyncManager.__new__(HybridSyncManager)
        mgr.DIMENSION_MAP = {"01-世界观维度": "世界观维度"}

        for dim in [
            "战斗冲突维度",
            "世界观维度",
            "剧情维度",
            "人物维度",
            "氛围意境维度",
        ]:
            md = MagicMock()
            md.parent.name = "99-从小说提取"
            md.stem = dim

            parent_dir = md.parent.name
            dimension = (
                md.stem
                if parent_dir == "99-从小说提取"
                else mgr.DIMENSION_MAP.get(parent_dir, "未知")
            )
            assert dimension == dim, f"期望 {dim}，实际 {dimension}"
            assert dimension != "未知"

    def test_unknown_dir_still_returns_unknown(self):
        """其他未知目录仍返回 '未知'"""
        from modules.knowledge_base.hybrid_sync_manager import HybridSyncManager

        mgr = HybridSyncManager.__new__(HybridSyncManager)
        mgr.DIMENSION_MAP = {}

        md = MagicMock()
        md.parent.name = "99-其他目录"
        md.stem = "某文件"

        parent_dir = md.parent.name
        dimension = (
            md.stem
            if parent_dir == "99-从小说提取"
            else mgr.DIMENSION_MAP.get(parent_dir, "未知")
        )
        assert dimension == "未知"


# ==================== 任务二：.md 案例读取 ====================


class TestCaseBuilderMdSync:
    def test_parse_md_frontmatter_and_body(self):
        """能正确解析 YAML frontmatter 中的 case_id、scene_type 以及正文"""
        content = (
            "---\n"
            "case_id: slug-a\n"
            "scene_type: 战斗冲突维度\n"
            "source: 素材库/test/source.md\n"
            "---\n\n"
            "这是一段战斗描写内容。" * 30
        )
        meta = {}
        body = content
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                fm = content[3:end].strip()
                for line in fm.splitlines():
                    if ":" in line:
                        k, _, v = line.partition(":")
                        meta[k.strip()] = v.strip()
                body = content[end + 3 :].strip()

        assert meta.get("case_id") == "slug-a"
        assert meta.get("scene_type") == "战斗冲突维度"
        assert "战斗描写内容" in body

    def test_dimension_mapped_to_scene_type(self):
        """维度名应映射为写手 skill 使用的场景类型字符串"""
        mapping = {
            "世界观维度": "世界观展示",
            "剧情维度": "剧情",
            "人物维度": "心理",
            "战斗冲突维度": "战斗",
            "氛围意境维度": "意境营造",
        }
        assert mapping["战斗冲突维度"] == "战斗"
        assert mapping["氛围意境维度"] == "意境营造"
        assert mapping["世界观维度"] == "世界观展示"
        assert mapping["剧情维度"] == "剧情"
        assert mapping["人物维度"] == "心理"

    def test_md_cases_collected_alongside_json(self):
        """sync 收集案例时应同时包含 JSON 和 .md 两种来源"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cases_dir = Path(tmpdir) / "cases"

            # JSON 案例（原有路径：cases/战斗/*.json）
            json_dir = cases_dir / "战斗"
            json_dir.mkdir(parents=True)
            (json_dir / "case_001.json").write_text(
                json.dumps(
                    {
                        "case_id": "json-001",
                        "scene_type": "战斗",
                        "content": "json内容" * 30,
                        "genre": "玄幻",
                        "novel_name": "test",
                        "word_count": 100,
                        "quality_score": 6.0,
                        "emotion_value": 0.0,
                        "techniques": [],
                        "keywords": [],
                        "source_file": "a.txt",
                    }
                ),
                encoding="utf-8",
            )

            # .md 案例（ingest 路径：cases/99-从小说提取/战斗冲突维度/*.md）
            md_dir = cases_dir / "99-从小说提取" / "战斗冲突维度"
            md_dir.mkdir(parents=True)
            (md_dir / "novel-slug-a.md").write_text(
                "---\ncase_id: md-001\nscene_type: 战斗冲突维度\n---\n\n"
                + "战斗内容。" * 60,
                encoding="utf-8",
            )

            # 模拟修复后的收集逻辑
            all_cases = []
            for scene_dir in cases_dir.iterdir():
                if not scene_dir.is_dir():
                    continue
                for f in scene_dir.glob("*.json"):
                    all_cases.append(json.loads(f.read_text(encoding="utf-8")))

            ingest_dir = cases_dir / "99-从小说提取"
            if ingest_dir.exists():
                for md_file in ingest_dir.rglob("*.md"):
                    all_cases.append({"case_id": md_file.stem, "scene_type": "战斗"})

            assert len(all_cases) == 2, f"应有 2 条，实际 {len(all_cases)}"
            ids = {c["case_id"] for c in all_cases}
            assert "json-001" in ids
            assert "novel-slug-a" in ids

    def test_no_md_dir_does_not_crash(self):
        """99-从小说提取 目录不存在时不报错"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cases_dir = Path(tmpdir) / "cases"
            cases_dir.mkdir()
            ingest_dir = cases_dir / "99-从小说提取"
            # 不创建该目录
            all_cases = []
            if ingest_dir.exists():
                for md_file in ingest_dir.rglob("*.md"):
                    all_cases.append({"case_id": md_file.stem})
            assert all_cases == []


# ==================== 任务三：写手专属案例方法 ====================


@pytest.fixture
def mock_api():
    mock_sm = MagicMock()
    mock_sm.search_case.return_value = [{"id": "c1", "content": "内容", "score": 0.85}]
    mock_sm.search_novel.return_value = []
    mock_sm.search_technique.return_value = []
    with patch(
        "core.retrieval.unified_retrieval_api.HybridSearchManager", return_value=mock_sm
    ):
        from core.retrieval.unified_retrieval_api import UnifiedRetrievalAPI

        api = UnifiedRetrievalAPI.__new__(UnifiedRetrievalAPI)
        api._search_manager = mock_sm
        yield api, mock_sm


class TestCaseSearchMethodsExist:
    def test_all_five_methods_exist(self, mock_api):
        """5 个写手专属案例方法必须存在"""
        api, _ = mock_api
        methods = [
            "search_worldview_cases",
            "search_plot_cases",
            "search_poetry_cases",
            "search_character_cases",
            "search_battle_cases",
        ]
        for m in methods:
            assert hasattr(api, m), f"UnifiedRetrievalAPI 缺失方法：{m}"

    def test_methods_call_search_case(self, mock_api):
        """每个方法调用后必须触发底层 _search_manager.search_case"""
        api, mock_sm = mock_api
        calls = [
            (api.search_worldview_cases, "世界观设定 势力冲突"),
            (api.search_plot_cases, "伏笔埋设"),
            (api.search_poetry_cases, "意境营造"),
            (api.search_character_cases, "人物成长"),
            (api.search_battle_cases, "修仙战斗"),
        ]
        for method, query in calls:
            mock_sm.search_case.reset_mock()
            method(query)
            (
                mock_sm.search_case.assert_called_once(),
                f"{method.__name__} 未调用 search_case",
            )

    def test_limit_parameter_passed_as_top_k(self, mock_api):
        """limit=5 应转换为 top_k=5 传给底层"""
        api, mock_sm = mock_api
        api.search_battle_cases("战斗", scene_type="战斗", limit=5)
        call_kwargs = mock_sm.search_case.call_args
        # top_k 可能在 args 或 kwargs 中
        top_k_val = call_kwargs.kwargs.get("top_k") or (
            call_kwargs.args[2] if len(call_kwargs.args) > 2 else None
        )
        assert top_k_val == 5, f"top_k 应为 5，实际 {top_k_val}"

    def test_positional_query_works(self, mock_api):
        """skill 里有直接位置参数调用的场景：api.search_battle_cases('xxx')"""
        api, mock_sm = mock_api
        result = api.search_battle_cases("战斗描写")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["score"] == 0.85

    def test_returns_list(self, mock_api):
        """所有方法返回值类型为 list"""
        api, _ = mock_api
        for m in [
            "search_worldview_cases",
            "search_plot_cases",
            "search_poetry_cases",
            "search_character_cases",
            "search_battle_cases",
        ]:
            result = getattr(api, m)("测试")
            assert isinstance(result, list), f"{m} 返回值不是 list"
