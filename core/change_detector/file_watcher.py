#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件变更检测器
============

使用文件修改时间(mtime) + 文件大小快速检测变更，
对变更文件使用MD5 hash确认内容变更。

核心功能：
- 检测单个文件变更
- 批量检测目录变更
- 状态持久化到缓存文件
- 增量检测支持

参考：统一提炼引擎重构方案.md 第9.5节
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FileChange:
    """文件变更记录"""

    path: str
    change_type: str  # "created", "modified", "deleted"
    old_mtime: Optional[float] = None
    new_mtime: Optional[float] = None
    old_size: Optional[int] = None
    new_size: Optional[int] = None
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass
class FileState:
    """文件状态记录"""

    path: str
    mtime: float
    size: int
    hash: Optional[str] = None
    last_checked: float = field(default_factory=lambda: datetime.now().timestamp())


class FileWatcher:
    """文件变更检测器"""

    # 状态缓存文件名
    STATE_CACHE_FILENAME = "change_detector_state.json"

    # Hash计算阈值（超过此大小才计算hash）
    HASH_THRESHOLD = 1024  # 1KB

    def __init__(
        self,
        project_root: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        use_hash: bool = True,
    ):
        """
        初始化文件检测器

        Args:
            project_root: 项目根目录
            cache_dir: 缓存目录（用于存储状态文件）
            use_hash: 是否使用hash确认变更
        """
        self.project_root = project_root or self._detect_project_root()
        self.cache_dir = cache_dir or (self.project_root / ".cache")
        self.use_hash = use_hash

        # 状态缓存
        self._state_cache: Dict[str, FileState] = {}
        self._state_file = self.cache_dir / self.STATE_CACHE_FILENAME

        # 加载已保存的状态
        self._load_state()

    def _detect_project_root(self) -> Path:
        """自动检测项目根目录"""
        current = Path(__file__).resolve()
        markers = ["README.md", "config.example.json", "tools", "设定"]

        for parent in current.parents:
            if any((parent / marker).exists() for marker in markers):
                if (parent / "设定").exists():
                    return parent

        return Path.cwd()

    def _load_state(self) -> None:
        """加载已保存的文件状态"""
        if self._state_file.exists():
            try:
                with open(self._state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for path, state_data in data.get("files", {}).items():
                    self._state_cache[path] = FileState(
                        path=path,
                        mtime=state_data.get("mtime", 0),
                        size=state_data.get("size", 0),
                        hash=state_data.get("hash"),
                        last_checked=state_data.get("last_checked", 0),
                    )
            except Exception as e:
                print(f"[FileWatcher] 加载状态失败: {e}")

    def _save_state(self) -> None:
        """保存文件状态到缓存"""
        # 确保缓存目录存在
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "files": {
                path: {
                    "mtime": state.mtime,
                    "size": state.size,
                    "hash": state.hash,
                    "last_checked": state.last_checked,
                }
                for path, state in self._state_cache.items()
            },
            "last_saved": datetime.now().isoformat(),
        }

        try:
            with open(self._state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[FileWatcher] 保存状态失败: {e}")

    def _get_file_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """获取文件信息（mtime, size, hash）"""
        if not file_path.exists():
            return None

        try:
            stat = file_path.stat()
            mtime = stat.st_mtime
            size = stat.st_size

            # 计算hash（仅对较大文件）
            hash_value = None
            if self.use_hash and size >= self.HASH_THRESHOLD:
                hash_value = self._compute_hash(file_path)

            return {
                "mtime": mtime,
                "size": size,
                "hash": hash_value,
            }
        except Exception as e:
            print(f"[FileWatcher] 获取文件信息失败 {file_path}: {e}")
            return None

    def _compute_hash(self, file_path: Path, algorithm: str = "md5") -> str:
        """计算文件hash"""
        hash_func = hashlib.new(algorithm)

        try:
            with open(file_path, "rb") as f:
                # 分块读取，避免内存溢出
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_func.update(chunk)

            return hash_func.hexdigest()
        except Exception as e:
            print(f"[FileWatcher] 计算hash失败 {file_path}: {e}")
            return ""

    def detect_change(self, file_path: Path) -> Optional[FileChange]:
        """
        检测单个文件变更

        Args:
            file_path: 文件路径

        Returns:
            FileChange: 变更记录，无变更返回None
        """
        path_str = str(file_path)

        # 获取当前文件信息
        current_info = self._get_file_info(file_path)

        # 获取之前的状态
        prev_state = self._state_cache.get(path_str)

        # 文件不存在
        if current_info is None:
            if prev_state:
                # 文件被删除
                change = FileChange(
                    path=path_str,
                    change_type="deleted",
                    old_mtime=prev_state.mtime,
                    old_size=prev_state.size,
                    old_hash=prev_state.hash,
                )
                # 删除状态记录
                del self._state_cache[path_str]
                return change
            return None

        # 新文件
        if prev_state is None:
            change = FileChange(
                path=path_str,
                change_type="created",
                new_mtime=current_info["mtime"],
                new_size=current_info["size"],
                new_hash=current_info["hash"],
            )
            # 更新状态缓存
            self._state_cache[path_str] = FileState(
                path=path_str,
                mtime=current_info["mtime"],
                size=current_info["size"],
                hash=current_info["hash"],
            )
            return change

        # 检查变更
        mtime_changed = current_info["mtime"] != prev_state.mtime
        size_changed = current_info["size"] != prev_state.size

        # 快速检测：mtime或size变更
        if mtime_changed or size_changed:
            # 确认变更：使用hash
            hash_changed = False
            if self.use_hash and current_info["hash"] and prev_state.hash:
                hash_changed = current_info["hash"] != prev_state.hash
            elif not prev_state.hash and current_info["hash"]:
                # 之前没有hash，现在有了（新计算）
                hash_changed = True

            if mtime_changed or size_changed or hash_changed or not self.use_hash:
                change = FileChange(
                    path=path_str,
                    change_type="modified",
                    old_mtime=prev_state.mtime,
                    new_mtime=current_info["mtime"],
                    old_size=prev_state.size,
                    new_size=current_info["size"],
                    old_hash=prev_state.hash,
                    new_hash=current_info["hash"],
                )
                # 更新状态缓存
                self._state_cache[path_str] = FileState(
                    path=path_str,
                    mtime=current_info["mtime"],
                    size=current_info["size"],
                    hash=current_info["hash"],
                )
                return change

        # 无变更，更新检查时间
        self._state_cache[path_str].last_checked = datetime.now().timestamp()
        return None

    def detect_changes(
        self,
        pattern: str,
        base_dir: Optional[Path] = None,
    ) -> List[FileChange]:
        """
        批量检测文件变更

        Args:
            pattern: glob模式，如 "*.md", "**/*.md"
            base_dir: 基础目录（默认项目根目录）

        Returns:
            变更列表
        """
        base_dir = base_dir or self.project_root
        changes = []

        # 获取匹配的文件列表
        if "**" in pattern:
            # 递归匹配
            files = list(base_dir.glob(pattern))
        else:
            # 单层匹配
            files = list(base_dir.glob(pattern))

        # 过滤非文件
        files = [f for f in files if f.is_file()]

        for file_path in files:
            change = self.detect_change(file_path)
            if change:
                changes.append(change)

        return changes

    def detect_directory_changes(
        self,
        directory: Path,
        extensions: list[str] | None = None,
    ) -> list[FileChange]:
        """
        检测目录下所有文件的变更

        Args:
            directory: 目录路径
            extensions: 文件扩展名过滤，如 ["md", "json"]

        Returns:
            变更列表
        """
        changes = []

        if not directory.exists():
            return changes

        # 遍历目录
        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue

            # 扩展名过滤
            if extensions:
                ext = file_path.suffix.lstrip(".")
                if ext not in extensions:
                    continue

            change = self.detect_change(file_path)
            if change:
                changes.append(change)

        return changes

    def get_file_state(self, file_path: Path) -> Optional[FileState]:
        """获取文件的当前状态"""
        return self._state_cache.get(str(file_path))

    def clear_state(self) -> None:
        """清除所有状态记录"""
        self._state_cache.clear()
        if self._state_file.exists():
            self._state_file.unlink()

    def reset_file_state(self, file_path: Path) -> None:
        """重置单个文件的状态"""
        path_str = str(file_path)
        if path_str in self._state_cache:
            del self._state_cache[path_str]

    def sync_state(self) -> None:
        """同步状态到缓存文件"""
        self._save_state()

    def get_all_states(self) -> Dict[str, FileState]:
        """获取所有文件状态"""
        return self._state_cache.copy()


# 测试代码
if __name__ == "__main__":
    import tempfile

    # 创建临时目录测试
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # 创建测试文件
        test_file1 = test_dir / "test1.md"
        test_file1.write_text("Hello World")

        test_file2 = test_dir / "test2.md"
        test_file2.write_text("Another File")

        # 初始化检测器
        watcher = FileWatcher(project_root=test_dir)

        print("=" * 60)
        print("文件变更检测器测试")
        print("=" * 60)

        # 第一次检测（应该检测到新文件）
        changes = watcher.detect_directory_changes(test_dir, extensions=["md"])
        print(f"\n第一次检测: 发现 {len(changes)} 个变更")
        for change in changes:
            print(f"  - {change.path}: {change.change_type}")

        # 保存状态
        watcher.sync_state()

        # 第二次检测（无变更）
        changes = watcher.detect_directory_changes(test_dir, extensions=["md"])
        print(f"\n第二次检测: 发现 {len(changes)} 个变更")

        # 修改文件
        test_file1.write_text("Modified Content")

        # 第三次检测（应该检测到修改）
        changes = watcher.detect_directory_changes(test_dir, extensions=["md"])
        print(f"\n第三次检测（修改后）: 发现 {len(changes)} 个变更")
        for change in changes:
            print(f"  - {change.path}: {change.change_type}")

        # 删除文件
        test_file2.unlink()

        # 第四次检测（应该检测到删除）
        changes = watcher.detect_directory_changes(test_dir, extensions=["md"])
        print(f"\n第四次检测（删除后）: 发现 {len(changes)} 个变更")
        for change in changes:
            print(f"  - {change.path}: {change.change_type}")
