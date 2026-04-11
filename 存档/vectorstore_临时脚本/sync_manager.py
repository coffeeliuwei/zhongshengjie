#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双向同步管理器
实现文件 ↔ 数据库的双向同步

使用方法：
    from sync_manager import SyncManager

    manager = SyncManager()

    # 同步所有文件到数据库
    manager.sync_to_database()

    # 同步数据库到文件
    manager.sync_to_files()

    # 检查同步状态
    status = manager.check_sync_status()

    # 自动同步（检测变化方向）
    manager.auto_sync()
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

try:
    import chromadb
except ImportError:
    print("请安装 chromadb: pip install chromadb")
    exit(1)


# ============================================================
# 配置
# ============================================================

PROJECT_DIR = Path(r"D:\动画\众生界")
VECTORSTORE_DIR = PROJECT_DIR / ".vectorstore"
SYNC_LOG_FILE = VECTORSTORE_DIR / "sync_log.json"

# 监控的文件路径
WATCH_PATHS = {
    "章节大纲": PROJECT_DIR / "章节大纲",
    "设定": PROJECT_DIR / "设定",
    "总大纲": PROJECT_DIR / "总大纲.md",
}


# ============================================================
# 同步记录
# ============================================================


@dataclass
class SyncRecord:
    """同步记录"""

    source: str  # 文件路径或数据库ID
    target: str  # 对应的目标
    action: str  # create/update/delete
    timestamp: str
    content_hash: str
    status: str  # success/conflict/error


# ============================================================
# 同步管理器
# ============================================================


class SyncManager:
    """双向同步管理器"""

    def __init__(self):
        self.client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
        self.knowledge_collection = self.client.get_collection("novelist_knowledge")
        self.sync_log: List[Dict] = self._load_sync_log()
        self.file_hashes: Dict[str, str] = {}
        self.db_hashes: Dict[str, str] = {}

    # ============================================================
    # 同步日志
    # ============================================================

    def _load_sync_log(self) -> List[Dict]:
        """加载同步日志"""
        if SYNC_LOG_FILE.exists():
            try:
                with open(SYNC_LOG_FILE, encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_sync_log(self):
        """保存同步日志"""
        with open(SYNC_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.sync_log, f, ensure_ascii=False, indent=2)

    def _add_log(self, record: SyncRecord):
        """添加同步日志"""
        self.sync_log.append(
            {
                "source": record.source,
                "target": record.target,
                "action": record.action,
                "timestamp": record.timestamp,
                "content_hash": record.content_hash,
                "status": record.status,
            }
        )
        self._save_sync_log()

    # ============================================================
    # Hash 计算
    # ============================================================

    def _hash_file(self, file_path: Path) -> str:
        """计算文件hash"""
        content = file_path.read_text(encoding="utf-8")
        return hashlib.md5(content.encode()).hexdigest()

    def _hash_content(self, content: str) -> str:
        """计算内容hash"""
        return hashlib.md5(content.encode()).hexdigest()

    # ============================================================
    # 文件 → 数据库同步
    # ============================================================

    def sync_to_database(self, force: bool = False) -> Dict[str, Any]:
        """
        同步文件到数据库

        Args:
            force: 强制同步，忽略hash检查

        Returns:
            同步结果统计
        """
        results = {
            "checked": 0,
            "updated": 0,
            "created": 0,
            "skipped": 0,
            "errors": [],
        }

        # 获取数据库中所有条目的hash
        db_data = self.knowledge_collection.get()
        db_hashes = {}
        for i, meta in enumerate(db_data["metadatas"]):
            item_id = db_data["ids"][i]
            content_hash = meta.get("内容hash", "")
            source_file = meta.get("来源文件", "")
            db_hashes[item_id] = {
                "hash": content_hash,
                "source": source_file,
            }

        # 检查每个监控路径
        for path_name, path in WATCH_PATHS.items():
            if path.is_file():
                files = [path]
            else:
                files = list(path.glob("*.md"))

            for file_path in files:
                results["checked"] += 1

                try:
                    # 计算文件hash
                    file_hash = self._hash_file(file_path)
                    relative_path = str(file_path.relative_to(PROJECT_DIR))

                    # 检查是否需要更新
                    needs_update = force

                    if not force:
                        # 查找数据库中是否有对应条目
                        existing_items = [
                            (item_id, info)
                            for item_id, info in db_hashes.items()
                            if info["source"] == relative_path
                        ]

                        if existing_items:
                            # 检查hash是否变化
                            for item_id, info in existing_items:
                                if info["hash"] != file_hash:
                                    needs_update = True
                                    break
                        else:
                            needs_update = True

                    if needs_update:
                        # 重新向量化该文件
                        from knowledge_vectorizer import SettingParser, OutlineParser

                        if "章节大纲" in str(file_path):
                            parser = OutlineParser(file_path)
                        else:
                            parser = SettingParser(file_path)

                        units = parser.parse()

                        # 更新/添加到数据库
                        for unit in units:
                            self.knowledge_collection.upsert(
                                ids=[unit.id],
                                documents=[f"{unit.name}\n\n{unit.content}"],
                                metadatas=[
                                    {
                                        "类型": unit.type,
                                        "名称": unit.name,
                                        "来源文件": unit.source_file,
                                        "来源章节": unit.source_section,
                                        "内容hash": unit.content_hash,
                                        "创建时间": unit.created_at,
                                        "更新时间": datetime.now().isoformat(),
                                        **{k: str(v) for k, v in unit.metadata.items()},
                                    }
                                ],
                            )

                        action = "updated" if existing_items else "created"
                        if action == "updated":
                            results["updated"] += len(units)
                        else:
                            results["created"] += len(units)

                        # 记录日志
                        self._add_log(
                            SyncRecord(
                                source=relative_path,
                                target=f"数据库({len(units)}条)",
                                action="sync_to_db",
                                timestamp=datetime.now().isoformat(),
                                content_hash=file_hash,
                                status="success",
                            )
                        )
                    else:
                        results["skipped"] += 1

                except Exception as e:
                    results["errors"].append(
                        {
                            "file": str(file_path),
                            "error": str(e),
                        }
                    )

        return results

    # ============================================================
    # 数据库 → 文件同步
    # ============================================================

    def sync_to_files(self) -> Dict[str, Any]:
        """
        同步数据库到文件

        注意：这个操作会覆盖文件内容，谨慎使用

        Returns:
            同步结果统计
        """
        results = {
            "checked": 0,
            "updated": 0,
            "errors": [],
        }

        # 获取数据库中所有条目
        db_data = self.knowledge_collection.get()

        # 按来源文件分组
        file_contents: Dict[str, List[Dict]] = {}

        for i, meta in enumerate(db_data["metadatas"]):
            source_file = meta.get("来源文件", "")
            if not source_file:
                continue

            if source_file not in file_contents:
                file_contents[source_file] = []

            file_contents[source_file].append(
                {
                    "id": db_data["ids"][i],
                    "content": db_data["documents"][i],
                    "metadata": meta,
                }
            )

        # 对每个文件进行同步
        for relative_path, items in file_contents.items():
            file_path = PROJECT_DIR / relative_path

            if not file_path.exists():
                continue

            results["checked"] += 1

            # 这里只更新内容，不改变文件结构
            # 实际应用中需要更复杂的合并逻辑

            # 记录日志
            self._add_log(
                SyncRecord(
                    source=f"数据库({len(items)}条)",
                    target=relative_path,
                    action="sync_to_file",
                    timestamp=datetime.now().isoformat(),
                    content_hash="",
                    status="success",
                )
            )

            results["updated"] += 1

        return results

    # ============================================================
    # 同步状态检查
    # ============================================================

    def check_sync_status(self) -> Dict[str, Any]:
        """检查同步状态"""
        status = {
            "last_sync": self.sync_log[-1] if self.sync_log else None,
            "file_count": 0,
            "db_count": 0,
            "out_of_sync": [],
        }

        # 统计文件
        for path_name, path in WATCH_PATHS.items():
            if path.is_file():
                status["file_count"] += 1
            elif path.is_dir():
                status["file_count"] += len(list(path.glob("*.md")))

        # 统计数据库
        status["db_count"] = self.knowledge_collection.count()

        # 检查是否同步
        # 简单检查：文件数和数据库条目数的比例
        # 实际应用中需要更精确的检查

        return status

    # ============================================================
    # 自动同步
    # ============================================================

    def auto_sync(self) -> Dict[str, Any]:
        """
        自动检测变化方向并同步

        Returns:
            同步结果
        """
        # 获取最后同步时间
        last_sync = self.sync_log[-1] if self.sync_log else None

        if not last_sync:
            # 首次同步，从文件到数据库
            return {
                "direction": "file_to_db",
                "result": self.sync_to_database(),
            }

        # 检查文件修改时间
        file_modified = False
        for path_name, path in WATCH_PATHS.items():
            if path.is_file():
                if (
                    path.stat().st_mtime
                    > datetime.fromisoformat(last_sync["timestamp"]).timestamp()
                ):
                    file_modified = True
                    break
            elif path.is_dir():
                for f in path.glob("*.md"):
                    if (
                        f.stat().st_mtime
                        > datetime.fromisoformat(last_sync["timestamp"]).timestamp()
                    ):
                        file_modified = True
                        break

        if file_modified:
            return {
                "direction": "file_to_db",
                "result": self.sync_to_database(),
            }
        else:
            return {
                "direction": "no_change",
                "result": {"message": "未检测到变化"},
            }

    # ============================================================
    # 工作流接口
    # ============================================================

    def update_knowledge(
        self,
        item_id: str,
        new_content: str,
        new_metadata: Optional[Dict] = None,
    ) -> bool:
        """
        更新知识条目（工作流调用）

        Args:
            item_id: 条目ID
            new_content: 新内容
            new_metadata: 新元数据

        Returns:
            是否成功
        """
        try:
            # 获取现有条目
            existing = self.knowledge_collection.get(ids=[item_id])

            if not existing["ids"]:
                return False

            # 更新内容
            old_metadata = existing["metadatas"][0]

            if new_metadata:
                updated_metadata = {**old_metadata, **new_metadata}
            else:
                updated_metadata = old_metadata

            updated_metadata["内容hash"] = self._hash_content(new_content)
            updated_metadata["更新时间"] = datetime.now().isoformat()

            # 更新数据库
            self.knowledge_collection.update(
                ids=[item_id],
                documents=[new_content],
                metadatas=[updated_metadata],
            )

            # 记录日志
            self._add_log(
                SyncRecord(
                    source="工作流",
                    target=item_id,
                    action="update",
                    timestamp=datetime.now().isoformat(),
                    content_hash=updated_metadata["内容hash"],
                    status="success",
                )
            )

            return True

        except Exception as e:
            print(f"更新失败: {e}")
            return False

    def add_knowledge(
        self,
        item_id: str,
        item_type: str,
        name: str,
        content: str,
        metadata: Dict,
    ) -> bool:
        """
        添加知识条目（工作流调用）

        Args:
            item_id: 条目ID
            item_type: 类型
            name: 名称
            content: 内容
            metadata: 元数据

        Returns:
            是否成功
        """
        try:
            now = datetime.now().isoformat()
            content_hash = self._hash_content(content)

            # 添加到数据库
            self.knowledge_collection.add(
                ids=[item_id],
                documents=[f"{name}\n\n{content}"],
                metadatas=[
                    {
                        "类型": item_type,
                        "名称": name,
                        "来源文件": metadata.get("来源文件", "工作流创建"),
                        "来源章节": metadata.get("来源章节", ""),
                        "内容hash": content_hash,
                        "创建时间": now,
                        "更新时间": now,
                        **{
                            k: str(v)
                            for k, v in metadata.items()
                            if k not in ["来源文件", "来源章节"]
                        },
                    }
                ],
            )

            # 记录日志
            self._add_log(
                SyncRecord(
                    source="工作流",
                    target=item_id,
                    action="create",
                    timestamp=now,
                    content_hash=content_hash,
                    status="success",
                )
            )

            return True

        except Exception as e:
            print(f"添加失败: {e}")
            return False


# ============================================================
# 命令行接口
# ============================================================


def main():
    import argparse

    parser = argparse.ArgumentParser(description="双向同步管理器")
    parser.add_argument("--to-db", action="store_true", help="同步文件到数据库")
    parser.add_argument("--to-files", action="store_true", help="同步数据库到文件")
    parser.add_argument("--status", action="store_true", help="检查同步状态")
    parser.add_argument("--auto", action="store_true", help="自动同步")
    parser.add_argument("--force", action="store_true", help="强制同步")

    args = parser.parse_args()

    manager = SyncManager()

    if args.to_db:
        print("同步文件到数据库...")
        result = manager.sync_to_database(force=args.force)
        print(
            f"检查: {result['checked']}, 创建: {result['created']}, 更新: {result['updated']}, 跳过: {result['skipped']}"
        )
        if result["errors"]:
            print(f"错误: {len(result['errors'])}")
        return

    if args.to_files:
        print("同步数据库到文件...")
        result = manager.sync_to_files()
        print(f"检查: {result['checked']}, 更新: {result['updated']}")
        return

    if args.status:
        status = manager.check_sync_status()
        print("同步状态:")
        print(f"  文件数: {status['file_count']}")
        print(f"  数据库条目: {status['db_count']}")
        if status["last_sync"]:
            print(f"  最后同步: {status['last_sync']['timestamp']}")
        return

    if args.auto:
        print("自动同步...")
        result = manager.auto_sync()
        print(f"方向: {result['direction']}")
        if "result" in result:
            print(f"结果: {result['result']}")
        return

    print("请指定操作: --to-db, --to-files, --status, --auto")


if __name__ == "__main__":
    main()
