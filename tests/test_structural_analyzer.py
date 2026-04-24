# tests/test_structural_analyzer.py
"""Tests for structural feature extraction."""

import sys
from pathlib import Path
import pytest

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def test_analyze_returns_required_fields():
    from core.inspiration.structural_analyzer import analyze

    result = analyze("他立在风口。三千铁骑压来。他抬手时屋檐在滴水。")
    required_fields = {
        "sentence_length_avg",
        "sentence_length_variance",
        "imagery_density",
        "perspective",
        "rhythm_pattern",
        "verb_density",
        "adjective_ratio",
    }
    assert required_fields.issubset(set(result.keys()))


def test_sentence_length_stats():
    from core.inspiration.structural_analyzer import analyze

    text = "短句。短句。这是一个稍微长一点的句子。"
    result = analyze(text)
    assert result["sentence_length_avg"] > 0
    assert result["sentence_length_variance"] >= 0


def test_imagery_density_bucketing():
    """密集意象应被识别为 high"""
    from core.inspiration.structural_analyzer import analyze

    high_imagery = "屋檐滴水，残阳如血，孤鸦掠过古塔。冷月照孤村，寒鸦栖枯枝。"
    low_imagery = "他说他来了。然后他走了。事情就这样发生了。"
    h = analyze(high_imagery)
    l = analyze(low_imagery)
    assert h["imagery_density"] in {"medium", "high"}
    assert l["imagery_density"] in {"low", "medium"}


def test_perspective_detection_third_person():
    from core.inspiration.structural_analyzer import analyze

    text = "他抬起手。他没说话。他转身离开。"
    result = analyze(text)
    assert result["perspective"] in {"主角", "旁观", "第三人称"}


def test_rhythm_pattern_returns_known_template():
    """节奏模式必须是预定义模板之一"""
    from core.inspiration.structural_analyzer import analyze, RHYTHM_TEMPLATES

    result = analyze("短。短。这是一个非常长的描述句子来打破节奏。短。短。")
    assert result["rhythm_pattern"] in RHYTHM_TEMPLATES


def test_empty_text_returns_safe_defaults():
    from core.inspiration.structural_analyzer import analyze

    result = analyze("")
    assert result["sentence_length_avg"] == 0
    assert result["imagery_density"] == "low"


def test_first_person_perspective():
    """第一人称应识别为主角"""
    from core.inspiration.structural_analyzer import analyze

    text = "我抬起手。我没说话。我转身离开。"
    result = analyze(text)
    assert result["perspective"] == "主角"


def test_verb_density_positive():
    """动词密度应为正数"""
    from core.inspiration.structural_analyzer import analyze

    text = "他抬起手挥刀斩下。"
    result = analyze(text)
    assert result["verb_density"] > 0
