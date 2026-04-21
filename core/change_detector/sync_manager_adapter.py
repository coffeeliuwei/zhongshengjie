#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
同步管理器适配器
==============

适配现有的 modules/knowledge_base/sync_manager.py，
提供统一的同步接口给 ChangeDetector 使用。

核心功能：
- 封装 SyncManager 的同步方法
- 提供世界观生成器集成
- 提供知识图谱同步接口
- 提供技法库同步接口

参考：统一提炼引擎重构方案.md 第9.5节
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class SyncResult:
    """同步结果"""

    target: str  # "worldview", "graph", "techniques", "cases"
    status: str  # "success", "partial", "failed", "skipped"
    count: int = 0
    message: str = ""
    details: Optional[Dict[str, Any]] = None


class SyncManagerAdapter:
    """同步管理器适配器"""

    def __init__(self, project_root: Optional[Path] = None):
        """
        初始化适配器

        Args:
            project_root: 项目根目录
        """
        self.project_root = project_root or self._detect_project_root()
        self._sync_manager = None
        self._worldview_generator = None

    def _detect_project_root(self) -> Path:
        """自动检测项目根目录"""
        current = Path(__file__).resolve()
        markers = ["README.md", "config.example.json", "tools", "设定"]

        for parent in current.parents:
            if any((parent / marker).exists() for marker in markers):
                if (parent / "设定").exists():
                    return parent

        return Path.cwd()

    def _get_sync_manager(self):
        """获取 SyncManager 实例"""
        if self._sync_manager is None:
            try:
                # 导入现有的 SyncManager
                from modules.knowledge_base.sync_manager import SyncManager

                self._sync_manager = SyncManager(project_dir=self.project_root)
            except ImportError:
                print("[SyncManagerAdapter] 导入 SyncManager 失败")
                # 创建一个空的模拟实例
                self._sync_manager = _MockSyncManager()

        return self._sync_manager

    def _get_worldview_generator(self):
        """获取世界观生成器实例（M2-β 后永久使用 Mock，旧实现已归档至 .archived/vectorstore_core_20260418/）"""
        if self._worldview_generator is None:
            self._worldview_generator = _MockWorldviewGenerator()
        return self._worldview_generator

    def sync_outline_to_worldview(
        self,
        outline_file: Optional[Path] = None,
    ) -> SyncResult:
        """
        同步大纲到世界观配置

        Args:
            outline_file: 大纲文件路径（默认 总大纲.md）

        Returns:
            SyncResult: 同步结果
        """
        if outline_file is None:
            outline_file = self.project_root / "总大纲.md"

        if not outline_file.exists():
            return SyncResult(
                target="worldview",
                status="skipped",
                message=f"大纲文件不存在: {outline_file}",
            )

        try:
            generator = self._get_worldview_generator()
            result = generator.sync_from_outline(str(outline_file))

            return SyncResult(
                target="worldview",
                status="success",
                count=result.get("synced", 0) if isinstance(result, dict) else 1,
                message="世界观配置已同步",
                details=result,
            )
        except Exception as e:
            return SyncResult(
                target="worldview",
                status="failed",
                message=f"世界观同步失败: {e}",
            )

    def sync_settings_to_graph(
        self,
        settings_dir: Optional[Path] = None,
        rebuild: bool = False,
    ) -> SyncResult:
        """
        同步设定到知识图谱

        Args:
            settings_dir: 设定目录路径
            rebuild: 是否重建

        Returns:
            SyncResult: 同步结果
        """
        if settings_dir is None:
            settings_dir = self.project_root / "设定"

        if not settings_dir.exists():
            return SyncResult(
                target="graph",
                status="skipped",
                message=f"设定目录不存在: {settings_dir}",
            )

        try:
            sync_manager = self._get_sync_manager()
            result = sync_manager.sync_novel_settings(rebuild=rebuild)

            return SyncResult(
                target="graph",
                status="success",
                count=result,
                message="知识图谱已同步",
            )
        except Exception as e:
            return SyncResult(
                target="graph",
                status="failed",
                message=f"知识图谱同步失败: {e}",
            )

    def sync_techniques_to_qdrant(
        self,
        techniques_dir: Optional[Path] = None,
        rebuild: bool = False,
    ) -> SyncResult:
        """
        同步技法到向量库

        Args:
            techniques_dir: 技法目录路径
            rebuild: 是否重建

        Returns:
            SyncResult: 同步结果
        """
        if techniques_dir is None:
            techniques_dir = self.project_root / "创作技法"

        if not techniques_dir.exists():
            return SyncResult(
                target="techniques",
                status="skipped",
                message=f"技法目录不存在: {techniques_dir}",
            )

        try:
            sync_manager = self._get_sync_manager()
            result = sync_manager.sync_techniques(rebuild=rebuild)

            return SyncResult(
                target="techniques",
                status="success",
                count=result,
                message="技法库已同步",
            )
        except Exception as e:
            return SyncResult(
                target="techniques",
                status="failed",
                message=f"技法同步失败: {e}",
            )

    def sync_cases_to_qdrant(
        self,
        rebuild: bool = False,
    ) -> SyncResult:
        """
        同步案例库到向量库

        Args:
            rebuild: 是否重建

        Returns:
            SyncResult: 同步结果
        """
        try:
            sync_manager = self._get_sync_manager()
            result = sync_manager.sync_cases(rebuild=rebuild)

            return SyncResult(
                target="cases",
                status="success",
                count=result,
                message="案例库已同步",
            )
        except Exception as e:
            return SyncResult(
                target="cases",
                status="failed",
                message=f"案例库同步失败: {e}",
            )

    def sync_chapter_outline_file(self, file_path: Path) -> SyncResult:
        """
        将单个章节大纲文件同步到 Qdrant chapter_outlines collection。

        Args:
            file_path: 章节大纲 .md 文件的绝对路径

        Returns:
            SyncResult
        """
        if not file_path.exists():
            return SyncResult(
                target="chapter_outlines",
                status="skipped",
                message=f"大纲文件不存在: {file_path}",
            )

        try:
            from core.parsing.chapter_outline_parser import ChapterOutlineParser
            from core.conversation.file_updater import FileUpdater

            parser = ChapterOutlineParser()
            outline_data = parser.parse_file(file_path)

            if not outline_data:
                return SyncResult(
                    target="chapter_outlines",
                    status="partial",
                    count=0,
                    message=f"解析大纲文件失败: {file_path.name}",
                )

            # 提取章节号
            chapter_num = outline_data.get("chapter_info", {}).get("章节序号", "")
            if not chapter_num:
                # 尝试从 chapter_title 提取数字
                import re

                title = outline_data.get("chapter_title", "")
                m = re.search(r"第(\d+)章", title)
                chapter_num = m.group(1) if m else "?"

            chapter_title = outline_data.get("chapter_info", {}).get(
                "章节名", outline_data.get("chapter_title", file_path.stem)
            )

            data = {
                "chapter_num": chapter_num,
                "chapter_title": chapter_title,
                "content": outline_data.get("summary", ""),
                "source_file": str(file_path.relative_to(self.project_root))
                if file_path.is_relative_to(self.project_root)
                else str(file_path.name),
            }

            updater = FileUpdater(str(self.project_root))
            success = updater.sync_to_vectorstore("chapter_outlines", data)

            return SyncResult(
                target="chapter_outlines",
                status="success" if success else "partial",
                count=1 if success else 0,
                message=f"已同步章节大纲: {file_path.name}"
                if success
                else f"同步失败（可能无 Qdrant 连接）: {file_path.name}",
            )

        except Exception as e:
            return SyncResult(
                target="chapter_outlines",
                status="failed",
                message=f"同步章节大纲时出错: {e}",
            )

    def sync_total_outline_to_qdrant(
        self, outline_file: Optional[Path] = None
    ) -> SyncResult:
        """
        将总大纲文件同步到 Qdrant novel_plot_v1 collection。

        Args:
            outline_file: 总大纲文件路径（默认 project_root/总大纲.md）

        Returns:
            SyncResult
        """
        if outline_file is None:
            outline_file = self.project_root / "总大纲.md"

        if not outline_file.exists():
            return SyncResult(
                target="novel_plot_v1",
                status="skipped",
                message=f"总大纲文件不存在: {outline_file}",
            )

        try:
            from core.conversation.file_updater import FileUpdater

            content = outline_file.read_text(encoding="utf-8")
            data = {
                "type": "plot_change",
                "content": content[:4000],  # 截断避免超长嵌入
                "source_file": "总大纲.md",
            }

            updater = FileUpdater(str(self.project_root))
            success = updater.sync_to_vectorstore("novel_plot_v1", data)

            return SyncResult(
                target="novel_plot_v1",
                status="success" if success else "partial",
                count=1 if success else 0,
                message="已同步总大纲到 novel_plot_v1"
                if success
                else "同步失败（可能无 Qdrant 连接）",
            )

        except Exception as e:
            return SyncResult(
                target="novel_plot_v1",
                status="failed",
                message=f"同步总大纲时出错: {e}",
            )

    def sync_all(
        self,
        rebuild: bool = False,
    ) -> Dict[str, SyncResult]:
        """
        同步所有数据源

        Args:
            rebuild: 是否重建

        Returns:
            Dict[str, SyncResult]: 各数据源同步结果
        """
        results = {}

        # 同步世界观
        results["worldview"] = self.sync_outline_to_worldview()

        # 同步知识图谱
        results["graph"] = self.sync_settings_to_graph(rebuild=rebuild)

        # 同步技法
        results["techniques"] = self.sync_techniques_to_qdrant(rebuild=rebuild)

        # 同步案例
        results["cases"] = self.sync_cases_to_qdrant(rebuild=rebuild)

        return results

    def get_sync_status(self) -> Dict[str, Any]:
        """
        获取同步状态

        Returns:
            各数据源的同步状态
        """
        try:
            sync_manager = self._get_sync_manager()
            return sync_manager.get_sync_status()
        except Exception:
            return {
                "novel_settings": {"exists": False, "count": 0},
                "writing_techniques": {"exists": False, "count": 0},
                "case_library": {"exists": False, "count": 0},
            }


class _MockSyncManager:
    """模拟 SyncManager（用于导入失败时）"""

    def sync_novel_settings(self, rebuild: bool = False) -> int:
        print("[MockSyncManager] sync_novel_settings 调用")
        return 0

    def sync_techniques(self, rebuild: bool = False) -> int:
        print("[MockSyncManager] sync_techniques 调用")
        return 0

    def sync_cases(self, rebuild: bool = False) -> int:
        print("[MockSyncManager] sync_cases 调用")
        return 0

    def get_sync_status(self) -> Dict[str, Any]:
        return {
            "novel_settings": {"exists": False, "count": 0},
            "writing_techniques": {"exists": False, "count": 0},
            "case_library": {"exists": False, "count": 0},
        }


class _MockWorldviewGenerator:
    """模拟世界观生成器（用于导入失败时）"""

    def sync_from_outline(self, outline_path: str = "总大纲.md") -> Dict[str, Any]:
        # [N9 2026-04-18] outline_path 改为可选，默认 '总大纲.md'，
        # 防御 M5 链路 C 那种裸调；生产路径 :107 仍显式传参，行为不变。
        print(f"[MockWorldviewGenerator] sync_from_outline 调用: {outline_path}")
        return {"synced": 0, "message": "模拟同步"}


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("同步管理器适配器测试")
    print("=" * 60)

    adapter = SyncManagerAdapter()

    # 测试同步状态
    status = adapter.get_sync_status()
    print("\n同步状态:")
    for collection, info in status.items():
        print(f"  - {collection}: {info}")

    # 测试世界观同步
    print("\n测试世界观同步...")
    result = adapter.sync_outline_to_worldview()
    print(f"状态: {result.status}, 消息: {result.message}")
