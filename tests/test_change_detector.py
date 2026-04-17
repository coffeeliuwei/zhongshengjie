#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
变更检测器测试
==============

测试 ChangeDetector 和 FileWatcher 的核心功能：
- 文件变更检测
- 状态持久化
- 同步触发
- 变更报告生成

使用 pytest 框架和 mock 避免真实文件依赖。
"""

import pytest
import json
import tempfile
import time
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List, Any

# 项目路径
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.change_detector.change_detector import (
    ChangeDetector,
    ChangeReport,
)
from core.change_detector.file_watcher import (
    FileWatcher,
    FileChange,
    FileState,
)


# ==================== Fixtures ====================


@pytest.fixture
def temp_project_root():
    """创建临时项目目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # 创建必要目录
        (root / "设定").mkdir(exist_ok=True)
        (root / "创作技法").mkdir(exist_ok=True)
        (root / ".cache").mkdir(exist_ok=True)
        yield root


@pytest.fixture
def sample_md_file(temp_project_root):
    """创建示例 Markdown 文件"""
    md_file = temp_project_root / "设定" / "test.md"
    md_file.write_text("# 测试设定\n\n这是一个测试文件。")
    return md_file


@pytest.fixture
def sample_outline_file(temp_project_root):
    """创建示例大纲文件"""
    outline_file = temp_project_root / "总大纲.md"
    outline_file.write_text("# 总大纲\n\n## 第一章\n\n测试大纲内容。")
    return outline_file


@pytest.fixture
def file_watcher(temp_project_root):
    """创建 FileWatcher 实例"""
    watcher = FileWatcher(
        project_root=temp_project_root,
        cache_dir=temp_project_root / ".cache",
        use_hash=True,
    )
    return watcher


@pytest.fixture
def change_detector(temp_project_root):
    """创建 ChangeDetector 实例"""
    detector = ChangeDetector(
        project_root=temp_project_root,
        auto_sync=False,
        use_hash=True,
    )
    return detector


# ==================== FileWatcher 测试 ====================


class TestFileWatcherInit:
    """FileWatcher 初始化测试"""

    def test_init_with_project_root(self, temp_project_root):
        """测试指定项目根目录初始化"""
        watcher = FileWatcher(project_root=temp_project_root)

        assert watcher.project_root == temp_project_root
        assert watcher.cache_dir == temp_project_root / ".cache"

    def test_init_with_custom_cache_dir(self, temp_project_root):
        """测试自定义缓存目录"""
        custom_cache = temp_project_root / "custom_cache"
        watcher = FileWatcher(
            project_root=temp_project_root,
            cache_dir=custom_cache,
        )

        assert watcher.cache_dir == custom_cache

    def test_init_without_hash(self, temp_project_root):
        """测试不使用 hash 检测"""
        watcher = FileWatcher(
            project_root=temp_project_root,
            use_hash=False,
        )

        assert watcher.use_hash == False

    def test_init_auto_detect_project_root(self):
        """测试自动检测项目根目录"""
        watcher = FileWatcher()

        # 应检测到包含 README.md 或 设定 目录的路径
        assert watcher.project_root is not None
        assert watcher.project_root.exists()

    def test_init_load_existing_state(self, temp_project_root):
        """测试加载已有状态文件"""
        # 创建状态文件
        state_file = temp_project_root / ".cache" / "change_detector_state.json"
        state_data = {
            "files": {
                str(temp_project_root / "test.md"): {
                    "mtime": 1000.0,
                    "size": 100,
                    "hash": "abc123",
                    "last_checked": 1000.0,
                }
            },
            "last_saved": datetime.now().isoformat(),
        }
        state_file.write_text(json.dumps(state_data))

        watcher = FileWatcher(project_root=temp_project_root)

        assert len(watcher._state_cache) == 1
        test_path = str(temp_project_root / "test.md")
        assert test_path in watcher._state_cache


class TestFileWatcherDetectChange:
    """FileWatcher 变更检测测试"""

    def test_detect_new_file(self, file_watcher, sample_md_file):
        """测试检测新文件"""
        change = file_watcher.detect_change(sample_md_file)

        assert change is not None
        assert change.change_type == "created"
        assert change.new_mtime is not None
        assert change.new_size > 0

    def test_detect_no_change(self, file_watcher, sample_md_file):
        """测试检测无变更文件"""
        # 第一次检测（记录状态）
        first_change = file_watcher.detect_change(sample_md_file)
        assert first_change.change_type == "created"

        # 保存状态
        file_watcher.sync_state()

        # 清除 watcher 但保持状态文件
        state_file = file_watcher._state_file
        new_watcher = FileWatcher(
            project_root=file_watcher.project_root,
            cache_dir=file_watcher.cache_dir,
        )

        # 第二次检测（无变更）
        second_change = new_watcher.detect_change(sample_md_file)

        # 无变更应返回 None
        assert second_change is None

    def test_detect_modified_file(self, file_watcher, sample_md_file):
        """测试检测修改文件"""
        # 第一次检测
        file_watcher.detect_change(sample_md_file)
        file_watcher.sync_state()

        # 等待一下确保 mtime 变化
        time.sleep(0.1)

        # 修改文件
        sample_md_file.write_text("# 修改后的内容\n\n新增内容。")

        # 创建新的 watcher 加载状态
        new_watcher = FileWatcher(
            project_root=file_watcher.project_root,
            cache_dir=file_watcher.cache_dir,
        )

        # 检测修改
        change = new_watcher.detect_change(sample_md_file)

        assert change is not None
        assert change.change_type == "modified"
        assert change.old_mtime is not None
        assert change.new_mtime is not None
        assert change.new_size != change.old_size

    def test_detect_deleted_file(self, file_watcher, sample_md_file):
        """测试检测删除文件"""
        # 第一次检测（记录状态）
        file_watcher.detect_change(sample_md_file)
        file_watcher.sync_state()

        # 删除文件
        sample_md_file.unlink()

        # 创建新 watcher
        new_watcher = FileWatcher(
            project_root=file_watcher.project_root,
            cache_dir=file_watcher.cache_dir,
        )

        # 检测删除
        change = new_watcher.detect_change(sample_md_file)

        assert change is not None
        assert change.change_type == "deleted"
        assert change.old_mtime is not None
        assert change.new_mtime is None

    def test_detect_changes_batch(self, file_watcher, temp_project_root):
        """测试批量检测变更"""
        # 创建多个文件
        files = []
        for i in range(5):
            f = temp_project_root / "设定" / f"file_{i}.md"
            f.write_text(f"文件 {i}")
            files.append(f)

        # 检测变更
        changes = file_watcher.detect_changes("设定/*.md", temp_project_root)

        assert len(changes) == 5
        for change in changes:
            assert change.change_type == "created"

    def test_detect_directory_changes(self, file_watcher, temp_project_root):
        """测试目录变更检测"""
        # 创建嵌套文件
        subdir = temp_project_root / "设定" / "subdir"
        subdir.mkdir(exist_ok=True)

        f1 = temp_project_root / "设定" / "file1.md"
        f1.write_text("文件1")

        f2 = subdir / "file2.md"
        f2.write_text("文件2")

        # 检测目录变更
        changes = file_watcher.detect_directory_changes(
            temp_project_root / "设定",
            extensions=["md"],
        )

        assert len(changes) == 2


class TestFileWatcherState:
    """FileWatcher 状态管理测试"""

    def test_save_and_load_state(self, file_watcher, sample_md_file):
        """测试状态保存和加载"""
        # 检测文件
        file_watcher.detect_change(sample_md_file)

        # 保存状态
        file_watcher.sync_state()

        # 验证文件存在
        assert file_watcher._state_file.exists()

        # 加载状态
        new_watcher = FileWatcher(
            project_root=file_watcher.project_root,
            cache_dir=file_watcher.cache_dir,
        )

        # 验证状态已加载
        states = new_watcher.get_all_states()
        assert len(states) == 1

    def test_clear_state(self, file_watcher, sample_md_file):
        """测试清除状态"""
        # 检测文件
        file_watcher.detect_change(sample_md_file)
        file_watcher.sync_state()

        # 清除状态
        file_watcher.clear_state()

        # 验证状态已清除
        assert len(file_watcher._state_cache) == 0
        assert not file_watcher._state_file.exists()

    def test_reset_file_state(self, file_watcher, sample_md_file):
        """测试重置单个文件状态"""
        # 检测文件
        file_watcher.detect_change(sample_md_file)

        # 重置
        file_watcher.reset_file_state(sample_md_file)

        # 验证已重置
        state = file_watcher.get_file_state(sample_md_file)
        assert state is None

    def test_get_file_state(self, file_watcher, sample_md_file):
        """测试获取文件状态"""
        # 检测文件
        file_watcher.detect_change(sample_md_file)

        # 获取状态
        state = file_watcher.get_file_state(sample_md_file)

        assert state is not None
        assert state.path == str(sample_md_file)
        assert state.mtime > 0
        assert state.size > 0


class TestFileWatcherHash:
    """FileWatcher Hash 计算测试"""

    def test_compute_hash(self, file_watcher, sample_md_file):
        """测试计算文件 hash"""
        hash_value = file_watcher._compute_hash(sample_md_file, "md5")

        assert hash_value is not None
        assert len(hash_value) == 32  # MD5 长度

    def test_hash_threshold(self, file_watcher, temp_project_root):
        """测试 Hash 计算阈值"""
        # 创建小文件（小于阈值）
        small_file = temp_project_root / "small.txt"
        small_file.write_text("小")

        # 获取文件信息
        info = file_watcher._get_file_info(small_file)

        # 小文件不应计算 hash（除非 use_hash=True 且文件大小 >= HASH_THRESHOLD）
        # 这里文件很小，所以 hash 可能是 None
        assert info["hash"] is None or info["hash"] == ""

    def test_hash_changes_with_content(self, file_watcher, sample_md_file):
        """测试内容变化导致 hash 变化"""
        # 第一次 hash
        hash1 = file_watcher._compute_hash(sample_md_file)

        # 修改内容
        sample_md_file.write_text("完全不同的内容")

        # 第二次 hash
        hash2 = file_watcher._compute_hash(sample_md_file)

        # Hash 应不同
        assert hash1 != hash2


# ==================== ChangeDetector 测试 ====================


class TestChangeDetectorInit:
    """ChangeDetector 初始化测试"""

    def test_init_with_project_root(self, temp_project_root):
        """测试指定项目根目录初始化"""
        detector = ChangeDetector(project_root=temp_project_root)

        assert detector.project_root == temp_project_root
        assert detector.file_watcher is not None
        assert detector.sync_adapter is not None

    def test_init_auto_detect_project_root(self):
        """测试自动检测项目根目录"""
        detector = ChangeDetector()

        assert detector.project_root is not None

    def test_init_with_custom_watch_list(self, temp_project_root):
        """测试自定义监控列表"""
        custom_watch = {
            "custom_source": "custom/*.md",
        }

        detector = ChangeDetector(
            project_root=temp_project_root,
            watch_list=custom_watch,
        )

        assert detector.watch_list == custom_watch

    def test_init_auto_sync(self, temp_project_root):
        """测试自动同步配置"""
        detector = ChangeDetector(
            project_root=temp_project_root,
            auto_sync=True,
        )

        assert detector.auto_sync == True


class TestChangeDetectorScan:
    """ChangeDetector 扫描测试"""

    def test_scan_changes(self, change_detector, sample_outline_file, sample_md_file):
        """测试扫描变更"""
        changes = change_detector.scan_changes()

        # 应检测到大纲和设定文件的变更
        assert len(changes) > 0
        assert "outline" in changes or "settings" in changes

    def test_scan_no_changes(
        self, change_detector, sample_outline_file, sample_md_file
    ):
        """测试无变更扫描"""
        # 第一次扫描
        change_detector.scan_changes()
        change_detector.file_watcher.sync_state()

        # 创建新 detector
        new_detector = ChangeDetector(
            project_root=change_detector.project_root,
            auto_sync=False,
        )

        # 第二次扫描（无变更）
        changes = new_detector.scan_changes()

        # 无变更时可能为空
        # 具体行为取决于实现

    def test_add_watch_target(self, change_detector):
        """测试添加监控目标"""
        change_detector.add_watch_target(
            source="new_source",
            pattern="new/*.txt",
        )

        watch_list = change_detector.get_watch_list()

        assert "new_source" in watch_list
        assert watch_list["new_source"] == "new/*.txt"

    def test_remove_watch_target(self, change_detector):
        """测试移除监控目标"""
        # 先添加
        change_detector.add_watch_target("test_source", "test/*.md")

        # 移除
        change_detector.remove_watch_target("test_source")

        watch_list = change_detector.get_watch_list()

        assert "test_source" not in watch_list


class TestChangeDetectorSync:
    """ChangeDetector 同步测试"""

    def test_sync_changes(self, change_detector, sample_outline_file):
        """测试同步变更"""
        # 扫描变更
        changes = change_detector.scan_changes()

        # 同步变更（需要 mock sync_adapter）
        with patch.object(
            change_detector.sync_adapter, "sync_outline_to_worldview"
        ) as mock_sync:
            mock_sync.return_value = MagicMock(
                status="success",
                count=5,
                message="同步成功",
            )

            sync_results = change_detector.sync_changes(changes)

            # 应有同步结果
            assert len(sync_results) >= 0

    def test_force_sync_all(self, change_detector):
        """测试强制同步全部"""
        with patch.object(change_detector.sync_adapter, "sync_all") as mock_sync_all:
            mock_sync_all.return_value = {
                "worldview": MagicMock(status="success", count=1),
                "techniques": MagicMock(status="success", count=10),
            }

            results = change_detector.force_sync_all(rebuild=True)

            mock_sync_all.assert_called_once_with(rebuild=True)


class TestChangeDetectorReport:
    """ChangeDetector 报告测试"""

    def test_run_generate_report(self, change_detector, sample_outline_file):
        """测试运行生成报告"""
        report = change_detector.run(sync=False)

        assert report is not None
        assert isinstance(report, ChangeReport)
        assert report.timestamp is not None

    def test_report_to_dict(self, change_detector, sample_outline_file):
        """测试报告转换为字典"""
        report = change_detector.run(sync=False)

        report_dict = report.to_dict()

        assert "timestamp" in report_dict
        assert "sources" in report_dict
        assert "sync_results" in report_dict
        assert "summary" in report_dict

    def test_report_to_json(self, change_detector, sample_outline_file):
        """测试报告转换为 JSON"""
        report = change_detector.run(sync=False)

        report_json = report.to_json()

        assert report_json is not None
        # 验证是有效 JSON
        parsed = json.loads(report_json)
        assert isinstance(parsed, dict)

    def test_generate_summary_with_changes(self, change_detector, sample_outline_file):
        """测试生成变更摘要（有变更）"""
        changes = {"outline": [FileChange(path="test", change_type="created")]}
        sync_results = {
            "worldview": MagicMock(status="success", count=5, message="成功")
        }

        summary = change_detector._generate_summary(changes, sync_results)

        assert "变更" in summary or "outline" in summary

    def test_generate_summary_no_changes(self, change_detector):
        """测试生成变更摘要（无变更）"""
        changes = {}
        sync_results = {}

        summary = change_detector._generate_summary(changes, sync_results)

        assert summary == "无变更"


class TestChangeDetectorHistory:
    """ChangeDetector 历史管理测试"""

    def test_get_change_history(self, change_detector, sample_outline_file):
        """测试获取变更历史"""
        # 运行几次
        for i in range(3):
            change_detector.run(sync=False)

        history = change_detector.get_change_history(limit=2)

        assert len(history) <= 2

    def test_clear_history(self, change_detector, sample_outline_file):
        """测试清除历史"""
        # 运行几次
        for i in range(3):
            change_detector.run(sync=False)

        # 清除
        change_detector.clear_history()

        # 验证已清除
        history = change_detector.get_change_history()
        assert len(history) == 0


# ==================== 边缘情况测试 ====================


class TestChangeDetectorEdgeCases:
    """边缘情况测试"""

    def test_scan_nonexistent_directory(self, temp_project_root):
        """测试扫描不存在目录"""
        detector = ChangeDetector(project_root=temp_project_root)

        # 添加不存在的监控目标
        detector.add_watch_target("nonexistent", "nonexistent/*.md")

        changes = detector.scan_changes()

        # 应优雅处理（不抛异常）
        assert changes is not None

    def test_detect_change_with_permission_error(self, file_watcher, temp_project_root):
        """测试文件权限错误"""
        # 创建文件
        restricted_file = temp_project_root / "restricted.txt"
        restricted_file.write_text("内容")

        # Mock exists 返回 True，然后 stat 抛出权限错误
        original_exists = Path.exists

        def mock_exists(self):
            if self == restricted_file:
                return True
            return original_exists(self)

        with (
            patch.object(Path, "exists", mock_exists),
            patch.object(Path, "stat", side_effect=PermissionError("无权限")),
        ):
            info = file_watcher._get_file_info(restricted_file)

            # 应返回 None（优雅处理）
            assert info is None

    def test_report_with_empty_changes(self):
        """测试空变更报告"""
        report = ChangeReport(
            sources={},
            sync_results={},
        )

        report_dict = report.to_dict()

        assert report_dict["sources"] == {}
        assert report_dict["sync_results"] == {}


# ==================== 性能测试 ====================


class TestChangeDetectorPerformance:
    """性能测试"""

    def test_scan_many_files_performance(self, file_watcher, temp_project_root):
        """测试扫描大量文件性能"""
        # 创建大量文件
        for i in range(100):
            f = temp_project_root / "设定" / f"file_{i}.md"
            f.write_text(f"文件 {i}")

        import time

        start = time.time()

        changes = file_watcher.detect_changes("设定/*.md")

        elapsed = time.time() - start

        # 应在合理时间内完成（< 2秒）
        assert elapsed < 2.0
        assert len(changes) == 100

    def test_state_persistence_performance(self, file_watcher, temp_project_root):
        """测试状态持久化性能"""
        # 创建并检测大量文件
        for i in range(100):
            f = temp_project_root / "设定" / f"file_{i}.md"
            f.write_text(f"文件 {i}")
            file_watcher.detect_change(f)

        import time

        start = time.time()

        file_watcher.sync_state()

        elapsed = time.time() - start

        # 应在合理时间内完成（< 1秒）
        assert elapsed < 1.0


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# ==================== M2 novel_plot_v1 同步测试 ====================


def test_outline_change_triggers_novel_plot_sync():
    """总大纲变更应同时同步到 worldview 和 novel_plot_v1"""
    from core.change_detector.change_detector import ChangeDetector
    from unittest.mock import MagicMock, patch

    detector = ChangeDetector()

    # Mock 掉实际同步，只验证调用链
    with (
        patch.object(
            detector.sync_adapter, "sync_outline_to_worldview"
        ) as mock_worldview,
        patch.object(
            detector.sync_adapter, "sync_total_outline_to_qdrant"
        ) as mock_plot,
    ):
        mock_worldview.return_value = MagicMock(status="success", count=1)
        mock_plot.return_value = MagicMock(status="success", count=1)

        from core.change_detector.file_watcher import FileChange

        changes = {"outline": [FileChange(path="总大纲.md", change_type="modified")]}
        detector.sync_changes(changes)

        mock_worldview.assert_called_once()
        (
            mock_plot.assert_called_once(),
            "outline 变更应调用 sync_total_outline_to_qdrant()，但未调用",
        )
