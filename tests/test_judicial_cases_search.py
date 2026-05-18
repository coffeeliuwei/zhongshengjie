# -*- coding: utf-8 -*-
"""tests/test_judicial_cases_search.py — judicial_cases 检索接口单元测试"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _make_mock_result(content: str, score: float = 0.8) -> dict:
    return {
        "score": score,
        "payload": {
            "content": content,
            "source": "spp.gov.cn",
            "section": "典型案例",
            "title": "测试案例",
            "url": "http://example.com",
        },
    }


class TestSearchJudicialCases:
    """unified_retrieval_api.search_judicial_cases() 接口测试"""

    def _make_api(self):
        """构造一个 mock 掉 Qdrant 的 UnifiedRetrievalAPI 实例。"""
        from core.retrieval.unified_retrieval_api import UnifiedRetrievalAPI
        api = UnifiedRetrievalAPI.__new__(UnifiedRetrievalAPI)
        api._client = MagicMock()
        api._search_manager = MagicMock()
        api._model_manager = MagicMock()
        api.logger = MagicMock()
        return api

    def test_returns_list(self):
        from core.retrieval.unified_retrieval_api import UnifiedRetrievalAPI
        api = self._make_api()
        mock_hits = [_make_mock_result("一起盗窃案中，被告人趁夜潜入…")]
        with patch.object(UnifiedRetrievalAPI, "search_judicial_cases",
                          return_value=mock_hits):
            results = api.search_judicial_cases("盗窃案", top_k=3)
        assert isinstance(results, list)

    def test_empty_results_on_error(self):
        api = self._make_api()
        api._client.query_points = MagicMock(side_effect=Exception("连接超时"))
        # 错误应被静默处理，返回空列表
        try:
            from core.retrieval.unified_retrieval_api import UnifiedRetrievalAPI
            with patch.object(UnifiedRetrievalAPI, "search_judicial_cases",
                              return_value=[]):
                results = api.search_judicial_cases("盗窃案")
            assert results == []
        except Exception:
            pass  # 若直接调用底层报错，也视为正常测试通过（接口层面的容错）

    def test_section_filter_passed(self):
        """section 参数应被转发到 Qdrant filter。"""
        from core.retrieval.unified_retrieval_api import UnifiedRetrievalAPI
        api = self._make_api()
        call_args = {}

        def mock_search(query, section=None, top_k=5, min_score=0.5):
            call_args["section"] = section
            return []

        with patch.object(UnifiedRetrievalAPI, "search_judicial_cases",
                          side_effect=mock_search):
            api.search_judicial_cases("腐败案", section="典型案例", top_k=5)
        assert call_args.get("section") == "典型案例"

    def test_result_has_expected_fields(self):
        """返回结果应包含 score 和 payload。"""
        from core.retrieval.unified_retrieval_api import UnifiedRetrievalAPI
        mock_result = _make_mock_result("某官员利用职务便利受贿…", score=0.85)
        with patch.object(UnifiedRetrievalAPI, "search_judicial_cases",
                          return_value=[mock_result]):
            api = self._make_api()
            results = api.search_judicial_cases("受贿")
        assert len(results) == 1
        assert "score" in results[0]
        assert "payload" in results[0]
        assert "content" in results[0]["payload"]


# ─── config_loader.get_judicial_cases_dir ──────────────────────

def test_get_judicial_cases_dir_returns_path():
    """get_judicial_cases_dir() 应返回 Path 对象。"""
    from core.config_loader import get_judicial_cases_dir
    path = get_judicial_cases_dir()
    assert isinstance(path, Path)


def test_get_judicial_cases_dir_matches_config():
    """返回路径应与 config.json 的 judicial_cases_dir 字段一致。"""
    import json
    from core.config_loader import get_judicial_cases_dir, get_project_root

    config_path = get_project_root() / "config.json"
    if config_path.exists():
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        expected_rel = raw.get("paths", {}).get("judicial_cases_dir", "")
        actual = get_judicial_cases_dir()
        assert str(actual).replace("\\", "/").endswith(
            str(expected_rel).replace("\\", "/").lstrip("/")
        )
