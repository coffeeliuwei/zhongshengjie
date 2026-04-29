import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.validation.validate_retrieval import CollectionValidator
from tools.validation.judge import SkipJudge


def _make_mock_qdrant(point_count: int, results: list):
    """构造返回固定结果的 mock Qdrant client"""
    client = MagicMock()
    collection_info = MagicMock()
    collection_info.points_count = point_count
    client.get_collection.return_value = collection_info
    mock_hits = []
    for text, score in results:
        hit = MagicMock()
        hit.score = score
        hit.payload = {"content": text, "scene_type": "战斗"}
        mock_hits.append(hit)
    query_resp = MagicMock()
    query_resp.points = mock_hits
    client.query_points.return_value = query_resp
    return client


def test_validator_skip_empty_collection():
    """空 collection 应被标记为 empty，跳过查询"""
    client = _make_mock_qdrant(point_count=0, results=[])
    queries = {"case_library_v2": {"description": "测试", "queries": ["查询1"]}}
    validator = CollectionValidator(
        qdrant_client=client,
        judge=SkipJudge(),
        queries=queries,
    )
    result = validator.validate_collection("case_library_v2")
    assert result["status"] == "empty"
    assert result["avg_ndcg5"] is None


def test_validator_skip_missing_collection():
    """不存在的 collection 应被标记为 missing"""
    client = MagicMock()
    client.get_collection.side_effect = Exception("Collection not found")
    queries = {"no_such_collection": {"description": "测试", "queries": ["查询1"]}}
    validator = CollectionValidator(
        qdrant_client=client,
        judge=SkipJudge(),
        queries=queries,
    )
    result = validator.validate_collection("no_such_collection")
    assert result["status"] == "missing"


def test_validator_skip_judge_no_ndcg():
    """SkipJudge 时 nDCG 为 None，avg_qdrant_score 有值"""
    results = [("文本" * 10, 0.85 - i * 0.05) for i in range(5)]
    client = _make_mock_qdrant(point_count=1000, results=results)
    queries = {
        "case_library_v2": {
            "description": "测试",
            "queries": ["主角逆转反击"],
        }
    }
    with patch("tools.validation.validate_retrieval.embed_query", return_value=[0.1] * 1024):
        validator = CollectionValidator(
            qdrant_client=client,
            judge=SkipJudge(),
            queries=queries,
        )
        result = validator.validate_collection("case_library_v2")
    assert result["status"] == "ok"
    assert result["avg_ndcg5"] is None
    assert result["avg_qdrant_score"] > 0


def test_validator_with_scores():
    """LLM judge 打分后 nDCG 计算正确"""
    from tools.validation.judge import BaseJudge

    class FixedJudge(BaseJudge):
        def score(self, q, r, c):
            return 2  # 全部高度相关

    results = [("文本" * 10, 0.9 - i * 0.05) for i in range(5)]
    client = _make_mock_qdrant(point_count=1000, results=results)
    queries = {
        "case_library_v2": {
            "description": "测试",
            "queries": ["主角逆转反击"],
        }
    }
    with patch("tools.validation.validate_retrieval.embed_query", return_value=[0.1] * 1024):
        validator = CollectionValidator(
            qdrant_client=client,
            judge=FixedJudge(),
            queries=queries,
        )
        result = validator.validate_collection("case_library_v2")
    assert result["status"] == "ok"
    assert result["avg_ndcg5"] == 1.0
    assert result["precision5"] == 1.0
