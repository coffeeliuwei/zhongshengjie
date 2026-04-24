"""测试技法提炼→确认→入库完整流程"""

from unittest.mock import patch, MagicMock
from pathlib import Path


def test_intent_router_has_persistent_extractors():
    """IntentRouter 应有持久化的提取器实例"""
    from core.conversation.intent_router import IntentRouter

    router = IntentRouter()
    assert hasattr(router, "_technique_extractor"), "缺少 _technique_extractor"
    assert hasattr(router, "_eval_criteria_extractor"), "缺少 _eval_criteria_extractor"


def test_confirm_technique_calls_write_and_sync():
    """确认技法后应写入文件并同步到向量库，而非返回'功能正在完善中'"""
    from core.conversation.intent_router import IntentRouter

    router = IntentRouter()

    # 模拟：提炼阶段先设置 pending_technique
    mock_candidate = MagicMock()
    mock_candidate.name = "测试技法"
    mock_candidate.dimension = "人物维度"
    mock_candidate.elements = ["要素1", "要素2"]
    mock_candidate.example_text = "示例文本"
    router._technique_extractor.pending_technique = mock_candidate

    # 模拟文件写入和向量同步
    with patch.object(
        router._technique_extractor, "confirm_and_save", return_value=True
    ) as mock_confirm:
        result = router.route(
            intent="confirm_technique", entities={}, user_input="确认"
        )

    assert result.success is True
    assert "功能正在完善中" not in result.message, "仍返回占位符，未实现真正入库"
    mock_confirm.assert_called_once()


def test_confirm_technique_no_pending_returns_graceful_error():
    """无待确认技法时，确认操作应返回有意义的提示而非崩溃"""
    from core.conversation.intent_router import IntentRouter

    router = IntentRouter()
    # 不设置 pending_technique，模拟用户没有先提炼就说"确认"
    router._technique_extractor.pending_technique = None
    result = router.route(intent="confirm_technique", entities={}, user_input="确认")

    assert result.success is True  # 不应崩溃
    assert result.message  # 应有提示信息


def test_confirm_evaluation_criteria_calls_save():
    """确认禁止项后应写入文件并同步，而非只返回文字"""
    from core.conversation.intent_router import IntentRouter

    router = IntentRouter()

    # 设置待确认的禁止项
    mock_candidate = MagicMock()
    mock_candidate.name = "测试禁止项"
    mock_candidate.description = "禁止使用AI味表达"
    router._eval_criteria_extractor.pending_criteria = mock_candidate

    with patch.object(
        router._eval_criteria_extractor, "confirm_and_save", return_value=True
    ) as mock_save:
        result = router.route(
            intent="confirm_evaluation_criteria",
            entities={"criterion_name": "测试禁止项"},
            user_input="确认",
        )

    assert result.success is True
    mock_save.assert_called_once()


def test_confirm_evaluation_criteria_no_pending():
    """无待确认禁止项时应给出有意义提示"""
    from core.conversation.intent_router import IntentRouter

    router = IntentRouter()
    # 确保 pending_criteria 为空
    router._eval_criteria_extractor.pending_criteria = None

    result = router.route(
        intent="confirm_evaluation_criteria",
        entities={},
        user_input="确认",
    )
    assert result.success is True
    assert result.message  # 不应为空
