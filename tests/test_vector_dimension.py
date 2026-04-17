# tests/test_vector_dimension.py
"""Tests for vector dimension consistency - BGE-M3 1024 dims"""

from pathlib import Path


def test_sync_manager_uses_1024_dimensions():
    """modules/knowledge_base/sync_manager.py 必须使用 1024 维"""
    file_path = Path("D:/动画/众生界/modules/knowledge_base/sync_manager.py")
    content = file_path.read_text(encoding="utf-8")

    # 检查 VECTOR_SIZE 赋值行（排除使用 self.VECTOR_SIZE 的行）
    for line in content.splitlines():
        if "VECTOR_SIZE" in line and " = " in line and "self." not in line:
            assert "1024" in line, f"sync_manager.py 应使用1024维，实际: {line}"


def test_sync_to_qdrant_uses_1024_dimensions():
    """.case-library/scripts/sync_to_qdrant.py 必须使用 1024 维"""
    file_path = Path("D:/动画/众生界/.case-library/scripts/sync_to_qdrant.py")
    content = file_path.read_text(encoding="utf-8")

    for line in content.splitlines():
        if "VECTOR_SIZE" in line and " = " in line and "size=" not in line:
            assert "1024" in line, f"sync_to_qdrant.py 应使用1024维，实际: {line}"


def test_search_manager_uses_1024_dimensions():
    """modules/knowledge_base/search_manager.py 必须使用 1024 维"""
    file_path = Path("D:/动画/众生界/modules/knowledge_base/search_manager.py")
    content = file_path.read_text(encoding="utf-8")

    for line in content.splitlines():
        if "VECTOR_SIZE" in line and " = " in line and "self." not in line:
            assert "1024" in line, f"search_manager.py 应使用1024维，实际: {line}"
