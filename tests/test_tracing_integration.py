# tests/test_tracing_integration.py
"""
验证 ConversationEntryLayer.process_input() 启动时会建立新的 trace_id。
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_new_trace_called_on_process_input():
    """process_input 调用后，core.tracing 应有有效的 trace_id"""
    from core.tracing import get_trace_id, clear_trace, is_tracing

    # 清空已有 trace
    clear_trace()
    assert not is_tracing(), "测试前应无 trace_id"

    # 尝试触发 process_input（可能因缺少配置而失败，但 trace 应已建立）
    try:
        from core.conversation.conversation_entry_layer import ConversationEntryLayer
        entry = ConversationEntryLayer(project_root=Path("."))
        entry.process_input("测试输入")
    except Exception:
        pass  # 允许因配置缺失而失败，只验证 trace_id 有没有建立

    assert is_tracing(), "process_input 应调用 new_trace()，建立 trace_id"
    tid = get_trace_id()
    assert tid.startswith("tr_"), f"trace_id 格式错误: {tid}"


def test_trace_id_format():
    """验证 new_trace() 生成的 ID 格式正确"""
    from core.tracing import new_trace, clear_trace
    clear_trace()
    tid = new_trace()
    parts = tid.split("_")
    assert len(parts) == 3, f"格式应为 tr_<uuid12>_<HHMMSS>，实际: {tid}"
    assert parts[0] == "tr"
    assert len(parts[1]) == 12
    assert len(parts[2]) == 6 and parts[2].isdigit()


def test_trace_context_manager():
    """TraceContext 应在退出时恢复旧 trace_id"""
    from core.tracing import TraceContext, set_trace_id, get_trace_id, clear_trace

    clear_trace()
    set_trace_id("tr_aaaaaaaaaaaa_120000")

    with TraceContext() as inner_id:
        assert inner_id != "tr_aaaaaaaaaaaa_120000"
        assert inner_id.startswith("tr_")

    # 退出后应恢复原 id
    assert get_trace_id() == "tr_aaaaaaaaaaaa_120000"