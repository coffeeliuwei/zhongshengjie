#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
清理旧版 Collections
===================

删除已迁移完成的旧版collections (384维):
- novel_settings → novel_settings_v2 已完成
- writing_techniques → writing_techniques_v2 已完成
- case_library → case_library_v2 迁移中

注意：只有在确认v2数据完整后才执行删除！
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config_loader import get_qdrant_url

from qdrant_client import QdrantClient
from datetime import datetime

QDRANT_DOCKER_URL = get_qdrant_url()


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def check_and_clean():
    client = QdrantClient(url=QDRANT_DOCKER_URL)

    log("=" * 60)
    log("Collection Cleanup Tool")
    log("=" * 60)

    # 检查迁移状态
    collections_to_check = [
        ("novel_settings", "novel_settings_v2", 160),
        ("writing_techniques", "writing_techniques_v2", 986),
        ("case_library", "case_library_v2", 342163),
    ]

    ready_to_delete = []

    for old_name, new_name, expected_min in collections_to_check:
        try:
            old_info = client.get_collection(old_name)
            old_count = old_info.points_count
        except:
            old_count = 0

        try:
            new_info = client.get_collection(new_name)
            new_count = new_info.points_count
        except:
            new_count = 0

        migration_pct = new_count / old_count * 100 if old_count > 0 else 0
        status = "READY" if new_count >= expected_min * 0.95 else "WAIT"

        log(f"\n{old_name} → {new_name}:")
        log(f"  Old: {old_count:,}, New: {new_count:,}")
        log(f"  Migration: {migration_pct:.1f}%")
        log(f"  Status: {status}")

        if status == "READY":
            ready_to_delete.append(old_name)

    log("\n" + "=" * 60)
    log(f"Ready to delete: {ready_to_delete}")
    log("=" * 60)

    if not ready_to_delete:
        log("\nNo collections ready for deletion.")
        return

    # 确认删除
    response = input("\nProceed with deletion? (yes/no): ")

    if response.lower() != "yes":
        log("Cancelled.")
        return

    # 执行删除
    for name in ready_to_delete:
        try:
            client.delete_collection(name)
            log(f"Deleted: {name}")
        except Exception as e:
            log(f"Error deleting {name}: {e}")

    log("\nCleanup complete!")


if __name__ == "__main__":
    check_and_clean()
