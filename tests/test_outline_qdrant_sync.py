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
