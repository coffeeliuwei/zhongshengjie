# tests/test_embedder.py
"""Tests for BGE-M3 embedder module.

Mock-based tests to avoid loading the real model.
"""

import pytest
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def test_embed_text_returns_1024_dim_vector():
    """embed_text 返回 1024 维 float 列表"""
    mock_model = MagicMock()
    mock_model.encode.return_value = {"dense_vecs": [[0.1] * 1024]}
    with patch("core.inspiration.embedder._get_model", return_value=mock_model):
        from core.inspiration.embedder import embed_text

        result = embed_text("测试文本")

    assert isinstance(result, list)
    assert len(result) == 1024
    assert all(isinstance(v, float) for v in result)


def test_embed_text_normalizes_output():
    """embed_text 对输出做归一化（非零向量）"""
    mock_model = MagicMock()
    mock_model.encode.return_value = {"dense_vecs": [[1.0] + [0.0] * 1023]}
    with patch("core.inspiration.embedder._get_model", return_value=mock_model):
        from core.inspiration.embedder import embed_text

        result = embed_text("测试文本")

    # 不应全为 0
    assert any(v != 0.0 for v in result)


def test_embed_text_empty_string_returns_vector():
    """空字符串也能安全编码"""
    mock_model = MagicMock()
    mock_model.encode.return_value = {"dense_vecs": [[0.0] * 1024]}
    with patch("core.inspiration.embedder._get_model", return_value=mock_model):
        from core.inspiration.embedder import embed_text

        result = embed_text("")

    assert len(result) == 1024


def test_get_model_raises_on_missing_path():
    """模型路径不存在时抛出有意义的错误"""
    with (
        patch(
            "core.inspiration.embedder.get_model_path", return_value="/nonexistent/path"
        ),
        patch("core.inspiration.embedder._MODEL", None),
    ):
        from core.inspiration.embedder import _load_model

        with pytest.raises(Exception):
            _load_model()
