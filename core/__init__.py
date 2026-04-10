"""
众生界 - 核心模块

⚠️ 状态说明：扩展备用，当前不启用

当前小说工作流通过 Skill 系统驱动（novelist-* Skills），而非本 Python 模块。
本模块为未来扩展预留：
  - Web 界面后端 API
  - CLI 命令行工具（python -m core kb --stats）
  - 自动化后台脚本
  - 会话数据提取（对话式工作流）

对话形式使用时，AI 直接读取文件、调用 Skills，无需经过此模块。

功能清单（预留）：
  - cli.py: CLI 命令入口
  - config_manager.py: 配置管理
  - path_manager.py: 路径管理
  - db_connection.py: 数据库连接（含降级模式）
  - error_handler.py: 统一错误处理框架
  - health_check.py: 系统健康检查
  - conversation/: 会话数据提取模块
"""

from .config_manager import ConfigManager
from .path_manager import PathManager
from .db_connection import DatabaseConnectionManager, DatabaseStatus, get_db_manager
from .error_handler import (
    NovelError,
    ErrorCode,
    ErrorLevel,
    CreationError,
    DatabaseError,
    FileError,
    ConfigError,
    SkillError,
    SearchError,
    SystemError,
    handle_errors,
    ErrorContext,
    ErrorCollector,
    raise_error,
)
from .health_check import (
    HealthChecker,
    HealthStatus,
    HealthCheckResult,
    HealthReport,
    run_health_check,
)
from .conversation import (
    IntentClassifier,
    IntentCategory,
    IntentResult,
    ConversationDataExtractor,
    ExtractionResult,
    FileUpdater,
    UpdateResult,
    process_user_input,
)

__all__ = [
    # 配置和路径
    "ConfigManager",
    "PathManager",
    # 数据库
    "DatabaseConnectionManager",
    "DatabaseStatus",
    "get_db_manager",
    # 错误处理
    "NovelError",
    "ErrorCode",
    "ErrorLevel",
    "CreationError",
    "DatabaseError",
    "FileError",
    "ConfigError",
    "SkillError",
    "SearchError",
    "SystemError",
    "handle_errors",
    "ErrorContext",
    "ErrorCollector",
    "raise_error",
    # 健康检查
    "HealthChecker",
    "HealthStatus",
    "HealthCheckResult",
    "HealthReport",
    "run_health_check",
    # 会话数据提取
    "IntentClassifier",
    "IntentCategory",
    "IntentResult",
    "ConversationDataExtractor",
    "ExtractionResult",
    "FileUpdater",
    "UpdateResult",
    "process_user_input",
]
