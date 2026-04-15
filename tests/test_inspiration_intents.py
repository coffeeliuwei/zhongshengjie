# tests/test_inspiration_intents.py
"""Tests for inspiration engine intent classification."""

import sys
from pathlib import Path
import pytest

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.conversation.intent_classifier import IntentClassifier, IntentCategory


@pytest.fixture
def classifier():
    return IntentClassifier()


def test_intent_category_feedback_exists():
    """IntentCategory.FEEDBACK 应存在"""
    assert hasattr(IntentCategory, "FEEDBACK")
    assert IntentCategory.FEEDBACK.value == "feedback"


def test_intent_category_management_exists():
    """IntentCategory.MANAGEMENT 应存在"""
    assert hasattr(IntentCategory, "MANAGEMENT")
    assert IntentCategory.MANAGEMENT.value == "management"


def test_reader_moment_feedback_positive(classifier):
    """正向共鸣反馈应被识别"""
    result = classifier.classify("第一章那段很震撼")
    assert result.intent == "reader_moment_feedback"
    assert result.category == IntentCategory.FEEDBACK


def test_reader_moment_feedback_negative(classifier):
    """负向共鸣反馈应被识别"""
    result = classifier.classify("那段有点出戏")
    assert result.intent == "reader_moment_feedback"
    assert result.category == IntentCategory.FEEDBACK


def test_overturn_feedback(classifier):
    """推翻反馈应被识别"""
    result = classifier.classify("这版不接受")
    assert result.intent == "overturn_feedback"
    assert result.category == IntentCategory.FEEDBACK


def test_inspiration_status_query(classifier):
    """灵感引擎状态查询应被识别"""
    result = classifier.classify("你最近学到了什么")
    assert result.intent == "inspiration_status_query"
    assert result.category == IntentCategory.QUERY


def test_constraint_query(classifier):
    """约束查询应被识别"""
    result = classifier.classify("查一下约束")
    assert result.intent == "constraint_query"
    assert result.category == IntentCategory.QUERY


def test_constraint_add(classifier):
    """添加约束应被识别"""
    result = classifier.classify("加一条约束")
    assert result.intent == "constraint_add"
    assert result.category == IntentCategory.MANAGEMENT


def test_inspiration_bailout(classifier):
    """关闭灵感引擎应被识别"""
    result = classifier.classify("关闭灵感引擎")
    assert result.intent == "inspiration_bailout"
    assert result.category == IntentCategory.WORKFLOW


def test_new_intents_count(classifier):
    """新增意图数量应为11个"""
    new_intents = [
        "reader_moment_feedback",
        "comparative_moment_feedback",
        "external_moment_inject",
        "inspiration_status_query",
        "overturn_feedback",
        "constraint_tuning",
        "constraint_add",
        "constraint_query",
        "inspiration_conflict_resolution",
        "inspiration_bailout",
        "connoisseur_audit_response",
    ]
    for intent in new_intents:
        assert intent in classifier._all_intents, f"{intent} 应在意图列表中"
