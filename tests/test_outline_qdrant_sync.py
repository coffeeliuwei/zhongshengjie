#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""大纲 Qdrant 同步系统测试"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_data_builder_registers_chapter_outlines_collection():
    """data_builder DEFAULT_CONFIG 必须包含 chapter_outlines collection"""
    from tools.data_builder import DEFAULT_CONFIG

    collections = DEFAULT_CONFIG["collections"]
    assert "chapter_outlines" in collections.values(), (
        "DEFAULT_CONFIG['collections'] 中缺少 chapter_outlines"
    )


def test_data_builder_registers_novel_plot_v1_collection():
    """data_builder DEFAULT_CONFIG 必须包含 novel_plot_v1 collection"""
    from tools.data_builder import DEFAULT_CONFIG

    collections = DEFAULT_CONFIG["collections"]
    assert "novel_plot_v1" in collections.values(), (
        "DEFAULT_CONFIG['collections'] 中缺少 novel_plot_v1"
    )


# === Task 2 测试 ===


def test_modify_plot_maps_to_novel_plot_v1():
    """modify_plot 意图必须映射到 novel_plot_v1 collection"""
    from core.conversation.data_extractor import ConversationDataExtractor

    mapping = ConversationDataExtractor.INTENT_COLLECTION_MAPPING
    assert mapping.get("modify_plot") == "novel_plot_v1", (
        f"modify_plot 应映射到 novel_plot_v1，实际: {mapping.get('modify_plot')}"
    )


def test_add_plot_point_maps_to_novel_plot_v1():
    """add_plot_point 意图必须映射到 novel_plot_v1 collection"""
    from core.conversation.data_extractor import ConversationDataExtractor

    mapping = ConversationDataExtractor.INTENT_COLLECTION_MAPPING
    assert mapping.get("add_plot_point") == "novel_plot_v1", (
        f"add_plot_point 应映射到 novel_plot_v1，实际: {mapping.get('add_plot_point')}"
    )


def test_novel_plot_v1_embedding_text_generated():
    """file_updater 必须能为 novel_plot_v1 生成非空嵌入文本"""
    from core.conversation.file_updater import FileUpdater

    updater = FileUpdater.__new__(FileUpdater)
    data = {"type": "plot_change", "content": "主角在第三章觉醒了新能力"}
    text = updater._generate_embedding_text("novel_plot_v1", data)
    assert text, "novel_plot_v1 的嵌入文本不应为空"
    assert "plot_change" in text or "主角" in text, (
        f"嵌入文本应包含 content 内容，实际: {text}"
    )


def test_chapter_outlines_embedding_text_generated():
    """file_updater 必须能为 chapter_outlines 生成非空嵌入文本"""
    from core.conversation.file_updater import FileUpdater

    updater = FileUpdater.__new__(FileUpdater)
    data = {
        "chapter_num": 1,
        "chapter_title": "天裂",
        "content": "场景1：城门守卫发现裂缝",
        "source_file": "章节大纲/第一章-天裂大纲.md",
    }
    text = updater._generate_embedding_text("chapter_outlines", data)
    assert text, "chapter_outlines 的嵌入文本不应为空"
    assert "天裂" in text or "第1章" in text, f"嵌入文本应包含章节信息，实际: {text}"


# === Task 3 测试 ===


def test_process_total_outline_is_deprecated(capsys):
    """_process_total_outline 应打印废弃警告并跳过"""
    import tempfile
    from pathlib import Path
    from unittest.mock import MagicMock
    from modules.knowledge_base.vectorizer_manager import VectorizerManager

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # 创建最小文件结构
        (tmp_path / "总大纲.md").write_text("# 总大纲\n内容", encoding="utf-8")

        manager = VectorizerManager(project_dir=tmp_path)
        mock_collection = MagicMock()

        manager._process_total_outline(mock_collection)

        # 不应调用 collection 的任何写入方法
        mock_collection.add.assert_not_called()
        mock_collection.upsert.assert_not_called()

        # 应打印废弃警告
        captured = capsys.readouterr()
        assert "DEPRECATED" in captured.out or "废弃" in captured.out, (
            f"应打印废弃警告，实际输出: {captured.out}"
        )


# === Task 4 测试 ===


def test_sync_manager_adapter_has_sync_chapter_outline_file():
    """SyncManagerAdapter 必须有 sync_chapter_outline_file 方法"""
    from core.change_detector.sync_manager_adapter import SyncManagerAdapter

    adapter = SyncManagerAdapter()
    assert hasattr(adapter, "sync_chapter_outline_file"), (
        "SyncManagerAdapter 缺少 sync_chapter_outline_file 方法"
    )
    assert callable(adapter.sync_chapter_outline_file)


def test_sync_manager_adapter_has_sync_total_outline_to_qdrant():
    """SyncManagerAdapter 必须有 sync_total_outline_to_qdrant 方法"""
    from core.change_detector.sync_manager_adapter import SyncManagerAdapter

    adapter = SyncManagerAdapter()
    assert hasattr(adapter, "sync_total_outline_to_qdrant"), (
        "SyncManagerAdapter 缺少 sync_total_outline_to_qdrant 方法"
    )
    assert callable(adapter.sync_total_outline_to_qdrant)


def test_sync_chapter_outline_file_returns_sync_result_for_missing_file():
    """不存在的大纲文件应返回 status=skipped 的 SyncResult"""
    from pathlib import Path
    from core.change_detector.sync_manager_adapter import SyncManagerAdapter

    adapter = SyncManagerAdapter()
    result = adapter.sync_chapter_outline_file(Path("/nonexistent/第一章大纲.md"))
    assert result.status == "skipped", (
        f"文件不存在时应返回 skipped，实际: {result.status}"
    )


def test_sync_total_outline_to_qdrant_returns_sync_result_for_missing_file(tmp_path):
    """不存在的总大纲文件应返回 status=skipped 的 SyncResult"""
    from core.change_detector.sync_manager_adapter import SyncManagerAdapter

    adapter = SyncManagerAdapter(project_root=tmp_path)
    result = adapter.sync_total_outline_to_qdrant()
    assert result.status == "skipped", (
        f"文件不存在时应返回 skipped，实际: {result.status}"
    )


def test_sync_chapter_outline_file_parses_and_returns_result(tmp_path):
    """存在的大纲文件应成功解析并返回非失败的 SyncResult"""
    from pathlib import Path
    from unittest.mock import patch, MagicMock
    from core.change_detector.sync_manager_adapter import SyncManagerAdapter

    # 创建最小大纲文件
    outline_file = tmp_path / "第一章-天裂大纲.md"
    outline_file.write_text(
        "# 《众生界》第1章：天裂\n\n## 章节信息\n\n| 项目 | 内容 |\n|------|------|\n| 章节名 | 天裂 |\n",
        encoding="utf-8",
    )

    adapter = SyncManagerAdapter(project_root=tmp_path)

    # mock file_updater 的 sync_to_vectorstore
    with patch("core.conversation.file_updater.FileUpdater") as MockFileUpdater:
        mock_updater = MagicMock()
        mock_updater.sync_to_vectorstore.return_value = True
        MockFileUpdater.return_value = mock_updater

        result = adapter.sync_chapter_outline_file(outline_file)

    assert result.status in ("success", "partial"), (
        f"文件存在时应返回 success 或 partial，实际: {result.status}"
    )
    assert mock_updater.sync_to_vectorstore.called
    call_args = mock_updater.sync_to_vectorstore.call_args
    assert call_args[0][0] == "chapter_outlines"
