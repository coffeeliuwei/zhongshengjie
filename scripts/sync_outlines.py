#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
大纲 Qdrant 同步脚本
==================

手动触发章节大纲和总大纲的全量 Qdrant 同步。

用法：
    # 全量同步（检测所有变更后同步）
    python scripts/sync_outlines.py

    # 强制全量重新同步（忽略变更检测状态）
    python scripts/sync_outlines.py --force

    # 仅同步总大纲
    python scripts/sync_outlines.py --total-only

    # 仅同步章节大纲
    python scripts/sync_outlines.py --chapters-only
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def sync_all_outlines(force: bool = False) -> None:
    """全量同步所有大纲文件到 Qdrant"""
    from core.change_detector.change_detector import ChangeDetector
    from core.change_detector.file_watcher import FileChange

    detector = ChangeDetector(project_root=PROJECT_ROOT)

    if force:
        print("[INFO] 强制全量同步模式：扫描所有大纲文件（忽略变更状态）")
        _force_sync_all(detector)
    else:
        print("[INFO] 增量同步模式：仅同步变更文件")
        changes = detector.scan_changes()

        if not changes:
            print("[INFO] 未检测到变更，无需同步。")
            return

        print(f"[INFO] 检测到变更：{list(changes.keys())}")
        results = detector.sync_changes(changes)

        for target, result in results.items():
            print(f"  [{result.status.upper()}] {target}: {result.message}")


def sync_total_outline() -> None:
    """仅同步总大纲"""
    from core.change_detector.sync_manager_adapter import SyncManagerAdapter

    adapter = SyncManagerAdapter(project_root=PROJECT_ROOT)
    result = adapter.sync_total_outline_to_qdrant()
    print(f"[{result.status.upper()}] novel_plot_v1: {result.message}")


def sync_chapter_outlines() -> None:
    """仅同步所有章节大纲"""
    from core.change_detector.sync_manager_adapter import SyncManagerAdapter

    adapter = SyncManagerAdapter(project_root=PROJECT_ROOT)
    outline_dir = PROJECT_ROOT / "章节大纲"

    if not outline_dir.exists():
        print("[WARN] 章节大纲目录不存在，跳过。")
        return

    files = list(outline_dir.glob("*.md"))
    if not files:
        print("[INFO] 章节大纲目录为空，无需同步。")
        return

    print(f"[INFO] 发现 {len(files)} 个章节大纲文件")
    success = 0
    for f in files:
        result = adapter.sync_chapter_outline_file(f)
        status_icon = "OK" if result.status == "success" else "FAIL"
        print(f"  [{status_icon}] {f.name}: {result.message}")
        if result.status == "success":
            success += 1

    print(f"\n[INFO] 同步完成：{success}/{len(files)} 成功")


def _force_sync_all(detector) -> None:
    """强制同步所有大纲（不经过变更检测）"""
    sync_total_outline()
    sync_chapter_outlines()


def main() -> None:
    parser = argparse.ArgumentParser(description="大纲 Qdrant 全量/增量同步工具")
    parser.add_argument("--force", action="store_true", help="强制全量重新同步")
    parser.add_argument("--total-only", action="store_true", help="仅同步总大纲")
    parser.add_argument("--chapters-only", action="store_true", help="仅同步章节大纲")
    args = parser.parse_args()

    if args.total_only:
        sync_total_outline()
    elif args.chapters_only:
        sync_chapter_outlines()
    else:
        sync_all_outlines(force=args.force)


if __name__ == "__main__":
    main()
