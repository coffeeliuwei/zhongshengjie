from core.extraction.extraction_formatter import (
    format_start_response,
    format_status_response,
)


def test_format_start_incremental_new():
    result = {"started": True, "pid": 1234, "mode": "incremental"}
    msg = format_start_response(result, "incremental")
    assert "增量提炼" in msg
    assert "进展" in msg


def test_format_start_full_new():
    result = {"started": True, "pid": 1234, "mode": "full"}
    msg = format_start_response(result, "full")
    assert "全量" in msg or "强制" in msg


def test_format_start_already_running():
    result = {
        "started": False,
        "status": {"raw": "[OK] 场景案例: 150 条", "running": True},
    }
    msg = format_start_response(result, "incremental")
    assert "进行中" in msg
    assert "150" in msg


def test_format_status_running():
    status = {"raw": "[OK] 场景案例: 150 条\n[..] 对话风格: 0 条", "running": True}
    msg = format_status_response(status)
    assert "正在进行" in msg
    assert "150" in msg


def test_format_status_finished():
    status = {"raw": "[OK] 场景案例: 150 条", "running": False}
    msg = format_status_response(status)
    assert "结束" in msg or "完成" in msg


def test_format_status_empty_raw():
    status = {"raw": "", "running": False}
    msg = format_status_response(status)
    assert "获取失败" in msg or "状态" in msg
