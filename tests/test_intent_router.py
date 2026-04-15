# tests/test_intent_router.py
"""Tests for IntentRouter — intent-to-backend routing layer."""

import pytest
from unittest.mock import MagicMock, patch


def test_routing_result_success():
    from core.conversation.intent_router import RoutingResult

    r = RoutingResult(success=True, message="OK", data={})
    assert r.success is True
    assert r.message == "OK"


def test_routing_result_needs_clarification():
    from core.conversation.intent_router import RoutingResult

    r = RoutingResult(
        success=True, message="需要确认", data={}, needs_clarification=True
    )
    assert r.needs_clarification is True


def test_unknown_intent_returns_unhandled():
    from core.conversation.intent_router import IntentRouter

    router = IntentRouter()
    result = router.route(
        intent="completely_unknown_intent_xyz",
        entities={},
        user_input="test",
    )
    assert result.success is False
    assert "unhandled" in result.message.lower() or "未处理" in result.message


def test_reader_moment_feedback_routed():
    """reader_moment_feedback 通过 FeedbackDispatcher 路由"""
    from core.conversation.intent_router import IntentRouter

    mock_result = {
        "status": "ok",
        "memory_point_ids": ["mp_001"],
        "message": "已记下 1 条记忆点",
    }

    with patch(
        "core.feedback.feedback_dispatcher.FeedbackDispatcher.dispatch",
        return_value=mock_result,
    ) as mock_handler:
        router = IntentRouter()
        result = router.route(
            intent="reader_moment_feedback",
            entities={},
            user_input="第2章末尾那段反打写得很解气",
        )

    mock_handler.assert_called_once()
    assert result.success is True
    assert "记忆点" in result.message


def test_reader_moment_feedback_needs_clarification():
    """后端返回 needs_clarification 时，RoutingResult 同步标记"""
    from core.conversation.intent_router import IntentRouter

    mock_result = {
        "status": "needs_clarification",
        "memory_point_ids": [],
        "message": "你说的是哪一章？",
    }

    with patch(
        "core.feedback.feedback_dispatcher.FeedbackDispatcher.dispatch",
        return_value=mock_result,
    ):
        router = IntentRouter()
        result = router.route(
            intent="reader_moment_feedback",
            entities={},
            user_input="那段写得很好",
        )

    assert result.needs_clarification is True


def test_overturn_feedback_routed():
    """overturn_feedback 通过 FeedbackDispatcher 路由并携带 overturn=True"""
    from core.conversation.intent_router import IntentRouter

    mock_result = {
        "status": "ok",
        "memory_point_ids": ["mp_x"],
        "message": "推翻事件已记录",
    }

    with patch(
        "core.feedback.feedback_dispatcher.FeedbackDispatcher.dispatch",
        return_value=mock_result,
    ) as mock_handler:
        router = IntentRouter()
        router.route(
            intent="overturn_feedback",
            entities={},
            user_input="这段虽然定稿了但我不满意",
        )

    call_kwargs = mock_handler.call_args.kwargs
    assert call_kwargs.get("is_overturn") is True


def test_connoisseur_audit_response_routed():
    """connoisseur_audit_response 调用 record_audit_label"""
    from core.conversation.intent_router import IntentRouter

    with patch(
        "core.conversation.intent_router.record_audit_label",
        return_value="标定结果已记录",
    ) as mock_fn:
        router = IntentRouter()
        result = router.route(
            intent="connoisseur_audit_response",
            entities={"audit_result": "第3次是真点火"},
            user_input="第3次是真点火，其余都是敷衍",
        )

    mock_fn.assert_called_once()
    assert result.success is True


def test_inspiration_status_query_routed():
    """inspiration_status_query 调用 status_reporter.report_status"""
    from core.conversation.intent_router import IntentRouter

    with patch(
        "core.conversation.intent_router.report_status",
        return_value="【灵感引擎状态】\n  · 累计记忆点：15 条\n",
    ) as mock_fn:
        router = IntentRouter()
        result = router.route(
            intent="inspiration_status_query",
            entities={},
            user_input="你学到了什么",
        )

    mock_fn.assert_called_once()
    assert result.success is True
    assert "记忆点" in result.message


def test_constraint_query_routed():
    """constraint_query 调用 constraint_library 列出约束"""
    from core.conversation.intent_router import IntentRouter

    with patch(
        "core.conversation.intent_router._query_constraints",
        return_value="视角反叛类约束：7 条",
    ) as mock_fn:
        router = IntentRouter()
        result = router.route(
            intent="constraint_query",
            entities={},
            user_input="查一下视角反叛这类约束现在有几条",
        )

    mock_fn.assert_called_once()
    assert result.success is True


def test_inspiration_bailout_routed():
    """inspiration_bailout 返回关闭确认"""
    from core.conversation.intent_router import IntentRouter

    router = IntentRouter()
    result = router.route(
        intent="inspiration_bailout",
        entities={},
        user_input="关掉灵感引擎这章不折腾了",
    )
    assert result.success is True
    assert "灵感引擎" in result.message


def test_extract_technique_routed():
    """extract_technique 调用 technique_extractor"""
    from core.conversation.intent_router import IntentRouter

    router = IntentRouter()
    result = router.route(
        intent="extract_technique",
        entities={},
        user_input="把这段动作克制的写法提炼成技法",
    )

    assert result.success is True
    # 未找到技法候选时仍返回成功（needs_clarification=True）


def test_extract_technique_from_file_routed():
    """extract_technique_from_file 需要 file_path 实体"""
    from core.conversation.intent_router import IntentRouter

    with patch("core.conversation.intent_router.TechniqueExtractor") as MockExtractor:
        MockExtractor.return_value.extract_from_file.return_value = []

        router = IntentRouter()
        result = router.route(
            intent="extract_technique_from_file",
            entities={"file_path": "正文/第一章.md"},
            user_input="从第一章提炼技法",
        )

    MockExtractor.return_value.extract_from_file.assert_called_once()
    assert result.success is True


def test_add_evaluation_criteria_routed():
    """add_evaluation_criteria 调用 eval_criteria_extractor"""
    from core.conversation.intent_router import IntentRouter

    router = IntentRouter()
    result = router.route(
        intent="add_evaluation_criteria",
        entities={},
        user_input="把嘴角勾起一抹加入禁止项",
    )

    assert result.success is True


def test_discover_prohibitions_from_file_routed():
    """discover_prohibitions_from_file 需要 file_path 实体"""
    from core.conversation.intent_router import IntentRouter

    router = IntentRouter()
    result = router.route(
        intent="discover_prohibitions_from_file",
        entities={"file_path": "正文/第一章.md"},
        user_input="扫描第一章找禁止项",
    )

    assert result.success is True
