# tests/test_intent_router_integration.py
"""Integration tests: conversation_entry_layer → IntentRouter."""

from unittest.mock import MagicMock, patch
import pytest


def test_feedback_intent_goes_through_router():
    """FEEDBACK 类意图通过 IntentRouter 处理"""
    from core.conversation.intent_router import IntentRouter, RoutingResult

    # 直接测试路由器处理
    router = IntentRouter()
    result = router.route(
        intent="reader_moment_feedback",
        entities={},
        user_input="第2章很解气",
    )
    assert result.success is True


def test_management_intent_goes_through_router():
    """MANAGEMENT 类意图通过 IntentRouter 处理"""
    from core.conversation.intent_router import IntentRouter

    router = IntentRouter()
    result = router.route(
        intent="constraint_query",
        entities={},
        user_input="查查约束",
    )
    assert result.success is True


def test_inspiration_status_query():
    """灵感引擎状态查询"""
    from core.conversation.intent_router import IntentRouter

    router = IntentRouter()
    result = router.route(
        intent="inspiration_status_query",
        entities={},
        user_input="你学到了什么",
    )
    assert result.success is True
