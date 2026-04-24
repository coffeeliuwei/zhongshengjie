# -*- coding: utf-8 -*-
"""统一 JSON Lines 日志工具。

每条日志为单行 JSON，字段：timestamp, module, level, message, + 任意 kwargs。
用法：
    from core.logging_utils import get_logger
    logger = get_logger("my_module")
    logger.info("启动完成", version="1.0")
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class JSONLogger:
    """写入 .jsonl 文件的结构化日志器。"""

    log_path: Path
    module_name: str

    def __init__(self, log_path: Path, module_name: str) -> None:
        self.log_path = Path(log_path)
        self.module_name = module_name
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, level: str, message: str, **kwargs: object) -> None:
        """写入一条 JSON 日志行。自动注入 trace_id（如有）。"""
        # 自动注入 trace_id（如果当前有追踪上下文且调用者未手动传入）
        if "trace_id" not in kwargs:
            try:
                from core.tracing import is_tracing, get_trace_id
                if is_tracing():
                    kwargs["trace_id"] = get_trace_id()
            except ImportError:
                pass

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "module": self.module_name,
            "level": level,
            "message": message,
            **kwargs,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            _ = f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    def info(self, message: str, **kwargs: object) -> None:
        self.log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs: object) -> None:
        self.log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs: object) -> None:
        self.log("ERROR", message, **kwargs)


def get_logger(module_name: str, log_dir: str = "logs") -> JSONLogger:
    """获取模块日志器（自动命名 .jsonl 文件）"""
    log_path = Path(log_dir) / f"{module_name}.jsonl"
    return JSONLogger(log_path, module_name)
