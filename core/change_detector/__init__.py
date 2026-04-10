#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
变更检测模块
==========

提供统一的文件变更检测和同步功能。

核心组件：
- ChangeDetector: 统一变更检测器，检测多数据源变更并触发同步
- FileWatcher: 文件变更检测器，使用hash/modtime检测变更
- SyncManagerAdapter: 同步管理器适配器，封装现有SyncManager

使用方式：
    from core.change_detector import ChangeDetector

    detector = ChangeDetector()
    report = detector.run()

    if report.sources:
        print(f"发现变更: {report.summary}")

参考：统一提炼引擎重构方案.md 第9.5节
"""

from pathlib import Path
from typing import Any

from .file_watcher import (
    FileWatcher,
    FileChange,
    FileState,
)

from .sync_manager_adapter import (
    SyncManagerAdapter,
    SyncResult,
)

from .change_detector import (
    ChangeDetector,
    ChangeReport,
)

__all__ = [
    # 变更检测器
    "ChangeDetector",
    "ChangeReport",
    # 文件检测器
    "FileWatcher",
    "FileChange",
    "FileState",
    # 同步适配器
    "SyncManagerAdapter",
    "SyncResult",
]

__version__ = "1.0.0"


def quick_scan(project_root: str | None = None) -> dict[str, Any]:
    """
    快速扫描变更的便捷函数

    Args:
        project_root: 项目根目录（可选）

    Returns:
        扫描结果字典
    """
    detector = ChangeDetector(project_root=Path(project_root) if project_root else None)
    report = detector.run(sync=False)

    return {
        "changes": {
            source: [change.path for change in changes]
            for source, changes in report.sources.items()
        },
        "summary": report.summary,
        "timestamp": report.timestamp.isoformat(),
    }


def quick_sync(
    project_root: str | None = None, rebuild: bool = False
) -> dict[str, Any]:
    """
    快速同步变更的便捷函数

    Args:
        project_root: 项目根目录（可选）
        rebuild: 是否重建

    Returns:
        同步结果字典
    """
    detector = ChangeDetector(project_root=Path(project_root) if project_root else None)
    report = detector.run(sync=True, rebuild=rebuild)

    return {
        "changes": {
            source: [change.path for change in changes]
            for source, changes in report.sources.items()
        },
        "sync_results": {
            target: {"status": result.status, "count": result.count}
            for target, result in report.sync_results.items()
        },
        "summary": report.summary,
        "timestamp": report.timestamp.isoformat(),
    }


# 导出便捷函数
__all__.extend(["quick_scan", "quick_sync"])
