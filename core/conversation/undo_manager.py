#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
撤销管理器
==========

管理操作历史和撤销功能。

核心功能：
- 记录操作历史
- 撤销最近操作
- 查看操作历史
- 批量撤销

参考：统一提炼引擎重构方案.md 第10.4.2节
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class OperationType(Enum):
    """操作类型"""

    FILE_UPDATE = "file_update"
    VECTORSTORE_SYNC = "vectorstore_sync"
    SETTING_ADD = "setting_add"
    SETTING_MODIFY = "setting_modify"
    SETTING_DELETE = "setting_delete"
    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETE = "workflow_complete"


@dataclass
class OperationRecord:
    """操作记录"""

    operation_id: str
    operation_type: OperationType
    timestamp: str
    description: str
    file_path: Optional[str] = None
    backup_path: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    can_undo: bool = True
    undone: bool = False


class UndoManager:
    """撤销管理器"""

    # 最大历史记录数
    MAX_HISTORY = 100

    # 可撤销的操作类型
    UNDOABLE_OPERATIONS = [
        OperationType.FILE_UPDATE,
        OperationType.SETTING_ADD,
        OperationType.SETTING_MODIFY,
        OperationType.SETTING_DELETE,
    ]

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化撤销管理器

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = (
            Path(project_root) if project_root else self._detect_project_root()
        )
        self.history_dir = self.project_root / "logs" / "operation_history"
        self.backup_dir = self.project_root / "logs" / "backups"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self._operation_history: List[OperationRecord] = []
        self._load_history()

    def _detect_project_root(self) -> Path:
        """自动检测项目根目录"""
        current = Path(__file__).resolve()
        markers = ["README.md", "config.example.json", "tools", "设定"]

        for parent in current.parents:
            if any((parent / marker).exists() for marker in markers):
                return parent

        return Path.cwd()

    def _load_history(self) -> None:
        """加载历史记录"""
        history_file = self.history_dir / "operations.json"

        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for item in data.get("operations", []):
                    self._operation_history.append(
                        OperationRecord(
                            operation_id=item.get("operation_id", ""),
                            operation_type=OperationType(
                                item.get("operation_type", "file_update")
                            ),
                            timestamp=item.get("timestamp", ""),
                            description=item.get("description", ""),
                            file_path=item.get("file_path"),
                            backup_path=item.get("backup_path"),
                            data=item.get("data"),
                            can_undo=item.get("can_undo", True),
                            undone=item.get("undone", False),
                        )
                    )

            except Exception as e:
                print(f"Error loading history: {e}")

    def _save_history(self) -> None:
        """保存历史记录"""
        history_file = self.history_dir / "operations.json"

        try:
            data = {
                "operations": [
                    {
                        "operation_id": op.operation_id,
                        "operation_type": op.operation_type.value,
                        "timestamp": op.timestamp,
                        "description": op.description,
                        "file_path": op.file_path,
                        "backup_path": op.backup_path,
                        "data": op.data,
                        "can_undo": op.can_undo,
                        "undone": op.undone,
                    }
                    for op in self._operation_history[-self.MAX_HISTORY :]
                ],
                "last_updated": datetime.now().isoformat(),
            }

            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"Error saving history: {e}")

    def record_operation(
        self,
        operation_type: OperationType,
        description: str,
        file_path: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        create_backup: bool = True,
    ) -> OperationRecord:
        """
        记录操作

        Args:
            operation_type: 操作类型
            description: 操作描述
            file_path: 文件路径（可选）
            data: 操作数据（可选）
            create_backup: 是否创建备份

        Returns:
            OperationRecord
        """
        # 生成操作ID
        operation_id = f"op_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # 创建备份
        backup_path = None
        if file_path and create_backup:
            backup_path = self._create_backup(file_path, operation_id)

        # 判断是否可撤销
        can_undo = (
            operation_type in self.UNDOABLE_OPERATIONS and backup_path is not None
        )

        # 创建记录
        record = OperationRecord(
            operation_id=operation_id,
            operation_type=operation_type,
            timestamp=datetime.now().isoformat(),
            description=description,
            file_path=file_path,
            backup_path=backup_path,
            data=data,
            can_undo=can_undo,
            undone=False,
        )

        # 添加到历史
        self._operation_history.append(record)
        self._save_history()

        return record

    def _create_backup(self, file_path: str, operation_id: str) -> Optional[str]:
        """
        创建文件备份

        Args:
            file_path: 文件路径
            operation_id: 操作ID

        Returns:
            备份路径
        """
        try:
            source_path = self.project_root / file_path

            if not source_path.exists():
                return None

            backup_name = f"{operation_id}_{Path(file_path).name}"
            backup_path = self.backup_dir / backup_name

            shutil.copy2(source_path, backup_path)

            return str(backup_path)

        except Exception as e:
            print(f"Error creating backup: {e}")
            return None

    def undo_last(self) -> Optional[OperationRecord]:
        """
        撤销最近一次操作

        Returns:
            撤销的操作记录，或None
        """
        # 查找最近的可撤销操作
        for record in reversed(self._operation_history):
            if record.can_undo and not record.undone:
                return self.undo_operation(record.operation_id)

        return None

    def undo_operation(self, operation_id: str) -> Optional[OperationRecord]:
        """
        撤销指定操作

        Args:
            operation_id: 操作ID

        Returns:
            撤销的操作记录，或None
        """
        # 查找操作
        record = None
        for op in self._operation_history:
            if op.operation_id == operation_id:
                record = op
                break

        if not record:
            return None

        # 检查是否可撤销
        if not record.can_undo or record.undone:
            return None

        # 执行撤销
        success = False

        if (
            record.operation_type == OperationType.FILE_UPDATE
            and record.file_path
            and record.backup_path
        ):
            success = self._restore_backup(record.file_path, record.backup_path)

        elif (
            record.operation_type
            in [OperationType.SETTING_ADD, OperationType.SETTING_MODIFY]
            and record.file_path
            and record.backup_path
        ):
            success = self._restore_backup(record.file_path, record.backup_path)

        if success:
            record.undone = True
            self._save_history()
            return record

        return None

    def _restore_backup(self, file_path: str, backup_path: str) -> bool:
        """
        从备份恢复文件

        Args:
            file_path: 目标文件路径
            backup_path: 备份文件路径

        Returns:
            是否成功恢复
        """
        try:
            target_path = self.project_root / file_path
            backup = Path(backup_path)

            if not backup.exists():
                print(f"Backup not found: {backup_path}")
                return False

            # 恢复文件
            shutil.copy2(backup, target_path)

            return True

        except Exception as e:
            print(f"Error restoring backup: {e}")
            return False

    def get_history(self, limit: int = 10) -> List[OperationRecord]:
        """
        获取操作历史

        Args:
            limit: 返回数量

        Returns:
            操作记录列表
        """
        return self._operation_history[-limit:]

    def get_undoable_operations(self) -> List[OperationRecord]:
        """
        获取可撤销的操作

        Returns:
            可撤销操作列表
        """
        return [op for op in self._operation_history if op.can_undo and not op.undone]

    def generate_undo_prompt(self) -> str:
        """
        生成撤销提示

        Returns:
            提示文本
        """
        undoable = self.get_undoable_operations()

        if not undoable:
            return "没有可撤销的操作。"

        prompt = "以下操作可以撤销：\n"

        for i, op in enumerate(undoable[-5:], 1):  # 只显示最近5个
            icon = "📝" if op.operation_type == OperationType.FILE_UPDATE else "⚙️"
            status = "已撤销" if op.undone else "可撤销"
            prompt += f"{i}. {icon} {op.description} ({status})\n"

        prompt += "\n回复「撤销」或「撤销第X个」来执行撤销。"

        return prompt

    def clear_history(self) -> None:
        """清空历史记录"""
        self._operation_history = []
        self._save_history()

    def clear_old_backups(self, days: int = 7) -> int:
        """
        清理旧备份文件

        Args:
            days: 保留天数

        Returns:
            清理的文件数量
        """
        cutoff = datetime.now() - timedelta(days=days)
        cleared = 0

        for backup_file in self.backup_dir.glob("*"):
            try:
                # 从文件名提取时间戳
                timestamp_str = backup_file.name.split("_")[1:3]
                timestamp_str = "_".join(timestamp_str)

                try:
                    file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    if file_time < cutoff:
                        backup_file.unlink()
                        cleared += 1
                except ValueError:
                    # 无法解析时间戳，跳过
                    pass

            except Exception as e:
                print(f"Error clearing backup {backup_file}: {e}")

        return cleared


# 需要导入 timedelta
from datetime import timedelta


# 测试代码
if __name__ == "__main__":
    manager = UndoManager()

    print("=" * 60)
    print("撤销管理器测试")
    print("=" * 60)

    # 记录测试操作
    record1 = manager.record_operation(
        operation_type=OperationType.SETTING_ADD,
        description="添加角色「血牙」的新能力「血脉守护」",
        file_path="设定/人物谱.md",
        data={"character": "血牙", "ability": "血脉守护"},
    )

    print(f"\n记录操作: {record1.operation_id}")
    print(f"类型: {record1.operation_type.value}")
    print(f"描述: {record1.description}")
    print(f"可撤销: {record1.can_undo}")

    # 获取历史
    history = manager.get_history(5)
    print(f"\n操作历史: {len(history)} 条")

    # 生成撤销提示
    print("\n" + manager.generate_undo_prompt())
