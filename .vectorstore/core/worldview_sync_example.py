#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
世界观同步集成示例
==================

展示如何在小说创作流程中集成世界观自动同步。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / ".vectorstore" / "core"))

from worldview_sync_hook import (
    WorldviewSyncHook,
    get_sync_hook,
    check_worldview_sync,
    sync_worldview_now,
    with_worldview_sync,
)


# ============================================================
# 示例1：在创作流程开始时检查同步
# ============================================================


def example_check_before_creation():
    """示例：创作前检查同步"""
    print("=" * 60)
    print("示例1：创作前检查同步")
    print("=" * 60)

    # 获取同步钩子
    hook = get_sync_hook()

    # 注册回调
    def on_change(data):
        print(f"检测到世界观变更: {data.get('changes')}")

    def on_error(data):
        print(f"同步错误: {data.get('error')}")

    hook.on("on_change", on_change)
    hook.on("on_error", on_error)

    # 检查并同步
    result = hook.check_and_sync()

    print(f"\n同步结果:")
    print(f"  成功: {result.get('success')}")
    print(f"  已同步: {result.get('synced')}")
    print(f"  消息: {result.get('message')}")

    if result.get("changes"):
        print(f"  变更: {result.get('changes')}")


# ============================================================
# 示例2：使用装饰器自动同步
# ============================================================


@with_worldview_sync
def create_chapter(chapter_num: int):
    """示例：创建章节时自动同步世界观"""
    print(f"\n创建第 {chapter_num} 章...")
    print("世界观已自动检查并同步")
    # 这里是实际的章节创建逻辑
    return {"chapter": chapter_num, "status": "created"}


def example_decorator_usage():
    """示例：装饰器用法"""
    print("\n" + "=" * 60)
    print("示例2：使用装饰器自动同步")
    print("=" * 60)

    result = create_chapter(1)
    print(f"结果: {result}")


# ============================================================
# 示例3：大纲变更后触发同步
# ============================================================


def example_outline_changed():
    """示例：大纲变更后触发同步"""
    print("\n" + "=" * 60)
    print("示例3：大纲变更后触发同步")
    print("=" * 60)

    hook = get_sync_hook()

    # 模拟大纲变更
    print("\n大纲已修改，触发同步...")

    result = hook.on_outline_changed()

    print(f"同步结果:")
    print(f"  类型: {result.get('sync_type')}")
    print(f"  消息: {result.get('message')}")


# ============================================================
# 示例4：查询同步状态
# ============================================================


def example_query_status():
    """示例：查询同步状态"""
    print("\n" + "=" * 60)
    print("示例4：查询同步状态")
    print("=" * 60)

    hook = get_sync_hook()

    # 获取状态
    status = hook.get_status()

    print(f"\n同步状态:")
    print(f"  需要同步: {'是' if status.get('sync_needed') else '否'}")
    print(f"  原因: {status.get('reason')}")

    # 获取差异
    if status.get("sync_needed"):
        diff = hook.get_diff()
        if diff.get("has_changes"):
            print(f"\n检测到变更:")
            print(f"  有变更: 是")


# ============================================================
# 示例5：完整的创作流程集成
# ============================================================


class NovelCreationWorkflow:
    """示例：完整的小说创作工作流"""

    def __init__(self):
        self.hook = get_sync_hook()
        self._setup_callbacks()

    def _setup_callbacks(self):
        """设置回调"""
        self.hook.on("before_sync", self._on_before_sync)
        self.hook.on("after_sync", self._on_after_sync)
        self.hook.on("on_change", self._on_worldview_change)

    def _on_before_sync(self, data):
        print("[工作流] 准备同步世界观...")

    def _on_after_sync(self, data):
        if data.get("synced"):
            print(f"[工作流] 世界观已同步 ({data.get('sync_type')})")

    def _on_worldview_change(self, data):
        print(f"[工作流] 世界观变更: {data.get('changes')}")
        # 这里可以触发其他逻辑，如通知作家更新

    def start_creation(self, chapter_num: int):
        """开始创作"""
        print(f"\n{'=' * 60}")
        print(f"开始创作第 {chapter_num} 章")
        print("=" * 60)

        # 步骤1：同步世界观
        print("\n[步骤1] 同步世界观配置")
        sync_result = self.hook.check_and_sync()

        if not sync_result.get("success"):
            print(f"警告: 世界观同步失败 - {sync_result.get('message')}")

        # 步骤2：加载世界观配置
        print("\n[步骤2] 加载世界观配置")
        from world_config_loader import load_world_config, get_current_world

        world_name = get_current_world()
        config = load_world_config(world_name)
        print(f"  当前世界观: {config.get('world_name')}")
        print(f"  力量体系: {len(config.get('power_systems', {}))} 个")
        print(f"  势力: {len(config.get('factions', {}))} 个")
        print(f"  角色: {len(config.get('key_characters', {}))} 个")

        # 步骤3：创作内容
        print("\n[步骤3] 开始创作...")
        # 这里是实际的创作逻辑

        return {"chapter": chapter_num, "status": "completed"}


def example_full_workflow():
    """示例：完整工作流"""
    print("\n" + "=" * 60)
    print("示例5：完整的创作工作流")
    print("=" * 60)

    workflow = NovelCreationWorkflow()
    result = workflow.start_creation(1)
    print(f"\n创作结果: {result}")


# ============================================================
# 主函数
# ============================================================


def main():
    """运行所有示例"""
    print("=" * 60)
    print("世界观同步集成示例")
    print("=" * 60)

    # 运行示例
    example_check_before_creation()
    example_decorator_usage()
    example_query_status()
    example_full_workflow()

    print("\n" + "=" * 60)
    print("示例运行完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
