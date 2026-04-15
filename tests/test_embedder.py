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


# ===== Task 2 Tests: resonance_feedback.py 传入真实 embedding =====


def test_handle_reader_feedback_uses_real_embedding(tmp_path):
    """handle_reader_feedback 应传入真实 embedding（非全零）给 sync.create"""
    from unittest.mock import patch, MagicMock, call
    import re

    # 准备假章节文件
    chapter_file = tmp_path / "正文" / "第一章.md"
    chapter_file.parent.mkdir(parents=True, exist_ok=True)
    chapter_file.write_text(
        "屋檐滴水，声声入耳，主角心中苦涩难言。\n战斗打响。", encoding="utf-8"
    )

    mock_sync = MagicMock()
    mock_sync.create.return_value = "mp_001"

    fake_embedding = [0.5] * 1024  # 非零

    with (
        patch(
            "core.inspiration.resonance_feedback._resolve_chapter_path",
            return_value=chapter_file,
        ),
        patch(
            "core.inspiration.resonance_feedback.MemoryPointSync",
            return_value=mock_sync,
        ),
        patch(
            "core.inspiration.resonance_feedback.embed_text",
            return_value=fake_embedding,
        ) as mock_embed,
    ):
        from core.inspiration.resonance_feedback import handle_reader_feedback

        result = handle_reader_feedback(
            user_input="第一章开头屋檐滴水那句很震撼",
            scene_type_lookup=lambda ch: "情感",
        )

    # embed_text 被调用
    assert mock_embed.called
    # sync.create 被调用时传入了 embedding 参数
    call_kwargs = mock_sync.create.call_args
    assert call_kwargs is not None
    passed_embedding = call_kwargs[1].get("embedding") or (
        call_kwargs[0][1] if len(call_kwargs[0]) > 1 else None
    )
    assert passed_embedding == fake_embedding
