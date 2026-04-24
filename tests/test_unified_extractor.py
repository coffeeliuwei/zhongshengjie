#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一提炼引擎测试
================

测试 UnifiedExtractor 的核心功能：
- 初始化测试
- 提取功能测试
- 状态管理测试
- 并行提取测试

使用 pytest 框架和 mock 避免真实数据依赖。
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from typing import Dict, Any

# 项目路径
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ==================== Fixtures ====================


@pytest.fixture
def temp_project_root():
    """创建临时项目目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # 创建必要的目录结构
        (root / ".novel-extractor").mkdir(parents=True, exist_ok=True)
        (root / "tools").mkdir(exist_ok=True)
        yield root


@pytest.fixture
def mock_progress_file(temp_project_root):
    """创建模拟的进度文件"""
    progress_file = temp_project_root / ".novel-extractor" / "unified_progress.json"
    progress_data = {
        "started_at": "2025-01-01T10:00:00",
        "finished_at": "2025-01-01T12:00:00",
        "status": "completed",
        "force_mode": False,
        "novels_scanned": 10,
        "novels_new": 2,
        "novels_modified": 3,
        "total_items_extracted": 100,
        "scene_discovery_count": 5,
        "dimensions": {
            "case": {
                "dimension_id": "case",
                "status": "completed",
                "start_time": "2025-01-01T10:00:00",
                "end_time": "2025-01-01T11:00:00",
                "items_extracted": 50,
                "novels_processed": 10,
            }
        },
    }
    progress_file.write_text(json.dumps(progress_data, ensure_ascii=False))
    return progress_file


@pytest.fixture
def mock_unified_config():
    """模拟 unified_config 模块"""
    mock_config = MagicMock()

    # 创建模拟的维度配置
    mock_dim = MagicMock()
    mock_dim.name = "测试维度"
    mock_dim.category = MagicMock()
    mock_dim.category.value = "core"

    mock_config.EXTRACTION_DIMENSIONS = {
        "case": mock_dim,
        "technique": mock_dim,
        "dialogue_style": mock_dim,
    }

    mock_config.DimensionCategory = MagicMock()
    mock_config.DimensionCategory.CORE = MagicMock()
    mock_config.DimensionCategory.HIGH = MagicMock()

    mock_config.init_system = MagicMock()
    mock_config.get_output_path = MagicMock(return_value=Path("/tmp/output"))
    mock_config.get_progress_path = MagicMock(return_value=Path("/tmp/progress.json"))

    return mock_config


@pytest.fixture
def mock_extractor_class():
    """模拟提取器类"""
    extractor = MagicMock()
    extractor.run = MagicMock(
        return_value={
            "items_extracted": 10,
            "novels_processed": 5,
        }
    )
    return extractor


# ==================== 初始化测试 ====================


class TestUnifiedExtractorInit:
    """初始化测试"""

    def test_init_with_default_config(self, temp_project_root):
        """测试默认配置初始化"""
        with patch("tools.unified_extractor.PROJECT_ROOT", temp_project_root), \
             patch("tools.unified_extractor.HAS_CONFIG_LOADER", False):
            from tools.unified_extractor import UnifiedExtractor

            extractor = UnifiedExtractor()

            assert extractor.project_root == temp_project_root
            assert (
                extractor.progress_file
                == temp_project_root / ".novel-extractor" / "unified_progress.json"
            )
            assert extractor.progress is not None

    def test_init_with_custom_config(self, temp_project_root):
        """测试自定义配置初始化"""
        custom_config = {
            "workers": 8,
            "timeout": 30,
        }

        with patch("tools.unified_extractor.PROJECT_ROOT", temp_project_root):
            from tools.unified_extractor import UnifiedExtractor

            extractor = UnifiedExtractor(config=custom_config)

            assert extractor.config == custom_config

    def test_init_load_existing_progress(self, temp_project_root, mock_progress_file):
        """测试加载已有进度"""
        with patch("tools.unified_extractor.PROJECT_ROOT", temp_project_root), \
             patch("tools.unified_extractor.HAS_CONFIG_LOADER", False):
            from tools.unified_extractor import UnifiedExtractor

            extractor = UnifiedExtractor()

            assert extractor.progress.started_at == "2025-01-01T10:00:00"
            assert extractor.progress.status == "completed"
            assert extractor.progress.novels_scanned == 10
            assert "case" in extractor.progress.dimensions

    def test_init_without_progress_file(self, temp_project_root):
        """测试无进度文件时的初始化"""
        # 不创建进度文件
        with patch("tools.unified_extractor.PROJECT_ROOT", temp_project_root), \
             patch("tools.unified_extractor.HAS_CONFIG_LOADER", False):
            from tools.unified_extractor import UnifiedExtractor

            extractor = UnifiedExtractor()

            assert extractor.progress.status == "idle"
            assert extractor.progress.dimensions == {}


# ==================== 提取功能测试 ====================


class TestUnifiedExtractorExtract:
    """提取功能测试"""

    @patch("tools.unified_extractor.HAS_UNIFIED_CONFIG", True)
    @patch("tools.unified_extractor.EXTRACTION_DIMENSIONS")
    def test_extract_single_dimension(
        self, temp_project_root, mock_unified_config, mock_extractor_class
    ):
        """测试单个维度提取"""
        # 设置模拟的维度配置
        mock_dimensions = {
            "case": MagicMock(name="案例库", category=MagicMock(value="core"))
        }

        with patch("tools.unified_extractor.PROJECT_ROOT", temp_project_root):
            from tools.unified_extractor import UnifiedExtractor

            extractor = UnifiedExtractor()

            # 模拟 _create_extractor 返回提取器实例
            with patch.object(
                extractor, "_create_extractor", return_value=mock_extractor_class
            ):
                result = extractor.extract_dimension("case", force=False, limit=5)

                assert result["status"] == "completed"
                assert result["dimension_id"] == "case"
                assert result["items_extracted"] == 10

    @patch("tools.unified_extractor.HAS_UNIFIED_CONFIG", True)
    def test_extract_dimension_not_found(self, temp_project_root):
        """测试未知维度提取"""
        with patch("tools.unified_extractor.EXTRACTION_DIMENSIONS", {}):
            with patch("tools.unified_extractor.PROJECT_ROOT", temp_project_root):
                from tools.unified_extractor import UnifiedExtractor

                extractor = UnifiedExtractor()
                result = extractor.extract_dimension("unknown_dimension")

                assert result["status"] == "failed"
                assert "未知维度" in result["error"]

    @patch("tools.unified_extractor.HAS_UNIFIED_CONFIG", True)
    def test_extract_dimension_extractor_failed(self, temp_project_root):
        """测试提取器创建失败"""
        mock_dimensions = {
            "case": MagicMock(name="案例库", category=MagicMock(value="core"))
        }

        with patch("tools.unified_extractor.EXTRACTION_DIMENSIONS", mock_dimensions):
            with patch("tools.unified_extractor.PROJECT_ROOT", temp_project_root):
                from tools.unified_extractor import UnifiedExtractor

                extractor = UnifiedExtractor()

                # 模拟无法创建提取器
                with patch.object(extractor, "_create_extractor", return_value=None):
                    result = extractor.extract_dimension("case")

                    assert result["status"] == "skipped"
                    assert "无法创建提取器" in result["error"]

    @patch("tools.unified_extractor.HAS_UNIFIED_CONFIG", True)
    def test_extract_dimension_with_exception(self, temp_project_root):
        """测试提取过程中异常处理"""
        mock_dimensions = {
            "case": MagicMock(name="案例库", category=MagicMock(value="core"))
        }

        mock_extractor = MagicMock()
        mock_extractor.run = MagicMock(side_effect=Exception("提取失败"))

        with patch("tools.unified_extractor.EXTRACTION_DIMENSIONS", mock_dimensions):
            with patch("tools.unified_extractor.PROJECT_ROOT", temp_project_root):
                from tools.unified_extractor import UnifiedExtractor

                extractor = UnifiedExtractor()

                with patch.object(
                    extractor, "_create_extractor", return_value=mock_extractor
                ):
                    result = extractor.extract_dimension("case")

                    assert result["status"] == "failed"
                    assert "提取失败" in result["error"]


# ==================== 状态管理测试 ====================


class TestUnifiedExtractorStatus:
    """状态管理测试"""

    def test_get_status(self, temp_project_root, mock_progress_file):
        """测试获取状态"""
        with patch("tools.unified_extractor.PROJECT_ROOT", temp_project_root):
            with patch("tools.unified_extractor.HAS_UNIFIED_CONFIG", True):
                from tools.unified_extractor import UnifiedExtractor

                extractor = UnifiedExtractor()
                status = extractor.get_status()

                assert "progress" in status
                assert "dimensions" in status
                assert status["progress"]["status"] == "completed"

    def test_save_progress(self, temp_project_root):
        """测试保存进度"""
        from tools.unified_extractor import UnifiedProgress, ExtractionTask

        with patch("tools.unified_extractor.PROJECT_ROOT", temp_project_root):
            from tools.unified_extractor import UnifiedExtractor

            extractor = UnifiedExtractor()

            # 更新进度
            extractor.progress.status = "running"
            extractor.progress.novels_scanned = 5
            extractor.progress.dimensions["test"] = ExtractionTask(
                dimension_id="test",
                status="completed",
                items_extracted=10,
            )

            # 保存
            extractor._save_progress()

            # 验证文件存在
            assert extractor.progress_file.exists()

            # 加载验证
            with open(extractor.progress_file, "r", encoding="utf-8") as f:
                saved_data = json.load(f)

            assert saved_data["status"] == "running"
            assert saved_data["novels_scanned"] == 5
            assert "test" in saved_data["dimensions"]

    def test_determine_final_status_all_completed(self, temp_project_root):
        """测试最终状态判定 - 全部完成"""
        with patch("tools.unified_extractor.PROJECT_ROOT", temp_project_root):
            from tools.unified_extractor import UnifiedExtractor

            extractor = UnifiedExtractor()

            results = {
                "dim1": {"status": "completed"},
                "dim2": {"status": "completed"},
            }

            status = extractor._determine_final_status(results)
            assert status == "completed"

    def test_determine_final_status_partial(self, temp_project_root):
        """测试最终状态判定 - 部分完成"""
        with patch("tools.unified_extractor.PROJECT_ROOT", temp_project_root):
            from tools.unified_extractor import UnifiedExtractor

            extractor = UnifiedExtractor()

            results = {
                "dim1": {"status": "completed"},
                "dim2": {"status": "failed"},
            }

            status = extractor._determine_final_status(results)
            assert status == "partial"

    def test_determine_final_status_all_failed(self, temp_project_root):
        """测试最终状态判定 - 全部失败"""
        with patch("tools.unified_extractor.PROJECT_ROOT", temp_project_root):
            from tools.unified_extractor import UnifiedExtractor

            extractor = UnifiedExtractor()

            results = {
                "dim1": {"status": "failed"},
                "dim2": {"status": "failed"},
            }

            status = extractor._determine_final_status(results)
            assert status == "failed"

    def test_determine_final_status_empty(self, temp_project_root):
        """测试最终状态判定 - 无结果"""
        with patch("tools.unified_extractor.PROJECT_ROOT", temp_project_root):
            from tools.unified_extractor import UnifiedExtractor

            extractor = UnifiedExtractor()

            status = extractor._determine_final_status({})
            assert status == "failed"


# ==================== 并行提取测试 ====================


class TestUnifiedExtractorParallel:
    """并行提取测试"""

    @pytest.mark.parametrize("workers", [1, 2, 4, 8])
    def test_parallel_extraction_workers(self, temp_project_root, workers):
        """测试不同并行数"""
        mock_dimensions = {
            "dim1": MagicMock(name="维度1", category=MagicMock(value="core")),
            "dim2": MagicMock(name="维度2", category=MagicMock(value="high")),
        }

        mock_extractor = MagicMock()
        mock_extractor.run = MagicMock(
            return_value={
                "items_extracted": 10,
                "novels_processed": 5,
            }
        )

        with patch("tools.unified_extractor.EXTRACTION_DIMENSIONS", mock_dimensions):
            with patch("tools.unified_extractor.HAS_UNIFIED_CONFIG", True):
                with patch("tools.unified_extractor.PROJECT_ROOT", temp_project_root):
                    from tools.unified_extractor import UnifiedExtractor

                    extractor = UnifiedExtractor()

                    # 模拟并行提取
                    with patch.object(
                        extractor, "_create_extractor", return_value=mock_extractor
                    ):
                        with patch.object(
                            extractor, "_run_parallel_extraction"
                        ) as mock_parallel:
                            mock_parallel.return_value = {
                                "dim1": {"status": "completed", "items_extracted": 10},
                                "dim2": {"status": "completed", "items_extracted": 10},
                            }

                            # 调用时应该传递 workers 参数
                            result = extractor.extract(
                                dimensions=["dim1", "dim2"],
                                workers=workers,
                                limit=5,
                            )

                            # 验证并行提取被调用
                            mock_parallel.assert_called_once()
                            call_args = mock_parallel.call_args
                            assert call_args[1]["workers"] == workers

    def test_parallel_extraction_priority_order(self, temp_project_root):
        """测试并行提取的优先级排序"""
        from tools.unified_extractor import DIMENSION_PRIORITY

        # 验证优先级配置存在
        assert "case" in DIMENSION_PRIORITY
        assert DIMENSION_PRIORITY["case"] == 1  # 最高优先级

        # 模拟维度列表
        dimensions = ["technique", "case", "dialogue_style"]

        # 按优先级排序
        sorted_dims = sorted(dimensions, key=lambda d: DIMENSION_PRIORITY.get(d, 99))

        # case 应排在第一位
        assert sorted_dims[0] == "case"


# ==================== 边缘情况测试 ====================


class TestUnifiedExtractorEdgeCases:
    """边缘情况测试"""

    def test_extract_with_none_dimensions(self, temp_project_root):
        """测试维度参数为 None"""
        with patch("tools.unified_extractor.HAS_UNIFIED_CONFIG", False):
            with patch("tools.unified_extractor.PROJECT_ROOT", temp_project_root):
                from tools.unified_extractor import UnifiedExtractor

                extractor = UnifiedExtractor()

                # HAS_UNIFIED_CONFIG 为 False 时，应该跳过或返回错误
                # 具体行为取决于实现

    def test_progress_to_dict(self):
        """测试进度转换为字典"""
        from tools.unified_extractor import UnifiedProgress, ExtractionTask

        progress = UnifiedProgress()
        progress.status = "running"
        progress.novels_scanned = 10
        progress.dimensions["test"] = ExtractionTask(
            dimension_id="test",
            status="completed",
            items_extracted=5,
        )

        result = progress.to_dict()

        assert result["status"] == "running"
        assert result["novels_scanned"] == 10
        assert "test" in result["dimensions"]
        assert isinstance(result["dimensions"]["test"], dict)

    def test_extraction_task_dataclass(self):
        """测试 ExtractionTask 数据类"""
        from tools.unified_extractor import ExtractionTask

        task = ExtractionTask(
            dimension_id="test",
            status="completed",
            start_time="2025-01-01T10:00:00",
            end_time="2025-01-01T11:00:00",
            items_extracted=50,
            novels_processed=10,
        )

        assert task.dimension_id == "test"
        assert task.status == "completed"
        assert task.items_extracted == 50

    def test_calculate_duration(self, temp_project_root):
        """测试执行时长计算"""
        from tools.unified_extractor import UnifiedExtractor

        with patch("tools.unified_extractor.PROJECT_ROOT", temp_project_root):
            extractor = UnifiedExtractor()

            # 设置时间
            extractor.progress.started_at = "2025-01-01T10:00:00"
            extractor.progress.finished_at = "2025-01-01T12:30:45"

            duration = extractor._calculate_duration()

            # 应返回格式化的时长
            assert duration != "unknown"
            assert "h" in duration or "m" in duration

    def test_calculate_duration_missing_time(self, temp_project_root):
        """测试缺少时间时的时长计算"""
        from tools.unified_extractor import UnifiedExtractor

        with patch("tools.unified_extractor.PROJECT_ROOT", temp_project_root), \
             patch("tools.unified_extractor.HAS_CONFIG_LOADER", False):
            extractor = UnifiedExtractor()
            # 确保进度时间为空
            extractor.progress.started_at = ""
            extractor.progress.finished_at = ""

            # 不设置时间
            duration = extractor._calculate_duration()

            assert duration == "unknown"


# ==================== 性能测试 ====================


class TestUnifiedExtractorPerformance:
    """性能测试"""

    def test_progress_save_performance(self, temp_project_root):
        """测试进度保存性能"""
        from tools.unified_extractor import UnifiedProgress, ExtractionTask

        with patch("tools.unified_extractor.PROJECT_ROOT", temp_project_root):
            from tools.unified_extractor import UnifiedExtractor

            extractor = UnifiedExtractor()

            # 创建大量维度
            for i in range(100):
                extractor.progress.dimensions[f"dim_{i}"] = ExtractionTask(
                    dimension_id=f"dim_{i}",
                    status="completed",
                    items_extracted=i,
                )

            import time

            start = time.time()
            extractor._save_progress()
            elapsed = time.time() - start

            # 应在合理时间内完成（< 1秒）
            assert elapsed < 1.0

    def test_memory_usage_with_large_progress(self, temp_project_root):
        """测试大量进度数据的内存使用"""
        from tools.unified_extractor import UnifiedProgress, ExtractionTask

        progress = UnifiedProgress()

        # 创建大量数据
        for i in range(1000):
            progress.dimensions[f"dim_{i}"] = ExtractionTask(
                dimension_id=f"dim_{i}",
                items_extracted=i * 10,
            )

        # 转换为字典不应导致内存问题
        result = progress.to_dict()

        assert len(result["dimensions"]) == 1000


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
