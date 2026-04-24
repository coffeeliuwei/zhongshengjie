from unittest.mock import patch, MagicMock
from core.conversation.intent_router import IntentRouter


def _make_mock_runner(started: bool, running: bool = False):
    runner = MagicMock()
    if started:
        runner.start.return_value = {
            "started": True,
            "pid": 9999,
            "mode": "incremental",
        }
    else:
        runner.start.return_value = {
            "started": False,
            "status": {"raw": "[OK] 场景案例: 100 条", "running": running},
        }
    return runner


def test_router_handles_incremental_extraction():
    router = IntentRouter()
    mock_runner = _make_mock_runner(started=True)

    with patch(
        "core.conversation.intent_router.ExtractionRunner", return_value=mock_runner
    ):
        result = router.route(
            intent="incremental_extraction",
            entities={},
            user_input="帮我把这批小说提炼一下",
        )

    assert result.success is True
    assert "增量" in result.message
    mock_runner.start.assert_called_once_with("incremental")


def test_router_handles_full_extraction():
    router = IntentRouter()
    mock_runner = MagicMock()
    mock_runner.start.return_value = {"started": True, "pid": 8888, "mode": "full"}

    with patch(
        "core.conversation.intent_router.ExtractionRunner", return_value=mock_runner
    ):
        result = router.route(
            intent="full_extraction",
            entities={},
            user_input="强制全量重新提炼",
        )

    assert result.success is True
    assert "全量" in result.message or "强制" in result.message
    mock_runner.start.assert_called_once_with("full")


def test_router_returns_status_when_already_running():
    router = IntentRouter()
    mock_runner = _make_mock_runner(started=False, running=True)

    with patch(
        "core.conversation.intent_router.ExtractionRunner", return_value=mock_runner
    ):
        result = router.route(
            intent="incremental_extraction",
            entities={},
            user_input="提炼一下",
        )

    assert result.success is True
    assert "进行中" in result.message


def test_router_extraction_extractor_dir_not_found():
    router = IntentRouter()
    mock_runner = MagicMock()
    mock_runner.start.side_effect = FileNotFoundError("提炼工具目录不存在")

    with patch(
        "core.conversation.intent_router.ExtractionRunner", return_value=mock_runner
    ):
        result = router.route(
            intent="incremental_extraction",
            entities={},
            user_input="提炼",
        )

    assert result.success is False
    assert "目录" in result.message or "不存在" in result.message
