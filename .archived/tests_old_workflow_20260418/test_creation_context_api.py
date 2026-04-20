import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_dependencies():
    """Mock Qdrant client and embedder"""
    import sys

    sys.path.insert(0, "D:/动画/众生界/.vectorstore/core")
    sys.path.insert(0, "D:/动画/众生界")
    import creation_context_api

    mock_client = MagicMock()
    mock_client.get_collections.return_value = MagicMock(collections=[])
    mock_client.search.return_value = [
        MagicMock(payload={"content": {"stage": "stage0_goal", "data": "test"}})
    ]

    mock_model = MagicMock()
    mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 1024)

    # Patch the functions directly on the module
    creation_context_api._get_client = lambda: mock_client
    creation_context_api._get_embedder = lambda: mock_model

    return {
        "client": mock_client,
        "embedder": mock_model,
        "module": creation_context_api,
    }


def test_save_stage_output(mock_dependencies):
    """save_stage_output 调用 qdrant upsert 并返回 point_id"""
    creation_context_api = mock_dependencies["module"]
    mock_client = mock_dependencies["client"]

    point_id = creation_context_api.save_stage_output(
        chapter="第1章",
        stage="stage0_goal",
        content={"goal": "血牙觉醒", "decisions": ["代价：遗忘母亲名字"]},
    )
    assert point_id is not None
    assert isinstance(point_id, str)
    mock_client.upsert.assert_called_once()


def test_query_context_returns_list(mock_dependencies):
    """query_context 返回内容列表"""
    creation_context_api = mock_dependencies["module"]
    mock_client = mock_dependencies["client"]

    results = creation_context_api.query_context(
        chapter="第1章", query="血牙的情感状态", top_k=3
    )
    assert isinstance(results, list)
    mock_client.search.assert_called_once()


def test_clear_chapter_context(mock_dependencies):
    """clear_chapter_context 调用 qdrant delete"""
    creation_context_api = mock_dependencies["module"]
    mock_client = mock_dependencies["client"]

    creation_context_api.clear_chapter_context("第1章")
    mock_client.delete.assert_called_once()
