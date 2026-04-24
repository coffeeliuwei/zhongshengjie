#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一变更检测器
=============

检测大纲、设定、技法、追踪文件的变更，并触发同步到对应存储。

核心功能：
- 监控多数据源变更
- 增量检测（基于hash/modtime）
- 自动触发同步
- 生成变更报告

参考：统一提炼引擎重构方案.md 第9.5节
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json

from .file_watcher import FileWatcher, FileChange
from .sync_manager_adapter import SyncManagerAdapter, SyncResult


@dataclass
class ChangeReport:
    """变更报告"""

    timestamp: datetime = field(default_factory=datetime.now)
    sources: Dict[str, List[FileChange]] = field(default_factory=dict)
    sync_results: Dict[str, SyncResult] = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "sources": {
                source: [
                    {
                        "path": change.path,
                        "change_type": change.change_type,
                        "old_mtime": change.old_mtime,
                        "new_mtime": change.new_mtime,
                    }
                    for change in changes
                ]
                for source, changes in self.sources.items()
            },
            "sync_results": {
                target: {
                    "status": result.status,
                    "count": result.count,
                    "message": result.message,
                }
                for target, result in self.sync_results.items()
            },
            "summary": self.summary,
        }

    def to_json(self) -> str:
        """转换为JSON"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class ChangeDetector:
    """统一变更检测器"""

    # 默认监控配置
    DEFAULT_WATCH_LIST = {
        "outline": "总大纲.md",
        "chapter_outlines": "章节大纲/*.md",  # 新增：I18/P3-#25
        "settings": "设定/*.md",
        "techniques": "创作技法/**/*.md",
        "tracking": "设定/hook_ledger.md",
    }

    # 变更到同步的映射
    SYNC_MAPPING = {
        "outline": "worldview",
        "chapter_outlines": "chapter_outlines",  # 新增：I18/P3-#25
        "settings": "graph",
        "techniques": "techniques",
        "tracking": None,  # tracking文件不需要同步到向量库
    }

    def __init__(
        self,
        project_root: Optional[Path] = None,
        watch_list: Optional[Dict[str, str]] = None,
        auto_sync: bool = True,
        use_hash: bool = True,
    ):
        """
        初始化变更检测器

        Args:
            project_root: 项目根目录
            watch_list: 监控配置（默认使用 DEFAULT_WATCH_LIST）
            auto_sync: 检测到变更后是否自动同步
            use_hash: 是否使用hash确认变更
        """
        self.project_root = project_root or self._detect_project_root()
        self.watch_list = watch_list or self.DEFAULT_WATCH_LIST.copy()
        self.auto_sync = auto_sync

        # 初始化组件
        self.file_watcher = FileWatcher(
            project_root=self.project_root,
            use_hash=use_hash,
        )
        self.sync_adapter = SyncManagerAdapter(
            project_root=self.project_root,
        )

        # 变更历史
        self._change_history: List[ChangeReport] = []

    def _detect_project_root(self) -> Path:
        """自动检测项目根目录"""
        current = Path(__file__).resolve()
        markers = ["README.md", "config.example.json", "tools", "设定"]

        for parent in current.parents:
            if any((parent / marker).exists() for marker in markers):
                if (parent / "设定").exists():
                    return parent

        return Path.cwd()

    def _detect_file_changes(self, pattern: str) -> List[FileChange]:
        """
        检测单个数据源的文件变更

        Args:
            pattern: glob模式

        Returns:
            变更列表
        """
        # 处理不同的pattern格式
        if pattern.startswith("设定/") or pattern.startswith("创作技法/"):
            # 相对于项目根目录
            base_dir = self.project_root
        else:
            base_dir = self.project_root

        # 调用 FileWatcher 检测变更
        changes = self.file_watcher.detect_changes(pattern, base_dir)

        return changes

    def scan_changes(self) -> Dict[str, List[FileChange]]:
        """
        扫描所有数据源变更

        Returns:
            Dict[str, List[FileChange]]: 各数据源的变更列表
        """
        changes = {}

        for source, pattern in self.watch_list.items():
            source_changes = self._detect_file_changes(pattern)
            if source_changes:
                changes[source] = source_changes

        return changes

    def sync_changes(
        self,
        changes: Dict[str, List[FileChange]],
        rebuild: bool = False,
    ) -> Dict[str, SyncResult]:
        """
        同步变更到对应的存储

        Args:
            changes: 变更字典
            rebuild: 是否重建

        Returns:
            Dict[str, SyncResult]: 同步结果
        """
        sync_results = {}

        # 大纲变更 → 世界观配置 + novel_plot_v1 (M2-修复)
        if changes.get("outline"):
            sync_results["worldview"] = self._sync_outline_to_worldview()
            sync_results["novel_plot_v1"] = (
                self.sync_adapter.sync_total_outline_to_qdrant()
            )

        # 章节大纲变更 → Qdrant chapter_outlines (I18/P3-#25)
        if changes.get("chapter_outlines"):
            outline_results = []
            for change in changes["chapter_outlines"]:
                file_path = Path(change.path)
                if change.change_type != "deleted" and file_path.exists():
                    result = self.sync_adapter.sync_chapter_outline_file(file_path)
                    outline_results.append(result)

            # 聚合结果
            success_count = sum(
                r.count for r in outline_results if r.status == "success"
            )
            failed = any(r.status == "failed" for r in outline_results)
            sync_results["chapter_outlines"] = SyncResult(
                target="chapter_outlines",
                status="failed" if failed else "success",
                count=success_count,
                message=f"已同步 {success_count}/{len(outline_results)} 个章节大纲",
            )

        # 设定变更 → 知识图谱
        if changes.get("settings"):
            sync_results["graph"] = self._sync_settings_to_graph(rebuild=rebuild)

        # 技法变更 → 向量库
        if changes.get("techniques"):
            sync_results["techniques"] = self._sync_techniques_to_qdrant(
                rebuild=rebuild
            )

        return sync_results

    def _sync_outline_to_worldview(self) -> SyncResult:
        """大纲 → 世界观配置"""
        outline_file = self.project_root / self.watch_list["outline"]
        return self.sync_adapter.sync_outline_to_worldview(outline_file)

    def _sync_settings_to_graph(self, rebuild: bool = False) -> SyncResult:
        """设定 → 知识图谱"""
        settings_dir = self.project_root / "设定"
        return self.sync_adapter.sync_settings_to_graph(
            settings_dir=settings_dir,
            rebuild=rebuild,
        )

    def _sync_techniques_to_qdrant(self, rebuild: bool = False) -> SyncResult:
        """技法 → 向量库"""
        techniques_dir = self.project_root / "创作技法"
        return self.sync_adapter.sync_techniques_to_qdrant(
            techniques_dir=techniques_dir,
            rebuild=rebuild,
        )

    def run(
        self,
        sync: bool = True,
        rebuild: bool = False,
    ) -> ChangeReport:
        """
        执行变更检测和同步

        Args:
            sync: 是否同步变更
            rebuild: 是否重建

        Returns:
            ChangeReport: 变更报告
        """
        # 检测变更
        changes = self.scan_changes()

        # 同步变更
        sync_results = {}
        if sync and changes:
            sync_results = self.sync_changes(changes, rebuild=rebuild)

        # 生成报告
        report = ChangeReport(
            sources=changes,
            sync_results=sync_results,
            summary=self._generate_summary(changes, sync_results),
        )

        # 保存到历史
        self._change_history.append(report)

        # 保存文件状态
        self.file_watcher.sync_state()

        return report

    def _generate_summary(
        self,
        changes: Dict[str, List[FileChange]],
        sync_results: Dict[str, SyncResult],
    ) -> str:
        """生成变更摘要"""
        total_changes = sum(len(c) for c in changes.values())

        if total_changes == 0:
            return "无变更"

        parts = []

        # 变更统计
        change_parts = []
        for source, source_changes in changes.items():
            if source_changes:
                change_parts.append(f"{source}: {len(source_changes)}个文件")

        if change_parts:
            parts.append("变更: " + ", ".join(change_parts))

        # 同步统计
        sync_parts = []
        for target, result in sync_results.items():
            if result.status == "success":
                sync_parts.append(f"{target}: 同步{result.count}条")
            elif result.status == "failed":
                sync_parts.append(f"{target}: 同步失败")

        if sync_parts:
            parts.append("同步: " + ", ".join(sync_parts))

        return "; ".join(parts)

    def get_change_history(
        self,
        limit: int = 10,
    ) -> List[ChangeReport]:
        """
        获取变更历史

        Args:
            limit: 最大数量

        Returns:
            变更报告列表
        """
        return self._change_history[-limit:]

    def clear_history(self) -> None:
        """清除变更历史"""
        self._change_history.clear()

    def reset_state(self) -> None:
        """重置文件状态"""
        self.file_watcher.clear_state()

    def add_watch_target(
        self,
        source: str,
        pattern: str,
    ) -> None:
        """
        添加监控目标

        Args:
            source: 数据源名称
            pattern: glob模式
        """
        self.watch_list[source] = pattern

    def remove_watch_target(self, source: str) -> None:
        """移除监控目标"""
        if source in self.watch_list:
            del self.watch_list[source]

    def get_watch_list(self) -> Dict[str, str]:
        """获取监控配置"""
        return self.watch_list.copy()

    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        return self.sync_adapter.get_sync_status()

    def force_sync_all(self, rebuild: bool = False) -> Dict[str, SyncResult]:
        """
        强制同步所有数据源

        Args:
            rebuild: 是否重建

        Returns:
            同步结果
        """
        return self.sync_adapter.sync_all(rebuild=rebuild)


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("统一变更检测器测试")
    print("=" * 60)

    detector = ChangeDetector()

    # 获取监控配置
    print("\n监控配置:")
    watch_list = detector.get_watch_list()
    for source, pattern in watch_list.items():
        print(f"  - {source}: {pattern}")

    # 获取同步状态
    print("\n同步状态:")
    status = detector.get_sync_status()
    for collection, info in status.items():
        print(
            f"  - {collection}: exists={info.get('exists')}, count={info.get('count')}"
        )

    # 执行变更检测
    print("\n执行变更检测...")
    report = detector.run(sync=False)

    print(f"变更摘要: {report.summary}")

    if report.sources:
        print("\n变更详情:")
        for source, changes in report.sources.items():
            print(f"  [{source}]")
            for change in changes:
                print(f"    - {Path(change.path).name}: {change.change_type}")

    # 输出JSON报告
    print("\n变更报告JSON:")
    print(report.to_json())
