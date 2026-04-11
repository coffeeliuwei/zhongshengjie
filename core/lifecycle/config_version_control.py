"""
配置版本控制 - ConfigVersionControl

管理配置文件快照，支持回滚和对比。

功能：
- create_snapshot(): 创建配置快照
- restore_snapshot(): 恢复快照
- list_snapshots(): 列出快照
- diff_snapshots(): 对比快照
- auto_snapshot(): 自动快照（配置变更时）

存储位置：.cache/config_snapshots/
"""

import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field

# 尝试导入配置管理器
try:
    from core.config_loader import get_project_root

    _project_root = Path(get_project_root())
except ImportError:
    _project_root = Path(__file__).parent.parent.parent

PROJECT_ROOT = _project_root


@dataclass
class ConfigSnapshot:
    """配置快照"""

    id: str  # 快照ID
    name: str  # 快照名称
    timestamp: str  # 创建时间
    description: Optional[str] = None  # 描述
    tags: List[str] = field(default_factory=list)  # 标签
    config_files: List[str] = field(default_factory=list)  # 包含的配置文件
    checksum: Optional[str] = None  # 整体校验和
    is_auto: bool = False  # 是否自动创建


@dataclass
class SnapshotDiff:
    """快照差异"""

    file: str  # 文件名
    old_value: Optional[Any] = None  # 旧值
    new_value: Optional[Any] = None  # 新值
    diff_type: str = "modified"  # modified/added/deleted
    line_count_change: int = 0  # 行数变化


# 配置文件路径定义
CONFIG_FILES = {
    "main_config": "config.json",
    "world_config": "config/worlds/众生界.json",
    "scene_types": "config/dimensions/scene_types.json",
    "power_types": "config/dimensions/power_types.json",
    "faction_types": "config/dimensions/faction_types.json",
    "technique_types": "config/dimensions/technique_types.json",
    "scene_writer_mapping": "config/scene_writer_mapping.json",
}


class ConfigVersionControl:
    """配置版本控制"""

    STORAGE_DIR = ".cache/config_snapshots"
    INDEX_FILE = ".cache/config_snapshots/index.json"

    def __init__(self, project_root: Optional[Path] = None):
        """
        初始化配置版本控制

        Args:
            project_root: 项目根目录，默认自动检测
        """
        self.project_root = Path(project_root) if project_root else PROJECT_ROOT
        self.storage_dir = self.project_root / self.STORAGE_DIR
        self.index_path = self.project_root / self.INDEX_FILE
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """确保存储目录和索引文件存在"""
        # 创建存储目录
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 创建索引文件
        if not self.index_path.exists():
            self._save_index({"snapshots": [], "current_checksums": {}})

    def _load_index(self) -> Dict[str, Any]:
        """加载快照索引"""
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"snapshots": [], "current_checksums": {}}

    def _save_index(self, index: Dict[str, Any]) -> None:
        """保存快照索引"""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def _calculate_checksum(self, file_path: Path) -> str:
        """计算文件校验和"""
        if not file_path.exists():
            return ""

        content = file_path.read_text(encoding="utf-8")
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _collect_config_files(self) -> Dict[str, Tuple[Path, str]]:
        """
        收集所有配置文件

        Returns:
            配置文件字典 {name: (path, checksum)}
        """
        configs = {}

        for name, relative_path in CONFIG_FILES.items():
            file_path = self.project_root / relative_path
            if file_path.exists():
                checksum = self._calculate_checksum(file_path)
                configs[name] = (file_path, checksum)

        return configs

    def create_snapshot(
        self,
        name: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_auto: bool = False,
    ) -> str:
        """
        创建配置快照

        Args:
            name: 快照名称
            description: 描述
            tags: 标签列表
            is_auto: 是否自动创建

        Returns:
            快照ID
        """
        # 生成快照ID
        timestamp = datetime.now()
        snapshot_id = hashlib.md5(
            f"{name}_{timestamp.isoformat()}".encode()
        ).hexdigest()[:12]

        # 收集配置文件
        configs = self._collect_config_files()

        # 创建快照目录
        snapshot_dir = self.storage_dir / snapshot_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        # 复制配置文件
        config_files = []
        checksums = {}

        for config_name, (file_path, checksum) in configs.items():
            # 复制文件
            target_path = snapshot_dir / f"{config_name}.json"
            shutil.copy2(file_path, target_path)
            config_files.append(config_name)
            checksums[config_name] = checksum

        # 计算整体校验和
        overall_checksum = hashlib.sha256(
            json.dumps(checksums, sort_keys=True).encode()
        ).hexdigest()[:16]

        # 创建快照记录
        snapshot = ConfigSnapshot(
            id=snapshot_id,
            name=name,
            timestamp=timestamp.isoformat(),
            description=description,
            tags=tags or [],
            config_files=config_files,
            checksum=overall_checksum,
            is_auto=is_auto,
        )

        # 更新索引
        index = self._load_index()
        index["snapshots"].append(asdict(snapshot))
        index["current_checksums"] = checksums
        self._save_index(index)

        return snapshot_id

    def restore_snapshot(
        self,
        snapshot_id: str,
        backup_current: bool = True,
    ) -> Dict[str, Any]:
        """
        恢复配置快照

        Args:
            snapshot_id: 快照ID
            backup_current: 是否备份当前配置

        Returns:
            恢复结果 {
                "success": bool,
                "restored_files": List[str],
                "backup_id": Optional[str]
            }
        """
        # 查找快照
        index = self._load_index()
        snapshot_data = None
        for snap in index["snapshots"]:
            if snap["id"] == snapshot_id:
                snapshot_data = snap
                break

        if not snapshot_data:
            return {
                "success": False,
                "error": f"Snapshot {snapshot_id} not found",
                "restored_files": [],
            }

        # 备份当前配置
        backup_id = None
        if backup_current:
            backup_id = self.create_snapshot(
                name=f"pre_restore_{snapshot_id}",
                description=f"Automatic backup before restoring {snapshot_id}",
                is_auto=True,
            )

        # 恢复配置文件
        snapshot_dir = self.storage_dir / snapshot_id
        restored_files = []

        for config_name in snapshot_data["config_files"]:
            source_path = snapshot_dir / f"{config_name}.json"

            if source_path.exists():
                target_relative = CONFIG_FILES.get(config_name)
                if target_relative:
                    target_path = self.project_root / target_relative

                    # 确保目标目录存在
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    # 复制文件
                    shutil.copy2(source_path, target_path)
                    restored_files.append(config_name)

        return {
            "success": True,
            "restored_files": restored_files,
            "backup_id": backup_id,
        }

    def list_snapshots(
        self,
        tags: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[ConfigSnapshot]:
        """
        列出配置快照

        Args:
            tags: 过滤标签
            limit: 最大数量

        Returns:
            快照列表
        """
        index = self._load_index()
        snapshots = []

        for snap_data in index["snapshots"]:
            # 标签过滤
            if tags:
                if not any(tag in snap_data.get("tags", []) for tag in tags):
                    continue

            snapshot = ConfigSnapshot(
                id=snap_data["id"],
                name=snap_data["name"],
                timestamp=snap_data["timestamp"],
                description=snap_data.get("description"),
                tags=snap_data.get("tags", []),
                config_files=snap_data.get("config_files", []),
                checksum=snap_data.get("checksum"),
                is_auto=snap_data.get("is_auto", False),
            )
            snapshots.append(snapshot)

        # 按时间倒序排序
        snapshots.sort(key=lambda s: s.timestamp, reverse=True)

        return snapshots[:limit]

    def diff_snapshots(
        self,
        snapshot_id1: str,
        snapshot_id2: str,
    ) -> List[SnapshotDiff]:
        """
        对比两个快照

        Args:
            snapshot_id1: 第一个快照ID（旧）
            snapshot_id2: 第二个快照ID（新）

        Returns:
            差异列表
        """
        index = self._load_index()

        # 查找快照
        snap1 = None
        snap2 = None
        for snap in index["snapshots"]:
            if snap["id"] == snapshot_id1:
                snap1 = snap
            elif snap["id"] == snapshot_id2:
                snap2 = snap

        if not snap1 or not snap2:
            return []

        # 加载配置文件
        dir1 = self.storage_dir / snapshot_id1
        dir2 = self.storage_dir / snapshot_id2

        diffs = []

        for config_name in set(snap1["config_files"] + snap2["config_files"]):
            file1_path = dir1 / f"{config_name}.json"
            file2_path = dir2 / f"{config_name}.json"

            # 文件状态判断
            if file1_path.exists() and file2_path.exists():
                # 都存在，对比内容
                content1 = json.loads(file1_path.read_text(encoding="utf-8"))
                content2 = json.loads(file2_path.read_text(encoding="utf-8"))

                # 递归对比
                content_diffs = self._compare_json(content1, content2, config_name)
                diffs.extend(content_diffs)

            elif file1_path.exists() and not file2_path.exists():
                # 旧文件存在，新文件不存在 - deleted
                diffs.append(
                    SnapshotDiff(
                        file=config_name,
                        old_value=json.loads(file1_path.read_text(encoding="utf-8")),
                        new_value=None,
                        diff_type="deleted",
                        line_count_change=-self._estimate_lines(file1_path),
                    )
                )

            elif not file1_path.exists() and file2_path.exists():
                # 旧文件不存在，新文件存在 - added
                diffs.append(
                    SnapshotDiff(
                        file=config_name,
                        old_value=None,
                        new_value=json.loads(file2_path.read_text(encoding="utf-8")),
                        diff_type="added",
                        line_count_change=self._estimate_lines(file2_path),
                    )
                )

        return diffs

    def _compare_json(
        self,
        old: Dict[str, Any],
        new: Dict[str, Any],
        prefix: str,
    ) -> List[SnapshotDiff]:
        """递归对比两个JSON对象"""
        diffs = []

        # 对比所有key
        all_keys = set(old.keys()) | set(new.keys())

        for key in all_keys:
            path = f"{prefix}.{key}"

            if key not in old:
                # 新增key
                diffs.append(
                    SnapshotDiff(
                        file=prefix,
                        old_value=None,
                        new_value=new[key],
                        diff_type="added",
                    )
                )

            elif key not in new:
                # 删除key
                diffs.append(
                    SnapshotDiff(
                        file=prefix,
                        old_value=old[key],
                        new_value=None,
                        diff_type="deleted",
                    )
                )

            elif old[key] != new[key]:
                # 修改key
                if isinstance(old[key], dict) and isinstance(new[key], dict):
                    # 递归对比
                    diffs.extend(self._compare_json(old[key], new[key], path))
                else:
                    diffs.append(
                        SnapshotDiff(
                            file=path,
                            old_value=old[key],
                            new_value=new[key],
                            diff_type="modified",
                        )
                    )

        return diffs

    def _estimate_lines(self, file_path: Path) -> int:
        """估算文件行数"""
        content = file_path.read_text(encoding="utf-8")
        return len(content.split("\n"))

    def auto_snapshot(self) -> Optional[str]:
        """
        自动快照（检测配置变更时）

        Returns:
            快照ID（如果配置有变更），否则None
        """
        # 收集当前配置checksum
        configs = self._collect_config_files()
        current_checksums = {name: checksum for name, (_, checksum) in configs.items()}

        # 加载上次checksum
        index = self._load_index()
        last_checksums = index.get("current_checksums", {})

        # 检测变更
        has_change = False
        for name, checksum in current_checksums.items():
            if name not in last_checksums or last_checksums[name] != checksum:
                has_change = True
                break

        if not has_change:
            return None

        # 创建自动快照
        snapshot_id = self.create_snapshot(
            name=f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            description="Automatic snapshot on config change",
            is_auto=True,
        )

        return snapshot_id

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """
        删除快照

        Args:
            snapshot_id: 快照ID

        Returns:
            是否成功
        """
        index = self._load_index()

        # 查找并删除
        for i, snap in enumerate(index["snapshots"]):
            if snap["id"] == snapshot_id:
                # 删除记录
                index["snapshots"].pop(i)
                self._save_index(index)

                # 删除文件目录
                snapshot_dir = self.storage_dir / snapshot_id
                if snapshot_dir.exists():
                    shutil.rmtree(snapshot_dir)

                return True

        return False

    def get_snapshot(self, snapshot_id: str) -> Optional[ConfigSnapshot]:
        """
        获取快照详情

        Args:
            snapshot_id: 快照ID

        Returns:
            快照对象
        """
        index = self._load_index()

        for snap_data in index["snapshots"]:
            if snap_data["id"] == snapshot_id:
                return ConfigSnapshot(
                    id=snap_data["id"],
                    name=snap_data["name"],
                    timestamp=snap_data["timestamp"],
                    description=snap_data.get("description"),
                    tags=snap_data.get("tags", []),
                    config_files=snap_data.get("config_files", []),
                    checksum=snap_data.get("checksum"),
                    is_auto=snap_data.get("is_auto", False),
                )

        return None

    def cleanup_old_snapshots(
        self, keep_days: int = 30, keep_manual: bool = True
    ) -> int:
        """
        清理旧快照

        Args:
            keep_days: 保留天数
            keep_manual: 是否保留手动快照

        Returns:
            清理数量
        """
        index = self._load_index()
        cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 3600)

        original_count = len(index["snapshots"])
        to_delete = []

        for snap in index["snapshots"]:
            # 检查时间
            snap_time = datetime.fromisoformat(snap["timestamp"]).timestamp()

            # 检查是否手动
            is_manual = not snap.get("is_auto", False)

            # 判断是否删除
            if snap_time < cutoff_time and (not keep_manual or not is_manual):
                to_delete.append(snap["id"])

        # 删除快照
        for snapshot_id in to_delete:
            self.delete_snapshot(snapshot_id)

        return len(to_delete)


# 便捷函数
def get_config_version_control(
    project_root: Optional[Path] = None,
) -> ConfigVersionControl:
    """获取配置版本控制实例"""
    return ConfigVersionControl(project_root)
