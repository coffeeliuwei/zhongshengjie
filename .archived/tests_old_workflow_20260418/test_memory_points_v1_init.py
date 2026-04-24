# tests/test_memory_points_v1_init.py
"""Tests for memory_points_v1 Qdrant collection initialization."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 添加 .vectorstore 目录到路径（因为目录名以点开头不是合法 Python 包名）
vectorstore_path = project_root / ".vectorstore"
sys.path.insert(0, str(vectorstore_path))

from memory_points_v1_config import COLLECTION_NAME, VECTOR_SIZE, init_collection


def test_collection_name_is_memory_points_v1():
    assert COLLECTION_NAME == "memory_points_v1"


def test_vector_size_matches_bge_m3():
    """BGE-M3 dense 向量为 1024 维"""
    assert VECTOR_SIZE == 1024


def test_init_collection_creates_when_missing():
    """当 Collection 不存在时创建"""
    mock_client = MagicMock()
    mock_client.get_collections.return_value = MagicMock(collections=[])

    result = init_collection(mock_client)

    assert result is True  # 返回 True 表示新建
    mock_client.create_collection.assert_called_once()
    call_kwargs = mock_client.create_collection.call_args.kwargs
    assert call_kwargs["collection_name"] == COLLECTION_NAME


def test_init_collection_skips_when_exists():
    """当 Collection 已存在时跳过"""
    mock_client = MagicMock()
    existing = MagicMock()
    existing.name = COLLECTION_NAME
    mock_client.get_collections.return_value = MagicMock(collections=[existing])

    result = init_collection(mock_client)

    assert result is False  # 返回 False 表示已存在
    mock_client.create_collection.assert_not_called()
