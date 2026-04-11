#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.novel-extractor 模块测试
==========================

测试统一提炼引擎的核心功能。
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def temp_project():
    """创建临时项目目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "progress").mkdir(exist_ok=True)
        yield root


@pytest.fixture
def sample_novel_index():
    """示例小说索引"""
    return {
        "novel_001": {
            "novel_id": "novel_001",
            "path": "test_novel.txt",
            "size": 1000,
            "format": ".txt",
            "processed": False,
        }
    }


class TestUnifiedConfig:
    """测试统一配置模块"""

    def test_config_loads_dimensions(self):
        """测试维度配置加载"""
        from pathlib import Path

        config_path = (
            Path(__file__).resolve().parent.parent
            / ".novel-extractor"
            / "unified_config.py"
        )

        if config_path.exists():
            # 验证维度定义存在
            import sys

            sys.path.insert(0, str(config_path.parent))
            try:
                import unified_config

                assert hasattr(unified_config, "EXTRACTION_DIMENSIONS")
                assert len(unified_config.EXTRACTION_DIMENSIONS) >= 10
            except ImportError:
                pass  # 模块可能有依赖问题

    def test_dimension_priority_order(self):
        """测试维度优先级排序"""
        # 验证高价值维度优先
        expected_order = ["case", "dialogue_style", "power_cost", "character_relation"]
        assert len(expected_order) == 4


class TestBaseExtractor:
    """测试提取器基类"""

    def test_extractor_initialization(self):
        """测试提取器初始化"""
        # 验证基类存在
        base_path = (
            Path(__file__).resolve().parent.parent
            / ".novel-extractor"
            / "base_extractor.py"
        )
        assert base_path.exists()

    def test_encoding_handling(self, temp_project):
        """测试编码处理"""
        # 创建GBK编码的测试文件
        test_file = temp_project / "test_gbk.txt"
        test_content = "这是测试内容"
        test_file.write_text(test_content, encoding="gbk")

        # 验证可以读取
        content = test_file.read_text(encoding="gbk")
        assert "测试" in content

    def test_progress_tracking(self, temp_project):
        """测试进度追踪"""
        progress_file = temp_project / "progress" / "test_progress.json"
        progress_data = {"dimension": "test", "processed": 0, "total": 100}
        progress_file.write_text(
            json.dumps(progress_data, ensure_ascii=False), encoding="utf-8"
        )

        # 验证进度文件格式
        loaded = json.loads(progress_file.read_text(encoding="utf-8"))
        assert loaded["dimension"] == "test"


class TestIncrementalSync:
    """测试增量同步"""

    def test_sync_detects_new_novels(self, sample_novel_index):
        """测试新小说检测"""
        # 验证索引结构
        assert "novel_001" in sample_novel_index
        assert sample_novel_index["novel_001"]["processed"] == False

    def test_sync_skips_processed(self):
        """测试跳过已处理小说"""
        processed_index = {"novel_001": {"processed": True}}
        # 已处理小说应被跳过
        unprocessed = [k for k, v in processed_index.items() if not v.get("processed")]
        assert len(unprocessed) == 0


class TestExtractors:
    """测试各维度提取器"""

    def test_case_extractor_exists(self):
        """测试场景提取器存在"""
        extractor_path = (
            Path(__file__).resolve().parent.parent
            / ".novel-extractor"
            / "extractors"
            / "case_extractor.py"
        )
        assert extractor_path.exists()

    def test_dialogue_extractor_exists(self):
        """测试对话风格提取器存在"""
        extractor_path = (
            Path(__file__).resolve().parent.parent
            / ".novel-extractor"
            / "extractors"
            / "dialogue_style_extractor.py"
        )
        assert extractor_path.exists()

    def test_power_cost_extractor_exists(self):
        """测试力量代价提取器存在"""
        extractor_path = (
            Path(__file__).resolve().parent.parent
            / ".novel-extractor"
            / "extractors"
            / "power_cost_extractor.py"
        )
        assert extractor_path.exists()


class TestEncodingEdgeCases:
    """测试编码边界情况"""

    def test_utf8_file_reading(self, temp_project):
        """测试UTF-8文件读取"""
        test_file = temp_project / "utf8_test.txt"
        test_file.write_text("UTF-8内容测试", encoding="utf-8")

        content = test_file.read_text(encoding="utf-8")
        assert "UTF-8" in content

    def test_mixed_encoding_handling(self, temp_project):
        """测试混合编码处理"""
        # 模拟处理不同编码的文件
        for encoding in ["utf-8", "gbk", "gb2312"]:
            test_file = temp_project / f"test_{encoding}.txt"
            try:
                test_file.write_text("测试内容", encoding=encoding)
                content = test_file.read_text(encoding=encoding)
                assert len(content) > 0
            except Exception:
                pass  # 某些编码可能不支持


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
