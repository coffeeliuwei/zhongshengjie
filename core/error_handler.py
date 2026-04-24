"""
统一错误处理框架

功能：
1. 定义项目统一的错误类型和错误码
2. 提供错误处理装饰器
3. 支持错误追踪和日志记录
4. 提供用户友好的错误信息

设计目的：
- 统一各模块的错误处理方式
- 提供清晰的错误追踪机制
- 便于调试和维护
"""

from enum import Enum
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
import traceback
import functools


class ErrorLevel(Enum):
    """错误级别"""

    WARNING = "warning"  # 警告，不影响主流程
    ERROR = "error"  # 错误，影响当前操作
    CRITICAL = "critical"  # 严重错误，影响整个系统


class ErrorCode(Enum):
    """错误码定义"""

    # 创作模块错误 (CREATION_001 - CREATION_099)
    CREATION_WORKFLOW_FAILED = ("CREATION_001", "工作流执行失败")
    CREATION_WRITER_TIMEOUT = ("CREATION_002", "作家执行超时")
    CREATION_EVALUATION_FAILED = ("CREATION_003", "评估失败")
    CREATION_ITERATION_EXCEEDED = ("CREATION_004", "迭代次数超限")
    CREATION_FUSION_FAILED = ("CREATION_005", "融合失败")
    CREATION_PHASE_FAILED = ("CREATION_006", "Phase 执行失败")

    # 数据库错误 (DATABASE_001 - DATABASE_099)
    DATABASE_CONNECTION_FAILED = ("DATABASE_001", "数据库连接失败")
    DATABASE_QUERY_FAILED = ("DATABASE_002", "数据库查询失败")
    DATABASE_COLLECTION_NOT_FOUND = ("DATABASE_003", "集合不存在")
    DATABASE_SYNC_FAILED = ("DATABASE_004", "数据同步失败")

    # 文件错误 (FILE_001 - FILE_099)
    FILE_NOT_FOUND = ("FILE_001", "文件不存在")
    FILE_PARSE_FAILED = ("FILE_002", "文件解析失败")
    FILE_WRITE_FAILED = ("FILE_003", "文件写入失败")

    # 配置错误 (CONFIG_001 - CONFIG_099)
    CONFIG_NOT_FOUND = ("CONFIG_001", "配置文件不存在")
    CONFIG_PARSE_FAILED = ("CONFIG_002", "配置解析失败")
    CONFIG_INVALID = ("CONFIG_003", "配置值无效")

    # 技能错误 (SKILL_001 - SKILL_099)
    SKILL_NOT_FOUND = ("SKILL_001", "技能文件不存在")
    SKILL_LOAD_FAILED = ("SKILL_002", "技能加载失败")
    SKILL_EXECUTION_FAILED = ("SKILL_003", "技能执行失败")

    # 检索错误 (SEARCH_001 - SEARCH_099)
    SEARCH_NO_RESULTS = ("SEARCH_001", "检索无结果")
    SEARCH_INDEX_FAILED = ("SEARCH_002", "索引失败")

    # 系统错误 (SYSTEM_001 - SYSTEM_099)
    SYSTEM_INITIALIZATION_FAILED = ("SYSTEM_001", "系统初始化失败")
    SYSTEM_SHUTDOWN_FAILED = ("SYSTEM_002", "系统关闭失败")
    SYSTEM_RESOURCE_EXHAUSTED = ("SYSTEM_003", "系统资源耗尽")

    # 未知错误
    UNKNOWN = ("UNKNOWN_000", "未知错误")

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message


@dataclass
class NovelError(Exception):
    """
    项目统一错误基类

    Attributes:
        error_code: 错误码
        error_message: 错误信息
        error_level: 错误级别
        details: 详细信息
        timestamp: 时间戳
        trace: 堆栈追踪
        suggestions: 解决建议
    """

    error_code: str = "UNKNOWN_000"
    error_message: str = "未知错误"
    error_level: ErrorLevel = ErrorLevel.ERROR
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    trace: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)

    def __post_init__(self):
        # 自动捕获堆栈
        if self.trace is None:
            self.trace = (
                traceback.format_exc()
                if traceback.format_exc() != "NoneType: None\n"
                else None
            )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error_code": self.error_code,
            "error_message": self.error_message,
            "error_level": self.error_level.value,
            "details": self.details,
            "timestamp": self.timestamp,
            "trace": self.trace,
            "suggestions": self.suggestions,
        }

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.error_message}"

    def user_message(self) -> str:
        """用户友好的错误信息"""
        msg = f"❌ 错误: {self.error_message}\n"
        msg += f"   错误码: {self.error_code}\n"
        if self.suggestions:
            msg += "   建议:\n"
            for s in self.suggestions:
                msg += f"   - {s}\n"
        return msg


# 具体错误类型
class CreationError(NovelError):
    """创作模块错误"""

    def __init__(
        self, error_code: ErrorCode = ErrorCode.CREATION_WORKFLOW_FAILED, **kwargs
    ):
        super().__init__(
            error_code=error_code.code,
            error_message=error_code.message,
            **kwargs,
        )


class DatabaseError(NovelError):
    """数据库错误"""

    def __init__(
        self, error_code: ErrorCode = ErrorCode.DATABASE_CONNECTION_FAILED, **kwargs
    ):
        super().__init__(
            error_code=error_code.code,
            error_message=error_code.message,
            error_level=ErrorLevel.CRITICAL,
            **kwargs,
        )


class FileError(NovelError):
    """文件错误"""

    def __init__(self, error_code: ErrorCode = ErrorCode.FILE_NOT_FOUND, **kwargs):
        super().__init__(
            error_code=error_code.code,
            error_message=error_code.message,
            **kwargs,
        )


class ConfigError(NovelError):
    """配置错误"""

    def __init__(self, error_code: ErrorCode = ErrorCode.CONFIG_NOT_FOUND, **kwargs):
        super().__init__(
            error_code=error_code.code,
            error_message=error_code.message,
            **kwargs,
        )


class SkillError(NovelError):
    """技能错误"""

    def __init__(self, error_code: ErrorCode = ErrorCode.SKILL_NOT_FOUND, **kwargs):
        super().__init__(
            error_code=error_code.code,
            error_message=error_code.message,
            **kwargs,
        )


class SearchError(NovelError):
    """检索错误"""

    def __init__(self, error_code: ErrorCode = ErrorCode.SEARCH_NO_RESULTS, **kwargs):
        super().__init__(
            error_code=error_code.code,
            error_message=error_code.message,
            error_level=ErrorLevel.WARNING,
            **kwargs,
        )


class SystemError(NovelError):
    """系统错误"""

    def __init__(
        self, error_code: ErrorCode = ErrorCode.SYSTEM_INITIALIZATION_FAILED, **kwargs
    ):
        super().__init__(
            error_code=error_code.code,
            error_message=error_code.message,
            error_level=ErrorLevel.CRITICAL,
            **kwargs,
        )


# 错误处理装饰器
def handle_errors(
    default_return: Any = None,
    reraise: bool = False,
    log_trace: bool = True,
    suggestions: Optional[List[str]] = None,
):
    """
    错误处理装饰器

    Args:
        default_return: 发生错误时的默认返回值
        reraise: 是否重新抛出异常
        log_trace: 是否记录堆栈追踪
        suggestions: 错误建议列表

    Usage:
        @handle_errors(default_return=None, reraise=False)
        def my_function():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except NovelError as e:
                # 项目自定义错误
                if suggestions:
                    e.suggestions = suggestions
                if log_trace:
                    _log_error(e)
                if reraise:
                    raise
                return default_return
            except Exception as e:
                # 未知错误，包装为 NovelError
                error = NovelError(
                    error_code=ErrorCode.UNKNOWN.code,
                    error_message=str(e),
                    error_level=ErrorLevel.ERROR,
                    suggestions=suggestions
                    or ["请检查输入参数", "查看日志获取详细信息"],
                )
                if log_trace:
                    _log_error(error)
                if reraise:
                    raise error
                return default_return

        return wrapper

    return decorator


def _log_error(error: NovelError):
    """记录错误日志"""
    import logging

    logger = logging.getLogger("novel_error")

    # 格式化日志
    log_msg = f"\n{'=' * 60}\n"
    log_msg += f"[ERROR] {error.error_code}: {error.error_message}\n"
    log_msg += f"Level: {error.error_level.value}\n"
    log_msg += f"Time: {error.timestamp}\n"

    if error.details:
        log_msg += f"Details: {error.details}\n"

    if error.trace:
        log_msg += f"\nTrace:\n{error.trace}\n"

    log_msg += f"{'=' * 60}\n"

    # 根据级别选择日志级别
    if error.error_level == ErrorLevel.WARNING:
        logger.warning(log_msg)
    elif error.error_level == ErrorLevel.CRITICAL:
        logger.critical(log_msg)
    else:
        logger.error(log_msg)


# 错误处理上下文管理器
class ErrorContext:
    """
    错误处理上下文管理器

    Usage:
        with ErrorContext("创作场景", error_code=ErrorCode.CREATION_WORKFLOW_FAILED):
            # 执行代码
            ...
    """

    def __init__(
        self,
        operation: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN,
        error_level: ErrorLevel = ErrorLevel.ERROR,
        suggestions: Optional[List[str]] = None,
        reraise: bool = False,
    ):
        self.operation = operation
        self.error_code = error_code
        self.error_level = error_level
        self.suggestions = suggestions or []
        self.reraise = reraise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # 发生异常
            error = NovelError(
                error_code=self.error_code.code,
                error_message=f"{self.operation} 失败: {str(exc_val)}",
                error_level=self.error_level,
                details={"operation": self.operation, "exception_type": str(exc_type)},
                suggestions=self.suggestions,
            )
            _log_error(error)

            if self.reraise:
                raise error

            # 返回 True 抑制异常
            return True

        return False


# 错误收集器
class ErrorCollector:
    """
    错误收集器

    用于收集多个操作中的错误，最后统一处理。

    Usage:
        collector = ErrorCollector()

        with collector.catch("操作1"):
            # 可能出错的代码
            ...

        with collector.catch("操作2"):
            # 可能出错的代码
            ...

        if collector.has_errors:
            print(collector.summary())
    """

    def __init__(self):
        self.errors: List[NovelError] = []

    def catch(self, operation: str, **kwargs) -> ErrorContext:
        """创建错误捕获上下文"""
        return ErrorContext(operation, reraise=False, **kwargs)

    def add_error(self, error: NovelError):
        """添加错误"""
        self.errors.append(error)

    @property
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0

    @property
    def has_critical_errors(self) -> bool:
        """是否有严重错误"""
        return any(e.error_level == ErrorLevel.CRITICAL for e in self.errors)

    def summary(self) -> str:
        """错误摘要"""
        if not self.has_errors:
            return "✅ 无错误"

        summary = f"❌ 发现 {len(self.errors)} 个错误:\n\n"

        for i, error in enumerate(self.errors, 1):
            level_icon = {"warning": "⚠️", "error": "❌", "critical": "🔴"}
            summary += f"{i}. {level_icon.get(error.error_level.value, '❌')} [{error.error_code}] {error.error_message}\n"

        return summary

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error_count": len(self.errors),
            "has_critical": self.has_critical_errors,
            "errors": [e.to_dict() for e in self.errors],
        }


# 便捷函数
def raise_error(
    error_code: ErrorCode,
    details: Optional[Dict] = None,
    suggestions: Optional[List[str]] = None,
):
    """
    便捷函数：抛出错误

    Usage:
        raise_error(ErrorCode.FILE_NOT_FOUND, details={"file": "xxx.md"})
    """
    error_classes = {
        "CREATION": CreationError,
        "DATABASE": DatabaseError,
        "FILE": FileError,
        "CONFIG": ConfigError,
        "SKILL": SkillError,
        "SEARCH": SearchError,
        "SYSTEM": SystemError,
    }

    prefix = error_code.code.split("_")[0]
    error_class = error_classes.get(prefix, NovelError)

    raise error_class(
        error_code=error_code, details=details or {}, suggestions=suggestions or []
    )


# 使用示例
if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    # 示例1：直接抛出错误
    print("=" * 60)
    print("示例1：抛出错误")
    print("=" * 60)

    try:
        raise CreationError(
            error_code=ErrorCode.CREATION_ITERATION_EXCEEDED,
            details={"iterations": 3, "max_iterations": 3},
            suggestions=["尝试降低场景复杂度", "增加阶段0的讨论"],
        )
    except NovelError as e:
        print(e.user_message())

    # 示例2：使用装饰器
    print("\n" + "=" * 60)
    print("示例2：装饰器处理错误")
    print("=" * 60)

    @handle_errors(default_return=None, suggestions=["检查文件路径"])
    def read_file(path: str):
        with open(path, "r") as f:
            return f.read()

    result = read_file("nonexistent_file.txt")
    print(f"返回值: {result}")

    # 示例3：错误收集器
    print("\n" + "=" * 60)
    print("示例3：错误收集器")
    print("=" * 60)

    collector = ErrorCollector()

    with collector.catch("读取配置"):
        raise ConfigError(error_code=ErrorCode.CONFIG_PARSE_FAILED)

    with collector.catch("连接数据库"):
        raise DatabaseError(error_code=ErrorCode.DATABASE_CONNECTION_FAILED)

    print(collector.summary())
