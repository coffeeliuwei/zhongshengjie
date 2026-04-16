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
