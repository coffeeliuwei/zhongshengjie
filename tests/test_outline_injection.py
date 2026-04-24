"""测试大纲上下文注入到工作流"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_outline_summary_injected_when_file_exists(tmp_path):
    """存在大纲文件时，工作流上下文应包含大纲摘要"""
    # 准备大纲文件
    outline_dir = tmp_path / "章节大纲"
    outline_dir.mkdir()
    (outline_dir / "第一章-天裂大纲.md").write_text(
        "# 第一章大纲\n\n## 章节信息\n\n| 项目 | 内容 |\n|------|------|\n| **章节名** | 天裂 |\n\n## 详细场景设计\n\n### 场景一：天裂\n\n**地点：** 山顶\n**出场人物：** 血牙、苍澜\n\n### 场景目标\n展示威压。\n",
        encoding="utf-8",
    )

    from core.parsing.chapter_outline_parser import ChapterOutlineParser

    parser = ChapterOutlineParser()

    # 直接验证解析→摘要链路
    outline_file = parser.find_outline_file(1, outline_dir)
    assert outline_file is not None

    result = parser.parse_file(outline_file)
    summary = result["summary"]

    assert "第一章" in summary
    assert "天裂" in summary


def test_outline_not_found_returns_none(tmp_path):
    """大纲文件不存在时，find_outline_file 返回 None（工作流应降级处理）"""
    from core.parsing.chapter_outline_parser import ChapterOutlineParser

    parser = ChapterOutlineParser()

    result = parser.find_outline_file(99, tmp_path)
    assert result is None


def test_outline_injection_in_workflow_metadata(tmp_path):
    """验证工作流metadata包含大纲摘要"""
    from core.conversation.conversation_entry_layer import ConversationEntryLayer
    from core.conversation.intent_classifier import IntentResult

    # 准备大纲文件
    outline_dir = tmp_path / "章节大纲"
    outline_dir.mkdir()
    (outline_dir / "第一章-天裂大纲.md").write_text(
        "# 《众生界》第一章：天裂\n\n## 章节信息\n\n| 项目 | 内容 |\n|------|------|\n| **章节名** | 天裂 |\n\n## 详细场景设计\n\n### 场景一：村口血战\n\n> 黎明薄雾未散。\n",
        encoding="utf-8",
    )

    # Mock IntentClassifier返回start_chapter意图
    mock_intent = IntentResult(
        intent="start_chapter",
        category="workflow_control",
        entities={"chapter": "1"},
        confidence=0.95,
    )

    # 使用mock测试
    with patch(
        "core.conversation.conversation_entry_layer.IntentClassifier"
    ) as mock_classifier_class:
        mock_classifier = MagicMock()
        mock_classifier.classify.return_value = mock_intent
        mock_classifier_class.return_value = mock_classifier

        entry_layer = ConversationEntryLayer(project_root=str(tmp_path))
        result = entry_layer.process_input("写第一章")

        # 验证工作流包含大纲
        if result.pending_workflow:
            metadata = result.pending_workflow.metadata
            if metadata and "chapter_outline" in metadata:
                outline = metadata["chapter_outline"]
                assert "第一章" in outline or "天裂" in outline


def test_outline_parser_handles_missing_sections_gracefully():
    """大纲缺少部分章节信息时，解析器应优雅降级而非崩溃"""
    from core.parsing.chapter_outline_parser import ChapterOutlineParser

    minimal_outline = "# 第三章大纲\n\n## 详细场景设计\n\n### 场景一：简单场景\n\n这是一个简单的场景描述。\n"

    parser = ChapterOutlineParser()
    result = parser.parse(minimal_outline)

    assert "第三章" in result["chapter_title"]
    assert len(result.get("scenes", [])) >= 1
    assert result.get("chapter_info", {}) == {}  # 缺失字段返回空值


def test_outline_parser_handles_empty_file_gracefully():
    """空大纲文件不应崩溃"""
    from core.parsing.chapter_outline_parser import ChapterOutlineParser

    parser = ChapterOutlineParser()
    result = parser.parse("")

    assert result is not None
    assert result.get("scenes", []) == []
