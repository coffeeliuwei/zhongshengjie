# core/tracing.py
"""跨 Agent 调用追踪模块

为多 Agent 协作提供链路追踪能力，便于定位问题和分析调用链。

用法:
    from core.tracing import get_trace_id, new_trace, set_trace_id
    
    # 创建新追踪
    trace_id = new_trace()
    
    # 获取当前追踪 ID
    current_id = get_trace_id()
    
    # 设置追踪 ID（用于接收外部传入的 trace_id）
    set_trace_id(trace_id)

追踪 ID 格式: tr_{uuid12}_{HHMMSS}
示例: tr_abc123def456_103000

日志集成:
    from core.logging_utils import JSONLogger
    logger = JSONLogger(Path("logs/workflow.jsonl"), "workflow")
    logger.info("阶段开始", trace_id=get_trace_id(), stage="stage_5")
"""

import uuid
from datetime import datetime
from contextvars import ContextVar
from typing import Optional


# 当前追踪 ID（上下文变量，支持异步场景）
_current_trace_id: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)


def get_trace_id() -> str:
    """获取当前追踪 ID
    
    如果当前上下文中没有追踪 ID，则自动创建一个。
    
    Returns:
        追踪 ID 字符串
    """
    tid = _current_trace_id.get()
    if tid is None:
        tid = new_trace()
    return tid


def set_trace_id(tid: str) -> None:
    """设置追踪 ID
    
    用于接收外部传入的 trace_id，或手动设置。
    
    Args:
        tid: 追踪 ID 字符串
    """
    _current_trace_id.set(tid)


def new_trace() -> str:
    """创建新的追踪 ID
    
    格式: tr_{uuid12}_{HHMMSS}
    
    Returns:
        新创建的追踪 ID
    """
    uuid_part = uuid.uuid4().hex[:12]
    time_part = datetime.now().strftime('%H%M%S')
    tid = f"tr_{uuid_part}_{time_part}"
    _current_trace_id.set(tid)
    return tid


def clear_trace() -> None:
    """清除当前追踪 ID
    
    用于在追踪结束后清理上下文。
    """
    _current_trace_id.set(None)


def is_tracing() -> bool:
    """检查是否处于追踪状态
    
    Returns:
        True 表示当前有追踪 ID
    """
    return _current_trace_id.get() is not None


# ==================== 追踪上下文管理器 ====================

class TraceContext:
    """追踪上下文管理器
    
    用于在代码块中自动管理追踪 ID。
    
    Example:
        with TraceContext() as trace_id:
            # 在此代码块中，所有日志都会带有 trace_id
            logger.info("操作开始", trace_id=trace_id)
            ...
            logger.info("操作完成", trace_id=trace_id)
    """
    
    def __init__(self, trace_id: Optional[str] = None):
        """初始化追踪上下文
        
        Args:
            trace_id: 指定的追踪 ID，不提供则自动创建
        """
        self.trace_id = trace_id
        self._previous_id: Optional[str] = None
    
    def __enter__(self) -> str:
        """进入追踪上下文
        
        Returns:
            追踪 ID
        """
        self._previous_id = _current_trace_id.get()
        if self.trace_id is None:
            self.trace_id = new_trace()
        else:
            set_trace_id(self.trace_id)
        return self.trace_id
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """退出追踪上下文
        
        恢复之前的追踪 ID（如果有）。
        """
        if self._previous_id is not None:
            _current_trace_id.set(self._previous_id)
        else:
            clear_trace()


def trace(name: Optional[str] = None):
    """追踪装饰器
    
    用于自动为函数添加追踪上下文。
    
    Args:
        name: 追踪名称（可选）
    
    Example:
        @trace("chapter_creation")
        def create_chapter(chapter_name: str):
            # 此函数执行时会有 trace_id
            logger.info("开始创作", trace_id=get_trace_id())
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with TraceContext() as tid:
                if name:
                    from core.logging_utils import get_logger
                    logger = get_logger("tracing")
                    logger.info(f"开始 {name}", trace_id=tid, function=func.__name__)
                return func(*args, **kwargs)
        return wrapper
    return decorator


# ==================== 子追踪 ID ====================

def new_sub_trace(parent_id: Optional[str] = None, suffix: str = "") -> str:
    """创建子追踪 ID
    
    用于在父追踪下创建子追踪，形成追踪树。
    
    Args:
        parent_id: 父追踪 ID，不提供则使用当前追踪 ID
        suffix: 子追踪后缀标识
    
    Returns:
        子追踪 ID，格式: {parent_id}.{suffix}_{uuid4}
    """
    if parent_id is None:
        parent_id = get_trace_id()
    
    sub_uuid = uuid.uuid4().hex[:4]
    if suffix:
        return f"{parent_id}.{suffix}_{sub_uuid}"
    else:
        return f"{parent_id}.sub_{sub_uuid}"


def get_parent_trace_id(trace_id: str) -> Optional[str]:
    """从子追踪 ID 中获取父追踪 ID
    
    Args:
        trace_id: 子追踪 ID
    
    Returns:
        父追踪 ID，如果不是子追踪则返回 None
    """
    if '.' in trace_id:
        return trace_id.split('.')[0]
    return None