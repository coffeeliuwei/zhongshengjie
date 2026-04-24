#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
世界观同步工作流钩子
====================

在小说创作流程中自动检查并同步世界观配置。

使用方式：
1. 在创作流程开始时调用 check_and_sync()
2. 在大纲修改后调用 on_outline_changed()
3. 手动触发同步 call sync_now()
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from datetime import datetime

# 添加core目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from worldview_sync import WorldviewSync, IncrementalSync
from world_config_loader import load_world_config, get_current_world


class WorldviewSyncHook:
    """世界观同步钩子 - 在创作流程中自动同步"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, project_root: Path = None):
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.sync = WorldviewSync(project_root)
        self._initialized = True
        self._last_sync_time = None
        self._auto_sync_enabled = True
        self._callbacks = {
            "before_sync": [],
            "after_sync": [],
            "on_change": [],
            "on_error": [],
        }

    # ============================================================
    # 回调注册
    # ============================================================

    def on(self, event: str, callback: Callable):
        """注册回调函数

        Args:
            event: 事件名称 (before_sync, after_sync, on_change, on_error)
            callback: 回调函数
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _trigger(self, event: str, data: Dict = None):
        """触发回调"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(data or {})
            except Exception as e:
                print(f"回调执行失败: {e}")

    # ============================================================
    # 核心同步方法
    # ============================================================

    def check_and_sync(self, force: bool = False) -> Dict[str, Any]:
        """检查并同步世界观配置

        在创作流程开始时调用，自动检测大纲变更并同步。

        Args:
            force: 是否强制同步

        Returns:
            同步结果
        """
        # 触发前置回调
        self._trigger("before_sync", {"force": force})

        # 检查是否启用自动同步
        try:
            from config_loader import is_auto_sync_enabled

            if not is_auto_sync_enabled() and not force:
                return {"success": True, "synced": False, "message": "自动同步已禁用"}
        except Exception:
            pass  # 配置加载失败时继续执行

        # 检查同步状态
        status = self.sync.check_sync_status()

        result = {"success": True, "synced": False, "message": None, "changes": None}

        if not status["sync_needed"] and not force:
            result["message"] = "世界观配置已是最新"
            self._trigger("after_sync", result)
            return result

        # 执行增量同步
        try:
            sync_result = self.sync.sync(force=force, incremental=True)
            result.update(sync_result)

            if sync_result.get("synced"):
                self._last_sync_time = datetime.now()

                # 触发变更回调
                if sync_result.get("changes"):
                    self._trigger(
                        "on_change",
                        {
                            "changes": sync_result["changes"],
                            "sync_type": sync_result.get("sync_type"),
                        },
                    )

            self._trigger("after_sync", result)

        except Exception as e:
            result["success"] = False
            result["message"] = f"同步失败: {e}"
            self._trigger("on_error", {"error": str(e)})

        return result

    def on_outline_changed(self, outline_path: str = None) -> Dict[str, Any]:
        """大纲变更时触发同步

        在大纲文件修改后调用。

        Args:
            outline_path: 大纲文件路径（可选）

        Returns:
            同步结果
        """
        return self.check_and_sync(force=True)

    def sync_now(self, incremental: bool = True) -> Dict[str, Any]:
        """立即同步

        手动触发同步操作。

        Args:
            incremental: 是否使用增量同步

        Returns:
            同步结果
        """
        return self.sync.sync(force=True, incremental=incremental)

    # ============================================================
    # 状态查询
    # ============================================================

    def get_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        return self.sync.check_sync_status()

    def get_diff(self) -> Dict[str, Any]:
        """获取变更差异"""
        return self.sync.diff()

    def get_last_sync_time(self) -> Optional[datetime]:
        """获取上次同步时间"""
        return self._last_sync_time

    def is_sync_needed(self) -> bool:
        """是否需要同步"""
        status = self.sync.check_sync_status()
        return status.get("sync_needed", False)

    # ============================================================
    # 配置方法
    # ============================================================

    def enable_auto_sync(self):
        """启用自动同步"""
        self._auto_sync_enabled = True

    def disable_auto_sync(self):
        """禁用自动同步"""
        self._auto_sync_enabled = False


# ============================================================
# 便捷函数
# ============================================================

_hook_instance = None


def get_sync_hook(project_root: Path = None) -> WorldviewSyncHook:
    """获取同步钩子实例"""
    global _hook_instance
    if _hook_instance is None:
        _hook_instance = WorldviewSyncHook(project_root)
    return _hook_instance


def check_worldview_sync(force: bool = False) -> Dict[str, Any]:
    """检查并同步世界观配置（便捷函数）"""
    hook = get_sync_hook()
    return hook.check_and_sync(force)


def sync_worldview_now(incremental: bool = True) -> Dict[str, Any]:
    """立即同步世界观（便捷函数）"""
    hook = get_sync_hook()
    return hook.sync_now(incremental)


def get_worldview_sync_status() -> Dict[str, Any]:
    """获取世界观同步状态（便捷函数）"""
    hook = get_sync_hook()
    return hook.get_status()


# ============================================================
# 工作流集成装饰器
# ============================================================


def with_worldview_sync(func):
    """装饰器：在函数执行前自动同步世界观

    使用示例：
    @with_worldview_sync
    def create_chapter(chapter_num):
        # 世界观已自动同步
        ...
    """

    def wrapper(*args, **kwargs):
        # 执行同步
        hook = get_sync_hook()
        sync_result = hook.check_and_sync()

        # 如果同步失败，打印警告但不中断
        if not sync_result.get("success"):
            print(f"警告: 世界观同步失败 - {sync_result.get('message')}")

        # 执行原函数
        return func(*args, **kwargs)

    return wrapper


# ============================================================
# 命令行接口
# ============================================================


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="世界观同步工作流钩子")
    parser.add_argument("--check", "-c", action="store_true", help="检查同步状态")
    parser.add_argument("--sync", "-s", action="store_true", help="执行同步")
    parser.add_argument("--diff", "-d", action="store_true", help="查看变更差异")
    parser.add_argument("--force", "-f", action="store_true", help="强制同步")

    args = parser.parse_args()

    hook = get_sync_hook()

    if args.check:
        status = hook.get_status()
        print("=" * 60)
        print("世界观同步状态")
        print("=" * 60)
        print(f"需要同步: {'是' if status.get('sync_needed') else '否'}")
        print(f"原因: {status.get('reason', '未知')}")

    elif args.sync:
        result = hook.check_and_sync(force=args.force)
        print("=" * 60)
        print("同步结果")
        print("=" * 60)
        print(f"状态: {'成功' if result.get('success') else '失败'}")
        print(f"类型: {result.get('sync_type', 'none')}")
        print(f"消息: {result.get('message', '无')}")
        if result.get("changes"):
            print("变更:")
            for change in result["changes"]:
                print(f"  - {change}")

    elif args.diff:
        diff_result = hook.get_diff()
        print("=" * 60)
        print("变更差异")
        print("=" * 60)
        print(f"消息: {diff_result.get('message', '无')}")
        print(f"有变更: {'是' if diff_result.get('has_changes') else '否'}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
