# -*- coding: utf-8 -*-
"""tests/test_style_injector.py — style_injector 单元测试"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ─── 辅助：最小 YAML 数据 ───────────────────────────────────────

_MOCK_AUTHORS = {
    "authors": [
        {
            "id": "作家A",
            "name": "作家A",
            "aws_profile": {"sentence_variety": 0.9},
            "behavior_constraints": ["禁用套句X", "用具体感官细节替代抽象情感词"],
            "bad_habits": ["过度使用'突然'"],
            "style_anchors": {
                "battle": "刀锋美学：以力量留白取代动作堆砌",
                "character": "情感内敛：用行为暗示心理",
            },
            "ai_blacklist": ["不由自主地", "眼中闪过一丝"],
        }
    ]
}

_MOCK_CONFIG = {
    "writers": {
        "剑尘": {
            "author_mix": {"作家A": 1.0},
            "available_authors": ["作家A", "作家B"],
            "default_scene_weights": {"战斗": 0.8, "突破": 0.2},
        }
    },
    "quality_gate": {
        "burstiness_threshold": 50,
        "blacklist_max_hits": 3,
        "blacklist_hit_rate_max": 0.15,
    },
}


# ─── build_writer_style_context ────────────────────────────────

def test_build_writer_style_context_returns_string():
    from tools import style_injector as si
    with patch.object(si, "_load_yaml", side_effect=lambda p: (
        _MOCK_AUTHORS if "author_styles" in str(p) else _MOCK_CONFIG
    )):
        result = si.build_writer_style_context("剑尘", "战斗", seed=42)
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_writer_style_context_contains_constraints():
    from tools import style_injector as si
    with patch.object(si, "_load_yaml", side_effect=lambda p: (
        _MOCK_AUTHORS if "author_styles" in str(p) else _MOCK_CONFIG
    )):
        result = si.build_writer_style_context("剑尘", "战斗", seed=42)
    # 行为约束应出现在风格包中
    assert "禁用套句X" in result or "具体感官细节" in result


def test_build_writer_style_context_unknown_writer():
    from tools import style_injector as si
    with patch.object(si, "_load_yaml", side_effect=lambda p: (
        _MOCK_AUTHORS if "author_styles" in str(p) else _MOCK_CONFIG
    )):
        # 未知写手 → 应返回字符串（降级或空）而非异常
        result = si.build_writer_style_context("未知写手", "战斗", seed=1)
    assert isinstance(result, str)


# ─── list_available_authors ────────────────────────────────────

def test_list_available_authors():
    from tools import style_injector as si
    with patch.object(si, "_load_yaml", side_effect=lambda p: (
        _MOCK_AUTHORS if "author_styles" in str(p) else _MOCK_CONFIG
    )):
        authors = si.list_available_authors("剑尘")
    assert isinstance(authors, list)
    assert "作家A" in authors


# ─── get_current_mix ───────────────────────────────────────────

def test_get_current_mix():
    from tools import style_injector as si
    with patch.object(si, "_load_yaml", side_effect=lambda p: (
        _MOCK_AUTHORS if "author_styles" in str(p) else _MOCK_CONFIG
    )):
        mix = si.get_current_mix("剑尘")
    assert isinstance(mix, dict)
    assert "作家A" in mix
    assert abs(sum(mix.values()) - 1.0) < 1e-6  # 权重之和为1
